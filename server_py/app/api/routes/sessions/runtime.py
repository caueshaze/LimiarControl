from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session as DbSession, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.campaign_member import CampaignMember
from app.models.session import Session
from app.models.session_runtime import SessionRuntime
from app.schemas.session import SessionRuntimeRead
from ._shared import serialize_session_runtime

router = APIRouter()


@router.get("/sessions/{session_id}/runtime", response_model=SessionRuntimeRead)
def get_session_runtime(
    session_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = session.exec(select(Session).where(Session.id == session_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a campaign member")
    runtime = session.exec(
        select(SessionRuntime).where(SessionRuntime.session_id == session_id)
    ).first()
    return serialize_session_runtime(entry, runtime)
