from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app.models.combat import CombatState
from app.schemas.combat_actions import CombatEntityActionRequest
from app.schemas.combat_spells import CombatAttackRequest
from app.services.combat_service.entity_size import SizeCategory, normalize_size_category
from app.services.combat_service.condition_effects_predicates import has_condition_immunity_from_source
from app.services.crown_of_madness import (
    find_crown_of_madness_effect_on_target,
    get_crown_of_madness_effects_for_caster,
    mark_crown_of_madness_forced_attack_pending,
    mark_crown_of_madness_forced_attack_resolved,
    remove_crown_of_madness_instance,
)
from app.services.game_time import get_game_time_seconds
from app.services.roll_resolution import resolve_saving_throw
from app.services.spell_effect_factories import (
    build_compelled_duel_effect,
    build_crown_of_madness_effect,
)
from app.services.compelled_duel import find_compelled_duel_effect_on_target
from ...condition_effects_saves import modify_saving_throw
from ...exceptions import CombatServiceError, _roll_dice_expression
from ...host_protocol import CombatServiceHostProtocol


if TYPE_CHECKING:
    _ControlSpellsBase = CombatServiceHostProtocol
else:
    _ControlSpellsBase = object


class ControlSpellsAutomationMixin(_ControlSpellsBase):
    @classmethod
    def _build_next_weapon_hit_concentration_marker(
        cls,
        *,
        spell_key: str,
        caster_participant_id: str,
        spell_name: str,
        concentration_group: str,
    ) -> dict:
        return cls._build_active_effect(
            kind="spell_effect",
            source_participant_id=caster_participant_id,
            duration_type="manual",
            expires_at_participant_id=caster_participant_id,
            metadata={
                "source_spell_key": spell_key,
                "source_spell_name": spell_name,
                "effect_role": "concentration_marker",
                "concentration": True,
                "concentration_group": concentration_group,
            },
            display_label=spell_name,
        )

    @classmethod
    def _build_ensnaring_strike_concentration_marker(
        cls,
        *,
        caster_participant_id: str,
        spell_name: str,
        concentration_group: str,
    ) -> dict:
        return cls._build_next_weapon_hit_concentration_marker(
            spell_key="ensnaring_strike",
            caster_participant_id=caster_participant_id,
            spell_name=spell_name,
            concentration_group=concentration_group,
        )

    @classmethod
    def _build_hail_of_thorns_concentration_marker(
        cls,
        *,
        caster_participant_id: str,
        spell_name: str,
        concentration_group: str,
    ) -> dict:
        return cls._build_next_weapon_hit_concentration_marker(
            spell_key="hail_of_thorns",
            caster_participant_id=caster_participant_id,
            spell_name=spell_name,
            concentration_group=concentration_group,
        )

    @classmethod
    def _build_ensnaring_strike_rider_effect(
        cls,
        *,
        caster_participant_id: str,
        spell_name: str,
        concentration_group: str,
        save_dc: int,
    ) -> dict:
        return cls._build_active_effect(
            kind="spell_effect",
            source_participant_id=caster_participant_id,
            duration_type="manual",
            expires_at_participant_id=caster_participant_id,
            metadata={
                "source_spell_key": "ensnaring_strike",
                "source_spell_name": spell_name,
                "effect_role": "next_weapon_hit_rider",
                "trigger": "next_weapon_hit",
                "consume_on": "weapon_hit",
                "weapon_attack_only": True,
                "save_ability": "strength",
                "save_dc": save_dc,
                "recurring_damage_timing": "start_of_target_turn",
                "recurring_damage_dice": "1d6",
                "recurring_damage_type": "piercing",
                "escape_action": True,
                "escape_check_ability": "strength",
                "escape_check_dc": save_dc,
                "concentration": False,
                "concentration_group": concentration_group,
            },
            display_label=spell_name,
        )

    @classmethod
    def _build_hail_of_thorns_rider_effect(
        cls,
        *,
        caster_participant_id: str,
        spell_name: str,
        concentration_group: str,
        save_dc: int,
        effect_dice: str,
    ) -> dict:
        return cls._build_active_effect(
            kind="spell_effect",
            source_participant_id=caster_participant_id,
            duration_type="manual",
            expires_at_participant_id=caster_participant_id,
            metadata={
                "source_spell_key": "hail_of_thorns",
                "source_spell_name": spell_name,
                "effect_role": "next_weapon_hit_rider",
                "trigger": "next_weapon_hit",
                "consume_on": "weapon_hit",
                "weapon_attack_only": True,
                "ranged_weapon_attack_only": True,
                "save_ability": "dexterity",
                "save_dc": save_dc,
                "effect_dice": effect_dice,
                "reactive_burst": {
                    "origin": "hit_target",
                    "shape": "sphere",
                    "radius_m": 1.5,
                    "damage_type": "piercing",
                    "save_success": "half",
                },
                "concentration": False,
                "concentration_group": concentration_group,
            },
            display_label=spell_name,
        )

    @classmethod
    def _build_ensnaring_strike_target_effect(
        cls,
        *,
        caster_participant_id: str,
        spell_name: str,
        concentration_group: str,
        save_dc: int,
    ) -> dict:
        effect = cls._build_active_effect(
            kind="condition",
            condition_type="restrained",
            source_participant_id=caster_participant_id,
            duration_type="manual",
            metadata={
                "source_spell_key": "ensnaring_strike",
                "source_spell_name": spell_name,
                "effect_role": "persistent_spell_condition",
                "concentration": False,
                "concentration_group": concentration_group,
                "recurring_damage_timing": "start_of_target_turn",
                "recurring_damage_dice": "1d6",
                "recurring_damage_type": "piercing",
                "escape_action": True,
                "escape_check_ability": "strength",
                "escape_check_dc": save_dc,
            },
            display_label="Restrained (Ensnaring Strike)",
        )
        metadata = effect.get("metadata") or {}
        metadata["source_effect_id"] = effect.get("id")
        effect["metadata"] = metadata
        return effect

    @classmethod
    def _list_next_weapon_hit_riders(
        cls,
        participant: dict,
    ) -> list[dict]:
        riders: list[dict] = []
        for effect in cls._get_participant_effects(participant):
            metadata = cls._get_effect_metadata(effect)
            if effect.get("kind") != "spell_effect":
                continue
            if metadata.get("effect_role") != "next_weapon_hit_rider":
                continue
            if metadata.get("trigger") != "next_weapon_hit":
                continue
            if metadata.get("consume_on") != "weapon_hit":
                continue
            riders.append(effect)
        riders.sort(
            key=lambda effect: (
                cls._safe_int(effect.get("created_at_game_time_seconds"), 0),
                str(effect.get("created_at") or ""),
            )
        )
        return riders

    @classmethod
    def _get_next_weapon_hit_pending_attack_flags(
        cls,
        attacker: dict,
    ) -> tuple[bool, bool]:
        pending_attack = attacker.get("pending_attack") if isinstance(attacker, dict) else None
        if not isinstance(pending_attack, dict):
            return False, False
        return (
            pending_attack.get("is_weapon_attack") is True,
            pending_attack.get("is_ranged_weapon") is True,
        )

    @classmethod
    def _target_has_large_or_larger_ensnaring_save_advantage(
        cls,
        target_participant: dict,
    ) -> bool:
        size_value = target_participant.get("effective_size") or target_participant.get("base_size")
        return normalize_size_category(size_value) in {
            SizeCategory.LARGE,
            SizeCategory.HUGE,
            SizeCategory.GARGANTUAN,
        }

    @classmethod
    def _merge_advantage_modes(
        cls,
        base_mode: str,
        *,
        extra_advantage: bool = False,
        extra_disadvantage: bool = False,
    ) -> str:
        if extra_advantage:
            if base_mode == "normal":
                base_mode = "advantage"
            elif base_mode == "disadvantage":
                base_mode = "normal"
        if extra_disadvantage:
            if base_mode == "normal":
                base_mode = "disadvantage"
            elif base_mode == "advantage":
                base_mode = "normal"
        return base_mode

    @classmethod
    async def _resolve_ensnaring_strike_weapon_hit(
        cls,
        db: Session,
        session_id: str,
        *,
        state: CombatState,
        attacker: dict,
        target_participant: dict,
        rider_effect: dict,
    ) -> dict:
        rider_metadata = cls._get_effect_metadata(rider_effect)
        spell_name = str(rider_metadata.get("source_spell_name") or "Ensnaring Strike")
        save_dc = cls._safe_int(rider_metadata.get("save_dc"), 0)
        if save_dc <= 0:
            raise CombatServiceError("Ensnaring Strike rider is missing a valid save DC.", 400)

        save_mod = modify_saving_throw(
            target_participant,
            "strength",
            source_participant=attacker,
            source_kind="participant",
        )
        advantage_mode = cls._merge_advantage_modes(
            save_mod.result,
            extra_advantage=cls._target_has_large_or_larger_ensnaring_save_advantage(target_participant),
        )
        roll_result = resolve_saving_throw(
            cls._build_roll_actor_stats_for_save(
                db,
                session_id,
                target_participant["ref_id"],
                target_participant["kind"],
                target_participant["display_name"],
            ),
            ability="strength",
            advantage_mode=advantage_mode,
            dc=save_dc,
            roll_source="system",
        )
        roll_result.check_modifier_sources = [
            *save_mod.advantage_source_details,
            *save_mod.disadvantage_source_details,
            *(roll_result.check_modifier_sources or []),
        ]
        is_saved = False if save_mod.auto_fail else bool(roll_result.success)
        concentration_group = rider_metadata.get("concentration_group")
        if not isinstance(concentration_group, str) or not concentration_group.strip():
            raise CombatServiceError("Ensnaring Strike rider is missing a concentration group.", 400)

        if is_saved:
            removed = cls._remove_effect_group(
                state,
                concentration_group=concentration_group,
            )
            if removed["removed_effects"]:
                flag_modified(state, "participants")
            return {
                "spell_key": "ensnaring_strike",
                "spell_name": spell_name,
                "triggered": True,
                "effect_applied": False,
                "is_saved": True,
                "roll_result": roll_result,
                "save_dc": save_dc,
                "log_suffix": (
                    f" {target_participant['display_name']} resistiu ao {spell_name} "
                    f"(Força {roll_result.total} vs CD {save_dc})."
                ),
            }

        target_effect = cls._build_ensnaring_strike_target_effect(
            caster_participant_id=attacker["id"],
            spell_name=spell_name,
            concentration_group=concentration_group,
            save_dc=save_dc,
        )
        cls._append_effect_to_participant(target_participant, target_effect)
        flag_modified(state, "participants")
        return {
            "spell_key": "ensnaring_strike",
            "spell_name": spell_name,
            "triggered": True,
            "effect_applied": True,
            "is_saved": False,
            "roll_result": roll_result,
            "save_dc": save_dc,
            "source_effect_id": target_effect.get("id"),
            "log_suffix": (
                f" {target_participant['display_name']} falhou no save de Força "
                f"({roll_result.total} vs CD {save_dc}) e ficou restrained por {spell_name}."
            ),
        }

    @classmethod
    def _collect_hail_of_thorns_secondary_targets(
        cls,
        *,
        state: CombatState,
        origin_target: dict,
    ) -> tuple[list[dict], list[str]]:
        affected_targets: list[dict] = [origin_target]
        skipped_missing_distance: list[str] = []
        origin_ref_id = origin_target.get("ref_id")
        if not isinstance(origin_ref_id, str):
            return affected_targets, skipped_missing_distance

        local_distances = state.local_distances if isinstance(state.local_distances, dict) else {}
        origin_distances = local_distances.get(origin_ref_id) if isinstance(local_distances.get(origin_ref_id), dict) else {}

        for participant in state.participants or []:
            if participant.get("id") == origin_target.get("id"):
                continue
            if participant.get("status") == "dead":
                continue
            ref_id = participant.get("ref_id")
            if not isinstance(ref_id, str):
                continue
            distance = origin_distances.get(ref_id) if isinstance(origin_distances, dict) else None
            if not isinstance(distance, (int, float)):
                skipped_missing_distance.append(ref_id)
                continue
            if float(distance) <= 1.5:
                affected_targets.append(participant)

        return affected_targets, skipped_missing_distance

    @classmethod
    async def _resolve_hail_of_thorns_weapon_hit(
        cls,
        db: Session,
        session_id: str,
        *,
        state: CombatState,
        attacker: dict,
        target_participant: dict,
        rider_effect: dict,
    ) -> dict:
        rider_metadata = cls._get_effect_metadata(rider_effect)
        spell_name = str(rider_metadata.get("source_spell_name") or "Hail of Thorns")
        save_dc = cls._safe_int(rider_metadata.get("save_dc"), 0)
        if save_dc <= 0:
            raise CombatServiceError("Hail of Thorns rider is missing a valid save DC.", 400)
        effect_dice = str(rider_metadata.get("effect_dice") or "").strip()
        if not effect_dice:
            raise CombatServiceError("Hail of Thorns rider is missing damage dice.", 400)
        concentration_group = rider_metadata.get("concentration_group")
        if not isinstance(concentration_group, str) or not concentration_group.strip():
            raise CombatServiceError("Hail of Thorns rider is missing a concentration group.", 400)

        burst_targets, skipped_missing_distance = cls._collect_hail_of_thorns_secondary_targets(
            state=state,
            origin_target=target_participant,
        )

        outcomes: list[dict] = []
        hp_updates: list[dict] = []
        log_lines = [f" {spell_name} explodiu ao redor de {target_participant['display_name']}."]

        for burst_target in burst_targets:
            save_mod = modify_saving_throw(
                burst_target,
                "dexterity",
                source_participant=attacker,
                source_kind="participant",
            )
            roll_result = resolve_saving_throw(
                cls._build_roll_actor_stats_for_save(
                    db,
                    session_id,
                    burst_target["ref_id"],
                    burst_target["kind"],
                    burst_target["display_name"],
                ),
                ability="dexterity",
                advantage_mode=save_mod.result,
                dc=save_dc,
                roll_source="system",
            )
            roll_result.check_modifier_sources = [
                *save_mod.advantage_source_details,
                *save_mod.disadvantage_source_details,
                *(roll_result.check_modifier_sources or []),
            ]
            is_saved = False if save_mod.auto_fail else bool(roll_result.success)
            rolled_damage = max(0, _roll_dice_expression(effect_dice))
            applied_damage = rolled_damage // 2 if is_saved else rolled_damage
            new_hp = previous_hp = concentration_check = None
            effect_msg = ""
            if applied_damage > 0:
                new_hp, effect_msg, previous_hp, concentration_check = cls._apply_damage_to_target(
                    db,
                    burst_target["ref_id"],
                    burst_target["kind"],
                    applied_damage,
                    damage_type="piercing",
                    is_magical_damage=True,
                    is_crit=False,
                    state=state,
                    attacker_participant_id=attacker.get("id"),
                )
                hp_updates.append(
                    {
                        "target_ref_id": burst_target["ref_id"],
                        "target_kind": burst_target["kind"],
                        "previous_hp": previous_hp,
                        "new_hp": new_hp,
                    }
                )
            concentration_summary = (
                f" {concentration_check['summary_text']}"
                if isinstance(concentration_check, dict)
                and isinstance(concentration_check.get("summary_text"), str)
                else ""
            )
            log_lines.append(
                f" {burst_target['display_name']}: DEX {roll_result.total} vs CD {save_dc}, "
                f"{'passou' if is_saved else 'falhou'} e sofreu {applied_damage} dano perfurante."
                f"{effect_msg}{concentration_summary}"
            )
            outcomes.append(
                {
                    "target_ref_id": burst_target["ref_id"],
                    "target_kind": burst_target["kind"],
                    "target_display_name": burst_target["display_name"],
                    "is_saved": is_saved,
                    "roll_result": roll_result,
                    "rolled_damage": rolled_damage,
                    "damage_applied": applied_damage,
                    "concentration_check": concentration_check,
                }
            )

        removed = cls._remove_effect_group(
            state,
            concentration_group=concentration_group,
        )
        if removed["removed_effects"]:
            flag_modified(state, "participants")

        return {
            "spell_key": "hail_of_thorns",
            "spell_name": spell_name,
            "triggered": True,
            "effect_applied": True,
            "affected_targets": outcomes,
            "hp_updates": hp_updates,
            "skipped_missing_distance": skipped_missing_distance,
            "log_suffix": "\n".join(log_lines),
        }

    @classmethod
    async def resolve_next_weapon_hit_riders(
        cls,
        db: Session,
        session_id: str,
        *,
        state: CombatState,
        attacker: dict,
        target_participant: dict | None,
        is_weapon_attack: bool,
    ) -> dict:
        if not is_weapon_attack or not isinstance(target_participant, dict):
            return {"log_suffix": ""}

        riders = cls._list_next_weapon_hit_riders(attacker)
        if not riders:
            return {"log_suffix": ""}

        _, is_ranged_weapon = cls._get_next_weapon_hit_pending_attack_flags(attacker)

        # V1 contract: resolve only the first matching rider in creation order.
        for rider in riders:
            rider_metadata = cls._get_effect_metadata(rider)
            if rider_metadata.get("weapon_attack_only") is True and not is_weapon_attack:
                continue
            if rider_metadata.get("ranged_weapon_attack_only") is True and not is_ranged_weapon:
                continue
            spell_key = str(rider_metadata.get("source_spell_key") or "").strip().lower()
            if spell_key == "ensnaring_strike":
                removed = cls._consume_effect_ids(attacker, [str(rider.get("id") or "")])
                if removed:
                    flag_modified(state, "participants")
                return await cls._resolve_ensnaring_strike_weapon_hit(
                    db,
                    session_id,
                    state=state,
                    attacker=attacker,
                    target_participant=target_participant,
                    rider_effect=rider,
                )
            if spell_key == "hail_of_thorns":
                removed = cls._consume_effect_ids(attacker, [str(rider.get("id") or "")])
                if removed:
                    flag_modified(state, "participants")
                return await cls._resolve_hail_of_thorns_weapon_hit(
                    db,
                    session_id,
                    state=state,
                    attacker=attacker,
                    target_participant=target_participant,
                    rider_effect=rider,
                )

        return {"log_suffix": ""}

    @classmethod
    async def resolve_ensnaring_strike_start_turn(
        cls,
        db: Session,
        session_id: str,
        *,
        state: CombatState,
        participant: dict,
    ) -> list[dict]:
        outcomes: list[dict] = []
        for effect in cls._get_participant_effects(participant):
            metadata = cls._get_effect_metadata(effect)
            if effect.get("kind") != "condition":
                continue
            if effect.get("condition_type") != "restrained":
                continue
            if metadata.get("source_spell_key") != "ensnaring_strike":
                continue
            if metadata.get("effect_role") != "persistent_spell_condition":
                continue
            if metadata.get("recurring_damage_timing") != "start_of_target_turn":
                continue
            damage_formula = str(metadata.get("recurring_damage_dice") or "").strip()
            damage_type = str(metadata.get("recurring_damage_type") or "").strip()
            if not damage_formula or not damage_type:
                continue
            rolled_damage = max(0, _roll_dice_expression(damage_formula))
            new_hp = previous_hp = concentration_check = None
            effect_msg = ""
            if rolled_damage > 0:
                new_hp, effect_msg, previous_hp, concentration_check = cls._apply_damage_to_target(
                    db,
                    participant["ref_id"],
                    participant["kind"],
                    rolled_damage,
                    damage_type=damage_type,
                    is_magical_damage=True,
                    is_crit=False,
                    state=state,
                    attacker_participant_id=effect.get("source_participant_id"),
                )
            spell_name = metadata.get("source_spell_name") or "Ensnaring Strike"
            await cls._emit_log(
                session_id,
                {
                    "message": (
                        f"{participant['display_name']} sofreu {rolled_damage} de dano {damage_type} "
                        f"de {spell_name} no início do turno.{effect_msg}"
                    ),
                    "source": "ensnaring_strike",
                },
            )
            outcomes.append(
                {
                    "source_effect_id": effect.get("id"),
                    "damage": rolled_damage,
                    "damage_type": damage_type,
                    "previous_hp": previous_hp,
                    "new_hp": new_hp,
                    "concentration_check": concentration_check,
                }
            )
        return outcomes

    @classmethod
    async def _cast_ensnaring_strike_automation(
        cls,
        db: Session,
        session_id: str,
        *,
        attacker: dict,
        attacker_model,
        actor_user_id: str,
        is_gm: bool,
        req,
        state: CombatState,
        spell_context: dict,
        target_participant: dict | None,
    ) -> dict:
        if getattr(req, "variant_key", None):
            raise CombatServiceError("Ensnaring Strike não possui variantes.", 400)

        result = cls._clear_concentration_for_source(
            state,
            source_participant_id=attacker["id"],
            db=db,
        )
        cls._sync_area_effects_if_changed(
            session_id,
            state,
            result["removed_area_effects"],
        )

        spell_name = spell_context["spell_name"]
        save_dc = cls._safe_int(spell_context.get("save_dc"), 0)
        if save_dc <= 0:
            raise CombatServiceError("Ensnaring Strike requires a valid spell save DC.", 400)

        concentration_group = str(uuid4())
        marker = cls._build_ensnaring_strike_concentration_marker(
            caster_participant_id=attacker["id"],
            spell_name=spell_name,
            concentration_group=concentration_group,
        )
        rider = cls._build_ensnaring_strike_rider_effect(
            caster_participant_id=attacker["id"],
            spell_name=spell_name,
            concentration_group=concentration_group,
            save_dc=save_dc,
        )
        cls._append_effect_to_participant(attacker, marker)
        cls._append_effect_to_participant(attacker, rider)
        flag_modified(state, "participants")

        summary_text = (
            f"{spell_name} armada: o próximo ataque com arma que acertar tentará enredar o alvo."
        )
        if result["removed_effects"] or result["removed_area_effects"]:
            summary_text += " A concentração anterior terminou."

        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=attacker["display_name"],
            target_kind=attacker["kind"],
            summary_text=summary_text,
            log_message=(
                f"{attacker['display_name']} conjurou {spell_name} sobre si e armou o próximo ataque com arma."
            ),
            extra={
                "concentration_group": concentration_group,
                "effect_applied": True,
                "rider_armed": True,
                "save_dc": save_dc,
            },
        )

    @classmethod
    async def _cast_hail_of_thorns_automation(
        cls,
        db: Session,
        session_id: str,
        *,
        attacker: dict,
        attacker_model,
        actor_user_id: str,
        is_gm: bool,
        req,
        state: CombatState,
        spell_context: dict,
        target_participant: dict | None,
    ) -> dict:
        if getattr(req, "variant_key", None):
            raise CombatServiceError("Hail of Thorns não possui variantes.", 400)

        result = cls._clear_concentration_for_source(
            state,
            source_participant_id=attacker["id"],
            db=db,
        )
        cls._sync_area_effects_if_changed(
            session_id,
            state,
            result["removed_area_effects"],
        )

        spell_name = spell_context["spell_name"]
        save_dc = cls._safe_int(spell_context.get("save_dc"), 0)
        if save_dc <= 0:
            raise CombatServiceError("Hail of Thorns requires a valid spell save DC.", 400)
        effect_dice = str(spell_context.get("effect_dice") or "").strip()
        if not effect_dice:
            raise CombatServiceError("Hail of Thorns requires effect dice in spell context.", 400)

        concentration_group = str(uuid4())
        marker = cls._build_hail_of_thorns_concentration_marker(
            caster_participant_id=attacker["id"],
            spell_name=spell_name,
            concentration_group=concentration_group,
        )
        rider = cls._build_hail_of_thorns_rider_effect(
            caster_participant_id=attacker["id"],
            spell_name=spell_name,
            concentration_group=concentration_group,
            save_dc=save_dc,
            effect_dice=effect_dice,
        )
        cls._append_effect_to_participant(attacker, marker)
        cls._append_effect_to_participant(attacker, rider)
        flag_modified(state, "participants")

        summary_text = (
            f"{spell_name} armada: o próximo ataque com arma à distância que acertar detonará o burst reativo."
        )
        if result["removed_effects"] or result["removed_area_effects"]:
            summary_text += " A concentração anterior terminou."

        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=attacker["display_name"],
            target_kind=attacker["kind"],
            summary_text=summary_text,
            log_message=(
                f"{attacker['display_name']} conjurou {spell_name} sobre si e armou o próximo ataque com arma à distância."
            ),
            extra={
                "concentration_group": concentration_group,
                "effect_applied": True,
                "rider_armed": True,
                "save_dc": save_dc,
                "effect_dice": effect_dice,
            },
        )

    @classmethod
    async def _cast_entangle_automation(
        cls,
        db: Session,
        session_id: str,
        *,
        attacker: dict,
        attacker_model,
        actor_user_id: str,
        is_gm: bool,
        req,
        state: CombatState,
        spell_context: dict,
        target_participant: dict | None,
    ) -> dict:
        raise CombatServiceError(
            "Entangle is resolved via the area-cast pipeline.",
            400,
        )

    @classmethod
    async def _cast_faerie_fire_automation(
        cls,
        db: Session,
        session_id: str,
        *,
        attacker: dict,
        attacker_model,
        actor_user_id: str,
        is_gm: bool,
        req,
        state: CombatState,
        spell_context: dict,
        target_participant: dict | None,
    ) -> dict:
        raise CombatServiceError(
            "Faerie Fire is resolved via the area-cast pipeline.",
            400,
        )

    @classmethod
    async def _cast_compelled_duel_automation(
        cls,
        db: Session,
        session_id: str,
        *,
        attacker: dict,
        attacker_model,
        actor_user_id: str,
        is_gm: bool,
        req,
        state: CombatState,
        spell_context: dict,
        target_participant: dict | None,
    ) -> dict:
        if target_participant is None:
            raise CombatServiceError("Duelo Compelido requer um alvo.", 400)
        if getattr(req, "variant_key", None):
            raise CombatServiceError("Duelo Compelido não possui variantes.", 400)
        if target_participant["ref_id"] == attacker["ref_id"]:
            raise CombatServiceError(
                "Duelo Compelido deve ser conjurado em outra criatura.", 400
            )

        spell_name = spell_context["spell_name"]
        target_name = target_participant["display_name"]
        save_ability = spell_context.get("save_ability") or "wisdom"
        save_dc = cls._safe_int(spell_context.get("save_dc"), 0)

        save_mod = modify_saving_throw(
            target_participant,
            save_ability,
            source_participant=attacker,
            source_kind="participant",
        )
        roll_result = resolve_saving_throw(
            cls._build_roll_actor_stats_for_save(
                db,
                session_id,
                target_participant["ref_id"],
                target_participant["kind"],
                target_participant["display_name"],
            ),
            ability=save_ability,
            advantage_mode=save_mod.result,
            dc=save_dc,
        )
        roll_result.check_modifier_sources = [
            *save_mod.advantage_source_details,
            *save_mod.disadvantage_source_details,
            *(roll_result.check_modifier_sources or []),
        ]
        roll_result.is_gm_roll = is_gm
        is_saved = bool(roll_result.success)

        concentration_group = None
        if not is_saved:
            # New concentration spell: end the caster's prior concentration first.
            result = cls._clear_concentration_for_source(
                state,
                source_participant_id=attacker["id"],
                db=db,
            )
            cls._sync_area_effects_if_changed(
                session_id, state, result["removed_area_effects"],
            )

            concentration_group = str(uuid4())
            game_time = get_game_time_seconds(session_id, db)
            effect = build_compelled_duel_effect(
                cls._build_combat_spell_effect_context(
                    spell_key="compelled_duel",
                    spell_name=spell_name,
                    caster_participant_id=attacker["id"],
                    target_participant_id=target_participant["id"],
                    game_time_seconds=game_time,
                    duration_seconds=60,
                    concentration=True,
                    concentration_group=concentration_group,
                    spell_save_dc=save_dc,
                    extra_metadata={
                        "duel_caster_ref_id": attacker["ref_id"],
                        "duel_target_ref_id": target_participant["ref_id"],
                    },
                )
            )
            cls._apply_factory_spell_effect_to_target(
                state=state,
                target_participant=target_participant,
                effect=effect,
                source_spell_key="compelled_duel",
            )
            flag_modified(state, "participants")

        if is_saved:
            summary_text = f"{target_name} resistiu ao {spell_name}."
            log_msg = (
                f"{attacker['display_name']} conjurou {spell_name} em {target_name}: "
                f"salvaguarda de Sabedoria bem-sucedida."
            )
        else:
            summary_text = (
                f"{target_name} falhou na salvaguarda e está compelido a duelar com "
                f"{attacker['display_name']}: desvantagem em ataques contra outras criaturas."
            )
            log_msg = (
                f"{attacker['display_name']} conjurou {spell_name} em {target_name}: "
                f"falhou na salvaguarda de Sabedoria."
            )

        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=target_name,
            target_kind=target_participant["kind"],
            action_kind="saving_throw",
            summary_text=summary_text,
            log_message=log_msg,
            extra={
                "is_saved": is_saved,
                "effect_applied": not is_saved,
                "roll": roll_result.total,
                "roll_result": roll_result,
                "save_ability": save_ability,
                "save_dc": spell_context.get("save_dc"),
                "save_success_outcome": "none",
                "concentration": not is_saved,
                "concentration_group": concentration_group,
                "duration_seconds": 60,
            },
        )

    @classmethod
    async def _cast_crown_of_madness_automation(
        cls,
        db: Session,
        session_id: str,
        *,
        attacker: dict,
        attacker_model,
        actor_user_id: str,
        is_gm: bool,
        req,
        state: CombatState,
        spell_context: dict,
        target_participant: dict | None,
    ) -> dict:
        if target_participant is None:
            raise CombatServiceError("Coroa da Loucura requer um alvo.", 400)
        if getattr(req, "variant_key", None):
            raise CombatServiceError("Coroa da Loucura não possui variantes.", 400)
        if target_participant["ref_id"] == attacker["ref_id"]:
            raise CombatServiceError("Coroa da Loucura deve ser conjurada em outra criatura.", 400)

        creature_type = cls.resolve_effective_creature_type(db, session_id, target_participant)
        if creature_type is not None and creature_type != "humanoid":
            raise CombatServiceError("Crown of Madness can only target humanoids.", 400)

        spell_name = spell_context["spell_name"]
        target_name = target_participant["display_name"]
        save_ability = spell_context.get("save_ability") or "wisdom"
        save_dc = cls._safe_int(spell_context.get("save_dc"), 0)

        save_mod = modify_saving_throw(
            target_participant,
            save_ability,
            source_participant=attacker,
            source_kind="participant",
        )
        roll_result = resolve_saving_throw(
            cls._build_roll_actor_stats_for_save(
                db,
                session_id,
                target_participant["ref_id"],
                target_participant["kind"],
                target_participant["display_name"],
            ),
            ability=save_ability,
            advantage_mode=save_mod.result,
            dc=save_dc,
        )
        roll_result.check_modifier_sources = [
            *save_mod.advantage_source_details,
            *save_mod.disadvantage_source_details,
            *(roll_result.check_modifier_sources or []),
        ]
        roll_result.is_gm_roll = is_gm
        is_saved = bool(roll_result.success)

        if is_saved:
            return cls._base_spell_result(
                spell_name=spell_name,
                spell_context=spell_context,
                target_display_name=target_name,
                target_kind=target_participant["kind"],
                action_kind="saving_throw",
                summary_text=f"{target_name} resistiu à {spell_name}.",
                log_message=(
                    f"{attacker['display_name']} conjurou {spell_name} em {target_name}: "
                    "salvaguarda de Sabedoria bem-sucedida."
                ),
                extra={
                    "is_saved": True,
                    "effect_applied": False,
                    "roll": roll_result.total,
                    "roll_result": roll_result,
                    "save_ability": save_ability,
                    "save_dc": save_dc,
                    "save_success_outcome": "none",
                },
            )

        if has_condition_immunity_from_source(target_participant, "charmed", source_participant=attacker):
            return cls._base_spell_result(
                spell_name=spell_name,
                spell_context=spell_context,
                target_display_name=target_name,
                target_kind=target_participant["kind"],
                action_kind="saving_throw",
                summary_text=f"{spell_name} não teve efeito em {target_name} (alvo protegido).",
                log_message=(
                    f"{attacker['display_name']} conjurou {spell_name} em {target_name}; "
                    "o alvo está protegido contra encantamentos dessa criatura."
                ),
                extra={
                    "is_saved": False,
                    "effect_applied": False,
                    "condition_applied": False,
                    "blocked_by_condition_immunity": True,
                    "roll": roll_result.total,
                    "roll_result": roll_result,
                    "save_ability": save_ability,
                    "save_dc": save_dc,
                    "save_success_outcome": "none",
                },
            )

        result = cls._clear_concentration_for_source(
            state,
            source_participant_id=attacker["id"],
            db=db,
        )
        cls._sync_area_effects_if_changed(session_id, state, result["removed_area_effects"])

        concentration_group = str(uuid4())
        game_time = get_game_time_seconds(session_id, db)
        duration_seconds = cls._safe_int(spell_context.get("duration_seconds"), 60)
        crown_effect = build_crown_of_madness_effect(
            cls._build_combat_spell_effect_context(
                spell_key="crown_of_madness",
                spell_name=spell_name,
                caster_participant_id=attacker["id"],
                target_participant_id=target_participant["id"],
                game_time_seconds=game_time,
                duration_seconds=duration_seconds,
                concentration=True,
                concentration_group=concentration_group,
                spell_save_dc=save_dc,
                extra_metadata={
                    "cast_round": state.round,
                    "cast_turn_participant_id": attacker.get("id"),
                    "target_ref_id": target_participant.get("ref_id"),
                },
            )
        )
        cls._append_effect_to_participant(target_participant, crown_effect)
        cls._append_effect_to_participant(
            target_participant,
            cls._build_active_effect(
                kind="condition",
                condition_type="charmed",
                source_participant_id=attacker["id"],
                duration_type="timed",
                created_at_game_time_seconds=game_time,
                expires_at_game_time_seconds=game_time + duration_seconds,
                metadata={
                    "source_spell_key": "crown_of_madness",
                    "source_spell_name": spell_name,
                    "source_effect_id": crown_effect.get("id"),
                    "concentration": True,
                    "concentration_group": concentration_group,
                    "caster_participant_id": attacker["id"],
                    "charmer_participant_id": attacker["id"],
                },
                display_label="Charmed (Crown of Madness)",
            ),
        )
        flag_modified(state, "participants")

        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=target_name,
            target_kind=target_participant["kind"],
            action_kind="saving_throw",
            summary_text=f"{target_name} falhou na salvaguarda e ficou sob Coroa da Loucura.",
            log_message=(
                f"{attacker['display_name']} conjurou {spell_name} em {target_name}: "
                "falhou na salvaguarda de Sabedoria."
            ),
            extra={
                "is_saved": False,
                "effect_applied": True,
                "condition_applied": "charmed",
                "roll": roll_result.total,
                "roll_result": roll_result,
                "save_ability": save_ability,
                "save_dc": save_dc,
                "save_success_outcome": "none",
                "concentration": True,
                "concentration_group": concentration_group,
                "duration_seconds": duration_seconds,
            },
        )

    @classmethod
    async def resolve_crown_of_madness_forced_attack(
        cls,
        db: Session,
        session_id: str,
        *,
        actor_user_id: str,
        is_gm: bool,
        controlled_target_ref_id: str,
        forced_attack_target_ref_id: str | None,
        weapon_item_id: str | None = None,
        combat_action_id: str | None = None,
    ) -> dict:
        state = cls.get_state(db, session_id)
        if state is None:
            raise CombatServiceError("No combat active for this session", 404)
        cls._require_active(state)

        if not is_gm:
            raise CombatServiceError("Only GM can resolve Crown of Madness forced attacks.", 403)

        controlled = next(
            (p for p in state.participants if p.get("ref_id") == controlled_target_ref_id),
            None,
        )
        if controlled is None:
            raise CombatServiceError("Controlled target not found in combat.", 404)
        crown_effect = find_crown_of_madness_effect_on_target(controlled)
        if crown_effect is None:
            raise CombatServiceError("Target is not under Crown of Madness.", 400)
        crown_meta = crown_effect.get("metadata") or {}
        if crown_meta.get("forced_attack_pending") is not True:
            raise CombatServiceError("Forced attack is not pending for this target this turn.", 400)

        current = cls._get_current_participant(state)
        if current.get("id") != controlled.get("id"):
            raise CombatServiceError("Forced attack can only be resolved on the controlled target turn.", 400)

        if forced_attack_target_ref_id is None:
            mark_crown_of_madness_forced_attack_resolved(controlled, skipped=True)
            resources = cls._get_turn_resources(controlled)
            resources["crown_of_madness_forced_attack_pending"] = False
            resources["crown_of_madness_forced_attack_resolved"] = True
            resources["crown_of_madness_forced_attack_skipped"] = True
            controlled["turn_resources"] = resources
            flag_modified(state, "participants")
            db.add(state)
            db.commit()
            db.refresh(state)
            await cls._emit_state(session_id, state)
            await cls._emit_log(
                session_id,
                {
                    "message": (
                        f"{controlled.get('display_name', 'Alvo')} não recebeu alvo válido para Coroa da Loucura "
                        "e pode agir normalmente."
                    ),
                    "source": "crown_of_madness",
                },
            )
            return {
                "resolved": True,
                "skipped": True,
                "actionConsumed": False,
            }

        if forced_attack_target_ref_id == controlled_target_ref_id:
            raise CombatServiceError("Forced attack target cannot be the controlled target itself.", 400)
        forced_target = next(
            (p for p in state.participants if p.get("ref_id") == forced_attack_target_ref_id),
            None,
        )
        if forced_target is None:
            raise CombatServiceError("Forced attack target not found in combat.", 404)

        distances = state.local_distances if isinstance(state.local_distances, dict) else {}
        distance_meters = None
        source_distances = distances.get(controlled_target_ref_id)
        if isinstance(source_distances, dict):
            raw_distance = source_distances.get(forced_attack_target_ref_id)
            if isinstance(raw_distance, (int, float)):
                distance_meters = float(raw_distance)
        if distance_meters is None:
            raise CombatServiceError("Distance between controlled target and forced target is not configured.", 400)
        if distance_meters > 1.5:
            raise CombatServiceError("Forced attack target is out of melee reach.", 400)

        action_result: dict
        if controlled.get("kind") == "player":
            action_result = await cls.attack(
                db,
                session_id,
                CombatAttackRequest(
                    actor_participant_id=controlled.get("id"),
                    target_ref_id=forced_attack_target_ref_id,
                    weapon_item_id=weapon_item_id,
                    has_advantage=False,
                    has_disadvantage=False,
                    roll_source="system",
                ),
                actor_user_id,
                True,
            )
        else:
            if not isinstance(combat_action_id, str) or not combat_action_id.strip():
                raise CombatServiceError(
                    "combat_action_id is required for forced attacks by session entities.",
                    400,
                )
            action_result = await cls.entity_action(
                db,
                session_id,
                CombatEntityActionRequest(
                    actor_participant_id=controlled.get("id"),
                    target_ref_id=forced_attack_target_ref_id,
                    combat_action_id=combat_action_id.strip(),
                    has_advantage=False,
                    has_disadvantage=False,
                    roll_source="system",
                ),
                actor_user_id,
                True,
            )

        state = cls.get_state(db, session_id)
        if state is None:
            raise CombatServiceError("No combat active for this session", 404)
        controlled_after = next(
            (p for p in state.participants if p.get("ref_id") == controlled_target_ref_id),
            None,
        )
        if controlled_after is None:
            raise CombatServiceError("Controlled target not found after action resolution.", 404)
        mark_crown_of_madness_forced_attack_resolved(controlled_after, skipped=False)
        resources = cls._get_turn_resources(controlled_after)
        resources["crown_of_madness_forced_attack_pending"] = False
        resources["crown_of_madness_forced_attack_resolved"] = True
        resources["crown_of_madness_forced_attack_skipped"] = False
        controlled_after["turn_resources"] = resources
        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_state(session_id, state)
        return {
            "resolved": True,
            "skipped": False,
            "actionConsumed": True,
            "attackResult": action_result,
        }

    @classmethod
    async def resolve_crown_of_madness_maintain(
        cls,
        db: Session,
        session_id: str,
        *,
        actor_user_id: str,
        is_gm: bool,
        actor_participant_id: str | None,
        target_ref_id: str,
        override_resource_limit: bool = False,
    ) -> dict:
        state = cls.get_state(db, session_id)
        if state is None:
            raise CombatServiceError("No combat active for this session", 404)
        cls._require_active(state)
        caster = cls._resolve_actor_participant(
            state, actor_user_id, is_gm, actor_participant_id,
        )
        cls._require_actor_status(caster, ("active",), "Only active participants can maintain Crown of Madness.")
        cls._require_action_capable(caster)

        target = next((p for p in state.participants if p.get("ref_id") == target_ref_id), None)
        if target is None:
            raise CombatServiceError("Crown target not found in combat.", 404)
        effect = find_crown_of_madness_effect_on_target(target)
        if effect is None:
            raise CombatServiceError("Target is not under Crown of Madness.", 400)
        if effect.get("source_participant_id") != caster.get("id"):
            raise CombatServiceError("Only the original caster can maintain this Crown of Madness.", 403)

        was_overridden = cls._consume_turn_resource(
            caster,
            "action",
            is_gm=is_gm,
            override_resource_limit=override_resource_limit,
        )
        metadata = effect.get("metadata") or {}
        metadata["last_maintained_round"] = state.round
        metadata["last_maintained_turn_participant_id"] = caster.get("id")
        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_state(session_id, state)
        await cls._emit_log(
            session_id,
            {
                "message": (
                    f"{caster.get('display_name', 'Conjurador')} manteve Coroa da Loucura sobre "
                    f"{target.get('display_name', 'alvo')}."
                ),
                "source": "crown_of_madness",
                "is_override": was_overridden,
                "overridden_resource": "action" if was_overridden else None,
            },
        )
        return {
            "maintained": True,
            "actionConsumed": True,
            "isOverride": was_overridden,
            "targetRefId": target_ref_id,
        }

    @classmethod
    def _apply_crown_of_madness_turn_start_state(
        cls,
        state: CombatState,
        participant: dict,
    ) -> bool:
        changed = mark_crown_of_madness_forced_attack_pending(participant)
        return bool(changed)

    @classmethod
    async def _resolve_crown_of_madness_maintenance_on_turn_end(
        cls,
        db: Session,
        session_id: str,
        state: CombatState,
        outgoing: dict,
    ) -> None:
        caster_id = outgoing.get("id")
        if not isinstance(caster_id, str) or not caster_id:
            return
        removed_any = False
        for _target, effect in get_crown_of_madness_effects_for_caster(state, caster_participant_id=caster_id):
            metadata = effect.get("metadata") or {}
            cast_round = cls._safe_int(metadata.get("cast_round"), 0)
            cast_turn_participant_id = metadata.get("cast_turn_participant_id")
            if cast_round == state.round and cast_turn_participant_id == outgoing.get("id"):
                continue
            last_round = cls._safe_int(metadata.get("last_maintained_round"), 0)
            last_turn_participant_id = metadata.get("last_maintained_turn_participant_id")
            maintained_this_turn = (
                last_round == state.round and last_turn_participant_id == outgoing.get("id")
            )
            if maintained_this_turn:
                continue
            group = metadata.get("concentration_group")
            source_effect_id = effect.get("id")
            removed = remove_crown_of_madness_instance(
                state,
                concentration_group=group if isinstance(group, str) else None,
                source_effect_id=source_effect_id if isinstance(source_effect_id, str) else None,
            )
            if removed:
                removed_any = True
        if removed_any:
            flag_modified(state, "participants")
            await cls._emit_log(
                session_id,
                {
                    "message": (
                        f"Coroa da Loucura terminou porque {outgoing.get('display_name', 'o conjurador')} "
                        "não usou a ação para manter o efeito."
                    ),
                    "source": "crown_of_madness",
                },
            )

    @classmethod
    async def _resolve_crown_of_madness_repeat_save_on_turn_end(
        cls,
        db: Session,
        session_id: str,
        state: CombatState,
        outgoing: dict,
    ) -> None:
        effect = find_crown_of_madness_effect_on_target(outgoing)
        if effect is None:
            return
        metadata = effect.get("metadata") or {}
        ability = str(metadata.get("repeat_save_ability") or "wisdom").strip().lower()
        dc = cls._safe_int(metadata.get("repeat_save_dc"), 0)
        if dc <= 0:
            return

        source_id = effect.get("source_participant_id")
        source_participant = next((p for p in state.participants if p.get("id") == source_id), None)
        save_mod = modify_saving_throw(
            outgoing,
            ability,
            source_participant=source_participant if isinstance(source_participant, dict) else None,
            source_kind="participant" if isinstance(source_participant, dict) else "passive_condition",
        )
        roll_result = resolve_saving_throw(
            cls._build_roll_actor_stats_for_save(
                db,
                session_id,
                outgoing["ref_id"],
                outgoing["kind"],
                outgoing["display_name"],
            ),
            ability=ability,
            advantage_mode=save_mod.result,
            dc=dc,
            roll_source="system",
        )
        roll_result.check_modifier_sources = [
            *save_mod.advantage_source_details,
            *save_mod.disadvantage_source_details,
            *(roll_result.check_modifier_sources or []),
        ]
        is_saved = False if save_mod.auto_fail else bool(roll_result.success)
        if is_saved:
            removed = remove_crown_of_madness_instance(
                state,
                concentration_group=metadata.get("concentration_group")
                if isinstance(metadata.get("concentration_group"), str)
                else None,
                source_effect_id=effect.get("id") if isinstance(effect.get("id"), str) else None,
            )
            if removed:
                flag_modified(state, "participants")
            await cls._emit_log(
                session_id,
                {
                    "message": f"{outgoing['display_name']} resiste à Coroa da Loucura e o efeito termina.",
                    "source": "repeat_save_resolve",
                },
            )
        else:
            await cls._emit_log(
                session_id,
                {
                    "message": f"{outgoing['display_name']} falha na salvaguarda e permanece sob a Coroa da Loucura.",
                    "source": "repeat_save_resolve",
                },
            )

    @classmethod
    async def resolve_compelled_duel_movement_save(
        cls,
        db: Session,
        session_id: str,
        *,
        actor_participant_id: str | None,
        actor_user_id: str,
        is_gm: bool,
        manual_roll: int | None = None,
    ) -> dict:
        """GM-adjudicated Wisdom save when a compelled target tries to move >9m
        from the caster. On success, movement is unrestricted for the rest of the
        actor's turn (a per-turn flag, reset at turn start)."""
        state = cls.get_state(db, session_id)
        if state is None:
            raise CombatServiceError("No combat active for this session", 404)
        cls._require_active(state)

        actor = cls._resolve_actor_participant(state, actor_user_id, is_gm, actor_participant_id)
        effect = find_compelled_duel_effect_on_target(actor)
        if effect is None:
            raise CombatServiceError("Esta criatura não está sob Duelo Compelido.", 400)

        metadata = effect.get("metadata") or {}
        save_dc = cls._safe_int(metadata.get("movement_restriction_save_dc"), 0)
        actor_name = actor.get("display_name") or "Alvo"

        resources = cls._get_turn_resources(actor)
        if resources.get("compelled_duel_movement_free"):
            return {
                "allowed": True,
                "rolled": False,
                "already_free_this_turn": True,
                "save_dc": save_dc,
            }

        save_mod = modify_saving_throw(
            actor,
            "wisdom",
            source_kind="passive_condition",
        )
        roll_result = resolve_saving_throw(
            cls._build_roll_actor_stats_for_save(
                db,
                session_id,
                actor["ref_id"],
                actor["kind"],
                actor_name,
            ),
            ability="wisdom",
            advantage_mode=save_mod.result,
            dc=save_dc,
            manual_roll=manual_roll,
        )
        cls._apply_flat_save_effect_bonus_to_roll_result(participant=actor, roll_result=roll_result)
        roll_result.is_gm_roll = is_gm
        succeeded = bool(roll_result.success)

        if succeeded:
            resources["compelled_duel_movement_free"] = True
            actor["turn_resources"] = resources
            flag_modified(state, "participants")
            db.add(state)
            db.commit()
            db.refresh(state)
            await cls._emit_state(session_id, state)
            await cls._emit_log(
                session_id,
                {
                    "message": (
                        f"{actor_name} passou na salvaguarda de Sabedoria (CD {save_dc}) do "
                        f"Duelo Compelido e pode se mover livremente neste turno."
                    ),
                    "source": "compelled_duel",
                },
            )
        else:
            await cls._emit_log(
                session_id,
                {
                    "message": (
                        f"{actor_name} falhou na salvaguarda de Sabedoria (CD {save_dc}) do "
                        f"Duelo Compelido e não pode se mover a mais de 9m do conjurador."
                    ),
                    "source": "compelled_duel",
                },
            )

        return {
            "allowed": succeeded,
            "rolled": True,
            "save_ability": "wisdom",
            "save_dc": save_dc,
            "roll": roll_result.total,
            "roll_result": roll_result,
        }
