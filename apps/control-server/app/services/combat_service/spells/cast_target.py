from __future__ import annotations

import logging
from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified

from app.models.inventory import InventoryItem
from app.services.roll_resolution import resolve_saving_throw
from app.services.magic_item_effects import (
    consume_inventory_item_charge,
    get_inventory_item_charges_current,
)

from ..combat_targeting import get_combat_targeting_service
from ..exceptions import CombatServiceError
from ..targeting_intent import SpellCastIntent
from .cast_target_commit import CastTargetCommitMixin
from .cast_target_effect import CastTargetEffectMixin
from .spell_resolution import SpellResolutionResult

logger = logging.getLogger(__name__)


class CastTargetMixin(CastTargetCommitMixin, CastTargetEffectMixin):
    @classmethod
    def _validate_cast_prerequisites(cls, db, session_id, req, actor_user_id, is_gm):
        state = cls.get_state(db, session_id)
        cls._require_active(state)
        attacker = cls._resolve_actor_participant(
            state, actor_user_id, is_gm, req.actor_participant_id,
        )
        cls._require_actor_status(
            attacker, ("active",), "You can only cast a spell when active."
        )
        cls._require_action_capable(attacker)
        if attacker["kind"] != "player":
            raise CombatServiceError(
                "Only players can use this spell casting flow.", 400
            )

        attacker_state_check, *_ = cls._get_stats(
            db, attacker["ref_id"], attacker["kind"], session_id
        )
        attacker_data_check = cls._as_dict(attacker_state_check.state_json)
        if cls._as_dict(attacker_data_check.get("wildShape")).get("active"):
            raise CombatServiceError("Cannot cast spells while in Wild Shape.", 400)

        had_pending = isinstance(attacker.get("pending_attack"), dict)
        cls._clear_participant_pending_attack(attacker)
        if had_pending:
            flag_modified(state, "participants")

        attacker_model, _, _, _, _, _ = cls._get_stats(
            db, attacker["ref_id"], attacker["kind"], session_id
        )
        return state, attacker, attacker_model

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
            target_mode=spell_context.get("target_mode"),
            range_meters=spell_context.get("range_meters"),
            requires_sight=bool(spell_context.get("requires_target_sight")),
            requires_effect=bool(spell_context.get("requires_target_effect")),
        )
        targeting_result = get_combat_targeting_service(state.use_map).validate(
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
        }

    @classmethod
    async def cast_spell(
        cls,
        db,
        session_id: str,
        req,
        actor_user_id: str,
        is_gm: bool,
    ):
        state, attacker, attacker_model = cls._validate_cast_prerequisites(
            db, session_id, req, actor_user_id, is_gm,
        )
        spell_context = cls._resolve_player_spell_context(
            db, session_id, attacker, attacker_model, req,
        )
        area_spell_spec = cls._resolve_supported_area_spell_spec(spell_context)
        if cls._normalize_area_shape(spell_context.get("target_mode")) is not None:
            if area_spell_spec is None:
                raise CombatServiceError(
                    "This area spell is not configured for map targeting yet.", 400,
                )
            logger.info(
                "[cast_spell] pipeline=generic_area spell=%s session=%s actor=%s",
                spell_context["spell_canonical_key"],
                session_id,
                attacker.get("ref_id"),
            )
            return await cls._cast_area_spell(
                db, session_id, req,
                attacker=attacker,
                attacker_model=attacker_model,
                actor_user_id=actor_user_id,
                is_gm=is_gm,
                state=state,
                spell_context=spell_context,
                area_spec=area_spell_spec,
            )

        resolution = await cls._resolve_cast_resolution(
            db, session_id, req, state, attacker, attacker_model,
            spell_context, actor_user_id, is_gm,
        )
        return await cls._commit_cast_result(
            db, session_id, state, attacker, spell_context,
            resolution, actor_user_id, is_gm,
        )
