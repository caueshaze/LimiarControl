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
from ..exceptions import CombatServiceError
from ..limiar_map_projection import maybe_sync_active_area_effects_to_limiar_map
from ..persistent_area_effects import build_persistent_spell_area_effect
from ..host_protocol import CombatServiceHostProtocol

if TYPE_CHECKING:
    _AreaMixinBase = CombatServiceHostProtocol
else:
    _AreaMixinBase = object


class SilentImageAreaMixin(_AreaMixinBase):
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
