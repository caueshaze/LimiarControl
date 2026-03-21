import re
from datetime import date, datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlmodel import Session as DbSession, select

from app.api.serializers.item import to_item_read
from app.models.inventory import InventoryItem
from app.models.party import Party
from app.models.party_member import PartyMember
from app.models.roll_event import RollEvent
from app.models.session import Session, SessionStatus
from app.models.session_command_event import SessionCommandEvent
from app.models.session_runtime import SessionRuntime
from app.schemas.inventory import InventoryRead
from app.schemas.item import ItemRead
from app.schemas.roll_event import RollDice, RollEventRead
from app.schemas.session import ActiveSessionRead, LobbyStatusRead, SessionRead, SessionRuntimeRead

DEPRECATION_REMOVAL_DATE = date(2026, 6, 1)

DICE_RE = re.compile(
    r"^\s*(?:(\d*)d(\d+))\s*(?:([+-])\s*(\d+))?\s*$", re.IGNORECASE
)


def parse_expression(expression: str) -> tuple[int, int, int] | None:
    match = DICE_RE.match(expression or "")
    if not match:
        return None
    count_raw, sides_raw, sign, modifier_raw = match.groups()
    count = int(count_raw) if count_raw else 1
    sides = int(sides_raw)
    modifier = int(modifier_raw) if modifier_raw else 0
    if sign == "-":
        modifier = -modifier
    if count < 1 or count > 50:
        return None
    if sides < 1 or sides > 1000:
        return None
    if modifier < -1000 or modifier > 1000:
        return None
    return count, sides, modifier

def to_session_read(entry: Session) -> SessionRead:
    number = entry.sequence_number if entry.sequence_number is not None else entry.number
    return SessionRead(
        id=entry.id,
        campaignId=entry.campaign_id,
        partyId=entry.party_id,
        number=number,
        title=entry.title,
        status=entry.status,
        isActive=entry.status in (SessionStatus.ACTIVE, SessionStatus.LOBBY),
        startedAt=entry.started_at,
        endedAt=entry.ended_at,
        durationSeconds=entry.duration_seconds,
        createdAt=entry.created_at,
        updatedAt=entry.updated_at,
    )


def resolve_party_id_for_campaign(campaign_id: str, session: DbSession) -> str | None:
    from app.models.party import Party as PartyModel
    parties = session.exec(select(PartyModel).where(PartyModel.campaign_id == campaign_id)).all()
    if len(parties) == 1:
        return parties[0].id
    if len(parties) > 1:
        raise HTTPException(
            status_code=409,
            detail="Multiple parties found for campaign; specify party explicitly",
        )
    return None


def require_party_member_or_gm(party_id: str, user, session: DbSession) -> Party:
    party = session.exec(select(Party).where(Party.id == party_id)).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    if party.gm_user_id == user.id:
        return party
    member = session.exec(
        select(PartyMember).where(
            PartyMember.party_id == party_id,
            PartyMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a party member")
    return party


def require_party_gm(party_id: str, user, session: DbSession) -> Party:
    party = session.exec(select(Party).where(Party.id == party_id)).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    if party.gm_user_id != user.id:
        raise HTTPException(status_code=403, detail="GM required")
    return party


def to_roll_read_local(entry: RollEvent) -> RollEventRead:
    return RollEventRead(
        id=entry.id,
        campaignId=entry.campaign_id or "",
        sessionId=entry.session_id,
        userId=entry.user_id,
        authorName=entry.author_name,
        roleMode=entry.role_mode,
        label=entry.label,
        expression=entry.expression,
        dice=RollDice(count=entry.count, sides=entry.sides, modifier=entry.modifier),
        results=entry.results,
        total=entry.total,
        createdAt=entry.created_at,
    )

def to_inventory_read(entry: InventoryItem) -> InventoryRead:
    return InventoryRead(
        id=entry.id,
        campaignId=entry.campaign_id,
        partyId=entry.party_id,
        memberId=entry.member_id,
        itemId=entry.item_id,
        quantity=entry.quantity,
        isEquipped=entry.is_equipped,
        notes=entry.notes,
        createdAt=entry.created_at,
        updatedAt=entry.updated_at,
    )


def check_character_sheets(party_id: str, player_members: list, db: DbSession) -> None:
    """Raises 422 if any joined player is missing a character sheet for this party."""
    from app.models.character_sheet import CharacterSheet as CharacterSheetModel
    from app.models.user import User as UserModel

    existing_ids = {
        cs.player_user_id
        for cs in db.exec(
            select(CharacterSheetModel).where(CharacterSheetModel.party_id == party_id)
        ).all()
    }
    missing = []
    for m in player_members:
        if m.user_id not in existing_ids:
            u = db.exec(select(UserModel).where(UserModel.id == m.user_id)).first()
            display = (u.display_name or u.username or m.user_id) if u else m.user_id
            missing.append({"userId": m.user_id, "displayName": display})
    if missing:
        raise HTTPException(
            status_code=422,
            detail={"code": "missing_character_sheets", "players": missing},
        )


def get_or_create_session_runtime(session_id: str, session: DbSession) -> SessionRuntime:
    runtime = session.exec(
        select(SessionRuntime).where(SessionRuntime.session_id == session_id)
    ).first()
    if runtime:
        return runtime
    runtime = SessionRuntime(session_id=session_id)
    session.add(runtime)
    session.flush()
    return runtime


def lobby_expected_map(runtime: SessionRuntime | None) -> dict[str, str]:
    entries = runtime.lobby_expected if runtime and isinstance(runtime.lobby_expected, list) else []
    result: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        user_id = entry.get("userId")
        display_name = entry.get("displayName")
        if isinstance(user_id, str):
            result[user_id] = display_name if isinstance(display_name, str) else user_id
    return result


def lobby_ready_list(runtime: SessionRuntime | None) -> list[str]:
    entries = runtime.lobby_ready if runtime and isinstance(runtime.lobby_ready, list) else []
    return [entry for entry in entries if isinstance(entry, str)]


def serialize_lobby_status(entry: Session, runtime: SessionRuntime | None) -> LobbyStatusRead:
    expected_items = [
        {"userId": user_id, "displayName": display_name}
        for user_id, display_name in lobby_expected_map(runtime).items()
    ]
    ready_items = lobby_ready_list(runtime)
    return LobbyStatusRead(
        sessionId=entry.id,
        campaignId=entry.campaign_id,
        partyId=entry.party_id,
        expected=expected_items,
        ready=ready_items,
        readyCount=len(ready_items),
        totalCount=len(expected_items),
    )


def serialize_session_runtime(entry: Session, runtime: SessionRuntime | None) -> SessionRuntimeRead:
    return SessionRuntimeRead(
        sessionId=entry.id,
        campaignId=entry.campaign_id,
        partyId=entry.party_id,
        status=entry.status,
        shopOpen=bool(runtime.shop_open) if runtime else False,
        combatActive=bool(runtime.combat_active) if runtime else False,
    )


def record_session_activity(
    session_entry: Session,
    command_type: str,
    db: DbSession,
    *,
    member_id: str,
    user_id: str | None = None,
    actor_name: str | None = None,
    payload: dict | None = None,
    created_at: datetime | None = None,
) -> SessionCommandEvent:
    entry = SessionCommandEvent(
        id=str(uuid4()),
        session_id=session_entry.id,
        user_id=user_id,
        member_id=member_id,
        actor_name=actor_name,
        command_type=command_type,
        payload_json=payload if isinstance(payload, dict) and payload else None,
        created_at=created_at or datetime.now(timezone.utc),
    )
    db.add(entry)
    return entry
