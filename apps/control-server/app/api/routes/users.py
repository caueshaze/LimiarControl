from typing import List, cast

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, col, select, or_

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.user import UserProfileRead, UserSearchRead

router = APIRouter()


@router.get("/{user_id}/profile", response_model=UserProfileRead)
def get_user_profile(
    user_id: str,
    _: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    entry = session.exec(select(User).where(User.id == user_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="User not found")

    return UserProfileRead(
        id=cast(str, entry.id),
        displayName=entry.display_name or entry.username,
        username=entry.username,
        avatarUrl=entry.avatar_url,
        tokenColor=entry.token_color,
        tokenImageUrl=entry.token_image_url,
        preferredWorkspaceMode=entry.preferred_workspace_mode,
    )


@router.get("/search", response_model=List[UserSearchRead])
def search_users(
    q: str = Query(..., min_length=2, description="Search term"),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    search_term = f"%{q}%"
    statement = (
        select(User)
        .where(
            or_(
                col(User.display_name).ilike(search_term),
                col(User.username).ilike(search_term),
            )
        )
        .limit(20)
    )
    results = session.exec(statement).all()
    
    return [
        UserSearchRead(
            id=cast(str, result.id),
            displayName=result.display_name or result.username,
            username=result.username,
        )
        for result in results
    ]
