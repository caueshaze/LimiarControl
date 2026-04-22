from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import get_current_user, get_session
from app.api.routes.combat import _is_session_gm, _publish_roll_result
from app.models.user import User
from app.schemas.combat import (
    CombatApplyDamageRequest,
    CombatApplyEffectRequest,
    CombatApplyHealingRequest,
    CombatConsumeReactionRequest,
    CombatDeathSaveRequest,
    CombatEntityActionRequest,
    CombatEntityActionResult,
    CombatReactionRequestRequest,
    CombatReactionResolveRequest,
    CombatRemoveEffectRequest,
    CombatResolveDamageRequest,
    CombatResolveSaveRequest,
    CombatReviveRequest,
    CombatReviveResult,
    CombatStandardActionRequest,
    CombatStandardActionResult,
)
from app.services.combat import CombatService, CombatServiceError

router = APIRouter()


@router.post(
    "/sessions/{session_id}/combat/action/entity",
    response_model=CombatEntityActionResult,
)
async def action_entity(
    session_id: str,
    req: CombatEntityActionRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    result = await CombatService.entity_action(
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


@router.post(
    "/sessions/{session_id}/combat/action/entity/damage",
    response_model=CombatEntityActionResult,
)
async def action_entity_damage(
    session_id: str,
    req: CombatResolveDamageRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    result = await CombatService.entity_action_damage(
        db, session_id, req, user.id, _is_session_gm(db, session_id, user)
    )
    concentration_roll = (
        result.get("concentration_check", {}).get("roll_result")
        if isinstance(result.get("concentration_check"), dict)
        else None
    )
    await _publish_roll_result(db, session_id, user, concentration_roll)
    return result


@router.post("/sessions/{session_id}/combat/action/apply-damage")
async def action_apply_damage(
    session_id: str,
    req: CombatApplyDamageRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    result = await CombatService.apply_damage(
        db, session_id, req, user.id, _is_session_gm(db, session_id, user)
    )
    concentration_roll = (
        result.get("concentration_check", {}).get("roll_result")
        if isinstance(result.get("concentration_check"), dict)
        else None
    )
    await _publish_roll_result(db, session_id, user, concentration_roll)
    return result


@router.post("/sessions/{session_id}/combat/action/apply-healing")
async def action_apply_healing(
    session_id: str,
    req: CombatApplyHealingRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await CombatService.apply_healing(
        db, session_id, req, user.id, _is_session_gm(db, session_id, user)
    )


@router.post("/sessions/{session_id}/combat/action/death-save")
async def action_death_save(
    session_id: str,
    req: CombatDeathSaveRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await CombatService.death_save(
        db,
        session_id,
        user.id,
        _is_session_gm(db, session_id, user),
        req.actor_participant_id,
    )


@router.post(
    "/sessions/{session_id}/combat/action/revive", response_model=CombatReviveResult
)
async def action_revive(
    session_id: str,
    req: CombatReviveRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await CombatService.revive_player(
        db,
        session_id,
        req.target_participant_id,
        user.id,
        _is_session_gm(db, session_id, user),
        hp=req.hp,
    )


@router.post(
    "/sessions/{session_id}/combat/action/standard",
    response_model=CombatStandardActionResult,
)
async def action_standard(
    session_id: str,
    req: CombatStandardActionRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    result = await CombatService.standard_action(
        db, session_id, req, user.id, _is_session_gm(db, session_id, user)
    )
    if result.get("roll_result"):
        await _publish_roll_result(db, session_id, user, result["roll_result"])
    return result


@router.post("/sessions/{session_id}/combat/action/consume-reaction")
async def action_consume_reaction(
    session_id: str,
    req: CombatConsumeReactionRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if not _is_session_gm(db, session_id, user):
        raise CombatServiceError(
            "Players can only request reactions, not consume directly.", 403
        )
    return await CombatService.consume_reaction(
        db, session_id, req, user.id, _is_session_gm(db, session_id, user)
    )


@router.post("/sessions/{session_id}/combat/action/reaction/request")
async def action_reaction_request(
    session_id: str,
    req: CombatReactionRequestRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await CombatService.request_reaction(db, session_id, req, user.id)


@router.post("/sessions/{session_id}/combat/action/reaction/resolve")
async def action_reaction_resolve(
    session_id: str,
    req: CombatReactionResolveRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if not _is_session_gm(db, session_id, user):
        raise CombatServiceError("Only GM can resolve reaction requests.", 403)
    return await CombatService.resolve_reaction(db, session_id, req)


@router.post("/sessions/{session_id}/combat/action/save-resolve")
async def action_save_resolve(
    session_id: str,
    req: CombatResolveSaveRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    result = await CombatService.resolve_pending_save(
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


@router.post("/sessions/{session_id}/combat/effects/apply")
async def apply_effect(
    session_id: str,
    req: CombatApplyEffectRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if not _is_session_gm(db, session_id, user):
        raise CombatServiceError("Only GM can apply effects", 403)
    return await CombatService.apply_effect(db, session_id, req)


@router.post("/sessions/{session_id}/combat/effects/remove")
async def remove_effect(
    session_id: str,
    req: CombatRemoveEffectRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if not _is_session_gm(db, session_id, user):
        raise CombatServiceError("Only GM can remove effects", 403)
    return await CombatService.remove_effect(db, session_id, req)


@router.get("/sessions/{session_id}/combat/effects")
def list_effects(
    session_id: str,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    state = CombatService.get_state(db, session_id)
    if not state:
        return []
    return CombatService.get_all_effects(state)
