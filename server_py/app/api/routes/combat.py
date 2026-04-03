from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.api.deps import get_current_user, get_session
from app.api.routes.sessions._shared import record_session_activity
from app.models.campaign import RoleMode
from app.models.campaign_member import CampaignMember
from app.models.combat import CombatState
from app.models.session import Session as CampaignSession
from app.models.user import User
from app.schemas.combat import (
    CombatApplyDamageRequest,
    CombatApplyEffectRequest,
    CombatConsumeReactionRequest,
    CombatReactionRequestRequest,
    CombatReactionResolveRequest,
    CombatStandardActionRequest,
    CombatStandardActionResult,
    CombatApplyHealingRequest,
    CombatAttackRequest,
    CombatAttackResult,
    CombatCastSpellRequest,
    CombatDeathSaveRequest,
    CombatEntityActionRequest,
    CombatEntityActionResult,
    CombatNextTurnRequest,
    CombatRemoveEffectRequest,
    CombatReviveRequest,
    CombatReviveResult,
    CombatResolveDamageRequest,
    CombatResolveSpellEffectRequest,
    CombatSetInitiativeRequest,
    CombatSpellResult,
    CombatStartRequest,
    CombatWildShapeAttackRequest,
)
from app.services.centrifugo import centrifugo
from app.services.combat import CombatService, CombatServiceError
from app.services.realtime import build_event, campaign_channel, event_version, session_channel

router = APIRouter()


def _is_session_gm(db: Session, session_id: str, user: User) -> bool:
    """Check if user is GM in the campaign that owns this session."""
    session_entry = db.exec(
        select(CampaignSession).where(CampaignSession.id == session_id)
    ).first()
    if not session_entry:
        return False
    member = db.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == session_entry.campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    return member is not None and member.role_mode == RoleMode.GM


async def _publish_roll_result(
    db: Session,
    session_id: str,
    user: User,
    result,
) -> None:
    if result is None:
        return
    if isinstance(result, dict):
        timestamp = result.get("timestamp")
        payload = dict(result)
    else:
        timestamp = result.timestamp
        payload = result.model_dump(mode="json")

    if timestamp is None:
        return

    session_entry = db.exec(select(CampaignSession).where(CampaignSession.id == session_id)).first()
    if not session_entry:
        return

    member = db.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == session_entry.campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not member or not member.id:
        return

    payload["partyId"] = session_entry.party_id

    await centrifugo.publish(
        session_channel(session_entry.id),
        build_event("roll_resolved", payload, version=event_version(timestamp)),
    )
    await centrifugo.publish(
        campaign_channel(session_entry.campaign_id),
        build_event("roll_resolved", payload, version=event_version(timestamp)),
    )

    record_session_activity(
        session_entry,
        "roll_resolved",
        db,
        member_id=member.id,
        user_id=user.id,
        actor_name=member.display_name,
        payload=payload,
        created_at=timestamp,
    )
    db.commit()

