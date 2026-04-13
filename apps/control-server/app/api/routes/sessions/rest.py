from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session as DbSession, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.campaign import RoleMode
from app.models.campaign_member import CampaignMember
from app.models.party import Party
from app.models.party_member import PartyMember, PartyMemberStatus
from app.models.session import Session, SessionStatus
from app.schemas.session_state import SessionUseHitDieRead
from app.services.centrifugo import centrifugo
from app.services.realtime import build_event, campaign_channel, event_version, session_channel
from app.services.session_rest import SessionRestError, use_hit_die
from app.services.session_state_finalize import finalize_session_state_data

from ._shared import get_session_rest_state, record_session_activity
from .shop import _ensure_player_session_state, _publish_session_state_realtime

router = APIRouter()


def _require_rest_player(entry: Session, user, session: DbSession) -> None:
    if entry.party_id:
        party = session.exec(select(Party).where(Party.id == entry.party_id)).first()
        if not party:
            raise HTTPException(status_code=404, detail="Party not found")
        if party.gm_user_id == user.id:
            raise HTTPException(status_code=403, detail="Only players can use Hit Dice")
        joined_member = session.exec(
            select(PartyMember).where(
                PartyMember.party_id == entry.party_id,
                PartyMember.user_id == user.id,
                PartyMember.status == PartyMemberStatus.JOINED,
            )
        ).first()
        if not joined_member:
            raise HTTPException(status_code=403, detail="Not a joined party member")
        return

    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not member or member.role_mode != RoleMode.PLAYER:
        raise HTTPException(status_code=403, detail="Only players can use Hit Dice")


@router.post("/sessions/{session_id}/rest/use-hit-die", response_model=SessionUseHitDieRead)
async def use_session_hit_die(
    session_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = session.exec(select(Session).where(Session.id == session_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")
    if entry.status != SessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Session is not active")

    _require_rest_player(entry, user, session)
    actor_member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not actor_member:
        raise HTTPException(status_code=404, detail="Campaign member not found")

    if get_session_rest_state(entry.id, session) != "short_rest":
        raise HTTPException(status_code=400, detail="Hit Dice can only be used during a short rest")

    state = _ensure_player_session_state(entry, user.id, session)
    try:
        next_state, outcome = use_hit_die(state.state_json)
    except SessionRestError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    state.state_json = finalize_session_state_data(next_state)
    session.add(state)
    record_session_activity(
        entry,
        "hit_dice_used",
        session,
        member_id=str(actor_member.id),
        user_id=user.id,
        actor_name=actor_member.display_name,
        payload=outcome,
    )
    session.commit()
    session.refresh(state)

    payload = {
        "sessionId": entry.id,
        "campaignId": entry.campaign_id,
        "partyId": entry.party_id,
        "playerUserId": user.id,
        **outcome,
        "issuedAt": (state.updated_at or state.created_at).isoformat(),
    }
    version = event_version(state.updated_at or state.created_at)
    await centrifugo.publish(
        session_channel(entry.id),
        build_event("hit_dice_used", payload, version=version),
    )
    await centrifugo.publish(
        campaign_channel(entry.campaign_id),
        build_event("hit_dice_used", payload, version=version),
    )
    await _publish_session_state_realtime(
        entry,
        user.id,
        state.updated_at or state.created_at,
        state.state_json if isinstance(state.state_json, dict) else None,
    )

    return SessionUseHitDieRead(
        sessionId=entry.id,
        campaignId=entry.campaign_id,
        partyId=entry.party_id,
        playerUserId=user.id,
        currentHp=int(outcome["currentHp"]),
        maxHp=int(outcome["maxHp"]),
        hitDiceRemaining=int(outcome["hitDiceRemaining"]),
        hitDiceTotal=int(outcome["hitDiceTotal"]),
        hitDieType=str(outcome["hitDieType"]),
        roll=int(outcome["roll"]),
        healingApplied=int(outcome["healingApplied"]),
        healingRolled=int(outcome["healingRolled"]),
        constitutionModifier=int(outcome["constitutionModifier"]),
    )
