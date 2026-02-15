from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.preferences import Preferences
from app.models.user import User
from app.schemas.preferences import PreferencesRead, PreferencesUpdate

router = APIRouter()


@router.get("/preferences", response_model=PreferencesRead)
def get_preferences(
    user: User = Depends(get_current_user), session: Session = Depends(get_session)
):
    prefs = session.exec(
        select(Preferences).where(Preferences.user_id == user.id)
    ).first()
    if not prefs:
        return PreferencesRead(selectedCampaignId=None)
    return PreferencesRead(selectedCampaignId=prefs.selected_campaign_id)


@router.put("/preferences", response_model=PreferencesRead)
def update_preferences(
    payload: PreferencesUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    prefs = session.exec(
        select(Preferences).where(Preferences.user_id == user.id)
    ).first()
    if not prefs:
        prefs = Preferences(
            user_id=user.id, selected_campaign_id=payload.selectedCampaignId
        )
    else:
        prefs.selected_campaign_id = payload.selectedCampaignId
    session.add(prefs)
    session.commit()
    session.refresh(prefs)
    return PreferencesRead(selectedCampaignId=prefs.selected_campaign_id)
