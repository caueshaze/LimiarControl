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
from app.services.spell_material_components import (
    MaterialConsumptionResult,
    SpellMaterialError,
    consume_spell_material,
    validate_spell_material,
)

from ..combat_targeting import get_combat_targeting_service
from ..cover_modifiers import cover_label, resolve_cover_modifier, resolve_cover_save_dc, resolve_cover_save_modifier, should_cover_apply_to_save
from ..exceptions import CombatServiceError
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
            save_mod = modify_saving_throw(
                target_participant,
                spell_context["save_ability"],
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
            roll_result.check_modifier_sources = [
                *save_mod.advantage_source_details,
                *save_mod.disadvantage_source_details,
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
