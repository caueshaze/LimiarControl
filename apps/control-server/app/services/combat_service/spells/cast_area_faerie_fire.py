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
from app.services.combat_service.condition_effects_saves import modify_saving_throw
from app.services.roll_resolution import resolve_saving_throw
from app.services.game_time import get_game_time_seconds
from app.services.spell_effect_factories import build_faerie_fire_effect
from ..limiar_map_projection import maybe_sync_active_area_effects_to_limiar_map
from .area_guardrails import build_area_guardrail_outcome, evaluate_area_target_guardrail
from ..host_protocol import CombatServiceHostProtocol

if TYPE_CHECKING:
    _AreaMixinBase = CombatServiceHostProtocol
else:
    _AreaMixinBase = object


class FaerieFireAreaMixin(_AreaMixinBase):
    @classmethod
    async def _cast_faerie_fire_area_debuff(
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
        prev = cls._clear_concentration_for_source(
            state, source_participant_id=attacker["id"], db=db,
        )
        if prev["removed_effects"]:
            flag_modified(state, "participants")
        if prev["removed_area_effects"]:
            flag_modified(state, "active_area_effects")
            maybe_sync_active_area_effects_to_limiar_map(session_id, state)

        concentration_group = str(uuid4())
        game_time = get_game_time_seconds(session_id, db)
        duration_seconds = cls._safe_int(spell_context.get("duration_seconds"), 60)
        save_ability = spell_context.get("save_ability") or "dexterity"
        save_dc = cls._safe_int(spell_context.get("save_dc"), 0)

        cls._append_effect_to_participant(
            attacker,
            cls._build_active_effect(
                kind="spell_effect",
                source_participant_id=attacker["id"],
                duration_type="timed",
                created_at_game_time_seconds=game_time,
                expires_at_game_time_seconds=game_time + duration_seconds,
                metadata={
                    "concentration": True,
                    "concentration_group": concentration_group,
                    "source_spell_key": spell_context["spell_canonical_key"],
                },
                display_label=spell_context["spell_name"],
            ),
        )
        flag_modified(state, "participants")

        affected_participants = [
            participant
            for participant in state.participants
            if participant["ref_id"] in targeting_result.affected_target_ref_ids
        ]
        area_target_outcomes: list[dict[str, Any]] = []
        excluded_target_outcomes: list[dict[str, Any]] = []

        for target_participant in affected_participants:
            guardrail_reason = evaluate_area_target_guardrail(
                db=db,
                session_id=session_id,
                attacker=attacker,
                target_participant=target_participant,
                spell_canonical_key=spell_context["spell_canonical_key"],
                assert_hostile_action_allowed=cls._assert_hostile_action_allowed,
                validate_spell_automation_target=cls._validate_spell_automation_target,
            )
            if guardrail_reason:
                excluded_target_outcomes.append(
                    build_area_guardrail_outcome(
                        target_participant=target_participant,
                        reason=guardrail_reason,
                    )
                )
                continue

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

            effect_applied = False
            if not is_saved:
                effect = build_faerie_fire_effect(
                    cls._build_combat_spell_effect_context(
                        spell_key="faerie_fire",
                        spell_name=spell_context["spell_name"],
                        caster_participant_id=attacker["id"],
                        target_participant_id=target_participant["id"],
                        game_time_seconds=game_time,
                        duration_seconds=duration_seconds,
                        concentration=True,
                        concentration_group=concentration_group,
                        spell_save_dc=save_dc,
                        extra_metadata={
                            "effect_target_participant_id": target_participant.get("id"),
                            "effect_target_ref_id": target_participant.get("ref_id"),
                            "effect_target_display_name": target_participant.get("display_name"),
                        },
                    )
                )
                cls._append_effect_to_participant(target_participant, effect)
                flag_modified(state, "participants")
                effect_applied = True

            area_target_outcomes.append(
                {
                    "target_ref_id": target_participant["ref_id"],
                    "target_display_name": target_participant["display_name"],
                    "target_kind": target_participant["kind"],
                    "is_saved": is_saved,
                    "roll": roll_result.total,
                    "roll_result": roll_result,
                    "damage_applied": None,
                    "healing_applied": None,
                    "new_hp": None,
                    "effect_applied": "faerie_fire" if effect_applied else None,
                }
            )

        area_target_outcomes.extend(excluded_target_outcomes)

        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_state(session_id, state)

        target_count = len(targeting_result.affected_target_ref_ids)
        log_lines = [
            f"{attacker['display_name']} conjurou {spell_context['spell_name']} em area "
            f"({area_spec['shape']}): {target_count} alvo{'s' if target_count != 1 else ''} na area.",
        ]
        for outcome in area_target_outcomes:
            if outcome.get("excluded_by_guardrail"):
                log_lines.append(
                    f"  {outcome['target_display_name']}: excluído por regra mecânica ({outcome.get('guardrail_reason')})."
                )
                continue
            if outcome.get("effect_applied") == "faerie_fire":
                log_lines.append(
                    f"  {outcome['target_display_name']}: save {outcome['roll']} vs DC {save_dc}, falhou (faerie fire)."
                )
            else:
                log_lines.append(
                    f"  {outcome['target_display_name']}: save {outcome['roll']} vs DC {save_dc}, passou."
                )
        log_message = "\n".join(log_lines)
        if was_overridden:
            log_message = f"[OVERRIDE: Limit for '{spell_context.get('action_cost') or 'action'}' ignored] {log_message}"
        await cls._emit_and_persist_log(db, session_id, actor_user_id, attacker.get("display_name"), {
            "message": log_message,
            "actorUserId": actor_user_id,
            "source": "gm_override" if is_gm else "player_turn",
            "is_override": was_overridden,
            "overridden_resource": (spell_context.get("action_cost") or "action") if was_overridden else None,
        })

        return {
            "spell_name": spell_context["spell_name"],
            "spell_canonical_key": spell_context["spell_canonical_key"],
            "action_kind": "saving_throw",
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
            "save_ability": save_ability,
            "save_dc": save_dc,
            "save_success_outcome": "none",
            "effect_dice": None,
            "effect_bonus": 0,
            "pending_spell_id": None,
            "effect_roll_required": False,
            "base_effect": None,
            "action_cost": spell_context.get("action_cost") or "action",
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
            "area_target_outcomes": area_target_outcomes,
            "target_count": target_count,
            "active_area_effect": None,
            "elemental_affinity_eligible": False,
            "elemental_affinity_damage_type": None,
            "elemental_affinity_bonus": None,
            "concentration_group": concentration_group,
        }
