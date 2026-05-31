"""Per-spell area-cast handler extracted from cast_area.py (mixin).

Composed into CombatService via CastAreaMixin; methods resolve through the MRO.
"""
from __future__ import annotations

from typing import Any, TYPE_CHECKING
from uuid import uuid4
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session
from app.models.combat import CombatState
from app.schemas.combat import CombatCastSpellRequest
from app.services.game_time import get_game_time_seconds
from ..condition_effects_predicates import has_condition_immunity_from_source
from ..exceptions import _roll_dice_expression
from ..host_protocol import CombatServiceHostProtocol

if TYPE_CHECKING:
    _AreaMixinBase = CombatServiceHostProtocol
else:
    _AreaMixinBase = object


class SleepAreaMixin(_AreaMixinBase):
    @classmethod
    def _participant_has_unconscious(cls, participant: dict) -> bool:
        for effect in cls._get_participant_effects(participant):
            if (
                effect.get("kind") == "condition"
                and str(effect.get("condition_type") or "").strip().lower() == "unconscious"
            ):
                return True
        return False

    @classmethod
    async def _cast_sleep_area(
        cls,
        db: Session,
        session_id: str,
        *,
        req: CombatCastSpellRequest,
        attacker: dict,
        actor_user_id: str,
        is_gm: bool,
        state: CombatState,
        spell_context: dict[str, Any],
        area_spec: dict[str, int | str],
        targeting_result,
        was_overridden: bool,
    ) -> dict[str, Any]:
        game_time = get_game_time_seconds(session_id, db)
        duration_seconds = cls._safe_int(spell_context.get("duration_seconds"), 60)
        source_effect_id = f"sleep:{uuid4()}"

        # Upcast: 5d8 base + 2d8 per slot above 1st.
        slot_level = cls._safe_int(spell_context.get("slot_level"), 1) or 1
        dice_count = 5 + 2 * max(0, slot_level - 1)
        pool_dice = f"{dice_count}d8"
        pool_total = _roll_dice_expression(pool_dice)
        remaining_pool = pool_total

        affected_participants = [
            participant
            for participant in state.participants
            if participant["ref_id"] in targeting_result.affected_target_ref_ids
        ]

        # Pure-RAW scope: no hostility guardrails. Filter only by Sleep eligibility,
        # then order the eligible creatures by ascending current HP.
        skipped: list[dict[str, Any]] = []
        eligible: list[tuple[dict, int]] = []
        for participant in affected_participants:
            if cls._participant_has_unconscious(participant):
                skipped.append({
                    "target_ref_id": participant["ref_id"],
                    "target_display_name": participant.get("display_name"),
                    "reason": "already_unconscious",
                })
                continue
            if cls.resolve_effective_creature_type(db, session_id, participant) == "undead":
                skipped.append({
                    "target_ref_id": participant["ref_id"],
                    "target_display_name": participant.get("display_name"),
                    "reason": "creature_type_undead",
                })
                continue
            if has_condition_immunity_from_source(
                participant, "charmed", source_participant=attacker
            ):
                skipped.append({
                    "target_ref_id": participant["ref_id"],
                    "target_display_name": participant.get("display_name"),
                    "reason": "immune_to_charmed",
                })
                continue
            current_hp, _max_hp = cls._get_target_hp_snapshot(
                db, session_id, participant["ref_id"], participant["kind"]
            )
            current_hp = cls._safe_int(current_hp, 0)
            if current_hp <= 0:
                skipped.append({
                    "target_ref_id": participant["ref_id"],
                    "target_display_name": participant.get("display_name"),
                    "reason": "no_hp",
                })
                continue
            eligible.append((participant, current_hp))

        eligible.sort(key=lambda pair: pair[1])

        affected: list[dict[str, Any]] = []
        for participant, current_hp in eligible:
            if current_hp > remaining_pool:
                # Higher-HP creatures also won't fit; stop selecting.
                break
            cls._append_effect_to_participant(
                participant,
                cls._build_active_effect(
                    kind="condition",
                    condition_type="unconscious",
                    source_participant_id=attacker["id"],
                    duration_type="timed",
                    created_at_game_time_seconds=game_time,
                    expires_at_game_time_seconds=game_time + duration_seconds,
                    metadata={
                        "source_spell_key": "sleep",
                        "source_spell_name": spell_context["spell_name"],
                        "source_effect_id": source_effect_id,
                        "wakes_on_damage": True,
                        "wakes_on_action": True,
                        "hp_at_cast": current_hp,
                    },
                    display_label="Unconscious (Sleep)",
                ),
            )
            remaining_pool -= current_hp
            affected.append({
                "target_ref_id": participant["ref_id"],
                "target_display_name": participant.get("display_name"),
                "target_kind": participant["kind"],
                "current_hp": current_hp,
                "condition_applied": "unconscious",
            })

        if affected:
            flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_state(session_id, state)

        log_lines = [
            f"{attacker['display_name']} conjurou {spell_context['spell_name']} "
            f"({pool_dice} = {pool_total} PV de sono).",
        ]
        for outcome in affected:
            log_lines.append(
                f"  {outcome['target_display_name']}: adormeceu "
                f"({outcome['current_hp']} PV)."
            )
        for outcome in skipped:
            log_lines.append(
                f"  {outcome['target_display_name']}: não afetado ({outcome['reason']})."
            )
        log_message = "\n".join(log_lines)
        action_cost = spell_context.get("action_cost") or "action"
        if was_overridden:
            log_message = f"[OVERRIDE: Limit for '{action_cost}' ignored] {log_message}"
        await cls._emit_and_persist_log(db, session_id, actor_user_id, attacker.get("display_name"), {
            "message": log_message,
            "actorUserId": actor_user_id,
            "source": "gm_override" if is_gm else "player_turn",
            "is_override": was_overridden,
            "overridden_resource": action_cost if was_overridden else None,
        })

        return {
            "spell_name": spell_context["spell_name"],
            "spell_canonical_key": spell_context["spell_canonical_key"],
            "action_kind": "utility",
            "effect_kind": None,
            "damage": 0,
            "healing": 0,
            "damage_type": None,
            "is_critical": False,
            "is_hit": None,
            "is_saved": None,
            "new_hp": None,
            "roll": None,
            "roll_result": None,
            "target_ac": None,
            "target_display_name": "Area effect",
            "target_kind": "session_entity",
            "save_ability": None,
            "save_dc": None,
            "save_success_outcome": None,
            "effect_dice": None,
            "effect_bonus": 0,
            "pending_spell_id": None,
            "effect_roll_required": False,
            "base_effect": None,
            "action_cost": action_cost,
            "summary_text": None,
            "inventory_refresh_required": spell_context.get("source_kind") == "magic_item",
            "material_consumed": bool(spell_context.get("material_consumed")),
            "material_key": spell_context.get("material_key"),
            "material_label": spell_context.get("material_label"),
            "material_quantity": spell_context.get("material_quantity"),
            "material_inventory_item_id": spell_context.get("material_inventory_item_id"),
            "concentration_check": None,
            "concentration_checks": [],
            "area_shape": area_spec["shape"],
            "affected_target_ref_ids": list(targeting_result.affected_target_ref_ids),
            "affected_cells": list(targeting_result.spatial_metadata.affected_cells),
            "area_target_outcomes": [],
            "target_count": len(targeting_result.affected_target_ref_ids),
            "active_area_effect": None,
            "elemental_affinity_eligible": False,
            "elemental_affinity_damage_type": None,
            "elemental_affinity_bonus": None,
            "concentration_group": None,
            "sleep_source_effect_id": source_effect_id,
            "pool_roll": {"dice": pool_dice, "total": pool_total},
            "remaining_pool": remaining_pool,
            "affected": affected,
            "skipped": skipped,
        }
