from __future__ import annotations

from typing import Any
from uuid import uuid4

from sqlmodel import Session

from app.integrations import LimiarMapClientError
from app.schemas.combat import (
    CombatMovementPreviewRequest,
    CombatMovementPreviewResponse,
)
from .exceptions import CombatServiceError
from .fall_damage import FALL_DAMAGE_METERS_PER_DIE
from .movement_hazards import compute_movement_hazard_outcomes
from .spells.area_targeting import AreaTargetingMixin


class CombatMovementMixin(AreaTargetingMixin):
    @classmethod
    async def _preview_or_confirm_movement(
        cls,
        db: Session,
        session_id: str,
        req: CombatMovementPreviewRequest,
        *,
        actor_user_id: str,
        is_gm: bool,
        confirm: bool,
    ) -> CombatMovementPreviewResponse:
        state = cls.get_state(db, session_id)
        cls._require_active(state)
        if not state.use_map:
            raise CombatServiceError("This combat was opened without a tactical map.", 400)

        actor = cls._resolve_actor_participant(
            state,
            actor_user_id,
            is_gm,
            req.actor_participant_id,
        )
        cls._require_actor_status(actor, ("active",), "You can only move while active.")
        cls._require_movement_capable(actor)

        client = cls._build_limiar_map_client()
        destination_cell = {
            "x": req.destination_cell.x,
            "y": req.destination_cell.y,
        }
        action_id = f"movement:{'confirm' if confirm else 'preview'}:{uuid4()}"

        try:
            response = (
                client.move_combatant(
                    session_id=session_id,
                    action_id=action_id,
                    combatant_id=actor["ref_id"],
                    destination_cell=destination_cell,
                )
                if confirm
                else client.preview_movement(
                    session_id=session_id,
                    action_id=action_id,
                    combatant_id=actor["ref_id"],
                    destination_cell=destination_cell,
                )
            )
        except LimiarMapClientError as exc:
            raise CombatServiceError(
                f"Movement {'confirmation' if confirm else 'preview'} is unavailable: {exc}",
                503,
            ) from exc

        if confirm and response.is_valid:
            await cls._apply_movement_hazards(
                db,
                session_id=session_id,
                state=state,
                actor=actor,
                response=response,
                actor_user_id=actor_user_id,
            )
            await cls._apply_movement_fall(
                db,
                session_id=session_id,
                actor=actor,
                response=response,
                actor_user_id=actor_user_id,
                is_gm=is_gm,
            )

        return CombatMovementPreviewResponse(
            is_valid=response.is_valid,
            reason=response.reason,
            source_cell=(
                {"x": response.source_cell.x, "y": response.source_cell.y}
                if response.source_cell is not None
                else None
            ),
            destination_cell={
                "x": response.destination_cell.x,
                "y": response.destination_cell.y,
            },
            path=[{"x": cell.x, "y": cell.y} for cell in response.path],
            path_cost_units=response.path_cost_units,
            movement_budget=response.movement_budget,
            movement_speed_cells=response.movement_speed_cells,
            remaining_budget=response.remaining_budget,
            map_version=response.version,
        )

    @classmethod
    async def _apply_movement_hazards(
        cls,
        db: Session,
        *,
        session_id: str,
        state: Any,
        actor: dict[str, Any],
        response: Any,
        actor_user_id: str,
    ) -> None:
        active_area_effects = (
            state.active_area_effects if isinstance(state.active_area_effects, list) else []
        )
        if not active_area_effects:
            return
        path_cells = [{"x": cell.x, "y": cell.y} for cell in response.path]
        outcomes = compute_movement_hazard_outcomes(active_area_effects, path_cells)
        if not outcomes:
            return

        target_ref_id = actor.get("ref_id")
        target_kind = actor.get("kind")
        if not target_ref_id or target_kind not in ("player", "session_entity"):
            return

        previous_hp_player: int | None = None
        previous_hp_entity: int | None = None
        applied: list[tuple[dict[str, Any], int, str]] = []
        for outcome in outcomes:
            new_hp, effect_msg, previous_hp, _concentration = cls._apply_damage_to_target(
                db,
                target_ref_id,
                target_kind,
                outcome["damage"],
                damage_type=outcome.get("damage_type"),
                is_crit=False,
                state=state,
            )
            if target_kind == "session_entity":
                if previous_hp_entity is None:
                    previous_hp_entity = previous_hp
            else:
                if previous_hp_player is None:
                    previous_hp_player = previous_hp
            applied.append((outcome, new_hp, effect_msg))

        db.commit()

        if target_kind == "player":
            target_state, *_ = cls._get_stats(db, target_ref_id, target_kind, session_id)
            await cls._emit_player_state_update(db, session_id, target_ref_id, target_state)
        elif previous_hp_entity is not None:
            await cls._emit_entity_hp_update(db, session_id, target_ref_id, previous_hp_entity)
        if state:
            await cls._emit_state(session_id, state)

        actor_name = actor.get("display_name") or "Combatant"
        for outcome, _new_hp, effect_msg in applied:
            spell_name = outcome["source_spell_name"]
            cells = outcome["cells_inside"]
            damage = outcome["damage"]
            damage_type = outcome.get("damage_type")
            type_suffix = f" {damage_type}" if isinstance(damage_type, str) and damage_type else ""
            cell_word = "cell" if cells == 1 else "cells"
            message = (
                f"{actor_name} took {damage}{type_suffix} damage from {spell_name} "
                f"({cells} {cell_word} traversed).{effect_msg}"
            )
            await cls._emit_log(
                session_id,
                {
                    "message": message,
                    "source": "movement_hazard",
                    "actorUserId": actor_user_id,
                    "spellCanonicalKey": outcome.get("source_spell_canonical_key"),
                    "effectId": outcome.get("effect_id"),
                    "damage": damage,
                    "damageType": damage_type,
                    "diceExpression": outcome.get("dice_expression"),
                    "damageInstances": outcome.get("damage_instances"),
                    "cellsTraversed": cells,
                    "metersTraversed": outcome.get("meters_inside"),
                },
            )

    @classmethod
    async def _apply_movement_fall(
        cls,
        db: Session,
        *,
        session_id: str,
        actor: dict[str, Any],
        response: Any,
        actor_user_id: str,
        is_gm: bool,
    ) -> None:
        source_elevation = response.source_elevation_meters if response.source_elevation_meters is not None else 0.0
        dest_elevation = response.destination_elevation_meters if response.destination_elevation_meters is not None else 0.0
        delta = dest_elevation - source_elevation
        if delta >= 0:
            return
        fall_height = abs(delta)
        if fall_height < FALL_DAMAGE_METERS_PER_DIE:
            return
        await cls.resolve_fall(
            db,
            session_id,
            actor["id"],
            fall_height,
            actor_user_id,
            is_gm,
        )

    @classmethod
    async def preview_movement(
        cls,
        db: Session,
        session_id: str,
        req: CombatMovementPreviewRequest,
        *,
        actor_user_id: str,
        is_gm: bool,
    ) -> CombatMovementPreviewResponse:
        return await cls._preview_or_confirm_movement(
            db,
            session_id,
            req,
            actor_user_id=actor_user_id,
            is_gm=is_gm,
            confirm=False,
        )

    @classmethod
    async def confirm_movement(
        cls,
        db: Session,
        session_id: str,
        req: CombatMovementPreviewRequest,
        *,
        actor_user_id: str,
        is_gm: bool,
    ) -> CombatMovementPreviewResponse:
        return await cls._preview_or_confirm_movement(
            db,
            session_id,
            req,
            actor_user_id=actor_user_id,
            is_gm=is_gm,
            confirm=True,
        )
