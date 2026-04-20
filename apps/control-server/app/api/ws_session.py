import json
import random
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlmodel import Session, select

from app.core.auth import decode_jwt
from app.db.session import engine
from app.models.campaign import Campaign
from app.models.campaign_member import CampaignMember
from app.models.party import Party
from app.models.party_member import PartyMember, PartyMemberStatus
from app.models.roll_event import RollEvent
from app.models.session import Session as CampaignSession, SessionStatus

from app.api.ws_registry import (
    room_registry,
    parse_expression,
    to_roll_read,
)

router = APIRouter()


@router.websocket("/sessions/{session_id}")
async def session_ws(websocket: WebSocket, session_id: str) -> None:
    token = websocket.query_params.get("token")
    await websocket.accept()
    await room_registry.add(session_id, websocket)
    print(f"WS connect session={session_id}")
    member_info: CampaignMember | None = None
    session_info: CampaignSession | None = None
    if not token:
        await websocket.send_json(
            {"type": "error", "payload": {"requestId": None, "message": "Missing token"}}
        )
        await websocket.close(code=1008)
        return
    payload = decode_jwt(token)
    if not payload or not payload.get("sub"):
        await websocket.send_json(
            {"type": "error", "payload": {"requestId": None, "message": "Invalid token"}}
        )
        await websocket.close(code=1008)
        return
    user_id = payload.get("sub")
    with Session(engine) as session:
        session_entry = session.exec(
            select(CampaignSession).where(CampaignSession.id == session_id)
        ).first()
        if not session_entry:
            await websocket.send_json(
                {"type": "error", "payload": {"requestId": None, "message": "Session not found"}}
            )
            await websocket.close(code=1008)
            return
        if session_entry.status not in (SessionStatus.ACTIVE, SessionStatus.LOBBY):
            await websocket.send_json(
                {"type": "error", "payload": {"requestId": None, "message": "Session is not active"}}
            )
            await websocket.close(code=1008)
            return
        session_info = session_entry
        if session_entry.party_id:
            party = session.exec(
                select(Party).where(Party.id == session_entry.party_id)
            ).first()
            if not party:
                await websocket.send_json(
                    {"type": "error", "payload": {"requestId": None, "message": "Party not found"}}
                )
                await websocket.close(code=1008)
                return
            if party.gm_user_id != user_id:
                party_member = session.exec(
                    select(PartyMember).where(
                        PartyMember.party_id == party.id,
                        PartyMember.user_id == user_id,
                    )
                ).first()
                if not party_member or party_member.status != PartyMemberStatus.JOINED:
                    await websocket.send_json(
                        {"type": "error", "payload": {"requestId": None, "message": "Party join required"}}
                    )
                    await websocket.close(code=1008)
                    return
        member = session.exec(
            select(CampaignMember).where(
                CampaignMember.campaign_id == session_entry.campaign_id,
                CampaignMember.user_id == user_id,
            )
        ).first()
        if not member:
            await websocket.send_json(
                {"type": "error", "payload": {"requestId": None, "message": "Join required"}}
            )
            await websocket.close(code=1008)
            return
        member_info = member
    await websocket.send_json(
        {"type": "connected", "payload": {"serverTime": datetime.now(timezone.utc).isoformat()}}
    )
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json(
                    {"type": "error", "payload": {"requestId": None, "message": "Invalid JSON"}}
                )
                continue

            message_type = data.get("type")
            payload = data.get("payload") or {}
            if not isinstance(payload, dict):
                payload = {}

            if message_type == "join":
                continue

            if message_type != "roll":
                await websocket.send_json(
                    {
                        "type": "error",
                        "payload": {
                            "requestId": payload.get("requestId"),
                            "message": "Unknown message type",
                        },
                    }
                )
                continue

            if member_info is None or session_info is None:
                await websocket.send_json(
                    {
                        "type": "error",
                        "payload": {"requestId": payload.get("requestId"), "message": "Join required"},
                    }
                )
                continue

            request_id = payload.get("requestId")
            expression = payload.get("expression", "")
            label = payload.get("label")
            advantage = payload.get("advantage")

            parsed = parse_expression(expression)
            if not parsed:
                print(f"DEBUG roll parse error session={session_id} expr={expression!r}")
                await websocket.send_json(
                    {
                        "type": "error",
                        "payload": {"requestId": request_id, "message": "Invalid dice expression"},
                    }
                )
                continue

            role_mode_value = member_info.role_mode
            author_name = member_info.display_name

            count, sides, modifier = parsed
            if advantage in ("advantage", "disadvantage"):
                set_a = [random.randint(1, sides) for _ in range(count)]
                set_b = [random.randint(1, sides) for _ in range(count)]
                sum_a = sum(set_a)
                sum_b = sum(set_b)
                if advantage == "advantage":
                    chosen, other = (set_a, set_b) if sum_a >= sum_b else (set_b, set_a)
                else:
                    chosen, other = (set_a, set_b) if sum_a <= sum_b else (set_b, set_a)
                results = chosen + other
                total = sum(chosen) + modifier
                suffix = " (Advantage)" if advantage == "advantage" else " (Disadvantage)"
                label = (label + suffix) if label else suffix.strip()
            else:
                results = [random.randint(1, sides) for _ in range(count)]
                total = sum(results) + modifier

            with Session(engine) as session:
                campaign = session.exec(
                    select(Campaign).where(Campaign.id == session_info.campaign_id)
                ).first()
                if not campaign:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "payload": {"requestId": request_id, "message": "Campaign not found"},
                        }
                    )
                    continue
                event = RollEvent(  # type: ignore[call-arg]
                    id=str(uuid4()),
                    campaign_id=campaign.id,
                    session_id=session_info.id,
                    user_id=user_id,
                    author_name=author_name,
                    role_mode=role_mode_value,
                    label=label,
                    expression=expression.strip(),
                    count=count,
                    sides=sides,
                    modifier=modifier,
                    results=results,
                    total=total,
                )
                session.add(event)
                session.commit()
                session.refresh(event)

            payload_out = to_roll_read(event).model_dump(mode="json")
            await room_registry.broadcast(
                session_id, {"type": "roll_created", "payload": payload_out}
            )
    except WebSocketDisconnect:
        pass
    finally:
        await room_registry.remove(session_id, websocket)
        print(f"WS disconnect session={session_id}")
