from __future__ import annotations

from uuid import uuid4


class CastTargetPlainMultiTargetResolverMixin:
    @classmethod
    async def _resolve_plain_multi_target_automation_cast(
        cls,
        db,
        session_id: str,
        req,
        state,
        attacker: dict,
        attacker_model,
        spell_context: dict,
        actor_user_id: str,
        is_gm: bool,
        targets: list[dict],
        *,
        spatial_results: dict | None = None,
    ) -> dict:
        """Consume resources once then invoke the automation handler per target.

        Modeled after _resolve_modal_multi_target_cast.  No variants.
        """
        from sqlalchemy.orm.attributes import flag_modified

        spell_mode = spell_context["spell_mode"]
        is_hostile_spell = spell_mode in ("spell_attack", "saving_throw", "direct_damage")
        player_state_ids_to_emit: set[str] = set()
        entity_previous_hp_map: dict[str, int] = {}
        total_damage = 0
        total_healing = 0
        outcomes: list[dict] = []
        shared_effect_group_id = str(uuid4()) if spell_context.get("concentration") else None
        any_effect_applied = False

        # Per-target mechanical validation (before resolving any)
        for participant in targets:
            if is_hostile_spell:
                cls._assert_hostile_action_allowed(
                    attacker, participant, action_label="a hostile spell"
                )
            cls._validate_spell_automation_target(
                db,
                session_id,
                spell_canonical_key=spell_context["spell_canonical_key"],
                target_participant=participant,
            )
            cls._validate_spell_target_creature_type_restriction(
                db,
                session_id,
                spell_canonical_key=spell_context["spell_canonical_key"],
                target_participant=participant,
            )
        cls._validate_feather_fall_trigger_context(
            req=req,
            spell_context=spell_context,
            targets=targets,
        )

        slot_spent = False
        action_cost = spell_context.get("action_cost") or "action"
        cls._ensure_turn_resource_available(
            attacker,
            action_cost,
            is_gm=is_gm,
            override_resource_limit=req.override_resource_limit,
        )
        if isinstance(spell_context.get("slot_level"), int):
            cls._ensure_player_spell_slot_available(
                attacker_model, spell_context["slot_level"]
            )
        was_overridden = cls._consume_turn_resource(
            attacker,
            action_cost,
            is_gm=is_gm,
            override_resource_limit=req.override_resource_limit,
        )
        if isinstance(spell_context.get("slot_level"), int):
            cls._consume_player_spell_slot(attacker_model, spell_context["slot_level"])
            db.add(attacker_model)
            slot_spent = True

        # Per-target automation resolution
        for participant in targets:
            outcome = await cls._cast_spell_via_automation(
                db,
                session_id,
                attacker=attacker,
                attacker_model=attacker_model,
                actor_user_id=actor_user_id,
                is_gm=is_gm,
                req=req,
                state=state,
                spell_context=spell_context,
                target_participant=participant,
            )
            if outcome is None and spell_mode == "saving_throw":
                resolution = cls._resolve_saving_throw_spell(
                    db,
                    session_id,
                    state=state,
                    attacker=attacker,
                    target_p=participant,
                    spell_context=spell_context,
                    req=req,
                    is_gm=is_gm,
                    spell_mode=spell_mode,
                    effect_kind=spell_context.get("effect_kind"),
                    effect_bonus=cls._safe_int(spell_context.get("effect_bonus"), 0),
                    effect_roll_required=spell_context["effect_dice"] is not None,
                    save_success_outcome=spell_context.get("save_success_outcome"),
                    targeting_result=(spatial_results or {}).get(participant["id"]),
                )
                if (
                    resolution.is_saved is False
                    and not resolution.pending_spell_id
                    and not resolution.pending_save_id
                    and cls._spell_context_has_declarative_effects(spell_context)
                ):
                    application = cls._apply_declarative_spell_effects(
                        state=state,
                        attacker=attacker,
                        target_participant=participant,
                        spell_context=spell_context,
                        effect_group_id=shared_effect_group_id,
                    )
                    applied_effects = application.get("applied_effects") or []
                    if applied_effects:
                        any_effect_applied = True
                    for active_effect in applied_effects:
                        metadata = cls._get_effect_metadata(active_effect)
                        repeat_save = metadata.get("repeat_save")
                        if isinstance(repeat_save, dict) and repeat_save.get("timing") == "target_turn_end":
                            repeat_save["dc"] = resolution.effective_dc
                            repeat_save["ability"] = str(spell_context.get("save_ability") or "wisdom")
                            repeat_save["source_participant_id"] = attacker.get("id")
                    applied_by_target = cls._build_applied_declarative_effects_by_target(applied_effects)
                else:
                    applied_by_target = []
                outcome = {
                    "target_ref_id": participant.get("ref_id"),
                    "target_participant_id": participant.get("id"),
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
                    "save": {
                        "ability": spell_context.get("save_ability"),
                        "dc": resolution.effective_dc,
                        "is_saved": resolution.is_saved,
                        "roll": resolution.roll_total,
                    },
                    "applied_declarative_effects_by_target": applied_by_target,
                }
            if outcome is None and spell_mode not in ("spell_attack", "saving_throw"):
                outcome = await cls._cast_spell_via_declarative_effects(
                    db,
                    session_id,
                    attacker=attacker,
                    attacker_model=attacker_model,
                    actor_user_id=actor_user_id,
                    is_gm=is_gm,
                    req=req,
                    state=state,
                    spell_context=spell_context,
                    target_participant=participant,
                    effect_group_id=shared_effect_group_id,
                )
            if outcome:
                if outcome.get("__applied_effect_count", 0):
                    any_effect_applied = True
                outcomes.append(outcome)
                total_damage += cls._safe_int(outcome.get("damage"), 0)
                total_healing += cls._safe_int(outcome.get("healing"), 0)
                if participant.get("kind") == "player":
                    player_state_ids_to_emit.add(participant["ref_id"])
                elif participant.get("kind") == "session_entity":
                    prev = outcome.get("previous_hp")
                    new = outcome.get("new_hp")
                    if isinstance(prev, int) and isinstance(new, int) and prev != new:
                        entity_previous_hp_map[participant["ref_id"]] = prev

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
            await cls._emit_entity_hp_update(db, session_id, ref_id, prev_hp)

        await cls._emit_state(session_id, state)

        target_count = len(targets)
        target_names = ", ".join(cls._participant_display_name(p) for p in targets)
        log_message = (
            f"{attacker['display_name']} conjurou {spell_context['spell_name']} em "
            f"{target_count} alvo{'s' if target_count != 1 else ''}: {target_names}."
        )
        if was_overridden:
            log_message = f"[OVERRIDE: Limit for '{action_cost}' ignored] {log_message}"
        await cls._emit_and_persist_log(
            db, session_id, actor_user_id, attacker.get("display_name"),
            {
                "message": log_message,
                "actorUserId": actor_user_id,
                "source": "gm_override" if is_gm else "player_turn",
                "is_override": was_overridden,
                "overridden_resource": action_cost if was_overridden else None,
            },
        )

        return {
            "spell_name": spell_context["spell_name"],
            "spell_canonical_key": spell_context["spell_canonical_key"],
            "selected_variant_key": None,
            "selected_variant_label": None,
            "context_origin": "initial_cast",
            "concentration_group": shared_effect_group_id if any_effect_applied else None,
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
            "summary_text": (
                f"{spell_context['spell_name']} resolvido em {target_count} "
                f"alvo{'s' if target_count != 1 else ''}."
            ),
            "inventory_refresh_required": False,
            "concentration_check": None,
            "concentration_checks": [],
            "area_shape": None,
            "affected_target_ref_ids": [p.get("ref_id") for p in targets],
            "affected_cells": [],
            "area_target_outcomes": [],
            "target_count": target_count,
            "plain_multi_target_outcomes": outcomes,
        }
