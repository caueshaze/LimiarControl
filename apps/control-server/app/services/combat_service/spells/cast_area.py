from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app.core.config import settings
from app.integrations import LimiarMapClientError
from app.models.combat import CombatState
from app.models.inventory import InventoryItem
from app.schemas.combat import CombatCastSpellRequest
from app.services.magic_item_effects import consume_inventory_item_charge
from app.services.roll_resolution import resolve_saving_throw

from ..combat_targeting import get_combat_targeting_service
from ..cover_modifiers import resolve_cover_save_dc, should_cover_apply_to_save
from ..exceptions import CombatServiceError
from ..limiar_map_projection import maybe_sync_active_area_effects_to_limiar_map
from ..persistent_area_effects import build_persistent_spell_area_effect
from ..targeting_intent import AreaTargetingIntent

logger = logging.getLogger(__name__)


class CastAreaMixin:
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

        Used when cover_applies_to_save warrants per-target DC reduction.
        Any target whose lookup fails maps to None so the cast continues at
        the base DC (defensive default — cover is a bonus, not a blocker).

        TODO: Replace N individual calls with a batch endpoint once the map
        API exposes one (follow-up: Batch area target spatial metadata lookup).
        """
        if not target_ref_ids:
            return {}
        if not use_map or not settings.limiar_map_enabled:
            return {ref_id: None for ref_id in target_ref_ids}
        client = cls._build_limiar_map_client()
        result: dict[str, str | None] = {}
        for target_ref_id in target_ref_ids:
            try:
                response = client.validate_single_target(
                    session_id=session_id,
                    action_id=f"{action_id}:cover:{target_ref_id}",
                    combatant_id=actor_ref_id,
                    target_combatant_id=target_ref_id,
                    range_cells=None,
                    requires_sight=False,
                    requires_effect=False,
                )
                result[target_ref_id] = response.cover
            except LimiarMapClientError as exc:
                logger.warning(
                    "Cover lookup failed for area target session_id=%s "
                    "target_ref_id=%s (%s); falling back to base DC",
                    session_id,
                    target_ref_id,
                    exc,
                )
                result[target_ref_id] = None
        return result

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

        affected_participants = [
            participant
            for participant in state.participants
            if participant["ref_id"] in targeting_result.affected_target_ref_ids
        ]
        for target_participant in affected_participants:
            cls._assert_hostile_action_allowed(
                attacker,
                target_participant,
                action_label="a hostile spell",
            )
            cls._validate_spell_automation_target(
                db,
                session_id,
                spell_canonical_key=spell_context["spell_canonical_key"],
                target_participant=target_participant,
            )
        cover_applies_to_save = spell_context.get("cover_applies_to_save")
        per_target_cover: dict[str, str | None] = {}
        if should_cover_apply_to_save(cover_applies_to_save):
            per_target_cover = cls._get_area_per_target_cover(
                session_id=session_id,
                action_id=f"area-cover:{uuid4()}",
                actor_ref_id=attacker["ref_id"],
                target_ref_ids=[p["ref_id"] for p in affected_participants],
                use_map=state.use_map,
            )

        base_save_dc = cls._safe_int(spell_context.get("save_dc"), 0)
        area_target_outcomes: list[dict[str, Any]] = []
        target_results_for_pending: list[dict[str, Any]] = []
        for target_participant in affected_participants:
            target_ref_id = target_participant["ref_id"]
            target_cover = per_target_cover.get(target_ref_id)
            effective_dc, _ = resolve_cover_save_dc(
                base_save_dc,
                target_cover,
                cover_applies_to_save,
                spell_context.get("save_ability"),
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
                dc=effective_dc,
            )
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
                "effective_dc": effective_dc,
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

        primary_result_target = (
            anchor_target
            or (affected_participants[0] if affected_participants else None)
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
            },
        )

        db.add(state)
        db.commit()
        db.refresh(state)

        if slot_spent:
            target_state, *_ = cls._get_stats(db, attacker["ref_id"], "player", session_id)
            await cls._emit_player_state_update(db, session_id, attacker["ref_id"], target_state)
        await cls._emit_state(session_id, state)

        target_count = len(area_target_outcomes)
        area_label = f"Area ({target_count} alvo{'s' if target_count != 1 else ''})"
        log_message = (
            f"{attacker['display_name']} lancou {spell_context['spell_name']} em area "
            f"({area_spec['shape']}): {target_count} alvo{'s' if target_count != 1 else ''} afetado{'s' if target_count != 1 else ''}. "
            "Efeito pendente."
        )
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

        active_area_effect: dict[str, Any] | None = None
        concentration_group: str | None = None
        if spell_context.get("effect_timing") == "persistent":
            if spell_context.get("concentration"):
                prev = cls._clear_concentration_for_source(
                    state, source_participant_id=attacker["id"],
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
