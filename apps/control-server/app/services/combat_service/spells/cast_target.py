from __future__ import annotations

import logging
from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified

from app.models.inventory import InventoryItem
from app.schemas.roll import RollActorStats
from app.services.combat_service.condition_effects import resolve_attack_advantage, resolve_spell_attack_kind
from app.services.roll_resolution import resolve_attack_base, resolve_saving_throw
from app.services.magic_item_effects import (
    consume_inventory_item_charge,
    get_inventory_item_charges_current,
)

from ..combat_targeting import get_combat_targeting_service
from ..cover_modifiers import resolve_cover_modifier
from ..exceptions import CombatServiceError
from ..targeting_diagnostics import NO_LINE_OF_EFFECT, NO_LINE_OF_SIGHT, NOT_VISIBLE, TARGET_OUT_OF_REACH
from ..targeting_intent import SpellCastIntent
from ..targeting_result import TargetingResult
from .cast_target_commit import CastTargetCommitMixin
from .cast_target_effect import CastTargetEffectMixin
from .spell_resolution import SpellResolutionResult

logger = logging.getLogger(__name__)


def _resolve_instance_spatial_error_phrase(result: TargetingResult) -> str:
    diag = result.diagnostics
    if diag:
        if TARGET_OUT_OF_REACH in diag.failure_reasons:
            return "is out of range"
        if NO_LINE_OF_SIGHT in diag.failure_reasons:
            return "has blocked line of sight"
        if NO_LINE_OF_EFFECT in diag.failure_reasons:
            return "has blocked line of effect"
        if NOT_VISIBLE in diag.failure_reasons:
            return "is not visible"
    return result.failure_reason or "cannot be targeted"


