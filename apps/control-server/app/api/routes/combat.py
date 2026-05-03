from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.api.deps import get_current_user, get_session
from app.api.routes.sessions._shared import record_session_activity
from app.models.campaign import RoleMode
from app.models.campaign_member import CampaignMember
from app.models.combat import CombatPhase, CombatState
from app.models.session import Session as CampaignSession
from app.models.user import User
from app.schemas.combat import (
    CombatMapEnsureResponse,
    CombatNextTurnRequest,
    CombatSetInitiativeRequest,
    CombatStartRequest,
    CombatUpdateDistancesRequest,
)
from app.services.centrifugo import centrifugo
from app.services.combat import (
    CombatService,
    CombatServiceError,
    get_limiar_map_projection_service,
)
from app.services.realtime import (
    build_event,
    campaign_channel,
    event_version,
    session_channel,
)

router = APIRouter()


def _is_session_gm(db: Session, session_id: str, user: User) -> bool:
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


def _require_session_member(
    db: Session,
    session_id: str,
    user: User,
) -> CampaignSession:
    session_entry = db.exec(
        select(CampaignSession).where(CampaignSession.id == session_id)
    ).first()
    if not session_entry:
        raise CombatServiceError("Session not found", 404)

    member = db.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == session_entry.campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if member is None:
        raise CombatServiceError("Not a campaign member", 403)

    return session_entry


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

    session_entry = db.exec(
        select(CampaignSession).where(CampaignSession.id == session_id)
    ).first()
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

    if isinstance(payload.get("check_modifier_sources"), list):
        payload["check_modifier_sources"] = payload["check_modifier_sources"]

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
        return {
            "phase": "ended",
            "participants": [],
            "round": 0,
            "current_turn_index": 0,
        }
    return state


@router.post(
    "/sessions/{session_id}/combat/map/ensure",
    response_model=CombatMapEnsureResponse,
)
def ensure_combat_map(
    session_id: str,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    _require_session_member(db, session_id, user)

    state = CombatService.get_state(db, session_id)
    if not state:
        return CombatMapEnsureResponse(
            session_id=session_id,
            combat_phase="ended",
            map_available=False,
            reason="combat_not_found",
        )

    phase = state.phase.value if hasattr(state.phase, "value") else str(state.phase)
    if state.phase not in (CombatPhase.active, CombatPhase.placement, "active", "placement"):
        return CombatMapEnsureResponse(
            session_id=session_id,
            combat_phase=phase,
            map_available=False,
            reason="combat_not_active",
        )

    if not state.use_map:
        return CombatMapEnsureResponse(
            session_id=session_id,
            combat_phase=phase,
            map_available=False,
            reason="map_disabled_for_combat",
        )

    result = get_limiar_map_projection_service().project_combat_start(
        db,
        session_id,
        state,
    )
    return CombatMapEnsureResponse(
        session_id=session_id,
        combat_phase=phase,
        map_available=result.map_available,
        reason=result.reason,
    )


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


@router.post("/sessions/{session_id}/combat/placement/confirm", response_model=CombatState)
async def confirm_combat_placement(
    session_id: str,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if not _is_session_gm(db, session_id, user):
        raise CombatServiceError("Only GM can confirm combat placement", 403)
    return await CombatService.confirm_placement(db, session_id)


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
    return await CombatService.end_combat(
        db, session_id, _is_session_gm(db, session_id, user)
    )


@router.patch("/sessions/{session_id}/combat/distances", response_model=CombatState)
async def update_distances(
    session_id: str,
    req: CombatUpdateDistancesRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if not _is_session_gm(db, session_id, user):
        raise CombatServiceError("Only GM can update combat distances", 403)
    return await CombatService.update_distances(db, session_id, req)


from app.api.routes.combat_attacks import router as _attacks_router
from app.api.routes.combat_spells import router as _spells_router
from app.api.routes.combat_actions import router as _actions_router

router.include_router(_attacks_router)
router.include_router(_spells_router)
router.include_router(_actions_router)
