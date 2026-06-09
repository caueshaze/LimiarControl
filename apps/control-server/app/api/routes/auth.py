from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.core.auth import build_access_token, hash_pin, verify_pin
from app.db.session import get_session
from app.models.campaign import RoleMode
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    MeResponse,
    RegisterRequest,
    UpdateProfileRequest,
)

router = APIRouter()


def normalize_username(username: str) -> str:
    return username.strip().lower()


_REGISTER_ADMIN_LOCK_KEY = 461337486


def _is_postgres_session(session: Session) -> bool:
    bind = session.get_bind()
    dialect = getattr(bind, "dialect", None)
    return getattr(dialect, "name", None) == "postgresql"


def _acquire_register_lock(session: Session) -> None:
    if _is_postgres_session(session):
        session.exec(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            params={"lock_key": _REGISTER_ADMIN_LOCK_KEY},
        )


@router.post("/auth/register", response_model=AuthResponse)
def register(payload: RegisterRequest, session: Session = Depends(get_session)):
    username = normalize_username(payload.username)
    if not username or not payload.pin.strip():
        raise HTTPException(status_code=400, detail="Invalid payload")
    _acquire_register_lock(session)

    existing = session.exec(select(User).where(User.username == username)).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")

    is_first_user = session.exec(select(func.count()).select_from(User)).one() == 0
    user = User(
        id=str(uuid4()),
        username=username,
        display_name=payload.displayName.strip() if payload.displayName else None,
        pin_hash=hash_pin(payload.pin.strip()),
        role=payload.role,
        is_system_admin=is_first_user,
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="Username already exists") from exc
    session.refresh(user)
    token = build_access_token(user.id, user.username)
    return AuthResponse(token=token)


@router.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, session: Session = Depends(get_session)):
    username = normalize_username(payload.username)
    user = session.exec(select(User).where(User.username == username)).first()
    if not user or not verify_pin(payload.pin.strip(), user.pin_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = build_access_token(user.id, user.username)
    return AuthResponse(token=token)


def _me_response(user: User) -> MeResponse:
    return MeResponse(
        userId=user.id,
        username=user.username,
        displayName=user.display_name,
        role=user.role,
        preferredWorkspaceMode=user.preferred_workspace_mode,
        isSystemAdmin=user.is_system_admin,
        avatarUrl=user.avatar_url,
        tokenColor=user.token_color,
        tokenImageUrl=user.token_image_url,
        onboardedAt=user.onboarded_at,
    )


@router.get("/auth/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user)):
    return _me_response(user)


@router.patch("/auth/me/profile", response_model=MeResponse)
def update_profile(
    payload: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    changed = False
    if payload.displayName is not None:
        trimmed = payload.displayName.strip()
        user.display_name = trimmed or None
        changed = True
    if payload.avatarUrl is not None:
        user.avatar_url = payload.avatarUrl or None
        changed = True
    if payload.tokenColor is not None:
        user.token_color = payload.tokenColor or None
        changed = True
    if payload.tokenImageUrl is not None:
        user.token_image_url = payload.tokenImageUrl or None
        changed = True
    if payload.preferredWorkspaceMode is not None:
        user.preferred_workspace_mode = payload.preferredWorkspaceMode
        changed = True
    if payload.markOnboarded and user.onboarded_at is None:
        user.onboarded_at = datetime.now(timezone.utc)
        changed = True

    if changed:
        session.add(user)
        session.commit()
        session.refresh(user)

    return _me_response(user)
