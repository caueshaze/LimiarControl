from __future__ import annotations

from typing import Any, Callable, ClassVar

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select

from app.models.campaign_entity import CampaignEntity
from app.models.combat import CombatState
from app.services.draconic_ancestry import resolve_draconic_lineage_state
from app.services.dragonborn_ancestry import resolve_dragonborn_lineage_state
from app.services.declarative_effect_lifecycle import remove_damage_terminated_effects_from_participant
from app.services.session_state_finalize import finalize_session_state_data


class CombatDamageCoreMixin:
    _normalize_damage_type: ClassVar[Callable[[object], str | None]]
    _get_stats: ClassVar[Callable[..., tuple[Any, Any, Any, Any, Any, Any]]]
    _get_participant_by_ref: ClassVar[Callable[[CombatState | None, str | None], dict[str, Any] | None]]
    _as_dict: ClassVar[Callable[[object], dict[str, Any]]]
    _safe_int: ClassVar[Callable[[object, int], int]]
    _reset_death_saves: ClassVar[Callable[[dict[str, Any]], None]]
    _sync_participant_status: ClassVar[Callable[..., str]]
    _resolve_concentration_check_after_damage: ClassVar[Callable[..., dict[str, Any] | None]]
    _is_player_dead_state: ClassVar[Callable[[dict[str, Any] | None], bool]]

    @classmethod
    def _build_concentration_roll_kwargs(cls, roll_source: str = "system", manual_roll: int | None = None) -> dict:
        if roll_source == "system" and manual_roll is None:
            return {}
        return {"concentration_roll_source": roll_source, "concentration_manual_roll": manual_roll}

    @classmethod
    def _apply_player_damage_resistances(cls, data: dict, amount: int, damage_type: str | None) -> tuple[int, str]:
        normalized_damage_type = cls._normalize_damage_type(damage_type)
        if amount <= 0 or not normalized_damage_type:
            return amount, ""
        draconic_lineage = resolve_draconic_lineage_state(data)
        dragonborn_lineage = resolve_dragonborn_lineage_state(data)
        resistances = {
            str(value).strip().lower()
            for value in [*draconic_lineage.get("resistances", []), *dragonborn_lineage.get("resistances", [])]
            if isinstance(value, str) and value.strip()
        }
        if normalized_damage_type not in resistances:
            return amount, ""
        reduced = max(0, amount // 2)
        return reduced, f"(Resistência a {normalized_damage_type}: {amount} -> {reduced})"

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
        is_magical_damage: bool = False,
        concentration_roll_source: str = "system",
        concentration_manual_roll: int | None = None,
        attacker_participant_id: str | None = None,
    ) -> tuple[int, str, int | None, dict | None]:
        target_model, *_ = cls._get_stats(db, target_ref_id, kind, state.session_id if state else "")
        message = ""
        target_participant = cls._get_participant_by_ref(state, target_ref_id) if state else None
        if kind == "player":
            from app.services.wild_shape_service import apply_damage_to_form, is_active as ws_is_active

            data = cls._as_dict(target_model.state_json)
            amount, resistance_msg = cls._apply_player_damage_resistances(data, amount, damage_type)
            if ws_is_active(data):
                data, ws_reverted, overflow = apply_damage_to_form(data, amount)
                if ws_reverted:
                    message = " (Wild Shape form destroyed — reverted to humanoid!"
                    if overflow > 0:
                        humanoid_hp = max(0, cls._safe_int(data.get("currentHP"), 0))
                        new_humanoid_hp = max(0, humanoid_hp - overflow)
                        data["currentHP"] = new_humanoid_hp
                        if humanoid_hp == 0 and new_humanoid_hp == 0:
                            fails = 2 if is_crit else 1
                            death_saves = cls._as_dict(data.get("deathSaves"))
                            death_saves["failures"] += fails
                            data["deathSaves"] = death_saves
                            message += f", {overflow} overflow while downed!)"
                        elif humanoid_hp > 0 and new_humanoid_hp == 0:
                            cls._reset_death_saves(data)
                            message += f", {overflow} overflow -> downed!)"
                        else:
                            message += f", {overflow} overflow damage applied)"
                    else:
                        message += ")"
                target_model.state_json = finalize_session_state_data(data)
                cls._sync_participant_status(db, state, target_ref_id, kind, target_model)
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
                if attacker_participant_id and amount > 0 and target_participant is not None:
                    remove_damage_terminated_effects_from_participant(state, target_participant, attacker_participant_id)
                if resistance_msg:
                    message = f"{message} {resistance_msg}".strip()
                return cls._safe_int(cls._as_dict(target_model.state_json).get("currentHP"), 0), message, None, concentration_check
            current = max(0, cls._safe_int(data.get("currentHP"), 0))
            data["currentHP"] = max(0, current - amount)
            if current == 0 and data["currentHP"] == 0:
                fails = 2 if is_crit else 1
                death_saves = cls._as_dict(data.get("deathSaves"))
                death_saves["failures"] += fails
                data["deathSaves"] = death_saves
            elif current > 0 and data["currentHP"] == 0:
                cls._reset_death_saves(data)
            target_model.state_json = finalize_session_state_data(data)
            status = cls._sync_participant_status(db, state, target_ref_id, kind, target_model)
            if current == 0 and data["currentHP"] == 0:
                message = " (Took damage while downed and DIED!)" if status == "dead" else f" (Took damage while downed! +{2 if is_crit else 1} failure(s))"
            elif current > 0 and data["currentHP"] == 0 and status == "downed":
                message = " (Fell unconscious!)"
            if resistance_msg:
                message = f"{message} {resistance_msg}".strip()
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
            if attacker_participant_id and amount > 0 and target_participant is not None:
                remove_damage_terminated_effects_from_participant(state, target_participant, attacker_participant_id)
            return cls._safe_int(cls._as_dict(target_model.state_json).get("currentHP"), 0), message, current, concentration_check
        npc = db.exec(select(CampaignEntity).where(CampaignEntity.id == target_model.campaign_entity_id)).first()
        base_hp = npc.max_hp if npc else 0
        current = target_model.current_hp if target_model.current_hp is not None else base_hp or 0
        target_model.current_hp = max(0, current - amount)
        status = cls._sync_participant_status(db, state, target_ref_id, kind, target_model)
        if current > 0 and target_model.current_hp == 0 and status == "defeated":
            message = " (DEFEATED!)"
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
        if attacker_participant_id and amount > 0 and target_participant is not None:
            remove_damage_terminated_effects_from_participant(state, target_participant, attacker_participant_id)
        return target_model.current_hp, message, current, concentration_check

    @staticmethod
    def _participant_has_prevent_healing(participant: dict) -> bool:
        for effect in (participant.get("active_effects") or []):
            if effect.get("kind") == "spell_effect":
                if (effect.get("metadata") or {}).get("prevent_healing") is True:
                    return True
        return False

    @classmethod
    def _apply_healing_to_target(cls, db: Session, target_ref_id: str, kind: str, amount: int, state: CombatState | None = None) -> tuple[int, str, int | None]:
        target_model, *_ = cls._get_stats(db, target_ref_id, kind, state.session_id if state else "")
        message = ""
        if kind == "player":
            from app.services.wild_shape_catalog import get_form
            from app.services.wild_shape_service import apply_healing_to_form, is_active as ws_is_active

            data = cls._as_dict(target_model.state_json)
            current = max(0, cls._safe_int(data.get("currentHP"), 0))
            if cls._is_player_dead_state(data):
                return current, " (Dead characters require explicit revive, not normal healing.)", current
            if state is not None:
                _p = next((p for p in (state.participants or []) if p.get("ref_id") == target_ref_id), None)
                if _p is not None and cls._participant_has_prevent_healing(_p):
                    return current, " (Recuperação de PV impedida — efeito ativo no alvo.)", current
            if ws_is_active(data):
                form_key = (data.get("wildShape") or {}).get("formKey")
                form = get_form(form_key) if isinstance(form_key, str) else None
                if form is not None:
                    data = apply_healing_to_form(data, amount, form)
                    target_model.state_json = finalize_session_state_data(data)
                    cls._sync_participant_status(db, state, target_ref_id, kind, target_model)
                    flag_modified(target_model, "state_json")
                    db.add(target_model)
                    if state:
                        flag_modified(state, "participants")
                        db.add(state)
                    return cls._safe_int((data.get("wildShape") or {}).get("formCurrentHP", 0), 0), "", None
            max_hp = max(0, cls._safe_int(data.get("maxHP"), 0))
            data["currentHP"] = min(max_hp, current + amount)
            target_model.state_json = finalize_session_state_data(data)
            status = cls._sync_participant_status(db, state, target_ref_id, kind, target_model)
            if current == 0 and data["currentHP"] > 0 and status == "active":
                message = " (Revived!)"
            flag_modified(target_model, "state_json")
            db.add(target_model)
            if state:
                flag_modified(state, "participants")
                db.add(state)
            return cls._safe_int(cls._as_dict(target_model.state_json).get("currentHP"), 0), message, current
        npc = db.exec(select(CampaignEntity).where(CampaignEntity.id == target_model.campaign_entity_id)).first()
        base_hp = npc.max_hp if npc else 999
        current = target_model.current_hp if target_model.current_hp is not None else base_hp or 0
        if state is not None:
            _p = next((p for p in (state.participants or []) if p.get("ref_id") == target_ref_id), None)
            if _p is not None and cls._participant_has_prevent_healing(_p):
                return current, " (Recuperação de PV impedida — efeito ativo no alvo.)", current
        target_model.current_hp = min(base_hp or 999, current + amount)
        status = cls._sync_participant_status(db, state, target_ref_id, kind, target_model)
        if current == 0 and target_model.current_hp > 0 and status == "active":
            message = " (Revived!)"
        db.add(target_model)
        if state:
            flag_modified(state, "participants")
            db.add(state)
        return target_model.current_hp, message, current
