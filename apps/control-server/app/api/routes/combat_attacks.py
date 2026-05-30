from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import get_current_user, get_session
from app.api.routes.combat import _is_session_gm, _publish_roll_result
from app.models.user import User
from app.schemas.combat import (
    CombatAttackRequest,
    CombatAttackResult,
    CombatResolveDamageRequest,
    CombatWildShapeAttackRequest,
)
from app.services.combat import CombatService

router = APIRouter()


@router.post(
    "/sessions/{session_id}/combat/action/attack", response_model=CombatAttackResult
)
async def action_attack(
    session_id: str,
    req: CombatAttackRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    assert user.id is not None  # authenticated user always has an id
    result = await CombatService.attack(
        db, session_id, req, user.id, _is_session_gm(db, session_id, user)
    )
    await _publish_roll_result(db, session_id, user, result.get("roll_result"))
    return result


@router.post(
    "/sessions/{session_id}/combat/action/attack/damage",
    response_model=CombatAttackResult,
)
async def action_attack_damage(
    session_id: str,
    req: CombatResolveDamageRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    assert user.id is not None  # authenticated user always has an id
    result = await CombatService.attack_damage(
        db, session_id, req, user.id, _is_session_gm(db, session_id, user)
    )
    concentration_roll = (
        result.get("concentration_check", {}).get("roll_result")
        if isinstance(result.get("concentration_check"), dict)
        else None
    )
    await _publish_roll_result(db, session_id, user, concentration_roll)
    return result


@router.post(
    "/sessions/{session_id}/combat/action/wild-shape-attack",
    response_model=CombatAttackResult,
)
async def action_wild_shape_attack(
    session_id: str,
    req: CombatWildShapeAttackRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    assert user.id is not None  # authenticated user always has an id
    result = await CombatService.wild_shape_attack(
        db, session_id, req, user.id, _is_session_gm(db, session_id, user)
    )
    await _publish_roll_result(db, session_id, user, result.get("roll_result"))
    return result
