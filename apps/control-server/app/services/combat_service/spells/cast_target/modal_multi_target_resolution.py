from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified

from ...exceptions import CombatServiceError
from ...targeting_result import TargetingResult


class CastTargetModalMultiTargetResolutionMixin:
    async def _resolve_modal_multi_target_cast(
        cls,
        db,
        session_id,
        req,
        state,
        attacker,
        attacker_model,
        spell_context,
        actor_user_id,
        is_gm,
        validated_assignments,
        *,
        spatial_results_by_participant_id: dict[str, TargetingResult] | None = None,
    ):
        slot_spent = False
        if spell_context.get("source_kind") == "magic_item":
            inventory_item = spell_context.get("inventory_item")
            source_item = spell_context.get("source_item")
            if not isinstance(inventory_item, InventoryItem):
                raise CombatServiceError("Magic item inventory entry is missing.", 400)
            remaining_charges = get_inventory_item_charges_current(inventory_item, source_item)
            if isinstance(remaining_charges, int) and remaining_charges <= 0:
                raise CombatServiceError("This item has no charges remaining.", 400)

        action_cost = spell_context.get("action_cost") or "action"
        was_overridden = cls._consume_turn_resource(
            attacker,
            action_cost,
            is_gm=is_gm,
            override_resource_limit=req.override_resource_limit,
        )

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

        shared_effect_group_id = str(uuid4()) if spell_context.get("concentration") else None
        outcomes: list[dict] = []
        target_variant_assignments: list[dict] = []
        manual_notes_by_target: list[dict] = []
        player_state_ids_to_emit = set()
        entity_previous_hp_map: dict[str, int] = {}
        total_damage = 0
        total_healing = 0
        spell_mode = spell_context["spell_mode"]

        is_hostile_spell = spell_mode in ("spell_attack", "saving_throw", "direct_damage")
        for assignment in validated_assignments:
            if is_hostile_spell:
                cls._assert_hostile_action_allowed(
                    attacker,
                    assignment["participant"],
                    action_label="a hostile spell",
                )
            cls._validate_spell_automation_target(
                db,
                session_id,
                spell_canonical_key=spell_context["spell_canonical_key"],
                target_participant=assignment["participant"],
            )
            cls._validate_spell_target_creature_type_restriction(
                db,
                session_id,
                spell_canonical_key=spell_context["spell_canonical_key"],
                target_participant=assignment["participant"],
            )

        for assignment in validated_assignments:
            participant = assignment["participant"]
            variant = assignment["variant"]
            target_variant_assignments.append(
                {
                    "target_ref_id": participant.get("ref_id"),
                    "target_participant_id": participant.get("id"),
                    "target_display_name": cls._participant_display_name(participant),
                    "variant_key": assignment["variant_key"],
                    "variant_label": assignment["variant_label"],
                }
            )
            if variant.manualNotes:
                manual_notes_by_target.append(
                    cls._build_variant_summary_for_target(
                        participant=participant,
                        variant=variant,
                    )
                )

            per_target_context = cls._merge_spell_context_with_variant(
                spell_context=spell_context,
                variant=variant,
                participant=participant,
                target_variant_assignments=target_variant_assignments,
            )
            automation_result = await cls._cast_spell_via_automation(
                db,
                session_id,
                attacker=attacker,
                attacker_model=attacker_model,
                actor_user_id=actor_user_id,
                is_gm=is_gm,
                req=req,
                state=state,
                spell_context=per_target_context,
                target_participant=participant,
            )
            if automation_result is None:
                automation_result = await cls._cast_spell_via_declarative_effects(
                    db,
                    session_id,
                    attacker=attacker,
                    attacker_model=attacker_model,
                    actor_user_id=actor_user_id,
                    is_gm=is_gm,
                    req=req,
                    state=state,
                    spell_context=per_target_context,
                    target_participant=participant,
                    effect_group_id=shared_effect_group_id,
                )

            if automation_result is not None:
                if automation_result.get("pending_spell_id") or automation_result.get("pending_save_id"):
                    raise CombatServiceError(
                        "Multi-target modal spells do not support pending follow-up resolution yet.",
                        400,
                    )
                outcome = {
                    "target_ref_id": participant.get("ref_id"),
                    "target_display_name": cls._participant_display_name(participant),
                    "target_kind": participant.get("kind", "session_entity"),
                    "damage": automation_result.get("damage", 0) or 0,
                    "healing": automation_result.get("healing", 0) or 0,
                    "is_hit": automation_result.get("is_hit"),
                    "is_saved": automation_result.get("is_saved"),
                    "is_critical": automation_result.get("is_critical", False),
                    "roll": automation_result.get("roll"),
                    "roll_result": automation_result.get("roll_result"),
                    "new_hp": automation_result.get("new_hp"),
                    "variant_key": assignment["variant_key"],
                    "variant_label": assignment["variant_label"],
                    "summary_text": automation_result.get("summary_text"),
                }
                player_state_ids_to_emit.update(
                    automation_result.get("__player_state_ids_to_emit") or set()
                )
            elif spell_mode == "spell_attack":
                outcome = cls._resolve_instance_attack(
                    db,
                    session_id,
                    state,
                    attacker,
                    participant,
                    per_target_context,
                    req,
                    is_gm,
                    targeting_result=(spatial_results_by_participant_id or {}).get(participant["id"]),
                )
                outcome["variant_key"] = assignment["variant_key"]
                outcome["variant_label"] = assignment["variant_label"]
                if outcome.get("roll_result") and (
                    outcome.get("roll_result").pending_spell_id
                    or outcome.get("roll_result").pending_save_id
                ):
                    raise CombatServiceError(
                        "Multi-target modal spells do not support pending follow-up resolution yet.",
                        400,
                    )
            elif spell_mode == "saving_throw":
                resolution = cls._resolve_saving_throw_spell(
                    db,
                    session_id,
                    state=state,
                    attacker=attacker,
                    target_p=participant,
                    spell_context=per_target_context,
                    req=req,
                    is_gm=is_gm,
                    spell_mode=spell_mode,
                    effect_kind=per_target_context.get("effect_kind"),
                    effect_bonus=cls._safe_int(per_target_context.get("effect_bonus"), 0),
                    effect_roll_required=per_target_context["effect_dice"] is not None,
                    save_success_outcome=per_target_context.get("save_success_outcome"),
                    targeting_result=(spatial_results_by_participant_id or {}).get(participant["id"]),
                )
                if resolution.pending_spell_id or resolution.pending_save_id:
                    raise CombatServiceError(
                        "Multi-target modal spells do not support pending follow-up resolution yet.",
                        400,
                    )
                outcome = {
                    "target_ref_id": participant.get("ref_id"),
                    "target_display_name": cls._participant_display_name(participant),
                    "target_kind": participant.get("kind", "session_entity"),
                    "damage": resolution.damage,
                    "healing": resolution.healing,
                    "is_hit": None,
                    "is_saved": resolution.is_saved,
                    "is_critical": False,
                    "roll": resolution.roll_total,
                    "roll_result": resolution.roll_result,
                    "new_hp": resolution.new_hp,
                    "variant_key": assignment["variant_key"],
                    "variant_label": assignment["variant_label"],
                }
            else:
                outcome = cls._resolve_direct_effect_spell(
                    db,
                    state,
                    attacker=attacker,
                    target_p=participant,
                    spell_context=per_target_context,
                    req=req,
                    spell_mode=spell_mode,
                    effect_kind=per_target_context.get("effect_kind"),
                    effect_bonus=cls._safe_int(per_target_context.get("effect_bonus"), 0),
                    effect_roll_required=per_target_context["effect_dice"] is not None,
                ).__dict__
                if outcome.get("pending_spell_id") or outcome.get("pending_save_id"):
                    raise CombatServiceError(
                        "Multi-target modal spells do not support pending follow-up resolution yet.",
                        400,
                    )
                outcome["target_ref_id"] = participant.get("ref_id")
                outcome["target_display_name"] = cls._participant_display_name(participant)
                outcome["target_kind"] = participant.get("kind", "session_entity")
                outcome["variant_key"] = assignment["variant_key"]
                outcome["variant_label"] = assignment["variant_label"]

            outcomes.append(outcome)
            total_damage += outcome.get("damage", 0) or 0
            total_healing += outcome.get("healing", 0) or 0
            previous_hp = outcome.get("previous_hp")
            if previous_hp is not None and participant.get("ref_id") not in entity_previous_hp_map:
                entity_previous_hp_map[participant.get("ref_id")] = previous_hp
            if participant.get("kind") == "player" and (
                (outcome.get("damage", 0) or 0) > 0 or (outcome.get("healing", 0) or 0) > 0
            ):
                player_state_ids_to_emit.add(participant.get("ref_id"))

        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)

        if slot_spent:
            player_state_ids_to_emit.add(attacker["ref_id"])

        for player_ref_id in player_state_ids_to_emit:
            target_state, *_ = cls._get_stats(db, player_ref_id, "player", session_id)
            await cls._emit_player_state_update(db, session_id, player_ref_id, target_state)

        for ref_id, prev_hp in entity_previous_hp_map.items():
            target_p_entity = next(
                (p for p in state.participants if p["ref_id"] == ref_id), None,
            )
            if target_p_entity and target_p_entity.get("kind") == "session_entity":
                await cls._emit_entity_hp_update(db, session_id, ref_id, prev_hp)

        await cls._emit_state(session_id, state)

        target_count = len(validated_assignments)
        target_names = ", ".join(
            cls._participant_display_name(assignment["participant"])
            for assignment in validated_assignments
        )
        log_message = (
            f"{attacker['display_name']} conjurou {spell_context['spell_name']} em {target_count} alvo"
            f"{'s' if target_count != 1 else ''}: {target_names}."
        )
        log_message = (
            f"{log_message}"
            f"{cls._format_variant_assignments_for_log(target_variant_assignments, manual_notes_by_target)}"
            f"{cls._format_manual_notes_for_log(manual_notes_by_target)}"
            f"{cls._format_concentration_group_for_log(shared_effect_group_id)}"
        ).strip()
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
            "selected_variant_key": None,
            "selected_variant_label": None,
            "context_origin": "initial_cast",
            "concentration_group": shared_effect_group_id,
            "action_kind": spell_mode,
            "effect_kind": spell_context.get("effect_kind"),
            "damage": total_damage,
            "healing": total_healing,
            "damage_type": spell_context.get("damage_type"),
            "is_critical": None,
            "is_hit": None,
            "is_saved": None,
            "new_hp": None,
            "roll": None,
            "roll_result": None,
            "target_ac": None,
            "target_display_name": f"{target_count} alvos",
            "target_kind": "session_entity",
            "save_ability": spell_context.get("save_ability"),
            "save_dc": spell_context.get("save_dc"),
            "save_success_outcome": spell_context.get("save_success_outcome"),
            "effect_dice": spell_context.get("effect_dice"),
            "effect_bonus": cls._safe_int(spell_context.get("effect_bonus"), 0),
            "pending_spell_id": None,
            "pending_save_id": None,
            "effect_roll_required": False,
            "base_effect": None,
            "action_cost": action_cost,
            "summary_text": f"{spell_context['spell_name']} aplicou efeitos em {target_count} alvos.",
            "inventory_refresh_required": spell_context.get("source_kind") == "magic_item",
            "concentration_check": None,
            "concentration_checks": [],
            "area_shape": None,
            "affected_target_ref_ids": [],
            "affected_cells": [],
            "area_target_outcomes": [],
            "target_count": target_count,
            "elemental_affinity_eligible": bool(spell_context.get("elemental_affinity_eligible")),
            "elemental_affinity_damage_type": spell_context.get("elemental_affinity_damage_type"),
            "elemental_affinity_bonus": spell_context.get("elemental_affinity_bonus"),
            "effect_instance_count": spell_context.get("effect_instance_count"),
            "effect_instance_dice": spell_context.get("effect_instance_dice"),
            "base_effect_instance_count": spell_context.get("base_effect_instance_count"),
            "effect_instance_outcomes": [],
            "target_variant_assignments": target_variant_assignments,
            "manual_notes_by_target": manual_notes_by_target,
        }

