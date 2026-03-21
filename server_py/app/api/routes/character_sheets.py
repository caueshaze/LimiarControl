from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.campaign_member import CampaignMember
from app.models.character_sheet import CharacterSheet
from app.models.party import Party
from app.models.party_member import PartyMember, PartyMemberStatus
from app.models.session import Session as CampaignSession, SessionStatus
from app.schemas.character_sheet import (
    CharacterSheetCreate,
    CharacterSheetRead,
    CharacterSheetUpdate,
)
from app.api.routes.sessions._shared import record_session_activity
from app.services.character_progression import (
    CharacterProgressionError,
    approve_level_up as approve_level_up_data,
    deny_level_up as deny_level_up_data,
    request_level_up as request_level_up_data,
)
from app.services.character_sheet_inventory import sync_character_sheet_inventory
from app.services.centrifugo import centrifugo
from app.services.race_config import normalize_race_state, validate_race_state
from app.services.realtime import build_event, campaign_channel, event_version
from app.api.routes.sessions.shop import (
    _ensure_player_session_state,
    _publish_session_state_realtime,
)

router = APIRouter()


def _require_party_member(party_id: str, user, session: Session) -> Party:
    party = session.exec(select(Party).where(Party.id == party_id)).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    if party.gm_user_id == user.id:
        return party
    member = session.exec(
        select(PartyMember).where(
            PartyMember.party_id == party_id,
            PartyMember.user_id == user.id,
            PartyMember.status == PartyMemberStatus.JOINED,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a party member")
    return party


def _to_read(entry: CharacterSheet) -> CharacterSheetRead:
    return CharacterSheetRead(
        id=entry.id,
        partyId=entry.party_id,
        playerId=entry.player_user_id,
        data=entry.data,
        createdAt=entry.created_at,
        updatedAt=entry.updated_at,
    )


def _validate_character_sheet_payload(data) -> None:
    ok, error = validate_race_state(data)
    if not ok:
        raise HTTPException(status_code=422, detail=error)


def _normalize_character_sheet_payload(data):
    if not isinstance(data, dict):
        return data
    normalized = normalize_race_state(data.get("race"), data.get("raceConfig"))
    return {
        **data,
        "race": normalized["race"],
        "raceConfig": normalized["raceConfig"],
    }


@router.get("/parties/{party_id}/character-sheet/me", response_model=CharacterSheetRead)
def get_my_character_sheet(
    party_id: str,
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _require_party_member(party_id, user, session)
    entry = session.exec(
        select(CharacterSheet).where(
            CharacterSheet.party_id == party_id,
            CharacterSheet.player_user_id == user.id,
        )
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Character sheet not found")
    return _to_read(entry)


@router.get(
    "/parties/{party_id}/character-sheets/{player_user_id}",
    response_model=CharacterSheetRead,
)
def get_party_character_sheet(
    party_id: str,
    player_user_id: str,
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    party = session.exec(select(Party).where(Party.id == party_id)).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    if party.gm_user_id != user.id:
        raise HTTPException(status_code=403, detail="GM required")

    entry = session.exec(
        select(CharacterSheet).where(
            CharacterSheet.party_id == party_id,
            CharacterSheet.player_user_id == player_user_id,
        )
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Character sheet not found")
    return _to_read(entry)


@router.post(
    "/parties/{party_id}/character-sheet",
    response_model=CharacterSheetRead,
    status_code=201,
)
def create_character_sheet(
    party_id: str,
    payload: CharacterSheetCreate,
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    party = _require_party_member(party_id, user, session)
    existing = session.exec(
        select(CharacterSheet).where(
            CharacterSheet.party_id == party_id,
            CharacterSheet.player_user_id == user.id,
        )
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Character sheet already exists")
    _validate_character_sheet_payload(payload.data)
    normalized_payload = _normalize_character_sheet_payload(payload.data)
    entry = CharacterSheet(
        id=str(uuid4()),
        party_id=party_id,
        player_user_id=user.id,
        data=normalized_payload,
    )
    session.add(entry)
    sync_character_sheet_inventory(
        party=party,
        player_user_id=user.id,
        sheet_data=normalized_payload,
        db=session,
    )
    session.commit()
    session.refresh(entry)
    return _to_read(entry)


@router.put("/parties/{party_id}/character-sheet/me", response_model=CharacterSheetRead)
def update_character_sheet(
    party_id: str,
    payload: CharacterSheetUpdate,
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    party = _require_party_member(party_id, user, session)
    entry = session.exec(
        select(CharacterSheet).where(
            CharacterSheet.party_id == party_id,
            CharacterSheet.player_user_id == user.id,
        )
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Character sheet not found")
    _validate_character_sheet_payload(payload.data)
    normalized_payload = _normalize_character_sheet_payload(payload.data)
    entry.data = normalized_payload
    session.add(entry)
    sync_character_sheet_inventory(
        party=party,
        player_user_id=user.id,
        sheet_data=normalized_payload,
        db=session,
        only_if_inventory_empty=True,
    )
    session.commit()
    session.refresh(entry)
    return _to_read(entry)


@router.delete("/parties/{party_id}/character-sheet/me", status_code=204)
def delete_character_sheet(
    party_id: str,
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _require_party_member(party_id, user, session)
    entry = session.exec(
        select(CharacterSheet).where(
            CharacterSheet.party_id == party_id,
            CharacterSheet.player_user_id == user.id,
        )
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Character sheet not found")
    session.delete(entry)
    session.commit()


# ---------------------------------------------------------------------------
# Level-Up Request / Approve / Deny
# ---------------------------------------------------------------------------

def _get_party_with_gm_check(party_id: str, user, session: Session) -> Party:
    party = session.exec(select(Party).where(Party.id == party_id)).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    if party.gm_user_id != user.id:
        raise HTTPException(status_code=403, detail="GM required")
    return party


def _require_joined_player(party_id: str, player_user_id: str, session: Session) -> None:
    member = session.exec(
        select(PartyMember).where(
            PartyMember.party_id == party_id,
            PartyMember.user_id == player_user_id,
            PartyMember.status == PartyMemberStatus.JOINED,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Player not found in party")


def _get_open_party_session(party_id: str, session: Session) -> CampaignSession | None:
    return session.exec(
        select(CampaignSession).where(
            CampaignSession.party_id == party_id,
            CampaignSession.status.in_([SessionStatus.LOBBY, SessionStatus.ACTIVE]),
        )
    ).first()


def _get_campaign_member(campaign_id: str, user_id: str, session: Session) -> CampaignMember | None:
    return session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.user_id == user_id,
        )
    ).first()


def _sync_progression_session_state(
    entry: CampaignSession | None,
    *,
    player_user_id: str,
    sheet_data: dict,
    session: Session,
):
    if not entry:
        return None

    state = _ensure_player_session_state(entry, player_user_id, session)
    state.state_json = {
        **state.state_json,
        "level": int(sheet_data.get("level", 1)),
        "experiencePoints": int(sheet_data.get("experiencePoints", 0)),
        "pendingLevelUp": bool(sheet_data.get("pendingLevelUp", False)),
    }
    session.add(state)
    return state


async def _publish_level_up_event(
    party: Party,
    *,
    event_type: str,
    player_user_id: str,
    sheet: CharacterSheet,
) -> None:
    version = event_version(sheet.updated_at or sheet.created_at)
    data = sheet.data or {}
    payload = {
        "partyId": party.id,
        "campaignId": party.campaign_id,
        "playerUserId": player_user_id,
        "level": data.get("level", 1),
        "experiencePoints": data.get("experiencePoints", 0),
        "pendingLevelUp": data.get("pendingLevelUp", False),
    }
    await centrifugo.publish(
        campaign_channel(party.campaign_id),
        build_event(event_type, payload, version=version),
    )


@router.post(
    "/parties/{party_id}/character-sheet/me/request-level-up",
    response_model=CharacterSheetRead,
)
async def request_level_up(
    party_id: str,
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    party = _require_party_member(party_id, user, session)
    entry = session.exec(
        select(CharacterSheet).where(
            CharacterSheet.party_id == party_id,
            CharacterSheet.player_user_id == user.id,
        )
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Character sheet not found")

    try:
        data = request_level_up_data(entry.data)
    except CharacterProgressionError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    entry.data = data
    session.add(entry)
    open_session = _get_open_party_session(party_id, session)
    state = _sync_progression_session_state(
        open_session,
        player_user_id=user.id,
        sheet_data=data,
        session=session,
    )
    if open_session:
        actor_member = _get_campaign_member(open_session.campaign_id, user.id, session)
        if actor_member:
            record_session_activity(
                open_session,
                "level_up_requested",
                session,
                member_id=str(actor_member.id),
                user_id=user.id,
                actor_name=actor_member.display_name,
                payload={
                    "targetUserId": user.id,
                    "targetDisplayName": actor_member.display_name,
                    "level": int(data.get("level", 1)),
                    "experiencePoints": int(data.get("experiencePoints", 0)),
                    "pendingLevelUp": bool(data.get("pendingLevelUp", False)),
                },
            )
    session.commit()
    session.refresh(entry)
    if state:
        session.refresh(state)

    await _publish_level_up_event(
        party,
        event_type="level_up_requested",
        player_user_id=user.id,
        sheet=entry,
    )
    if open_session and state:
        await _publish_session_state_realtime(
            open_session,
            user.id,
            state.updated_at or state.created_at,
            state.state_json if isinstance(state.state_json, dict) else None,
        )

    return _to_read(entry)


@router.post(
    "/parties/{party_id}/character-sheets/{player_user_id}/approve-level-up",
    response_model=CharacterSheetRead,
)
async def approve_level_up(
    party_id: str,
    player_user_id: str,
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    party = _get_party_with_gm_check(party_id, user, session)
    _require_joined_player(party_id, player_user_id, session)
    entry = session.exec(
        select(CharacterSheet).where(
            CharacterSheet.party_id == party_id,
            CharacterSheet.player_user_id == player_user_id,
        )
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Character sheet not found")

    try:
        data = approve_level_up_data(entry.data)
    except CharacterProgressionError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    entry.data = data
    session.add(entry)
    open_session = _get_open_party_session(party_id, session)
    state = _sync_progression_session_state(
        open_session,
        player_user_id=player_user_id,
        sheet_data=data,
        session=session,
    )
    if open_session:
        actor_member = _get_campaign_member(open_session.campaign_id, user.id, session)
        target_member = _get_campaign_member(open_session.campaign_id, player_user_id, session)
        if actor_member:
            record_session_activity(
                open_session,
                "level_up_approved",
                session,
                member_id=str(actor_member.id),
                user_id=user.id,
                actor_name=actor_member.display_name,
                payload={
                    "targetUserId": player_user_id,
                    "targetDisplayName": target_member.display_name if target_member else player_user_id,
                    "level": int(data.get("level", 1)),
                    "experiencePoints": int(data.get("experiencePoints", 0)),
                    "pendingLevelUp": bool(data.get("pendingLevelUp", False)),
                },
            )
    session.commit()
    session.refresh(entry)
    if state:
        session.refresh(state)

    await _publish_level_up_event(
        party,
        event_type="level_up_approved",
        player_user_id=player_user_id,
        sheet=entry,
    )
    if open_session and state:
        await _publish_session_state_realtime(
            open_session,
            player_user_id,
            state.updated_at or state.created_at,
            state.state_json if isinstance(state.state_json, dict) else None,
        )

    return _to_read(entry)


@router.post(
    "/parties/{party_id}/character-sheets/{player_user_id}/deny-level-up",
    response_model=CharacterSheetRead,
)
async def deny_level_up(
    party_id: str,
    player_user_id: str,
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    party = _get_party_with_gm_check(party_id, user, session)
    _require_joined_player(party_id, player_user_id, session)
    entry = session.exec(
        select(CharacterSheet).where(
            CharacterSheet.party_id == party_id,
            CharacterSheet.player_user_id == player_user_id,
        )
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Character sheet not found")

    try:
        data = deny_level_up_data(entry.data)
    except CharacterProgressionError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    entry.data = data
    session.add(entry)
    open_session = _get_open_party_session(party_id, session)
    state = _sync_progression_session_state(
        open_session,
        player_user_id=player_user_id,
        sheet_data=data,
        session=session,
    )
    if open_session:
        actor_member = _get_campaign_member(open_session.campaign_id, user.id, session)
        target_member = _get_campaign_member(open_session.campaign_id, player_user_id, session)
        if actor_member:
            record_session_activity(
                open_session,
                "level_up_denied",
                session,
                member_id=str(actor_member.id),
                user_id=user.id,
                actor_name=actor_member.display_name,
                payload={
                    "targetUserId": player_user_id,
                    "targetDisplayName": target_member.display_name if target_member else player_user_id,
                    "level": int(data.get("level", 1)),
                    "experiencePoints": int(data.get("experiencePoints", 0)),
                    "pendingLevelUp": bool(data.get("pendingLevelUp", False)),
                },
            )
    session.commit()
    session.refresh(entry)
    if state:
        session.refresh(state)

    await _publish_level_up_event(
        party,
        event_type="level_up_denied",
        player_user_id=player_user_id,
        sheet=entry,
    )
    if open_session and state:
        await _publish_session_state_realtime(
            open_session,
            player_user_id,
            state.updated_at or state.created_at,
            state.state_json if isinstance(state.state_json, dict) else None,
        )

    return _to_read(entry)
