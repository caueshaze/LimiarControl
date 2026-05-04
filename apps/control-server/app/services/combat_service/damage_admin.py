from __future__ import annotations

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app.services.session_state_finalize import finalize_session_state_data

from .damage_core import CombatDamageCoreMixin
from .exceptions import CombatServiceError, _roll_dice_expression
from .fall_damage import FallDamageResolution, compute_fall_damage


class CombatDamageAdminMixin(CombatDamageCoreMixin):
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
        target = next((participant for participant in state.participants if participant.get("id") == target_participant_id), None)
        if not target:
            raise CombatServiceError("Participant not found in combat", 404)
        if target.get("kind") != "player":
            raise CombatServiceError("Only player participants can be revived.", 400)
        if target.get("status") != "dead":
            raise CombatServiceError("Only dead players can be revived with this action.", 400)
        target_model, *_ = cls._get_stats(db, target["ref_id"], "player", session_id)
        data = cls._as_dict(target_model.state_json)
        if not cls._is_player_dead_state(data):
            raise CombatServiceError("Target player is not in a dead state.", 400)
        revive_hp = max(1, cls._safe_int(hp, 1))
        max_hp = max(1, cls._safe_int(data.get("maxHP"), revive_hp))
        data["currentHP"] = min(max_hp, revive_hp)
        cls._reset_death_saves(data)
        target_model.state_json = finalize_session_state_data(data)
        status = cls._sync_participant_status(db, state, target["ref_id"], "player", target_model)
        flag_modified(target_model, "state_json")
        db.add(target_model)
        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_player_state_update(db, session_id, target["ref_id"], target_model)
        await cls._emit_state(session_id, state)
        await cls._emit_and_persist_log(db, session_id, actor_user_id, None, {"message": f"{target['display_name']} foi revivido com {data['currentHP']} PV.", "actorUserId": actor_user_id, "source": "gm_override"})
        return {"new_hp": int(data["currentHP"]), "status": status}

    @classmethod
    async def apply_damage(cls, db: Session, session_id: str, req, actor_user_id: str, is_gm: bool):
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
            **cls._build_concentration_roll_kwargs(req.concentration_roll_source, req.concentration_manual_roll),
        )
        db.commit()
        if req.kind == "player":
            target_state, *_ = cls._get_stats(db, req.target_ref_id, req.kind, session_id)
            await cls._emit_player_state_update(db, session_id, req.target_ref_id, target_state)
        elif previous_hp != new_hp:
            await cls._emit_entity_hp_update(db, session_id, req.target_ref_id, previous_hp)
        if state:
            await cls._emit_state(session_id, state)
        summary = f" {concentration_check['summary_text']}" if isinstance(concentration_check, dict) and isinstance(concentration_check.get("summary_text"), str) else ""
        await cls._emit_and_persist_log(db, session_id, actor_user_id, None, {"message": f"GM applied {req.amount} damage.{effect_msg}{summary}", "source": "gm_override", "actorUserId": actor_user_id})
        return {"new_hp": new_hp, "concentration_check": concentration_check}

    @classmethod
    async def apply_healing(cls, db: Session, session_id: str, req, actor_user_id: str, is_gm: bool):
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
        await cls._emit_and_persist_log(db, session_id, actor_user_id, None, {"message": f"GM applied {req.amount} healing.{effect_msg}", "source": "gm_override", "actorUserId": actor_user_id})
        return {"new_hp": new_hp}

    @classmethod
    async def resolve_fall(
        cls,
        db: Session,
        session_id: str,
        participant_id: str,
        height_meters: float,
        actor_user_id: str,
        is_gm: bool,
    ) -> dict:
        if not is_gm:
            raise CombatServiceError("Only GM can resolve fall damage", 403)
        state = cls.get_state(db, session_id)
        cls._require_active(state)
        participant = next(
            (p for p in state.participants if p.get("id") == participant_id),
            None,
        )
        if not participant:
            raise CombatServiceError("Participant not found in combat", 404)
        ref_id = participant.get("ref_id")
        kind = participant.get("kind")
        display_name = participant.get("display_name") or "Combatant"
        computation = compute_fall_damage(height_meters)
        if not computation.causes_damage:
            resolution = FallDamageResolution(
                participant_id=participant_id,
                height_meters=computation.height_meters,
                effective_height_meters=computation.effective_height_meters,
                dice_count=computation.dice_count,
                dice_sides=computation.dice_sides,
                damage_formula=computation.damage_formula,
                damage_type=computation.damage_type,
                damage_total=0,
                causes_damage=False,
                applied_damage=False,
            )
            db.commit()
            await cls._emit_state(session_id, state)
            await cls._emit_and_persist_log(
                db,
                session_id,
                actor_user_id,
                None,
                {
                    "message": f"{display_name} falls {height_meters}m and takes no damage.",
                    "source": "environmental_fall",
                    "actorUserId": actor_user_id,
                    "participantId": participant_id,
                    "heightMeters": height_meters,
                    "causesDamage": False,
                },
            )
            return {"resolution": resolution.model_dump(mode="json"), "new_hp": None, "concentration_check": None}
        damage_total = _roll_dice_expression(computation.damage_formula)
        new_hp, effect_msg, previous_hp, concentration_check = cls._apply_damage_to_target(
            db,
            ref_id,
            kind,
            damage_total,
            damage_type=computation.damage_type,
            is_crit=False,
            state=state,
        )
        db.commit()
        if kind == "player":
            target_state, *_ = cls._get_stats(db, ref_id, kind, session_id)
            await cls._emit_player_state_update(db, session_id, ref_id, target_state)
        elif previous_hp != new_hp:
            await cls._emit_entity_hp_update(db, session_id, ref_id, previous_hp)
        if state:
            await cls._emit_state(session_id, state)
        await cls._emit_and_persist_log(
            db,
            session_id,
            actor_user_id,
            None,
            {
                "message": f"{display_name} falls {height_meters}m and takes {damage_total} {computation.damage_type} damage.{effect_msg}",
                "source": "environmental_fall",
                "actorUserId": actor_user_id,
                "participantId": participant_id,
                "heightMeters": height_meters,
                "damageTotal": damage_total,
                "damageType": computation.damage_type,
                "damageFormula": computation.damage_formula,
                "diceCount": computation.dice_count,
                "causesDamage": True,
            },
        )
        resolution = FallDamageResolution(
            participant_id=participant_id,
            height_meters=computation.height_meters,
            effective_height_meters=computation.effective_height_meters,
            dice_count=computation.dice_count,
            dice_sides=computation.dice_sides,
            damage_formula=computation.damage_formula,
            damage_type=computation.damage_type,
            damage_total=damage_total,
            causes_damage=True,
            applied_damage=True,
        )
        return {"resolution": resolution.model_dump(mode="json"), "new_hp": new_hp, "concentration_check": concentration_check}
