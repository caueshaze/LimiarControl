from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, text

from app.core.config import settings
from app.db.session import get_session

router = APIRouter()


@router.post("/reset")
def reset_database(session: Session = Depends(get_session)):
    if settings.app_env != "development":
        raise HTTPException(status_code=403, detail="Forbidden")
    session.exec(text("TRUNCATE TABLE roll_event RESTART IDENTITY CASCADE"))
    session.exec(text("TRUNCATE TABLE campaign_session RESTART IDENTITY CASCADE"))
    session.exec(text("TRUNCATE TABLE campaign_member RESTART IDENTITY CASCADE"))
    session.exec(text("TRUNCATE TABLE inventoryitem RESTART IDENTITY CASCADE"))
    session.exec(text("TRUNCATE TABLE npc RESTART IDENTITY CASCADE"))
    session.exec(text("TRUNCATE TABLE item RESTART IDENTITY CASCADE"))
    session.exec(text("TRUNCATE TABLE campaign RESTART IDENTITY CASCADE"))
    session.exec(text("TRUNCATE TABLE preferences RESTART IDENTITY CASCADE"))
    session.exec(text("TRUNCATE TABLE app_user RESTART IDENTITY CASCADE"))
    session.commit()
    return {"ok": True}
