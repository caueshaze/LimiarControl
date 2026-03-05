from typing import List

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select, or_

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.user import UserSearchRead

router = APIRouter()


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
                User.display_name.ilike(search_term),
                User.username.ilike(search_term),
            )
        )
        .limit(20)
    )
    results = session.exec(statement).all()
    
    return [
        UserSearchRead(
            id=result.id,
            displayName=result.display_name or result.username,
            username=result.username,
        )
        for result in results
    ]
