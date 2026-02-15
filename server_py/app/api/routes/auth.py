from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.core.auth import build_access_token, hash_pin, verify_pin
from app.db.session import get_session
from app.models.user import User
from app.schemas.auth import AuthResponse, LoginRequest, MeResponse, RegisterRequest

router = APIRouter()


def normalize_username(username: str) -> str:
    return username.strip().lower()


@router.post("/auth/register", response_model=AuthResponse)
def register(payload: RegisterRequest, session: Session = Depends(get_session)):
    username = normalize_username(payload.username)
    if not username or not payload.pin.strip():
        raise HTTPException(status_code=400, detail="Invalid payload")
    existing = session.exec(select(User).where(User.username == username)).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")
    user = User(
        id=str(uuid4()),
        username=username,
        display_name=payload.displayName.strip() if payload.displayName else None,
        pin_hash=hash_pin(payload.pin.strip()),
        role=payload.role,
    )
    session.add(user)
    session.commit()
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


@router.get("/auth/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user)):
    return MeResponse(
        userId=user.id,
        username=user.username,
        displayName=user.display_name,
        role=user.role,
    )
