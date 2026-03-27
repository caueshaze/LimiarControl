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


class CombatDamageMixin:

    @classmethod
    def _apply_damage_to_target(cls, db: Session, target_ref_id: str, kind: str, amount: int, is_crit: bool = False, state: CombatState | None = None) -> tuple[int, str, int | None]:
        """Returns new_hp, status_effect_message, previous_hp."""
        target_model, *_ = cls._get_stats(db, target_ref_id, kind, state.session_id if state else "")
        msg = ""

        if kind == "player":
            from app.services.wild_shape_service import apply_damage_to_form, is_active as ws_is_active

            data = cls._as_dict(target_model.state_json)

            # ── Wild Shape HP routing ─────────────────────────────────────────
            if ws_is_active(data):
                data, ws_reverted, overflow = apply_damage_to_form(data, amount)
                if ws_reverted:
                    msg = " (Wild Shape form destroyed — reverted to humanoid!"
                    if overflow > 0:
                        # PHB 5e: excess damage carries over to humanoid form
                        humanoid_hp = max(0, cls._safe_int(data.get("currentHP"), 0))
                        new_humanoid_hp = max(0, humanoid_hp - overflow)
                        data["currentHP"] = new_humanoid_hp
                        if humanoid_hp == 0 and new_humanoid_hp == 0:
                            fails = 2 if is_crit else 1
                            death_saves = cls._as_dict(data.get("deathSaves"))
                            death_saves["failures"] += fails
                            data["deathSaves"] = death_saves
                            msg += f", {overflow} overflow while downed!)"
                        elif humanoid_hp > 0 and new_humanoid_hp == 0:
                            cls._reset_death_saves(data)
                            msg += f", {overflow} overflow → downed!)"
                        else:
                            msg += f", {overflow} overflow damage applied)"
                    else:
                        msg += ")"
                target_model.state_json = finalize_session_state_data(data)
                status = cls._sync_participant_status(db, state, target_ref_id, kind, target_model)
                flag_modified(target_model, "state_json")
                db.add(target_model)
                if state:
                    flag_modified(state, "participants")
                    db.add(state)
                return cls._safe_int(cls._as_dict(target_model.state_json).get("currentHP"), 0), msg, None

            # ── Normal humanoid HP ────────────────────────────────────────────
            current = max(0, cls._safe_int(data.get("currentHP"), 0))
            data["currentHP"] = max(0, current - amount)

            if current == 0 and data["currentHP"] == 0:
                # Already at 0 HP, takes damage
                fails = 2 if is_crit else 1
                death_saves = cls._as_dict(data.get("deathSaves"))
                death_saves["failures"] += fails
                data["deathSaves"] = death_saves
            elif current > 0 and data["currentHP"] == 0:
                # Dropped to 0 HP just now
                cls._reset_death_saves(data)

            target_model.state_json = finalize_session_state_data(data)
            status = cls._sync_participant_status(db, state, target_ref_id, kind, target_model)
            if current == 0 and data["currentHP"] == 0:
                msg = (
                    " (Took damage while downed and DIED!)"
                    if status == "dead"
                    else f" (Took damage while downed! +{2 if is_crit else 1} failure(s))"
                )
            elif current > 0 and data["currentHP"] == 0 and status == "downed":
                msg = " (Fell unconscious!)"
            flag_modified(target_model, "state_json")
            db.add(target_model)
            if state:
                flag_modified(state, "participants")
                db.add(state)
            return cls._safe_int(cls._as_dict(target_model.state_json).get("currentHP"), 0), msg, current
        else:
            npc = db.exec(select(CampaignEntity).where(CampaignEntity.id == target_model.campaign_entity_id)).first()
            base_hp = npc.max_hp if npc else 0
            current = target_model.current_hp if target_model.current_hp is not None else base_hp or 0
            target_model.current_hp = max(0, current - amount)
            status = cls._sync_participant_status(db, state, target_ref_id, kind, target_model)
            if current > 0 and target_model.current_hp == 0 and status == "defeated":
                msg = " (DEFEATED!)"
            db.add(target_model)
            if state:
                flag_modified(state, "participants")
                db.add(state)
            return target_model.current_hp, msg, current

    @classmethod
    def _apply_healing_to_target(cls, db: Session, target_ref_id: str, kind: str, amount: int, state: CombatState | None = None) -> tuple[int, str, int | None]:
        target_model, *_ = cls._get_stats(db, target_ref_id, kind, state.session_id if state else "")
        msg = ""

        if kind == "player":
            from app.services.wild_shape_catalog import get_form
            from app.services.wild_shape_service import apply_healing_to_form, is_active as ws_is_active

            data = cls._as_dict(target_model.state_json)

            # ── Wild Shape: heal the beast form's HP ──────────────────────────
            if ws_is_active(data):
                form_key = (data.get("wildShape") or {}).get("formKey")
                form = get_form(form_key) if isinstance(form_key, str) else None
                if form is not None:
                    data = apply_healing_to_form(data, amount, form)
                    target_model.state_json = finalize_session_state_data(data)
                    status = cls._sync_participant_status(db, state, target_ref_id, kind, target_model)
                    flag_modified(target_model, "state_json")
                    db.add(target_model)
                    if state:
                        flag_modified(state, "participants")
                        db.add(state)
                    form_hp = (data.get("wildShape") or {}).get("formCurrentHP", 0)
                    return cls._safe_int(form_hp, 0), "", None

            # ── Normal humanoid HP ────────────────────────────────────────────
            current = max(0, cls._safe_int(data.get("currentHP"), 0))
            max_hp = max(0, cls._safe_int(data.get("maxHP"), 0))
            data["currentHP"] = min(max_hp, current + amount)
            target_model.state_json = finalize_session_state_data(data)
            status = cls._sync_participant_status(db, state, target_ref_id, kind, target_model)
            if current == 0 and data["currentHP"] > 0 and status == "active":
                msg = " (Revived!)"

            flag_modified(target_model, "state_json")
            db.add(target_model)
            if state:
                flag_modified(state, "participants")
                db.add(state)
            return cls._safe_int(cls._as_dict(target_model.state_json).get("currentHP"), 0), msg, current
        else:
            npc = db.exec(select(CampaignEntity).where(CampaignEntity.id == target_model.campaign_entity_id)).first()
            base_hp = npc.max_hp if npc else 999
            current = target_model.current_hp if target_model.current_hp is not None else base_hp or 0
            max_hp = base_hp or 999
            target_model.current_hp = min(max_hp, current + amount)
            status = cls._sync_participant_status(db, state, target_ref_id, kind, target_model)
            if current == 0 and target_model.current_hp > 0 and status == "active":
                msg = " (Revived!)"
            db.add(target_model)
            if state:
                flag_modified(state, "participants")
                db.add(state)
            return target_model.current_hp, msg, current

    @classmethod
    async def apply_damage(cls, db: Session, session_id: str, req: CombatApplyDamageRequest, actor_user_id: str, is_gm: bool):
        if not is_gm:
            raise CombatServiceError("Only GM can arbitrarily apply damage directly", 403)
            
        state = cls.get_state(db, session_id)
        new_hp, effect_msg, previous_hp = cls._apply_damage_to_target(db, req.target_ref_id, req.kind, req.amount, False, state)
        db.commit()
        if req.kind == "player":
            target_state, *_ = cls._get_stats(db, req.target_ref_id, req.kind, session_id)
            await cls._emit_player_state_update(db, session_id, req.target_ref_id, target_state)
        elif previous_hp != new_hp:
            await cls._emit_entity_hp_update(db, session_id, req.target_ref_id, previous_hp)
        if state:
            await cls._emit_state(session_id, state)
        
        await cls._emit_log(session_id, {
            "message": f"GM applied {req.amount} damage.{effect_msg}",
            "source": "gm_override",
            "actorUserId": actor_user_id
        })
        return {"new_hp": new_hp}

    @classmethod
    async def apply_healing(cls, db: Session, session_id: str, req: CombatApplyHealingRequest, actor_user_id: str, is_gm: bool):
        if not is_gm:
            raise CombatServiceError("Only GM can arbitrarily apply healing directly", 403)
            
        state = cls.get_state(db, session_id)
        new_hp, effect_msg, previous_hp = cls._apply_healing_to_target(db, req.target_ref_id, req.kind, req.amount, state)
        db.commit()
        if req.kind == "player":
            target_state, *_ = cls._get_stats(db, req.target_ref_id, req.kind, session_id)
            await cls._emit_player_state_update(db, session_id, req.target_ref_id, target_state)
        elif previous_hp != new_hp:
            await cls._emit_entity_hp_update(db, session_id, req.target_ref_id, previous_hp)
        if state:
            await cls._emit_state(session_id, state)

        await cls._emit_log(session_id, {
            "message": f"GM applied {req.amount} healing.{effect_msg}",
            "source": "gm_override",
            "actorUserId": actor_user_id
        })
        return {"new_hp": new_hp}
