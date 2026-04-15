from __future__ import annotations

from uuid import uuid4

from sqlmodel import Session

from app.integrations import LimiarMapClientError
from app.schemas.combat import (
    CombatMovementPreviewRequest,
    CombatMovementPreviewResponse,
)
from .exceptions import CombatServiceError
from .spells.area_targeting import AreaTargetingMixin


class CombatMovementMixin(AreaTargetingMixin):
    @classmethod
    def _preview_or_confirm_movement(
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
    def preview_movement(
        cls,
        db: Session,
        session_id: str,
        req: CombatMovementPreviewRequest,
        *,
        actor_user_id: str,
        is_gm: bool,
    ) -> CombatMovementPreviewResponse:
        return cls._preview_or_confirm_movement(
            db,
            session_id,
            req,
            actor_user_id=actor_user_id,
            is_gm=is_gm,
            confirm=False,
        )

    @classmethod
    def confirm_movement(
        cls,
        db: Session,
        session_id: str,
        req: CombatMovementPreviewRequest,
        *,
        actor_user_id: str,
        is_gm: bool,
    ) -> CombatMovementPreviewResponse:
        return cls._preview_or_confirm_movement(
            db,
            session_id,
            req,
            actor_user_id=actor_user_id,
            is_gm=is_gm,
            confirm=True,
        )
