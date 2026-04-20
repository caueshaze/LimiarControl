from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlmodel import Session, select

from app.core.auth import decode_jwt
from app.db.session import engine
from app.models.campaign import Campaign
from app.models.campaign_member import CampaignMember

from app.api.ws_registry import campaign_room_registry

router = APIRouter()


@router.websocket("/campaigns/{campaign_id}")
async def campaign_ws(websocket: WebSocket, campaign_id: str) -> None:
    token = websocket.query_params.get("token")
    await websocket.accept()
    await campaign_room_registry.add(campaign_id, websocket)
    print(f"WS connect campaign={campaign_id}")
    connected_user_id: str | None = None
    connected_display_name: str = "Unknown"
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
        campaign = session.exec(
            select(Campaign).where(Campaign.id == campaign_id)
        ).first()
        if not campaign:
            await websocket.send_json(
                {"type": "error", "payload": {"requestId": None, "message": "Campaign not found"}}
            )
            await websocket.close(code=1008)
            return
        member = session.exec(
            select(CampaignMember).where(
                CampaignMember.campaign_id == campaign_id,
                CampaignMember.user_id == user_id,
            )
        ).first()
        if not member:
            await websocket.send_json(
                {"type": "error", "payload": {"requestId": None, "message": "Join required"}}
            )
            await websocket.close(code=1008)
            return
        connected_user_id = user_id
        connected_display_name: str = member.display_name or user_id or ""

    await campaign_room_registry.add_with_user(
        campaign_id, websocket, connected_user_id or "", connected_display_name
    )
    await campaign_room_registry.broadcast(
        campaign_id,
        {
            "type": "user_online",
            "payload": {
                "userId": connected_user_id,
                "displayName": connected_display_name,
            },
        },
    )
    await websocket.send_json(
        {
            "type": "connected",
            "payload": {
                "serverTime": datetime.now(timezone.utc).isoformat(),
                "onlineUsers": campaign_room_registry.get_online_users(campaign_id),
            },
        }
    )
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await campaign_room_registry.remove_with_user(campaign_id, websocket, connected_user_id)
        if connected_user_id:
            await campaign_room_registry.broadcast(
                campaign_id,
                {
                    "type": "user_offline",
                    "payload": {
                        "userId": connected_user_id,
                        "displayName": connected_display_name,
                    },
                },
            )
        print(f"WS disconnect campaign={campaign_id}")
