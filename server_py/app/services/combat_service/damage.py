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
from app.services.dragonborn_ancestry import resolve_dragonborn_lineage_state
from app.services.centrifugo import centrifugo
from app.services.draconic_ancestry import resolve_draconic_lineage_state
from app.services.realtime import build_event, campaign_channel, event_version, session_channel
from app.services.session_state_finalize import finalize_session_state_data

from .exceptions import CombatServiceError, _roll_dice_expression


class CombatDamageMixin:

    @classmethod
    def _build_concentration_roll_kwargs(
        cls,
        roll_source: str = "system",
        manual_roll: int | None = None,
    ) -> dict:
        if roll_source == "system" and manual_roll is None:
            return {}
        return {
            "concentration_roll_source": roll_source,
            "concentration_manual_roll": manual_roll,
        }

    @classmethod
    def _apply_damage_to_target(
        cls,
        db: Session,
        target_ref_id: str,
        kind: str,
        amount: int,
        is_crit: bool = False,
        state: CombatState | None = None,
        *,
        damage_type: str | None = None,
        concentration_roll_source: str = "system",
        concentration_manual_roll: int | None = None,
    ) -> tuple[int, str, int | None, dict | None]:
        """Returns new_hp, status_effect_message, previous_hp, concentration_check."""
        target_model, *_ = cls._get_stats(db, target_ref_id, kind, state.session_id if state else "")
        msg = ""
        target_participant = cls._get_participant_by_ref(state, target_ref_id) if state else None

        if kind == "player":
            from app.services.wild_shape_service import apply_damage_to_form, is_active as ws_is_active

            data = cls._as_dict(target_model.state_json)
            amount, resistance_msg = cls._apply_player_damage_resistances(
                data,
                amount,
                damage_type,
            )

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
                concentration_check = cls._resolve_concentration_check_after_damage(
                    db,
                    state.session_id if state else "",
                    state=state,
                    target_participant=target_participant,
                    target_ref_id=target_ref_id,
                    target_kind=kind,
                    damage_taken=amount,
                    roll_source=concentration_roll_source,
                    manual_roll=concentration_manual_roll,
                )
                if state:
                    flag_modified(state, "participants")
                    db.add(state)
                if resistance_msg:
                    msg = f"{msg} {resistance_msg}".strip()
                return (
                    cls._safe_int(cls._as_dict(target_model.state_json).get("currentHP"), 0),
                    msg,
                    None,
                    concentration_check,
                )

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
            if resistance_msg:
                msg = f"{msg} {resistance_msg}".strip()
            flag_modified(target_model, "state_json")
            db.add(target_model)
            concentration_check = cls._resolve_concentration_check_after_damage(
                db,
                state.session_id if state else "",
                state=state,
                target_participant=target_participant,
                target_ref_id=target_ref_id,
                target_kind=kind,
                damage_taken=amount,
                roll_source=concentration_roll_source,
                manual_roll=concentration_manual_roll,
            )
            if state:
                flag_modified(state, "participants")
                db.add(state)
            return (
                cls._safe_int(cls._as_dict(target_model.state_json).get("currentHP"), 0),
                msg,
                current,
                concentration_check,
            )
        else:
            npc = db.exec(select(CampaignEntity).where(CampaignEntity.id == target_model.campaign_entity_id)).first()
            base_hp = npc.max_hp if npc else 0
            current = target_model.current_hp if target_model.current_hp is not None else base_hp or 0
            target_model.current_hp = max(0, current - amount)
            status = cls._sync_participant_status(db, state, target_ref_id, kind, target_model)
            if current > 0 and target_model.current_hp == 0 and status == "defeated":
                msg = " (DEFEATED!)"
            db.add(target_model)
            concentration_check = cls._resolve_concentration_check_after_damage(
                db,
                state.session_id if state else "",
                state=state,
                target_participant=target_participant,
                target_ref_id=target_ref_id,
                target_kind=kind,
                damage_taken=amount,
                roll_source=concentration_roll_source,
                manual_roll=concentration_manual_roll,
            )
            if state:
                flag_modified(state, "participants")
                db.add(state)
            return target_model.current_hp, msg, current, concentration_check

    @classmethod
    def _apply_player_damage_resistances(
        cls,
        data: dict,
        amount: int,
        damage_type: str | None,
    ) -> tuple[int, str]:
        normalized_damage_type = cls._normalize_damage_type(damage_type)
        if amount <= 0 or not normalized_damage_type:
            return amount, ""

        draconic_lineage = resolve_draconic_lineage_state(data)
        dragonborn_lineage = resolve_dragonborn_lineage_state(data)
        resistances = {
            str(value).strip().lower()
            for value in [
                *draconic_lineage.get("resistances", []),
                *dragonborn_lineage.get("resistances", []),
            ]
            if isinstance(value, str) and value.strip()
        }
        if normalized_damage_type not in resistances:
            return amount, ""

        reduced = max(0, amount // 2)
        return reduced, f"(Resistência a {normalized_damage_type}: {amount} -> {reduced})"

    @classmethod
    def _apply_healing_to_target(cls, db: Session, target_ref_id: str, kind: str, amount: int, state: CombatState | None = None) -> tuple[int, str, int | None]:
        target_model, *_ = cls._get_stats(db, target_ref_id, kind, state.session_id if state else "")
        msg = ""

        if kind == "player":
            from app.services.wild_shape_catalog import get_form
            from app.services.wild_shape_service import apply_healing_to_form, is_active as ws_is_active

            data = cls._as_dict(target_model.state_json)
            current = max(0, cls._safe_int(data.get("currentHP"), 0))

            if cls._is_player_dead_state(data):
                return current, " (Dead characters require explicit revive, not normal healing.)", current

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
    async def revive_player(
        cls,
        db: Session,
        session_id: str,
        target_participant_id: str,
        actor_user_id: str,
        is_gm: bool,
        *,
        hp: int | None = None,
    ) -> dict[str, int | str]:
        if not is_gm:
            raise CombatServiceError("Only GM can revive a dead player.", 403)

        state = cls.get_state(db, session_id)
        cls._require_active(state)

        target_p = next(
            (participant for participant in state.participants if participant.get("id") == target_participant_id),
            None,
        )
        if not target_p:
            raise CombatServiceError("Participant not found in combat", 404)
        if target_p.get("kind") != "player":
            raise CombatServiceError("Only player participants can be revived.", 400)
        if target_p.get("status") != "dead":
            raise CombatServiceError("Only dead players can be revived with this action.", 400)

        target_model, *_ = cls._get_stats(db, target_p["ref_id"], "player", session_id)
        data = cls._as_dict(target_model.state_json)
        if not cls._is_player_dead_state(data):
            raise CombatServiceError("Target player is not in a dead state.", 400)

        revive_hp = max(1, cls._safe_int(hp, 1))
        max_hp = max(1, cls._safe_int(data.get("maxHP"), revive_hp))
        data["currentHP"] = min(max_hp, revive_hp)
        cls._reset_death_saves(data)

        target_model.state_json = finalize_session_state_data(data)
        status = cls._sync_participant_status(db, state, target_p["ref_id"], "player", target_model)

        flag_modified(target_model, "state_json")
        db.add(target_model)
        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)

        await cls._emit_player_state_update(db, session_id, target_p["ref_id"], target_model)
        await cls._emit_state(session_id, state)
        await cls._emit_log(session_id, {
            "message": f"{target_p['display_name']} was revived with {data['currentHP']} HP.",
            "actorUserId": actor_user_id,
            "source": "gm_override",
        })

        return {"new_hp": int(data["currentHP"]), "status": status}

    @classmethod
    async def apply_damage(cls, db: Session, session_id: str, req: CombatApplyDamageRequest, actor_user_id: str, is_gm: bool):
        if not is_gm:
            raise CombatServiceError("Only GM can arbitrarily apply damage directly", 403)
            
        state = cls.get_state(db, session_id)
        new_hp, effect_msg, previous_hp, concentration_check = cls._apply_damage_to_target(
            db,
            req.target_ref_id,
            req.kind,
            req.amount,
            damage_type=req.type_override,
            is_crit=False,
            state=state,
            **cls._build_concentration_roll_kwargs(
                req.concentration_roll_source,
                req.concentration_manual_roll,
            ),
        )
        db.commit()
        if req.kind == "player":
            target_state, *_ = cls._get_stats(db, req.target_ref_id, req.kind, session_id)
            await cls._emit_player_state_update(db, session_id, req.target_ref_id, target_state)
        elif previous_hp != new_hp:
            await cls._emit_entity_hp_update(db, session_id, req.target_ref_id, previous_hp)
        if state:
            await cls._emit_state(session_id, state)
        
        concentration_summary = (
            f" {concentration_check['summary_text']}"
            if isinstance(concentration_check, dict)
            and isinstance(concentration_check.get("summary_text"), str)
            else ""
        )
        await cls._emit_log(session_id, {
            "message": f"GM applied {req.amount} damage.{effect_msg}{concentration_summary}",
            "source": "gm_override",
            "actorUserId": actor_user_id
        })
        return {"new_hp": new_hp, "concentration_check": concentration_check}

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
