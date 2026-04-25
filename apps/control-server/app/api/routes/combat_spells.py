from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import get_current_user, get_session
from app.api.routes.combat import _is_session_gm, _publish_roll_result
from app.models.user import User
from app.schemas.combat import (
    CombatAreaPreviewRequest,
    CombatAreaPreviewResponse,
    CombatCastSpellRequest,
    CombatMapPreviewState,
    CombatMovementPreviewRequest,
    CombatMovementPreviewResponse,
    CombatResolveSpellEffectRequest,
    CombatSpellResult,
)
from app.services.combat import CombatService

router = APIRouter()


@router.post(
    "/sessions/{session_id}/combat/action/cast", response_model=CombatSpellResult
)
async def action_cast_spell(
    session_id: str,
    req: CombatCastSpellRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    result = await CombatService.cast_spell(
        db, session_id, req, user.id, _is_session_gm(db, session_id, user)
    )
    await _publish_roll_result(db, session_id, user, result.get("roll_result"))
    concentration_roll = (
        result.get("concentration_check", {}).get("roll_result")
        if isinstance(result.get("concentration_check"), dict)
        else None
    )
    await _publish_roll_result(db, session_id, user, concentration_roll)
    return result


@router.get(
    "/sessions/{session_id}/combat/map-state",
    response_model=CombatMapPreviewState,
)
def get_area_targeting_map_state(
    session_id: str,
    actor_participant_id: str | None = None,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return CombatService.get_area_targeting_map_state(
        db,
        session_id,
        actor_user_id=user.id,
        is_gm=_is_session_gm(db, session_id, user),
        actor_participant_id=actor_participant_id,
    )


@router.post(
    "/sessions/{session_id}/combat/action/cast/preview",
    response_model=CombatAreaPreviewResponse,
)
def action_cast_spell_preview(
    session_id: str,
    req: CombatAreaPreviewRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return CombatService.preview_area_spell_targeting(
        db,
        session_id,
        req,
        user.id,
        _is_session_gm(db, session_id, user),
    )


@router.post(
    "/sessions/{session_id}/combat/action/move/preview",
    response_model=CombatMovementPreviewResponse,
)
async def action_move_preview(
    session_id: str,
    req: CombatMovementPreviewRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await CombatService.preview_movement(
        db,
        session_id,
        req,
        actor_user_id=user.id,
        is_gm=_is_session_gm(db, session_id, user),
    )


@router.post(
    "/sessions/{session_id}/combat/action/move",
    response_model=CombatMovementPreviewResponse,
)
async def action_move(
    session_id: str,
    req: CombatMovementPreviewRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await CombatService.confirm_movement(
        db,
        session_id,
        req,
        actor_user_id=user.id,
        is_gm=_is_session_gm(db, session_id, user),
    )


@router.post(
    "/sessions/{session_id}/combat/action/cast/effect", response_model=CombatSpellResult
)
async def action_cast_spell_effect(
    session_id: str,
    req: CombatResolveSpellEffectRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    result = await CombatService.cast_spell_effect(
        db, session_id, req, user.id, _is_session_gm(db, session_id, user)
    )
    concentration_roll = (
        result.get("concentration_check", {}).get("roll_result")
        if isinstance(result.get("concentration_check"), dict)
        else None
    )
    await _publish_roll_result(db, session_id, user, concentration_roll)
    return result
