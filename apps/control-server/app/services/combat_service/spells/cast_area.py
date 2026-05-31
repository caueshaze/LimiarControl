from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app.core.config import settings
from app.models.combat import CombatState
from app.models.inventory import InventoryItem
from app.schemas.combat import CombatCastSpellRequest
from app.services.magic_item_effects import consume_inventory_item_charge
from app.services.combat_service.condition_effects_saves import modify_saving_throw
from app.services.roll_resolution import resolve_saving_throw
from app.services.game_time import get_game_time_seconds
from app.services.spell_effect_factories import build_faerie_fire_effect
from app.services.spell_material_components import (
    MaterialConsumptionResult,
    SpellMaterialError,
    consume_spell_material,
    validate_spell_material,
)

from ..combat_targeting import get_combat_targeting_service
from ..cover_modifiers import cover_label, resolve_cover_modifier, resolve_cover_save_dc, resolve_cover_save_modifier, should_cover_apply_to_save
from app.services.create_or_destroy_water import (
    normalize_water_payload,
    resolve_cube_side_meters,
    resolve_water_amount,
    select_obscurement_effects_in_cells,
)
from app.services.shatter import (
    INORGANIC_SAVE_DISADV_SOURCE,
    SHATTER_KEY,
    is_inorganic_participant,
)
from ..condition_effects_predicates import has_condition_immunity_from_source
from ..exceptions import CombatServiceError, _roll_dice_expression
from ..host_protocol import CombatServiceHostProtocol
from ..limiar_map_projection import maybe_sync_active_area_effects_to_limiar_map
from ..persistent_area_effects import build_persistent_spell_area_effect
from ..targeting_intent import AreaTargetingIntent
from .area_spatial_metadata import get_area_per_target_cover
from .area_guardrails import build_area_guardrail_outcome, evaluate_area_target_guardrail

logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    _CastAreaBase = CombatServiceHostProtocol
else:
    _CastAreaBase = object


