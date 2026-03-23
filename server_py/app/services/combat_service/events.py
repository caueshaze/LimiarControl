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

from .exceptions import CombatServiceError, _roll_dice_expression


class CombatEventsMixin:

    @classmethod
    def _get_current_participant(cls, state: CombatState) -> dict:
        if not state.participants:
            raise CombatServiceError("No participants in combat")
        if state.current_turn_index < 0 or state.current_turn_index >= len(state.participants):
            raise CombatServiceError("Current turn index is invalid")
        return state.participants[state.current_turn_index]

    @classmethod
    def _get_participant_by_ref(cls, state: CombatState | None, ref_id: str) -> dict | None:
        if not state:
            return None
        return next((p for p in state.participants if p.get("ref_id") == ref_id), None)

    @classmethod
    def _reset_death_saves(cls, data: dict):
        data["deathSaves"] = {"successes": 0, "failures": 0}

    @classmethod
    async def _emit_state(cls, session_id: str, state: CombatState):
        channel = session_channel(session_id)
        payload = {
            "id": state.id,
            "session_id": state.session_id,
            "phase": state.phase.value,
            "round": state.round,
            "current_turn_index": state.current_turn_index,
            "participants": state.participants,
        }
        event = build_event("combat_state_updated", payload)
        await centrifugo.publish(channel, event)

    @classmethod
    async def _emit_log(cls, session_id: str, log_payload: dict):
        channel = session_channel(session_id)
        event = build_event("combat_log_added", log_payload)
        await centrifugo.publish(channel, event)

    @classmethod
    def _get_session_entry(cls, db: Session, session_id: str) -> CampaignSession | None:
        return db.exec(select(CampaignSession).where(CampaignSession.id == session_id)).first()

    @classmethod
    def _get_campaign_system_for_session(cls, db: Session, session_id: str) -> SystemType:
        entry = cls._get_session_entry(db, session_id)
        if not entry:
            raise CombatServiceError("Session not found", 404)
        campaign = db.exec(select(Campaign).where(Campaign.id == entry.campaign_id)).first()
        if not campaign:
            raise CombatServiceError("Campaign not found", 404)
        return campaign.system

    @classmethod
    def _get_campaign_item_for_session(cls, db: Session, session_id: str, item_id: str) -> Item:
        entry = cls._get_session_entry(db, session_id)
        if not entry:
            raise CombatServiceError("Session not found", 404)
        item = db.exec(
            select(Item).where(
                Item.id == item_id,
                Item.campaign_id == entry.campaign_id,
            )
        ).first()
        if not item:
            raise CombatServiceError("Referenced campaign item was not found.", 404)
        return item

    @classmethod
    async def _emit_player_state_update(
        cls,
        db: Session,
        session_id: str,
        player_user_id: str,
        state_model: SessionState,
    ):
        entry = cls._get_session_entry(db, session_id)
        if not entry:
            return
        timestamp = state_model.updated_at or state_model.created_at or datetime.now(timezone.utc)
        event = build_event(
            "session_state_updated",
            {
                "sessionId": entry.id,
                "campaignId": entry.campaign_id,
                "partyId": entry.party_id,
                "playerUserId": player_user_id,
                "state": state_model.state_json if isinstance(state_model.state_json, dict) else None,
            },
            version=event_version(timestamp),
        )
        await centrifugo.publish(campaign_channel(entry.campaign_id), event)

    @classmethod
    async def _emit_entity_hp_update(
        cls,
        db: Session,
        session_id: str,
        session_entity_id: str,
        previous_hp: int | None,
    ):
        entry = cls._get_session_entry(db, session_id)
        if not entry:
            return
        target = db.exec(
            select(SessionEntity).where(
                SessionEntity.id == session_entity_id,
                SessionEntity.session_id == session_id,
            )
        ).first()
        if not target:
            return
        npc = db.exec(
            select(CampaignEntity).where(CampaignEntity.id == target.campaign_entity_id)
        ).first()
        payload = {
            "sessionId": entry.id,
            "campaignId": entry.campaign_id,
            "partyId": entry.party_id,
            "sessionEntityId": target.id,
            "campaignEntityId": target.campaign_entity_id,
            "visibleToPlayers": target.visible_to_players,
            "label": target.label,
            "currentHp": target.current_hp,
            "entityName": npc.name if npc else (target.label or "Entity"),
            "entityCategory": npc.category if npc else None,
            "maxHp": npc.max_hp if npc else None,
            "armorClass": npc.armor_class if npc else None,
            "speedMeters": npc.speed_meters if npc else None,
        }
        if previous_hp is not None:
            payload["previousHp"] = previous_hp
        if previous_hp is not None and target.current_hp is not None:
            payload["hpDelta"] = target.current_hp - previous_hp
        timestamp = target.updated_at or target.created_at or datetime.now(timezone.utc)
        event = build_event(
            "entity_hp_updated",
            payload,
            version=event_version(timestamp),
        )
        await centrifugo.publish(session_channel(entry.id), event)
        await centrifugo.publish(campaign_channel(entry.campaign_id), event)
