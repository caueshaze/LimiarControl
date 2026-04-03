from __future__ import annotations

from datetime import datetime, timezone
import random
from math import floor

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select

from app.models.base_item import BaseItemKind, BaseItemWeaponRangeType
from app.models.campaign import Campaign, SystemType
from app.models.combat import CombatPhase, CombatState
from app.models.session import Session as CampaignSession
from app.models.session_entity import SessionEntity
from app.models.session_state import SessionState
from app.models.campaign_entity import CampaignEntity
from app.models.inventory import InventoryItem
from app.models.item import Item, ItemType
from app.schemas.combat import (
    CombatApplyDamageRequest,
    CombatApplyHealingRequest,
    CombatAttackRequest,
    CombatCastSpellRequest,
    CombatEntityActionRequest,
    CombatSetInitiativeRequest,
    CombatStartRequest,
)
from app.schemas.campaign_entity import (
    SKILL_ABILITY_MAP,
    CombatAction,
    ability_modifier as derive_ability_modifier,
    resolve_initiative_bonus as resolve_entity_initiative_bonus,
    resolve_saving_throw_bonus as resolve_entity_saving_throw_bonus,
    resolve_skill_bonus as resolve_entity_skill_bonus,
)
from app.services.base_items import get_base_item_by_canonical_key
from app.services.base_spells import get_base_spell_by_canonical_key
from app.services.centrifugo import centrifugo
from app.services.realtime import build_event, campaign_channel, event_version, session_channel
from app.services.session_state_finalize import finalize_session_state_data

from .exceptions import CombatServiceError, _roll_dice_expression


class CombatStatusMixin:
    @classmethod
    def _normalize_player_death_saves(cls, death_saves: dict | None) -> dict[str, int]:
        source = cls._as_dict(death_saves)
        return {
            "successes": min(3, max(0, cls._safe_int(source.get("successes"), 0))),
            "failures": min(3, max(0, cls._safe_int(source.get("failures"), 0))),
        }

    @classmethod
    def _is_player_dead_state(cls, data: dict | None) -> bool:
        normalized_data = cls._as_dict(data)
        current_hp = max(0, cls._safe_int(normalized_data.get("currentHP"), 0))
        death_saves = cls._normalize_player_death_saves(normalized_data.get("deathSaves"))
        return current_hp <= 0 and death_saves["failures"] >= 3

    @classmethod
    def _sync_participant_status(
        cls,
        db: Session,
        state: CombatState | None,
        target_ref_id: str,
        kind: str,
        target_model,
    ) -> str:
        participant = cls._get_participant_by_ref(state, target_ref_id)
        previous_status = participant.get("status") if isinstance(participant, dict) else None

        if kind == "player":
            data = cls._as_dict(target_model.state_json)
            current_hp = max(0, cls._safe_int(data.get("currentHP"), 0))
            normalized_death_saves = cls._normalize_player_death_saves(data.get("deathSaves"))

            if current_hp > 0:
                normalized_death_saves = {"successes": 0, "failures": 0}
                status = "active"
            elif normalized_death_saves["failures"] >= 3:
                status = "dead"
            elif normalized_death_saves["successes"] >= 3:
                status = "stable"
            else:
                status = "downed"

            data["currentHP"] = current_hp
            data["deathSaves"] = normalized_death_saves
            target_model.state_json = finalize_session_state_data(data)

            if participant:
                participant["status"] = status
                if status != "active" and previous_status != status:
                    cls._clear_concentration_for_participant_status(
                        state,
                        source_participant_id=participant.get("id"),
                    )

            return status

        current_hp = target_model.current_hp
        if current_hp is None:
            npc = db.exec(
                select(CampaignEntity).where(CampaignEntity.id == target_model.campaign_entity_id)
            ).first()
            current_hp = npc.max_hp if npc and npc.max_hp is not None else 0

        current_hp = max(0, current_hp)
        target_model.current_hp = current_hp
        status = "active" if current_hp > 0 else "defeated"

        if participant:
            participant["status"] = status
            if status != "active" and previous_status != status:
                cls._clear_concentration_for_participant_status(
                    state,
                    source_participant_id=participant.get("id"),
                )

        return status

    @classmethod
    def sync_participant_status_for_session(
        cls,
        db: Session,
        session_id: str,
        target_ref_id: str,
        kind: str,
    ) -> CombatState | None:
        state = cls.get_state(db, session_id)
        if not state or state.phase == CombatPhase.ended:
            return state

        target_model, *_ = cls._get_stats(db, target_ref_id, kind, session_id)
        cls._sync_participant_status(db, state, target_ref_id, kind, target_model)
        if kind == "player":
            flag_modified(target_model, "state_json")
        db.add(target_model)
        flag_modified(state, "participants")
        db.add(state)
        return state

    @classmethod
    def _sync_all_participant_statuses(cls, db: Session, state: CombatState):
        if not state.participants:
            return

        for participant in state.participants:
            target_model, *_ = cls._get_stats(db, participant["ref_id"], participant["kind"], state.session_id)
            cls._sync_participant_status(
                db,
                state,
                participant["ref_id"],
                participant["kind"],
                target_model,
            )
            if participant["kind"] == "player":
                flag_modified(target_model, "state_json")
            db.add(target_model)

        flag_modified(state, "participants")
        db.add(state)