@router.get("/sessions/{session_id}/combat")
def get_combat_state(
    session_id: str,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    state = CombatService.get_state(db, session_id)
    if not state:
        return {"phase": "ended", "participants": [], "round": 0, "current_turn_index": 0}
    return state


@router.post("/sessions/{session_id}/combat/start", response_model=CombatState)
async def start_combat(
    session_id: str,
    req: CombatStartRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if not _is_session_gm(db, session_id, user):
        raise CombatServiceError("Only GM can start combat", 403)
    return await CombatService.start_combat(db, session_id, req)


@router.put("/sessions/{session_id}/combat/initiative", response_model=CombatState)
async def set_initiative(
    session_id: str,
    req: CombatSetInitiativeRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if not _is_session_gm(db, session_id, user):
        raise CombatServiceError("Only GM can set initiative", 403)
    return await CombatService.set_initiative(db, session_id, req)


@router.post("/sessions/{session_id}/combat/turn/next", response_model=CombatState)
async def next_turn(
    session_id: str,
    req: CombatNextTurnRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await CombatService.next_turn(
        db,
        session_id,
        user.id,
        _is_session_gm(db, session_id, user),
        req.actor_participant_id,
    )


@router.post("/sessions/{session_id}/combat/end", response_model=CombatState)
async def end_combat(
    session_id: str,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await CombatService.end_combat(db, session_id, _is_session_gm(db, session_id, user))


@router.post("/sessions/{session_id}/combat/action/attack", response_model=CombatAttackResult)
async def action_attack(
    session_id: str,
    req: CombatAttackRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    result = await CombatService.attack(db, session_id, req, user.id, _is_session_gm(db, session_id, user))
    await _publish_roll_result(db, session_id, user, result.get("roll_result"))
    return result


@router.post("/sessions/{session_id}/combat/action/attack/damage", response_model=CombatAttackResult)
async def action_attack_damage(
    session_id: str,
    req: CombatResolveDamageRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    result = await CombatService.attack_damage(db, session_id, req, user.id, _is_session_gm(db, session_id, user))
    concentration_roll = (
        result.get("concentration_check", {}).get("roll_result")
        if isinstance(result.get("concentration_check"), dict)
        else None
    )
    await _publish_roll_result(db, session_id, user, concentration_roll)
    return result


@router.post("/sessions/{session_id}/combat/action/wild-shape-attack", response_model=CombatAttackResult)
async def action_wild_shape_attack(
    session_id: str,
    req: CombatWildShapeAttackRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    result = await CombatService.wild_shape_attack(db, session_id, req, user.id, _is_session_gm(db, session_id, user))
    await _publish_roll_result(db, session_id, user, result.get("roll_result"))
    return result


@router.post("/sessions/{session_id}/combat/action/cast", response_model=CombatSpellResult)
async def action_cast_spell(
    session_id: str,
    req: CombatCastSpellRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    result = await CombatService.cast_spell(db, session_id, req, user.id, _is_session_gm(db, session_id, user))
    await _publish_roll_result(db, session_id, user, result.get("roll_result"))
    concentration_roll = (
        result.get("concentration_check", {}).get("roll_result")
        if isinstance(result.get("concentration_check"), dict)
        else None
    )
    await _publish_roll_result(db, session_id, user, concentration_roll)
    return result


@router.post("/sessions/{session_id}/combat/action/cast/effect", response_model=CombatSpellResult)
async def action_cast_spell_effect(
    session_id: str,
    req: CombatResolveSpellEffectRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    result = await CombatService.cast_spell_effect(db, session_id, req, user.id, _is_session_gm(db, session_id, user))
    concentration_roll = (
        result.get("concentration_check", {}).get("roll_result")
        if isinstance(result.get("concentration_check"), dict)
        else None
    )
    await _publish_roll_result(db, session_id, user, concentration_roll)
    return result


@router.post("/sessions/{session_id}/combat/action/entity", response_model=CombatEntityActionResult)
async def action_entity(
    session_id: str,
    req: CombatEntityActionRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    result = await CombatService.entity_action(db, session_id, req, user.id, _is_session_gm(db, session_id, user))
    await _publish_roll_result(db, session_id, user, result.get("roll_result"))
    concentration_roll = (
        result.get("concentration_check", {}).get("roll_result")
        if isinstance(result.get("concentration_check"), dict)
        else None
    )
    await _publish_roll_result(db, session_id, user, concentration_roll)
    return result


@router.post("/sessions/{session_id}/combat/action/entity/damage", response_model=CombatEntityActionResult)
async def action_entity_damage(
    session_id: str,
    req: CombatResolveDamageRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    result = await CombatService.entity_action_damage(db, session_id, req, user.id, _is_session_gm(db, session_id, user))
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
    result = await CombatService.apply_damage(db, session_id, req, user.id, _is_session_gm(db, session_id, user))
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
    return await CombatService.apply_healing(db, session_id, req, user.id, _is_session_gm(db, session_id, user))


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


@router.post("/sessions/{session_id}/combat/action/revive", response_model=CombatReviveResult)
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


# --- Standard Actions ---


@router.post("/sessions/{session_id}/combat/action/standard", response_model=CombatStandardActionResult)
async def action_standard(
    session_id: str,
    req: CombatStandardActionRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    result = await CombatService.standard_action(db, session_id, req, user.id, _is_session_gm(db, session_id, user))
    if result.get("roll_result"):
        await _publish_roll_result(db, session_id, user, result["roll_result"])
    return result


# --- Action Economy ---


@router.post("/sessions/{session_id}/combat/action/consume-reaction")
async def action_consume_reaction(
    session_id: str,
    req: CombatConsumeReactionRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if not _is_session_gm(db, session_id, user):
        raise CombatServiceError("Players can only request reactions, not consume directly.", 403)
    return await CombatService.consume_reaction(db, session_id, req, user.id, _is_session_gm(db, session_id, user))


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


# --- Active Effects ---


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
