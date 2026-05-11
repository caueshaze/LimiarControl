from fastapi import APIRouter, Depends
from pydantic import BaseModel
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
    CombatResolveSpellContextRequest,
    CombatResolvedSpellContext,
    CombatResolveSpellEffectRequest,
    CombatSpellResult,
)
from app.services.combat import CombatService


class SpiritualWeaponActionRequest(BaseModel):
    actor_participant_id: str
    anchor_id: str
    destination: dict | None = None
    target_ref_id: str | None = None
    target_kind: str | None = None
    manual_roll: int | None = None


class MageHandActionRequest(BaseModel):
    actor_participant_id: str
    anchor_id: str
    destination: dict

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
    "/sessions/{session_id}/combat/spells/resolve-context",
    response_model=CombatResolvedSpellContext,
)
def resolve_spell_context(
    session_id: str,
    req: CombatResolveSpellContextRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return CombatService.resolve_spell_context(
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


@router.post("/sessions/{session_id}/combat/spiritual-weapon-action")
async def spiritual_weapon_action(
    session_id: str,
    req: SpiritualWeaponActionRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await CombatService.use_spiritual_weapon_action(
        db,
        session_id,
        req,
        user.id,
        is_gm=_is_session_gm(db, session_id, user),
    )


@router.post("/sessions/{session_id}/combat/mage-hand-action")
async def mage_hand_action(
    session_id: str,
    req: MageHandActionRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await CombatService.use_mage_hand_action(
        db,
        session_id,
        req,
        user.id,
        is_gm=_is_session_gm(db, session_id, user),
    )