class CastTargetMixin(CastTargetCommitMixin, CastTargetEffectMixin):
    @classmethod
    def _validate_cast_prerequisites(
        cls,
        db,
        session_id,
        req,
        actor_user_id,
        is_gm,
        *,
        clear_pending_attack: bool = True,
    ):
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

        if clear_pending_attack:
            had_pending = isinstance(attacker.get("pending_attack"), dict)
            cls._clear_participant_pending_attack(attacker)
            if had_pending:
                flag_modified(state, "participants")

        attacker_model, _, _, _, _, _ = cls._get_stats(
            db, attacker["ref_id"], attacker["kind"], session_id
        )
        return state, attacker, attacker_model

    @classmethod
    def _resolve_area_size_meters(cls, spell_context: dict) -> float | None:
        area_shape = spell_context.get("area_shape")
        if not area_shape:
            return None
        if area_shape in ("sphere", "cylinder"):
            value = spell_context.get("radius_meters")
        elif area_shape == "line":
            value = spell_context.get("length_meters")
        elif area_shape == "cube":
            value = spell_context.get("side_meters")
        elif area_shape == "cone":
            value = (
                spell_context.get("length_meters")
                or spell_context.get("radius_meters")
            )
        else:
            value = None
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _build_resolved_spell_context_response(cls, req, spell_context: dict) -> dict:
        resolution_type = spell_context.get("spell_mode")
        range_meters = spell_context.get("range_meters")
        try:
            range_meters_value = float(range_meters) if range_meters is not None else None
        except (TypeError, ValueError):
            range_meters_value = None
        return {
            "spell_id": req.spell_id or spell_context.get("spell_canonical_key"),
            "spell_canonical_key": spell_context.get("spell_canonical_key"),
            "campaign_spell_id": req.campaign_spell_id,
            "inventory_item_id": spell_context.get("inventory_item_id"),
            "spell_name": spell_context["spell_name"],
            "spell_level": cls._safe_int(spell_context.get("spell_level"), 0),
            "slot_level": spell_context.get("slot_level"),
            "target_type": spell_context.get("target_type"),
            "selection_type": spell_context.get("selection_type"),
            "area_shape": spell_context.get("area_shape"),
            "area_size_meters": cls._resolve_area_size_meters(spell_context),
            "range_meters": range_meters_value,
            "resolution_type": resolution_type,
            "requires_attack_roll": resolution_type == "spell_attack",
            "requires_saving_throw": resolution_type == "saving_throw",
            "save_ability": spell_context.get("save_ability"),
            "damage_type": spell_context.get("damage_type"),
            "damage_preview": spell_context.get("effect_dice"),
            "effect_instance_count": cls._safe_int(
                spell_context.get("effect_instance_count"),
                1,
            ),
            "effect_instance_dice": spell_context.get("effect_instance_dice"),
            "base_effect_instance_count": spell_context.get("base_effect_instance_count"),
            "upcast_applied": bool(spell_context.get("upcast_applied")),
            "upcast_added_instances": cls._safe_int(
                spell_context.get("upcast_added_instances"),
                0,
            ),
            "upcast_instance_effect_dice": spell_context.get("upcast_instance_effect_dice"),
            "cover_applies_to_save": spell_context.get("cover_applies_to_save"),
        }

    @classmethod
    def resolve_spell_context(
        cls,
        db,
        session_id: str,
        req,
        actor_user_id: str,
        is_gm: bool,
    ) -> dict:
        _, attacker, attacker_model = cls._validate_cast_prerequisites(
            db,
            session_id,
            req,
            actor_user_id,
            is_gm,
            clear_pending_attack=False,
        )
        spell_context = cls._resolve_player_spell_context(
            db, session_id, attacker, attacker_model, req,
        )
        return cls._build_resolved_spell_context_response(req, spell_context)

    @classmethod
    def _validate_instance_targets(cls, *, req, spell_context, state):
        raw = getattr(req, "effect_instance_targets", None)
        if not raw:
            return None

        instance_count = spell_context.get("effect_instance_count", 1)
        if instance_count <= 1:
            raise CombatServiceError(
                "effect_instance_targets is only supported for multi-instance spells.", 400
            )

        indices = set()
        for t in raw:
            idx = t.instance_index
            if idx < 1 or idx > instance_count:
                raise CombatServiceError(
                    f"Instance index {idx} is out of range (1..{instance_count}).", 400
                )
            if idx in indices:
                raise CombatServiceError(
                    f"Duplicate instance index: {idx}.", 400
                )
            indices.add(idx)

        missing = set(range(1, instance_count + 1)) - indices
        if missing:
            sorted_missing = sorted(missing)
            raise CombatServiceError(
                f"Missing instance target assignments: {', '.join(str(m) for m in sorted_missing)}.", 400
            )

        participants_by_ref = {p["ref_id"]: p for p in state.participants}
        validated = []
        for t in raw:
            participant = participants_by_ref.get(t.target_ref_id)
            if participant is None:
                raise CombatServiceError(
                    f"Invalid target_ref_id for instance {t.instance_index}: {t.target_ref_id}.", 400
                )
            validated.append({
                "instance_index": t.instance_index,
                "target_ref_id": t.target_ref_id,
                "participant": participant,
            })

        return validated

    @classmethod
    def _validate_instance_spatial_targets(
        cls,
        *,
        state,
        attacker: dict,
        spell_context: dict,
        validated_targets: list[dict],
        session_id: str,
    ) -> dict[str, TargetingResult]:
        """Validate range/LoS/LoE for each unique targetRefId before consuming any resources.

        Deduplicates validation by targetRefId — each unique target is validated once.
        Raises CombatServiceError with instance_index and reason on first failure.
        Returns a dict of TargetingResult keyed by target_ref_id so that cover metadata
        can be reused downstream (e.g. in _resolve_instance_attack) without re-validating.
        """
        targeting_service = get_combat_targeting_service(state.use_map)

        unique_ref_to_first_instance: dict[str, int] = {}
        for vt in validated_targets:
            ref_id = vt["target_ref_id"]
            if ref_id not in unique_ref_to_first_instance:
                unique_ref_to_first_instance[ref_id] = vt["instance_index"]

        results_by_ref: dict[str, TargetingResult] = {}

        for target_ref_id, first_instance_index in unique_ref_to_first_instance.items():
            intent = SpellCastIntent(
                session_id=session_id,
                action_id=f"targeting-instance:{first_instance_index}",
                actor_ref_id=attacker["ref_id"],
                actor_kind=attacker["kind"],
                requested_target_ref_id=target_ref_id,
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
            result = targeting_service.validate(intent, state)

            if not result.is_valid:
                participant = next(
                    (vt["participant"] for vt in validated_targets if vt["target_ref_id"] == target_ref_id),
                    None,
                )
                target_label = (participant or {}).get("display_name") or target_ref_id
                reason_phrase = _resolve_instance_spatial_error_phrase(result)
                raise CombatServiceError(
                    f"Instance {first_instance_index} target {target_label} {reason_phrase}.",
                    status_code=400,
                )

            results_by_ref[target_ref_id] = result

        return results_by_ref

    @classmethod
    def _resolve_instance_direct(cls, db, state, attacker, target_p, spell_context, req):
        instance_dice = spell_context.get("effect_instance_dice")
        if not instance_dice:
            raise CombatServiceError(
                "Multi-instance spell is missing effect_instance_dice.", 400
            )
        effect_kind = spell_context.get("effect_kind") or "damage"
        damage_type = spell_context.get("damage_type")

        _, total = cls._resolve_damage_roll(instance_dice, roll_source="system")
        amount = max(0, total)

        new_hp = None
        previous_hp = None
        if amount > 0:
            new_hp, _, previous_hp, _ = cls._apply_spell_effect(
                db, state,
                target_p["ref_id"], target_p["kind"],
                effect_kind, amount,
                damage_type=damage_type,
                concentration_roll_source=req.concentration_roll_source,
                concentration_manual_roll=req.concentration_manual_roll,
            )

        return {
            "target_ref_id": target_p["ref_id"],
            "target_display_name": target_p.get("display_name", ""),
            "target_kind": target_p.get("kind", "session_entity"),
            "damage": amount if effect_kind != "healing" else 0,
            "healing": amount if effect_kind == "healing" else 0,
            "is_hit": None,
            "is_saved": None,
            "is_critical": False,
            "roll": None,
            "roll_result": None,
            "new_hp": new_hp,
            "previous_hp": previous_hp,
        }

    @classmethod
    def _resolve_instance_attack(
        cls, db, session_id, state, attacker, target_p, spell_context, req, is_gm,
        *,
        targeting_result: TargetingResult | None = None,
    ):
        instance_dice = spell_context.get("effect_instance_dice")
        if not instance_dice:
            raise CombatServiceError(
                "Multi-instance spell is missing effect_instance_dice.", 400
            )
        effect_kind = spell_context.get("effect_kind") or "damage"
        damage_type = spell_context.get("damage_type")
        attack_bonus = cls._safe_int(spell_context.get("attack_bonus"), 0)

        _, target_ac_raw, *_ = cls._get_stats(db, target_p["ref_id"], target_p["kind"], session_id)
        cover = targeting_result.spatial_metadata.cover if targeting_result else None
        cover_modifier = resolve_cover_modifier(cover)
        base_ac = target_ac_raw if target_ac_raw is not None else 10
        target_ac = base_ac + cover_modifier

        adv_ctx = resolve_attack_advantage(attacker, target_p, resolve_spell_attack_kind())
        has_adv = req.has_advantage or bool(adv_ctx.advantage_sources)
        has_dis = req.has_disadvantage or bool(adv_ctx.disadvantage_sources)
        adv_mode = (
            "advantage" if has_adv and not has_dis
            else "disadvantage" if has_dis and not has_adv
            else "normal"
        )

        roll_result = resolve_attack_base(
            RollActorStats(
                display_name=attacker["display_name"],
                abilities={},
                actor_kind="player",
                actor_ref_id=attacker["ref_id"],
            ),
            advantage_mode=adv_mode,
            bonus_override=attack_bonus,
            target_ac=target_ac,
            roll_source="system",
        )
        roll_result.is_gm_roll = is_gm
        roll_result.roll_source = "system"

        is_critical = roll_result.selected_roll == 20
        is_hit = bool(roll_result.success)

        damage = 0
        healing = 0
        new_hp = None
        previous_hp = None

        if is_hit:
            _, total = cls._resolve_damage_roll(instance_dice, critical=is_critical, roll_source="system")
            amount = max(0, total)
            if amount > 0:
                new_hp, _, previous_hp, _ = cls._apply_spell_effect(
                    db, state,
                    target_p["ref_id"], target_p["kind"],
                    effect_kind, amount,
                    damage_type=damage_type,
                    is_critical=is_critical,
                    concentration_roll_source=req.concentration_roll_source,
                    concentration_manual_roll=req.concentration_manual_roll,
                )
                if effect_kind == "healing":
                    healing = amount
                else:
                    damage = amount
        else:
            flag_modified(state, "participants")

        return {
            "target_ref_id": target_p["ref_id"],
            "target_display_name": target_p.get("display_name", ""),
            "target_kind": target_p.get("kind", "session_entity"),
            "damage": damage,
            "healing": healing,
            "is_hit": is_hit,
            "is_saved": None,
            "is_critical": is_critical,
            "roll": roll_result.total,
            "roll_result": roll_result,
            "new_hp": new_hp,
            "previous_hp": previous_hp,
            "cover": cover,
            "base_ac": base_ac,
            "effective_ac": target_ac,
            "cover_modifier": cover_modifier,
        }

    @classmethod
    async def _resolve_multi_instance_cast(
        cls, db, session_id, req, state, attacker, attacker_model,
        spell_context, actor_user_id, is_gm, validated_targets,
        *,
        spatial_results_by_target_ref: dict[str, TargetingResult] | None = None,
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
            attacker, action_cost,
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

        spell_mode = spell_context["spell_mode"]
        is_hostile = spell_mode in ("spell_attack", "saving_throw", "direct_damage")
        if is_hostile:
            seen = set()
            for vt in validated_targets:
                ref_id = vt["target_ref_id"]
                if ref_id not in seen:
                    cls._assert_hostile_action_allowed(
                        attacker, vt["participant"], action_label="a hostile spell",
                    )
                    seen.add(ref_id)

        logger.info(
            "[cast_spell] pipeline=multi_instance spell=%s instances=%d session=%s actor=%s",
            spell_context["spell_canonical_key"],
            len(validated_targets),
            session_id,
            attacker.get("ref_id"),
        )

        outcomes = []
        entity_previous_hp_map = {}

        for vt in validated_targets:
            target_p = vt["participant"]

            if spell_mode == "spell_attack":
                instance_targeting_result = (spatial_results_by_target_ref or {}).get(
                    vt["target_ref_id"]
                )
                outcome = cls._resolve_instance_attack(
                    db, session_id, state, attacker, target_p, spell_context, req, is_gm,
                    targeting_result=instance_targeting_result,
                )
            else:
                outcome = cls._resolve_instance_direct(
                    db, state, attacker, target_p, spell_context, req,
                )

            outcome["instance_index"] = vt["instance_index"]
            outcomes.append(outcome)

            ref_id = vt["target_ref_id"]
            if ref_id not in entity_previous_hp_map and outcome.get("previous_hp") is not None:
                entity_previous_hp_map[ref_id] = outcome["previous_hp"]

        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)

        player_state_ids = set()
        if slot_spent:
            player_state_ids.add(attacker["ref_id"])

        for outcome in outcomes:
            if outcome["damage"] > 0 or outcome["healing"] > 0:
                if outcome["target_kind"] == "player":
                    player_state_ids.add(outcome["target_ref_id"])

        for player_ref_id in player_state_ids:
            target_state, *_ = cls._get_stats(db, player_ref_id, "player", session_id)
            await cls._emit_player_state_update(db, session_id, player_ref_id, target_state)

        for ref_id, prev_hp in entity_previous_hp_map.items():
            target_p_entity = next(
                (p for p in state.participants if p["ref_id"] == ref_id), None,
            )
            if target_p_entity and target_p_entity.get("kind") == "session_entity":
                await cls._emit_entity_hp_update(db, session_id, ref_id, prev_hp)

        await cls._emit_state(session_id, state)

        log_message = cls._build_multi_instance_log_message(
            attacker=attacker,
            spell_context=spell_context,
            outcomes=outcomes,
            was_overridden=was_overridden,
            action_cost=action_cost,
        )
        await cls._emit_log(session_id, {
            "message": log_message,
            "actorUserId": actor_user_id,
            "source": "gm_override" if is_gm else "player_turn",
            "is_override": was_overridden,
            "overridden_resource": action_cost if was_overridden else None,
        })

        total_damage = sum(o["damage"] for o in outcomes)
        total_healing = sum(o["healing"] for o in outcomes)
        first_outcome = outcomes[0] if outcomes else None

        return {
            "spell_name": spell_context["spell_name"],
            "spell_canonical_key": spell_context["spell_canonical_key"],
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
            "target_display_name": first_outcome["target_display_name"] if first_outcome else "",
            "target_kind": first_outcome["target_kind"] if first_outcome else "session_entity",
            "save_ability": spell_context.get("save_ability"),
            "save_dc": spell_context.get("save_dc"),
            "save_success_outcome": spell_context.get("save_success_outcome"),
            "effect_dice": spell_context.get("effect_instance_dice"),
            "effect_bonus": 0,
            "pending_spell_id": None,
            "pending_save_id": None,
            "effect_roll_required": False,
            "effect_rolls": [],
            "base_effect": None,
            "effect_roll_source": None,
            "action_cost": action_cost,
            "summary_text": None,
            "inventory_refresh_required": spell_context.get("source_kind") == "magic_item",
            "concentration_check": None,
            "concentration_checks": [],
            "area_shape": None,
            "affected_target_ref_ids": [],
            "affected_cells": [],
            "area_target_outcomes": [],
            "target_count": len(validated_targets),
            "elemental_affinity_eligible": bool(spell_context.get("elemental_affinity_eligible")),
            "elemental_affinity_damage_type": spell_context.get("elemental_affinity_damage_type"),
            "elemental_affinity_bonus": spell_context.get("elemental_affinity_bonus"),
            "effect_instance_count": spell_context.get("effect_instance_count"),
            "effect_instance_dice": spell_context.get("effect_instance_dice"),
            "base_effect_instance_count": spell_context.get("base_effect_instance_count"),
            "effect_instance_outcomes": outcomes,
        }

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
    async def _resolve_no_external_target_cast(
        cls, db, session_id, req, state, attacker, attacker_model,
        spell_context, actor_user_id, is_gm,
    ):
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
            target_participant=attacker,
        )
        if automation_result is not None:
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
            return await cls._commit_cast_result(
                db,
                session_id,
                state,
                attacker,
                spell_context,
                {
                    "result": result,
                    "spell_mode": automation_result["action_kind"],
                    "effect_kind": automation_result["effect_kind"],
                    "effect_bonus": cls._safe_int(
                        automation_result.get("effect_bonus"), 0
                    ),
                    "save_success_outcome": spell_context.get("save_success_outcome"),
                    "slot_spent": slot_spent,
                    "inventory_refresh_required": spell_context.get("source_kind") == "magic_item"
                    or bool(automation_result.get("inventory_refresh_required")),
                    "summary_text": automation_result.get("summary_text"),
                    "custom_log_message": automation_result.get("__log_message"),
                    "automation_player_state_ids": automation_result.get("__player_state_ids_to_emit") or set(),
                    "was_overridden": was_overridden,
                    "action_cost": action_cost,
                    "target_p": attacker,
                    "automation_result": automation_result,
                },
                actor_user_id,
                is_gm,
            )

        db.add(state)
        db.commit()
        db.refresh(state)

        if slot_spent:
            target_state, *_ = cls._get_stats(db, attacker["ref_id"], "player", session_id)
            await cls._emit_player_state_update(db, session_id, attacker["ref_id"], target_state)
        await cls._emit_state(session_id, state)
        log_message = f"{attacker['display_name']} conjurou {spell_context['spell_name']}."
        if spell_context.get("effect_timing") == "triggered":
            log_message = f"{log_message} Efeito preparado para gatilho."
        elif spell_context.get("effect_timing") == "persistent":
            log_message = f"{log_message} Efeito persistente iniciado."
        if was_overridden:
            log_message = f"[OVERRIDE: Limit for '{action_cost}' ignored] {log_message}"
        await cls._emit_log(session_id, {
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
            "target_display_name": attacker.get("display_name"),
            "target_kind": attacker.get("kind"),
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
            "concentration_check": None,
            "concentration_checks": [],
            "area_shape": None,
            "affected_target_ref_ids": [],
            "affected_cells": [],
            "area_target_outcomes": [],
            "target_count": 0,
            "elemental_affinity_eligible": bool(spell_context.get("elemental_affinity_eligible")),
            "elemental_affinity_damage_type": spell_context.get("elemental_affinity_damage_type"),
            "elemental_affinity_bonus": spell_context.get("elemental_affinity_bonus"),
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
        validated_targets = cls._validate_instance_targets(
            req=req, spell_context=spell_context, state=state,
        )
        if validated_targets is not None:
            spatial_results_by_target_ref = cls._validate_instance_spatial_targets(
                state=state,
                attacker=attacker,
                spell_context=spell_context,
                validated_targets=validated_targets,
                session_id=session_id,
            )
            return await cls._resolve_multi_instance_cast(
                db, session_id, req, state, attacker, attacker_model,
                spell_context, actor_user_id, is_gm, validated_targets,
                spatial_results_by_target_ref=spatial_results_by_target_ref,
            )
        area_spell_spec = cls._resolve_supported_area_spell_spec(spell_context)
        if cls._normalize_area_shape(spell_context.get("area_shape")) is not None:
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

        if spell_context.get("selection_type") in ("none", "self"):
            return await cls._resolve_no_external_target_cast(
                db, session_id, req, state, attacker, attacker_model,
                spell_context, actor_user_id, is_gm,
            )

        resolution = await cls._resolve_cast_resolution(
            db, session_id, req, state, attacker, attacker_model,
            spell_context, actor_user_id, is_gm,
        )
        return await cls._commit_cast_result(
            db, session_id, state, attacker, spell_context,
            resolution, actor_user_id, is_gm,
        )
