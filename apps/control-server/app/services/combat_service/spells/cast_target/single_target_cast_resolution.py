from __future__ import annotations

import logging
from uuid import uuid4

from app.models.inventory import InventoryItem
from app.services.magic_item_effects import consume_inventory_item_charge, get_inventory_item_charges_current

from ...combat_targeting import get_combat_targeting_service
from ...exceptions import CombatServiceError
from ...targeting_intent import SpellCastIntent
from ..spell_resolution import SpellResolutionResult

logger = logging.getLogger(__name__)


class CastTargetSingleTargetCastResolutionMixin:
    @classmethod
    async def _resolve_cast_resolution(
        cls, db, session_id, req, state, attacker, attacker_model,
        spell_context, actor_user_id, is_gm,
    ):
        targeting_intent = SpellCastIntent(
            session_id=session_id,
            action_id=f"targeting:{uuid4()}",
            actor_ref_id=attacker["ref_id"],
            actor_kind=attacker["kind"],
            requested_target_ref_id=req.target_ref_id,
            spell_canonical_key=spell_context["spell_canonical_key"],
            spell_mode=spell_context["spell_mode"],
            target_type=spell_context.get("target_type"),
            selection_type=spell_context.get("selection_type"),
            attack_type=spell_context.get("attack_type"),
            range_kind=spell_context.get("range_kind"),
            area_shape=spell_context.get("area_shape"),
            range_meters=spell_context.get("range_meters"),
            requires_sight=bool(spell_context.get("requires_target_sight")),
            requires_effect=bool(spell_context.get("requires_target_effect")),
        )
        # Resolve through the package namespace so tests patching
        # cast_target.get_combat_targeting_service take effect.
        from . import get_combat_targeting_service as _get_targeting_service

        targeting_result = _get_targeting_service(state.use_map).validate(
            targeting_intent, state
        )
        if not targeting_result.is_valid:
            diag = targeting_result.diagnostics
            logger.info(
                "[cast_spell] targeting failed session=%s actor=%s target=%s | %s",
                session_id,
                attacker.get("ref_id"),
                req.target_ref_id,
                diag.compact_log() if diag else targeting_result.failure_reason,
            )
            target_p = next(
                (p for p in state.participants if p["ref_id"] == req.target_ref_id),
                None,
            )
            cls._record_spell_cast_rejected_activity(
                db,
                session_id=session_id,
                actor_user_id=actor_user_id,
                actor_ref_id=attacker["ref_id"],
                actor_display_name=attacker.get("display_name") or attacker["ref_id"],
                spell_context=spell_context,
                reason=cls._map_spell_rejection_reason(
                    diag.primary_failure() if diag else None
                ),
                target_ref_id=req.target_ref_id,
                target_display_name=target_p.get("display_name") if target_p else None,
            )
            raise CombatServiceError(
                targeting_result.failure_reason or "Target not found in combat"
            )

        target_p = next(
            (
                p
                for p in state.participants
                if p["ref_id"] == targeting_result.validated_primary_target_ref_id
            ),
            None,
        )
        if not target_p:
            raise CombatServiceError("Target not found in combat")

        is_hostile_spell = (
            spell_context["spell_mode"] in ("spell_attack", "saving_throw", "direct_damage")
            or spell_context["spell_canonical_key"] == "hunters_mark"
        )
        if is_hostile_spell:
            cls._assert_hostile_action_allowed(
                attacker,
                target_p,
                action_label="a hostile spell",
            )
        cls._validate_spell_automation_target(
            db,
            session_id,
            spell_canonical_key=spell_context["spell_canonical_key"],
            target_participant=target_p,
        )
        cls._validate_spell_target_creature_type_restriction(
            db,
            session_id,
            spell_canonical_key=spell_context["spell_canonical_key"],
            target_participant=target_p,
        )
        cls._check_declarative_requires_unarmored_for_target(
            db,
            session_id,
            spell_context=spell_context,
            target_participant=target_p,
        )

        slot_spent = False
        if spell_context.get("source_kind") == "magic_item":
            inventory_item = spell_context.get("inventory_item")
            source_item = spell_context.get("source_item")
            if not isinstance(inventory_item, InventoryItem):
                raise CombatServiceError("Magic item inventory entry is missing.", 400)
            remaining_charges = get_inventory_item_charges_current(
                inventory_item, source_item
            )
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

        effect_roll_required = spell_context["effect_dice"] is not None
        spell_mode = spell_context["spell_mode"]
        effect_kind = spell_context["effect_kind"]
        effect_bonus = cls._safe_int(spell_context.get("effect_bonus"), 0)
        save_success_outcome = spell_context.get("save_success_outcome")
        inventory_refresh_required = spell_context.get("source_kind") == "magic_item"
        summary_text = None
        custom_log_message = None
        automation_player_state_ids = set()

        automation_result = await cls._cast_spell_via_automation(
            db,
            session_id,
            attacker=attacker,
            attacker_model=attacker_model,
            actor_user_id=actor_user_id,
            is_gm=is_gm,
            req=req,
            state=state,
            spell_context=spell_context,
            target_participant=target_p,
        )
        # Spell attacks with declarative effects must go through the attack-roll
        # path first; applying effects before the roll would bypass hit/miss.
        if automation_result is None and spell_mode not in ("spell_attack", "saving_throw"):
            automation_result = await cls._cast_spell_via_declarative_effects(
                db,
                session_id,
                attacker=attacker,
                attacker_model=attacker_model,
                actor_user_id=actor_user_id,
                is_gm=is_gm,
                req=req,
                state=state,
                spell_context=spell_context,
                target_participant=target_p,
            )
        on_hit_applied_declarative_effects_by_target: list | None = None
        if automation_result is not None:
            spell_mode = automation_result["action_kind"]
            effect_kind = automation_result["effect_kind"]
            result = SpellResolutionResult(
                roll_result=automation_result["roll_result"],
                roll_total=automation_result["roll"],
                target_ac=automation_result["target_ac"],
                is_critical=automation_result["is_critical"],
                is_hit=automation_result["is_hit"],
                is_saved=automation_result["is_saved"],
                new_hp=automation_result["new_hp"],
                pending_spell_id=automation_result["pending_spell_id"],
                damage=automation_result["damage"],
                healing=automation_result["healing"],
            )
            effect_roll_required = automation_result["effect_roll_required"]
            summary_text = automation_result.get("summary_text")
            inventory_refresh_required = inventory_refresh_required or bool(
                automation_result.get("inventory_refresh_required")
            )
            custom_log_message = automation_result.get("__log_message")
            automation_player_state_ids = automation_result.get("__player_state_ids_to_emit") or set()
        elif spell_mode == "spell_attack":
            result = cls._resolve_spell_attack(
                db,
                session_id,
                state=state,
                attacker=attacker,
                target_p=target_p,
                spell_context=spell_context,
                req=req,
                is_gm=is_gm,
                spell_mode=spell_mode,
                effect_kind=effect_kind,
                effect_bonus=effect_bonus,
                effect_roll_required=effect_roll_required,
                targeting_result=targeting_result,
            )
            # Apply declarative on-hit effects (e.g. Ray of Frost movement penalty).
            # Only applies when the attack lands and there is no pending dice roll.
            if result.is_hit and not result.pending_spell_id:
                if cls._spell_context_has_declarative_effects(spell_context):
                    application = cls._apply_declarative_spell_effects(
                        state=state,
                        attacker=attacker,
                        target_participant=target_p,
                        spell_context=spell_context,
                    )
                    applied_effects = application["applied_effects"]
                    cls._apply_temp_hp_from_granted_effects(db, state, applied_effects)
                    on_hit_applied_declarative_effects_by_target = (
                        cls._build_applied_declarative_effects_by_target(applied_effects)
                    )
            if result.is_hit:
                cls._apply_spell_attack_delayed_damage_effect(
                    target_participant=target_p,
                    spell_context=spell_context,
                    attacker=attacker,
                )
        elif spell_mode == "saving_throw":
            result = cls._resolve_saving_throw_spell(
                db,
                session_id,
                state=state,
                attacker=attacker,
                target_p=target_p,
                spell_context=spell_context,
                req=req,
                is_gm=is_gm,
                spell_mode=spell_mode,
                effect_kind=effect_kind,
                effect_bonus=effect_bonus,
                effect_roll_required=effect_roll_required,
                save_success_outcome=save_success_outcome,
                targeting_result=targeting_result,
            )
            if (
                automation_result is None
                and result.is_saved is False
                and not result.pending_spell_id
                and not result.pending_save_id
                and cls._spell_context_has_declarative_effects(spell_context)
            ):
                application = cls._apply_declarative_spell_effects(
                    state=state,
                    attacker=attacker,
                    target_participant=target_p,
                    spell_context=spell_context,
                )
                for active_effect in application.get("applied_effects") or []:
                    metadata = cls._get_effect_metadata(active_effect)
                    repeat_save = metadata.get("repeat_save")
                    if isinstance(repeat_save, dict) and repeat_save.get("timing") == "target_turn_end":
                        repeat_save["dc"] = result.effective_dc
                        repeat_save["ability"] = str(spell_context.get("save_ability") or "wisdom")
                        repeat_save["source_participant_id"] = attacker.get("id")
                on_hit_applied_declarative_effects_by_target = (
                    cls._build_applied_declarative_effects_by_target(
                        application.get("applied_effects")
                    )
                )
        else:
            result = cls._resolve_direct_effect_spell(
                db,
                state,
                attacker=attacker,
                target_p=target_p,
                spell_context=spell_context,
                req=req,
                spell_mode=spell_mode,
                effect_kind=effect_kind,
                effect_bonus=effect_bonus,
                effect_roll_required=effect_roll_required,
            )

        return {
            "result": result,
            "spell_mode": spell_mode,
            "effect_kind": effect_kind,
            "effect_bonus": effect_bonus,
            "save_success_outcome": save_success_outcome,
            "slot_spent": slot_spent,
            "inventory_refresh_required": inventory_refresh_required,
            "summary_text": summary_text,
            "custom_log_message": custom_log_message,
            "automation_player_state_ids": automation_player_state_ids,
            "was_overridden": was_overridden,
            "action_cost": action_cost,
            "target_p": target_p,
            "automation_result": automation_result,
            "on_hit_applied_declarative_effects_by_target": on_hit_applied_declarative_effects_by_target,
        }

