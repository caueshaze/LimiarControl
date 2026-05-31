from __future__ import annotations

from typing import Any, Callable, ClassVar

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select

from app.models.campaign_entity import CampaignEntity
from app.models.combat import CombatState
from app.services.draconic_ancestry import resolve_draconic_lineage_state
from app.services.dragonborn_ancestry import resolve_dragonborn_lineage_state
from app.services.declarative_effect_lifecycle import remove_damage_terminated_effects_from_participant
from app.services.sleep_spell import remove_sleep_unconscious_on_damage
from app.services.session_state_finalize import finalize_session_state_data
from app.services.warding_bond import (
    break_warding_bonds_for_caster,
    find_target_role_effect,
    remove_warding_bonds_involving_participants,
)
from app.services.compelled_duel import (
    break_compelled_duel_if_ally_harms_target,
    break_compelled_duel_on_target_defeated,
)


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
    def _apply_warding_bond_resistance(cls, participant: dict | None, amount: int) -> tuple[int, str]:
        """Warding Bond grants the target resistance to all damage."""
        if amount <= 0 or not isinstance(participant, dict):
            return amount, ""
        if find_target_role_effect(participant) is None:
            return amount, ""
        reduced = max(0, amount // 2)
        return reduced, f"(Vínculo de Proteção: resistência {amount} -> {reduced})"

    @classmethod
    def _is_warding_bond_caster(cls, participant: dict | None) -> bool:
        if not isinstance(participant, dict):
            return False
        for effect in participant.get("active_effects") or []:
            if not isinstance(effect, dict) or effect.get("kind") != "spell_effect":
                continue
            metadata = effect.get("metadata") or {}
            if metadata.get("source_spell_key") == "warding_bond" and metadata.get("warding_bond_role") == "caster":
                return True
        return False

    @classmethod
    def _apply_warding_bond_effects_after_damage(
        cls,
        db: Session,
        state: CombatState | None,
        target_participant: dict | None,
        *,
        target_new_hp: int | None,
        final_amount: int,
        is_crit: bool,
        warding_bond_share: bool,
    ) -> None:
        if state is None or not isinstance(target_participant, dict):
            return

        # If the damaged creature is a Warding Bond caster and just dropped to 0
        # HP, every bond it created ends. This also covers the caster receiving
        # reflected (shared) damage, since that flows through this same path.
        if (
            isinstance(target_new_hp, int)
            and target_new_hp <= 0
            and cls._is_warding_bond_caster(target_participant)
        ):
            break_warding_bonds_for_caster(state, target_participant.get("ref_id"))

        # Reflected damage never re-triggers sharing, and only positive damage
        # is mirrored onto the caster.
        if warding_bond_share or final_amount <= 0:
            return
        bond = find_target_role_effect(target_participant)
        if bond is None:
            return
        caster_ref = (bond.get("metadata") or {}).get("bond_caster_participant_id")
        caster = next(
            (p for p in (state.participants or []) if isinstance(p, dict) and p.get("ref_id") == caster_ref),
            None,
        )
        if caster is None or not caster.get("ref_id") or not caster.get("kind"):
            # Dangling bond (caster gone): fail safe by removing it.
            remove_warding_bonds_involving_participants(
                state, [caster_ref, target_participant.get("ref_id")]
            )
            return
        cls._apply_damage_to_target(
            db,
            caster["ref_id"],
            caster["kind"],
            final_amount,
            is_crit=is_crit,
            state=state,
            warding_bond_share=True,
        )

    @classmethod
    def _apply_compelled_duel_breaks_after_damage(
        cls,
        state: CombatState | None,
        target_participant: dict | None,
        *,
        target_new_hp: int | None,
        attacker_participant_id: str | None,
    ) -> None:
        if state is None or not isinstance(target_participant, dict):
            return
        target_ref = target_participant.get("ref_id")
        # Target died -> the duel ends.
        if isinstance(target_new_hp, int) and target_new_hp <= 0:
            break_compelled_duel_on_target_defeated(state, target_ref)
            return
        # A creature friendly to the caster damaging the target ends the duel.
        if attacker_participant_id:
            attacker = next(
                (
                    p
                    for p in (state.participants or [])
                    if isinstance(p, dict) and p.get("id") == attacker_participant_id
                ),
                None,
            )
            if attacker is not None:
                break_compelled_duel_if_ally_harms_target(state, attacker.get("ref_id"), target_ref)

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
        warding_bond_share: bool = False,
    ) -> tuple[int, str, int | None, dict | None]:
        target_model, *_ = cls._get_stats(db, target_ref_id, kind, state.session_id if state else "")
        message = ""
        target_participant = cls._get_participant_by_ref(state, target_ref_id) if state else None
        if kind == "player":
            from app.services.wild_shape_service import apply_damage_to_form, is_active as ws_is_active

            data = cls._as_dict(target_model.state_json)
            if not warding_bond_share:
                amount, resistance_msg = cls._apply_player_damage_resistances(data, amount, damage_type)
                amount, wb_resistance_msg = cls._apply_warding_bond_resistance(target_participant, amount)
                resistance_msg = f"{resistance_msg} {wb_resistance_msg}".strip()
            else:
                resistance_msg = ""
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
                ws_new_hp = cls._safe_int(cls._as_dict(target_model.state_json).get("currentHP"), 0)
                cls._apply_warding_bond_effects_after_damage(
                    db,
                    state,
                    target_participant,
                    target_new_hp=ws_new_hp,
                    final_amount=amount,
                    is_crit=is_crit,
                    warding_bond_share=warding_bond_share,
                )
                cls._apply_compelled_duel_breaks_after_damage(
                    state,
                    target_participant,
                    target_new_hp=ws_new_hp,
                    attacker_participant_id=attacker_participant_id,
                )
                return ws_new_hp, message, None, concentration_check
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
            if amount > 0 and target_participant is not None:
                remove_sleep_unconscious_on_damage(target_participant, amount)
            player_new_hp = cls._safe_int(cls._as_dict(target_model.state_json).get("currentHP"), 0)
            cls._apply_warding_bond_effects_after_damage(
                db,
                state,
                target_participant,
                target_new_hp=player_new_hp,
                final_amount=amount,
                is_crit=is_crit,
                warding_bond_share=warding_bond_share,
            )
            cls._apply_compelled_duel_breaks_after_damage(
                state,
                target_participant,
                target_new_hp=player_new_hp,
                attacker_participant_id=attacker_participant_id,
            )
            return player_new_hp, message, current, concentration_check
        npc = db.exec(select(CampaignEntity).where(CampaignEntity.id == target_model.campaign_entity_id)).first()
        base_hp = npc.max_hp if npc else 0
        current = target_model.current_hp if target_model.current_hp is not None else base_hp or 0
        if not warding_bond_share:
            amount, npc_wb_resistance_msg = cls._apply_warding_bond_resistance(target_participant, amount)
            if npc_wb_resistance_msg:
                message = f"{message} {npc_wb_resistance_msg}".strip()
        target_model.current_hp = max(0, current - amount)
        status = cls._sync_participant_status(db, state, target_ref_id, kind, target_model)
        if current > 0 and target_model.current_hp == 0 and status == "defeated":
            message = f"{message} (DEFEATED!)".strip()
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
        if amount > 0 and target_participant is not None:
            remove_sleep_unconscious_on_damage(target_participant, amount)
        cls._apply_warding_bond_effects_after_damage(
            db,
            state,
            target_participant,
            target_new_hp=target_model.current_hp,
            final_amount=amount,
            is_crit=is_crit,
            warding_bond_share=warding_bond_share,
        )
        cls._apply_compelled_duel_breaks_after_damage(
            state,
            target_participant,
            target_new_hp=target_model.current_hp,
            attacker_participant_id=attacker_participant_id,
        )
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