class CastAreaMixin(_CastAreaBase):
    @classmethod
    def _get_area_per_target_cover(
        cls,
        *,
        session_id: str,
        action_id: str,
        actor_ref_id: str,
        target_ref_ids: list[str],
        use_map: bool,
    ) -> dict[str, str | None]:
        """Return cover from actor position to each affected area target.

        Thin wrapper that handles the use_map / settings guard and client
        creation, then delegates to the shared get_area_per_target_cover
        helper so both the cast path and the preview path use identical logic.
        """
        if not target_ref_ids:
            return {}
        if not use_map or not settings.limiar_map_enabled:
            return {ref_id: None for ref_id in target_ref_ids}
        client = cls._build_limiar_map_client()
        return get_area_per_target_cover(
            client=client,
            session_id=session_id,
            action_id=action_id,
            actor_ref_id=actor_ref_id,
            target_ref_ids=target_ref_ids,
        )

    @classmethod
    async def _cast_entangle_persistent_area(
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

        try:
            active_area_effect = build_persistent_spell_area_effect(
                state=state,
                attacker=attacker,
                spell_context=spell_context,
                area_spec=area_spec,
                targeting_result=targeting_result,
                origin_cell=req.origin_cell.model_dump() if req.origin_cell is not None else None,
                anchor_cell=req.anchor_cell.model_dump() if req.anchor_cell is not None else None,
                concentration_group=concentration_group,
            )
        except ValueError as exc:
            raise CombatServiceError(str(exc), 400) from exc

        state.active_area_effects = [
            *(state.active_area_effects or []),
            active_area_effect,
        ]
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
                    "concentration_area_effect_id": active_area_effect["id"],
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

        save_ability = spell_context.get("save_ability") or "strength"
        save_dc = cls._safe_int(spell_context.get("save_dc"), 0)
        area_effect_id = active_area_effect.get("id")

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

            condition_applied = False
            if not is_saved:
                cls._append_effect_to_participant(
                    target_participant,
                    cls._build_active_effect(
                        kind="condition",
                        condition_type="restrained",
                        source_participant_id=attacker["id"],
                        duration_type="timed",
                        created_at_game_time_seconds=game_time,
                        expires_at_game_time_seconds=game_time + duration_seconds,
                        metadata={
                            "source_spell_key": "entangle",
                            "source_spell_name": spell_context["spell_name"],
                            "source_effect_id": area_effect_id,
                            "concentration": True,
                            "concentration_group": concentration_group,
                            "escape_action": True,
                            "escape_check_ability": "strength",
                            "escape_check_dc": save_dc,
                        },
                        display_label="Restrained (Entangle)",
                    ),
                )
                condition_applied = True
                flag_modified(state, "participants")

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
                    "condition_applied": "restrained" if condition_applied else None,
                }
            )

        area_target_outcomes.extend(excluded_target_outcomes)

        db.add(state)
        db.commit()
        db.refresh(state)
        maybe_sync_active_area_effects_to_limiar_map(session_id, state)
        await cls._emit_state(session_id, state)

        target_count = len(targeting_result.affected_target_ref_ids)
        log_lines = [
            f"{attacker['display_name']} conjurou {spell_context['spell_name']} em area "
            f"({area_spec['shape']}): {target_count} alvo{'s' if target_count != 1 else ''} na area.",
            "A área virou terreno difícil enquanto a concentração durar.",
        ]
        for outcome in area_target_outcomes:
            if outcome.get("excluded_by_guardrail"):
                log_lines.append(
                    f"  {outcome['target_display_name']}: excluído por regra mecânica ({outcome.get('guardrail_reason')})."
                )
                continue
            if outcome.get("condition_applied") == "restrained":
                log_lines.append(
                    f"  {outcome['target_display_name']}: save {outcome['roll']} vs DC {save_dc}, falhou (restrained)."
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
            "active_area_effect": active_area_effect,
            "elemental_affinity_eligible": False,
            "elemental_affinity_damage_type": None,
            "elemental_affinity_bonus": None,
            "concentration_group": concentration_group,
        }

    _ILLUSION_APPEARANCE_CATEGORIES = {"object", "creature", "phenomenon", "other"}

    @classmethod
    def _validate_illusion_appearance(cls, appearance: Any) -> dict[str, str]:
        """Validate and normalize a Silent Image appearance payload."""
        description = ""
        category = "other"
        if appearance is not None:
            if hasattr(appearance, "model_dump"):
                appearance = appearance.model_dump()
            if isinstance(appearance, dict):
                description = str(appearance.get("description") or "").strip()
                category = str(appearance.get("category") or "other").strip().lower()
        if not description:
            raise CombatServiceError(
                "Silent Image requires a non-empty appearance description.", 400
            )
        if category not in cls._ILLUSION_APPEARANCE_CATEGORIES:
            raise CombatServiceError(
                "Silent Image appearance category must be one of: "
                "object, creature, phenomenon, other.",
                400,
            )
        return {"description": description, "category": category}

    @classmethod
    async def _cast_silent_image_illusion(
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
        appearance = cls._validate_illusion_appearance(
            getattr(req, "illusion_appearance", None)
        )

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
        duration_seconds = cls._safe_int(spell_context.get("duration_seconds"), 600)

        _, _, _, _, prof_bonus, spell_mod = cls._get_stats(
            db, attacker["ref_id"], attacker["kind"], session_id
        )
        investigation_dc = 8 + cls._safe_int(prof_bonus, 0) + cls._safe_int(spell_mod, 0)

        try:
            active_area_effect = build_persistent_spell_area_effect(
                state=state,
                attacker=attacker,
                spell_context=spell_context,
                area_spec=area_spec,
                targeting_result=targeting_result,
                origin_cell=req.origin_cell.model_dump() if req.origin_cell is not None else None,
                anchor_cell=req.anchor_cell.model_dump() if req.anchor_cell is not None else None,
                concentration_group=concentration_group,
            )
        except ValueError as exc:
            raise CombatServiceError(str(exc), 400) from exc

        active_area_effect.update(
            {
                "appearance": appearance,
                "discerned_by_ref_ids": [],
                "investigation_dc": investigation_dc,
            }
        )

        state.active_area_effects = [
            *(state.active_area_effects or []),
            active_area_effect,
        ]
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
                    "concentration_area_effect_id": active_area_effect["id"],
                },
                display_label=spell_context["spell_name"],
            ),
        )
        flag_modified(state, "participants")

        db.add(state)
        db.commit()
        db.refresh(state)
        maybe_sync_active_area_effects_to_limiar_map(session_id, state)
        await cls._emit_state(session_id, state)

        action_cost = spell_context.get("action_cost") or "action"
        log_message = (
            f"{attacker['display_name']} conjurou {spell_context['spell_name']}: "
            f"uma ilusão visual ({appearance['description']}) surge na área."
        )
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
            "target_display_name": "Illusion",
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
            "affected_target_ref_ids": [],
            "affected_cells": list(targeting_result.spatial_metadata.affected_cells),
            "area_target_outcomes": [],
            "target_count": 0,
            "active_area_effect": active_area_effect,
            "elemental_affinity_eligible": False,
            "elemental_affinity_damage_type": None,
            "elemental_affinity_bonus": None,
            "concentration_group": concentration_group,
        }

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

    @classmethod
    def _area_save_spell_specific_mode(
        cls,
        spell_context: dict[str, Any],
        target_participant: dict,
    ) -> tuple[str, str | None]:
        """Spell-specific one-off save advantage/disadvantage for an area save.

        No-op (``("normal", None)``) for every spell except Shatter, which gives
        disadvantage to creatures carrying explicit inorganic material metadata.
        """
        if spell_context.get("spell_canonical_key") == SHATTER_KEY and is_inorganic_participant(
            target_participant
        ):
            return "disadvantage", INORGANIC_SAVE_DISADV_SOURCE
        return "normal", None

    @classmethod
    async def _cast_create_or_destroy_water(
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
        has_anchor = req.anchor_cell is not None or req.origin_cell is not None
        try:
            payload = normalize_water_payload(
                getattr(req, "water_payload", None), has_anchor=has_anchor
            )
        except ValueError as exc:
            raise CombatServiceError(str(exc), 400) from exc

        mode = payload["mode"]
        target_kind = payload["target_kind"]
        slot_level = cls._safe_int(spell_context.get("slot_level"), 1) or 1
        gallons, liters = resolve_water_amount(slot_level)
        cube_side = resolve_cube_side_meters(slot_level)

        environment_effects: dict[str, Any] = {}
        amount = None
        area = None
        removed_fog_effect_ids: list[str] = []

        if target_kind == "container":
            amount = {"gallons": gallons, "liters": liters}
            environment_effects = {
                "create_water": mode == "create",
                "destroy_water": mode == "destroy",
            }
        else:  # area
            area = {"shape": "cube", "side_meters": cube_side}
            if mode == "create":
                environment_effects = {
                    "rain": True,
                    "extinguishes_exposed_flames": True,
                }
            else:  # destroy / area -> destroy fog
                environment_effects = {"destroy_fog": True}
                cells = targeting_result.spatial_metadata.affected_cells
                obscurement_effects = select_obscurement_effects_in_cells(state, cells)
                removed_fog_effect_ids = [
                    e["id"] for e in obscurement_effects if isinstance(e.get("id"), str)
                ]
                groups = {
                    e["concentration_group"]
                    for e in obscurement_effects
                    if e.get("concentration_group")
                }
                ungrouped_ids = {
                    e["id"]
                    for e in obscurement_effects
                    if not e.get("concentration_group") and isinstance(e.get("id"), str)
                }
                for group in groups:
                    cls._remove_effect_group(state, concentration_group=group)
                if ungrouped_ids:
                    state.active_area_effects = [
                        e
                        for e in (state.active_area_effects or [])
                        if e.get("id") not in ungrouped_ids
                    ]
                if removed_fog_effect_ids:
                    flag_modified(state, "participants")
                    flag_modified(state, "active_area_effects")
                    maybe_sync_active_area_effects_to_limiar_map(session_id, state)

        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_state(session_id, state)

        if target_kind == "container":
            detail = (
                f"criou {liters} L de água limpa"
                if mode == "create"
                else f"destruiu até {liters} L de água"
            )
        elif mode == "create":
            detail = f"fez chover em um cubo de {cube_side} m, apagando chamas expostas"
        else:
            detail = f"dissipou névoa em um cubo de {cube_side} m"
        log_message = f"{attacker['display_name']} conjurou {spell_context['spell_name']}: {detail}."
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
            "target_display_name": "Environment",
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
            "affected_target_ref_ids": [],
            "affected_cells": list(targeting_result.spatial_metadata.affected_cells),
            "area_target_outcomes": [],
            "target_count": 0,
            "active_area_effect": None,
            "elemental_affinity_eligible": False,
            "elemental_affinity_damage_type": None,
            "elemental_affinity_bonus": None,
            "concentration_group": None,
            "mode": mode,
            "target_kind": target_kind,
            "amount": amount,
            "area": area,
            "environment_effects": environment_effects,
            "removed_fog_effect_ids": removed_fog_effect_ids,
        }

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

    @classmethod
    async def _cast_area_spell(
        cls,
        db: Session,
        session_id: str,
        req: CombatCastSpellRequest,
        *,
        attacker: dict,
        attacker_model,
        actor_user_id: str,
        is_gm: bool,
        state: CombatState,
        spell_context: dict[str, Any],
        area_spec: dict[str, int | str],
    ) -> dict[str, Any]:
        targeting_intent = AreaTargetingIntent(
            session_id=session_id,
            action_id=f"targeting:{uuid4()}",
            actor_ref_id=attacker["ref_id"],
            actor_kind=attacker["kind"],
            requested_target_ref_id=req.target_ref_id,
            spell_canonical_key=spell_context["spell_canonical_key"],
            spell_mode=spell_context["spell_mode"],
            shape=str(area_spec["shape"]),
            size_meters=cls._safe_int(area_spec.get("size_meters"), 0),
            range_meters=cls._safe_optional_int(area_spec.get("range_meters")),
            target_type=spell_context.get("target_type"),
            selection_type=spell_context.get("selection_type"),
            origin_type=spell_context.get("origin_type"),
            target_anchor=spell_context.get("target_anchor"),
            attack_type=spell_context.get("attack_type"),
            range_kind=spell_context.get("range_kind"),
            effect_timing=spell_context.get("effect_timing"),
            area_shape=spell_context.get("area_shape"),
            origin_cell=req.origin_cell.model_dump() if req.origin_cell is not None else None,
            anchor_cell=req.anchor_cell.model_dump() if req.anchor_cell is not None else None,
            requires_sight=bool(spell_context.get("requires_point_sight")),
            requires_effect=bool(spell_context.get("requires_point_effect")),
        )
        targeting_result = get_combat_targeting_service(state.use_map).validate(targeting_intent, state)
        if not targeting_result.is_valid:
            cls._record_spell_cast_rejected_activity(
                db,
                session_id=session_id,
                actor_user_id=actor_user_id,
                actor_ref_id=attacker["ref_id"],
                actor_display_name=attacker.get("display_name") or attacker["ref_id"],
                spell_context=spell_context,
                reason=cls._map_spell_rejection_reason(
                    targeting_result.diagnostics.primary_failure()
                    if targeting_result.diagnostics
                    else None
                ),
                area_origin=req.anchor_cell.model_dump() if req.anchor_cell is not None else None,
            )
            raise CombatServiceError(
                targeting_result.failure_reason or "Area targeting could not be resolved.",
                400,
            )

        anchor_target = next(
            (p for p in state.participants if p["ref_id"] == req.target_ref_id),
            None,
        ) if isinstance(req.target_ref_id, str) else None

        if spell_context.get("effect_timing") != "immediate":
            return await cls._cast_non_immediate_area_spell(
                db,
                session_id,
                req,
                attacker=attacker,
                attacker_model=attacker_model,
                actor_user_id=actor_user_id,
                is_gm=is_gm,
                state=state,
                spell_context=spell_context,
                area_spec=area_spec,
                targeting_result=targeting_result,
            )

        if spell_context["spell_mode"] != "saving_throw" or spell_context["effect_kind"] != "damage":
            raise CombatServiceError(
                "This area spell flow currently supports only saving throw damage spells.",
                400,
            )

        action_cost = spell_context.get("action_cost") or "action"
        was_overridden = cls._consume_turn_resource(
            attacker,
            action_cost,
            is_gm=is_gm,
            override_resource_limit=req.override_resource_limit,
        )

        slot_spent = False
        material_result = MaterialConsumptionResult(
            required=False,
            consumed=False,
            material_key=None,
            material_label=None,
            quantity=0,
            inventory_item_id=None,
        )
        spell_material_config = SimpleNamespace(
            material_component_consumed=bool(spell_context.get("material_component_consumed")),
            consumable_material_options_json=spell_context.get("consumable_material_options_json"),
        )
        caster_user_id = str(attacker.get("actor_user_id") or attacker.get("ref_id") or "").strip()
        try:
            material_result = validate_spell_material(
                db,
                session_id=session_id,
                caster_user_id=caster_user_id,
                spell=spell_material_config,
                consumable_material_key=req.consumable_material_key,
            )
        except SpellMaterialError as exc:
            raise CombatServiceError(exc.detail, 400) from exc
        if spell_context.get("source_kind") == "magic_item":
            inventory_item = spell_context.get("inventory_item")
            source_item = spell_context.get("source_item")
            if not isinstance(inventory_item, InventoryItem):
                raise CombatServiceError("Magic item inventory entry is missing.", 400)
            try:
                consume_inventory_item_charge(inventory_item, source_item)
            except ValueError as exc:
                raise CombatServiceError(str(exc), 400) from exc
            db.add(inventory_item)
        elif isinstance(spell_context.get("slot_level"), int):
            cls._consume_player_spell_slot(attacker_model, spell_context["slot_level"])
            db.add(attacker_model)
            slot_spent = True
        try:
            material_result = consume_spell_material(
                db,
                session_id=session_id,
                caster_user_id=caster_user_id,
                spell=spell_material_config,
                consumable_material_key=req.consumable_material_key,
            )
        except SpellMaterialError as exc:
            raise CombatServiceError(exc.detail, 400) from exc
        spell_context["material_consumed"] = material_result.consumed
        spell_context["material_key"] = material_result.material_key
        spell_context["material_label"] = material_result.material_label
        spell_context["material_quantity"] = (
            material_result.quantity if material_result.required else None
        )
        spell_context["material_inventory_item_id"] = material_result.inventory_item_id

        affected_participants = [
            participant
            for participant in state.participants
            if participant["ref_id"] in targeting_result.affected_target_ref_ids
        ]
        eligible_participants: list[dict[str, Any]] = []
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
            eligible_participants.append(target_participant)
        cover_applies_to_save = spell_context.get("cover_applies_to_save")
        per_target_cover: dict[str, str | None] = {}
        if should_cover_apply_to_save(cover_applies_to_save):
            per_target_cover = cls._get_area_per_target_cover(
                session_id=session_id,
                action_id=f"area-cover:{uuid4()}",
                actor_ref_id=attacker["ref_id"],
                target_ref_ids=[p["ref_id"] for p in eligible_participants],
                use_map=state.use_map,
            )

        base_save_dc = cls._safe_int(spell_context.get("save_dc"), 0)
        area_target_outcomes: list[dict[str, Any]] = []
        target_results_for_pending: list[dict[str, Any]] = []
        for target_participant in eligible_participants:
            target_ref_id = target_participant["ref_id"]
            target_cover = per_target_cover.get(target_ref_id)
            effective_dc, _ = resolve_cover_save_dc(
                base_save_dc,
                target_cover,
                cover_applies_to_save,
                spell_context.get("save_ability"),
            )
            spell_save_mode, extra_save_source = cls._area_save_spell_specific_mode(
                spell_context, target_participant
            )
            save_mod = modify_saving_throw(
                target_participant,
                spell_context["save_ability"],
                spell_save_mode,
                source_participant=attacker,
                source_kind="participant",
            )
            roll_result = resolve_saving_throw(
                cls._build_roll_actor_stats_for_save(
                    db,
                    session_id,
                    target_ref_id,
                    target_participant["kind"],
                    target_participant["display_name"],
                ),
                ability=spell_context["save_ability"],
                advantage_mode=save_mod.result,
                dc=effective_dc,
            )
            extra_sources = (
                [{"type": "disadvantage", "source": extra_save_source}]
                if extra_save_source
                else []
            )
            roll_result.check_modifier_sources = [
                *save_mod.advantage_source_details,
                *save_mod.disadvantage_source_details,
                *extra_sources,
                *(roll_result.check_modifier_sources or []),
            ]
            roll_result.is_gm_roll = is_gm
            is_saved = bool(roll_result.success)
            outcome = {
                "target_ref_id": target_ref_id,
                "target_display_name": target_participant["display_name"],
                "target_kind": target_participant["kind"],
                "is_saved": is_saved,
                "roll": roll_result.total,
                "roll_result": roll_result,
                "damage_applied": None,
                "healing_applied": None,
                "new_hp": None,
                "cover": target_cover,
                "effective_save_dc": effective_dc,
                "base_save_dc": base_save_dc,
                "cover_modifier": resolve_cover_save_modifier(target_cover) if should_cover_apply_to_save(cover_applies_to_save) else 0,
                "save_disadvantage_sources": [extra_save_source] if extra_save_source else [],
            }
            area_target_outcomes.append(outcome)
            target_results_for_pending.append(
                {
                    "target_ref_id": target_participant["ref_id"],
                    "target_kind": target_participant["kind"],
                    "target_display_name": target_participant["display_name"],
                    "is_saved": is_saved,
                    "roll": roll_result.total,
                    "roll_result": roll_result.model_dump(mode="json"),
                }
            )

        area_target_outcomes.extend(excluded_target_outcomes)

        if not target_results_for_pending:
            db.add(state)
            db.commit()
            db.refresh(state)
            if slot_spent:
                target_state, *_ = cls._get_stats(db, attacker["ref_id"], "player", session_id)
                await cls._emit_player_state_update(db, session_id, attacker["ref_id"], target_state)
            await cls._emit_state(session_id, state)
            log_message = (
                f"{attacker['display_name']} lancou {spell_context['spell_name']} em area "
                f"({area_spec['shape']}), mas todos os alvos espaciais foram excluidos por regras mecânicas."
            )
            if excluded_target_outcomes:
                blocked_lines = [
                    f"  {outcome['target_display_name']}: {outcome['guardrail_reason']}"
                    for outcome in excluded_target_outcomes
                ]
                log_message = "\n".join([log_message, *blocked_lines])
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
                "action_kind": spell_context["spell_mode"],
                "effect_kind": spell_context["effect_kind"],
                "damage": 0,
                "healing": 0,
                "damage_type": spell_context.get("damage_type"),
                "is_critical": False,
                "is_hit": None,
                "is_saved": None,
                "new_hp": None,
                "roll": None,
                "roll_result": None,
                "target_ac": None,
                "target_display_name": "Area effect",
                "target_kind": "session_entity",
                "save_ability": spell_context.get("save_ability"),
                "save_dc": spell_context.get("save_dc"),
                "save_success_outcome": spell_context.get("save_success_outcome"),
                "effect_dice": spell_context.get("effect_dice"),
                "effect_bonus": cls._safe_int(spell_context.get("effect_bonus"), 0),
                "pending_spell_id": None,
                "effect_roll_required": False,
                "base_effect": None,
                "action_cost": action_cost,
                "summary_text": "Todos os alvos na área foram excluídos por regras mecânicas.",
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
                "target_count": len(targeting_result.affected_target_ref_ids),
                "elemental_affinity_eligible": bool(spell_context.get("elemental_affinity_eligible")),
                "elemental_affinity_damage_type": spell_context.get("elemental_affinity_damage_type"),
                "elemental_affinity_bonus": spell_context.get("elemental_affinity_bonus"),
            }

        primary_result_target = (
            anchor_target
            or (eligible_participants[0] if eligible_participants else None)
        )
        primary_target_ref_id = (
            primary_result_target["ref_id"]
            if primary_result_target is not None
            else req.target_ref_id
        )
        primary_target_kind = (
            primary_result_target["kind"]
            if primary_result_target is not None
            else "session_entity"
        )
        primary_target_display_name = (
            primary_result_target["display_name"]
            if primary_result_target is not None
            else "Area target"
        )

        pending_spell_id = cls._create_pending_spell_effect(
            state,
            attacker,
            {
                "spell_name": spell_context["spell_name"],
                "spell_canonical_key": spell_context["spell_canonical_key"],
                "action_kind": spell_context["spell_mode"],
                "effect_kind": spell_context["effect_kind"],
                "effect_dice": spell_context["effect_dice"],
                "effect_bonus": cls._safe_int(spell_context.get("effect_bonus"), 0),
                "damage_type": spell_context.get("damage_type"),
                "elemental_affinity_eligible": spell_context.get("elemental_affinity_eligible"),
                "elemental_affinity_damage_type": spell_context.get("elemental_affinity_damage_type"),
                "elemental_affinity_bonus": spell_context.get("elemental_affinity_bonus"),
                "target_ref_id": primary_target_ref_id,
                "target_kind": primary_target_kind,
                "target_display_name": primary_target_display_name,
                "save_ability": spell_context.get("save_ability"),
                "save_dc": spell_context.get("save_dc"),
                "save_success_outcome": spell_context.get("save_success_outcome"),
                "is_saved": False,
                "is_critical": False,
                "roll": None,
                "roll_result": None,
                "area_shape": area_spec["shape"],
                "affected_cells": list(targeting_result.spatial_metadata.affected_cells),
                "affected_target_ref_ids": list(targeting_result.affected_target_ref_ids),
                "affected_token_ids": list(targeting_result.spatial_metadata.affected_token_ids),
                "area_targets": target_results_for_pending,
                "area_guardrail_outcomes": excluded_target_outcomes,
            },
        )

        db.add(state)
        db.commit()
        db.refresh(state)

        if slot_spent:
            target_state, *_ = cls._get_stats(db, attacker["ref_id"], "player", session_id)
            await cls._emit_player_state_update(db, session_id, attacker["ref_id"], target_state)
        await cls._emit_state(session_id, state)

        target_count = len(targeting_result.affected_target_ref_ids)
        area_label = f"Area ({target_count} alvo{'s' if target_count != 1 else ''})"
        log_lines = [
            f"{attacker['display_name']} lancou {spell_context['spell_name']} em area "
            f"({area_spec['shape']}): {target_count} alvo{'s' if target_count != 1 else ''} na area.",
        ]
        for area_outcome in area_target_outcomes:
            if area_outcome.get("excluded_by_guardrail"):
                log_lines.append(
                    f"  {area_outcome['target_display_name']}: excluído por regra mecânica ({area_outcome.get('guardrail_reason')})."
                )
                continue
            save_text = "passou" if area_outcome["is_saved"] else "falhou"
            outcome_dc = area_outcome["effective_save_dc"]
            outcome_cover = area_outcome.get("cover")
            outcome_modifier = area_outcome.get("cover_modifier", 0)
            if outcome_modifier > 0 and outcome_cover:
                clabel = cover_label(outcome_cover)
                log_lines.append(
                    f"  {area_outcome['target_display_name']}: save {area_outcome['roll']} vs DC efetiva {outcome_dc} (base {base_save_dc} - {clabel}), {save_text}."
                )
            else:
                log_lines.append(
                    f"  {area_outcome['target_display_name']}: save {area_outcome['roll']} vs DC {outcome_dc}, {save_text}."
                )
        log_lines.append("Efeito pendente.")
        log_message = "\n".join(log_lines)
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
            "action_kind": spell_context["spell_mode"],
            "effect_kind": spell_context["effect_kind"],
            "damage": 0,
            "healing": 0,
            "damage_type": spell_context.get("damage_type"),
            "is_critical": False,
            "is_hit": None,
            "is_saved": None,
            "new_hp": None,
            "roll": None,
            "roll_result": None,
            "target_ac": None,
            "target_display_name": area_label,
            "target_kind": primary_target_kind,
            "save_ability": spell_context.get("save_ability"),
            "save_dc": spell_context.get("save_dc"),
            "save_success_outcome": spell_context.get("save_success_outcome"),
            "effect_dice": spell_context.get("effect_dice"),
            "effect_bonus": cls._safe_int(spell_context.get("effect_bonus"), 0),
            "pending_spell_id": pending_spell_id,
            "effect_roll_required": True,
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
            "area_target_outcomes": area_target_outcomes,
            "target_count": target_count,
            "elemental_affinity_eligible": bool(spell_context.get("elemental_affinity_eligible")),
            "elemental_affinity_damage_type": spell_context.get("elemental_affinity_damage_type"),
            "elemental_affinity_bonus": spell_context.get("elemental_affinity_bonus"),
        }

    @classmethod
    async def _cast_non_immediate_area_spell(
        cls,
        db: Session,
        session_id: str,
        req: CombatCastSpellRequest,
        *,
        attacker: dict,
        attacker_model,
        actor_user_id: str,
        is_gm: bool,
        state: CombatState,
        spell_context: dict[str, Any],
        area_spec: dict[str, int | str],
        targeting_result,
    ) -> dict[str, Any]:
        action_cost = spell_context.get("action_cost") or "action"
        was_overridden = cls._consume_turn_resource(
            attacker,
            action_cost,
            is_gm=is_gm,
            override_resource_limit=req.override_resource_limit,
        )

        slot_spent = False
        material_result = MaterialConsumptionResult(
            required=False,
            consumed=False,
            material_key=None,
            material_label=None,
            quantity=0,
            inventory_item_id=None,
        )
        spell_material_config = SimpleNamespace(
            material_component_consumed=bool(spell_context.get("material_component_consumed")),
            consumable_material_options_json=spell_context.get("consumable_material_options_json"),
        )
        caster_user_id = str(attacker.get("actor_user_id") or attacker.get("ref_id") or "").strip()
        try:
            material_result = validate_spell_material(
                db,
                session_id=session_id,
                caster_user_id=caster_user_id,
                spell=spell_material_config,
                consumable_material_key=req.consumable_material_key,
            )
        except SpellMaterialError as exc:
            raise CombatServiceError(exc.detail, 400) from exc
        if spell_context.get("source_kind") == "magic_item":
            inventory_item = spell_context.get("inventory_item")
            source_item = spell_context.get("source_item")
            if not isinstance(inventory_item, InventoryItem):
                raise CombatServiceError("Magic item inventory entry is missing.", 400)
            try:
                consume_inventory_item_charge(inventory_item, source_item)
            except ValueError as exc:
                raise CombatServiceError(str(exc), 400) from exc
            db.add(inventory_item)
        elif isinstance(spell_context.get("slot_level"), int):
            cls._consume_player_spell_slot(attacker_model, spell_context["slot_level"])
            db.add(attacker_model)
            slot_spent = True
        try:
            material_result = consume_spell_material(
                db,
                session_id=session_id,
                caster_user_id=caster_user_id,
                spell=spell_material_config,
                consumable_material_key=req.consumable_material_key,
            )
        except SpellMaterialError as exc:
            raise CombatServiceError(exc.detail, 400) from exc
        spell_context["material_consumed"] = material_result.consumed
        spell_context["material_key"] = material_result.material_key
        spell_context["material_label"] = material_result.material_label
        spell_context["material_quantity"] = (
            material_result.quantity if material_result.required else None
        )
        spell_context["material_inventory_item_id"] = material_result.inventory_item_id

        if spell_context.get("spell_canonical_key") == "entangle":
            return await cls._cast_entangle_persistent_area(
                db,
                session_id,
                req=req,
                attacker=attacker,
                actor_user_id=actor_user_id,
                is_gm=is_gm,
                state=state,
                spell_context=spell_context,
                area_spec=area_spec,
                targeting_result=targeting_result,
                was_overridden=was_overridden,
            )
        if spell_context.get("spell_canonical_key") == "faerie_fire":
            return await cls._cast_faerie_fire_area_debuff(
                db,
                session_id,
                req=req,
                attacker=attacker,
                actor_user_id=actor_user_id,
                is_gm=is_gm,
                state=state,
                spell_context=spell_context,
                area_spec=area_spec,
                targeting_result=targeting_result,
                was_overridden=was_overridden,
            )
        if spell_context.get("spell_canonical_key") == "silent_image":
            return await cls._cast_silent_image_illusion(
                db,
                session_id,
                req=req,
                attacker=attacker,
                actor_user_id=actor_user_id,
                is_gm=is_gm,
                state=state,
                spell_context=spell_context,
                area_spec=area_spec,
                targeting_result=targeting_result,
                was_overridden=was_overridden,
            )
        if spell_context.get("spell_canonical_key") == "sleep":
            return await cls._cast_sleep_area(
                db,
                session_id,
                req=req,
                attacker=attacker,
                actor_user_id=actor_user_id,
                is_gm=is_gm,
                state=state,
                spell_context=spell_context,
                area_spec=area_spec,
                targeting_result=targeting_result,
                was_overridden=was_overridden,
            )
        if spell_context.get("spell_canonical_key") == "create_or_destroy_water":
            return await cls._cast_create_or_destroy_water(
                db,
                session_id,
                req=req,
                attacker=attacker,
                actor_user_id=actor_user_id,
                is_gm=is_gm,
                state=state,
                spell_context=spell_context,
                area_spec=area_spec,
                targeting_result=targeting_result,
                was_overridden=was_overridden,
            )

        active_area_effect: dict[str, Any] | None = None
        concentration_group: str | None = None
        if spell_context.get("effect_timing") == "persistent":
            if spell_context.get("concentration"):
                prev = cls._clear_concentration_for_source(
                    state, source_participant_id=attacker["id"], db=db,
                )
                if prev["removed_effects"]:
                    flag_modified(state, "participants")
                if prev["removed_area_effects"]:
                    flag_modified(state, "active_area_effects")
                    maybe_sync_active_area_effects_to_limiar_map(session_id, state)
                concentration_group = str(uuid4())
            try:
                active_area_effect = build_persistent_spell_area_effect(
                    state=state,
                    attacker=attacker,
                    spell_context=spell_context,
                    area_spec=area_spec,
                    targeting_result=targeting_result,
                    origin_cell=req.origin_cell.model_dump() if req.origin_cell is not None else None,
                    anchor_cell=req.anchor_cell.model_dump() if req.anchor_cell is not None else None,
                    concentration_group=concentration_group,
                )
            except ValueError as exc:
                raise CombatServiceError(str(exc), 400) from exc
            state.active_area_effects = [
                *(state.active_area_effects or []),
                active_area_effect,
            ]
            if concentration_group:
                cls._append_effect_to_participant(
                    attacker,
                    cls._build_active_effect(
                        kind="spell_effect",
                        source_participant_id=attacker["id"],
                        duration_type="manual",
                        metadata={
                            "concentration": True,
                            "concentration_group": concentration_group,
                            "source_spell_key": spell_context["spell_canonical_key"],
                            "concentration_area_effect_id": active_area_effect["id"],
                        },
                        display_label=spell_context["spell_name"],
                    ),
                )
                flag_modified(state, "participants")

        db.add(state)
        db.commit()
        db.refresh(state)
        if active_area_effect is not None:
            maybe_sync_active_area_effects_to_limiar_map(session_id, state)

        if slot_spent:
            target_state, *_ = cls._get_stats(db, attacker["ref_id"], "player", session_id)
            await cls._emit_player_state_update(db, session_id, attacker["ref_id"], target_state)
        await cls._emit_state(session_id, state)

        affected_target_ref_ids = list(targeting_result.affected_target_ref_ids)
        affected_cells = list(targeting_result.spatial_metadata.affected_cells)
        timing_label = "persistente" if spell_context.get("effect_timing") == "persistent" else "acionado"
        log_message = (
            f"{attacker['display_name']} conjurou {spell_context['spell_name']} em area "
            f"({area_spec['shape']}): efeito {timing_label} sem dano imediato."
        )
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
            "action_kind": spell_context["spell_mode"],
            "effect_kind": spell_context["effect_kind"],
            "damage": 0,
            "healing": 0,
            "damage_type": spell_context.get("damage_type"),
            "is_critical": False,
            "is_hit": None,
            "is_saved": None,
            "new_hp": None,
            "roll": None,
            "roll_result": None,
            "target_ac": None,
            "target_display_name": "Area effect",
            "target_kind": "session_entity",
            "save_ability": spell_context.get("save_ability"),
            "save_dc": spell_context.get("save_dc"),
            "save_success_outcome": spell_context.get("save_success_outcome"),
            "effect_dice": spell_context.get("effect_dice"),
            "effect_bonus": cls._safe_int(spell_context.get("effect_bonus"), 0),
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
            "affected_target_ref_ids": affected_target_ref_ids,
            "affected_cells": affected_cells,
            "area_target_outcomes": [],
            "target_count": len(affected_target_ref_ids),
            "active_area_effect": active_area_effect,
            "elemental_affinity_eligible": bool(spell_context.get("elemental_affinity_eligible")),
            "elemental_affinity_damage_type": spell_context.get("elemental_affinity_damage_type"),
            "elemental_affinity_bonus": spell_context.get("elemental_affinity_bonus"),
        }
