"""Wild Shape endpoints — Druid transform/revert and available forms listing."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session as DbSession, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.party import Party
from app.models.party_member import PartyMember, PartyMemberStatus
from app.models.session import Session, SessionStatus
from app.models.user import User
from app.services.centrifugo import centrifugo
from app.services.realtime import build_event, campaign_channel, event_version, session_channel
from app.services.session_state_finalize import finalize_session_state_data
from app.services.wild_shape_catalog import WildFormStats, get_form, get_forms_for_level
from app.services.wild_shape_service import WildShapeError, revert, transform

from .sessions._shared import record_session_activity
from .sessions.shop import _ensure_player_session_state, _publish_session_state_realtime

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class NaturalAttackRead(BaseModel):
    name: str
    name_pt: str
    attack_bonus: int
    damage_dice: str
    damage_bonus: int
    damage_type: str


class WildFormRead(BaseModel):
    canonical_key: str
    display_name: str
    display_name_pt: str
    cr: str
    cr_numeric: float
    min_druid_level: int
    size: str
    max_hp: int
    armor_class: int
    speed_meters: int
    str_score: int
    dex_score: int
    con_score: int
    int_score: int
    wis_score: int
    cha_score: int
    natural_attacks: list[NaturalAttackRead]
    tags: list[str]

    @classmethod
    def from_stats(cls, form: WildFormStats) -> "WildFormRead":
        return cls(
            canonical_key=form.canonical_key,
            display_name=form.display_name,
            display_name_pt=form.display_name_pt,
            cr=form.cr,
            cr_numeric=form.cr_numeric,
            min_druid_level=form.min_druid_level,
            size=form.size,
            max_hp=form.max_hp,
            armor_class=form.armor_class,
            speed_meters=form.speed_meters,
            str_score=form.str_score,
            dex_score=form.dex_score,
            con_score=form.con_score,
            int_score=form.int_score,
            wis_score=form.wis_score,
            cha_score=form.cha_score,
            natural_attacks=[
                NaturalAttackRead(
                    name=a.name,
                    name_pt=a.name_pt,
                    attack_bonus=a.attack_bonus,
                    damage_dice=a.damage_dice,
                    damage_bonus=a.damage_bonus,
                    damage_type=a.damage_type,
                )
                for a in form.natural_attacks
            ],
            tags=list(form.tags),
        )


class WildShapeTransformRequest(BaseModel):
    form_key: str


class WildShapeStateRead(BaseModel):
    active: bool
    form_key: str | None
    form_current_hp: int
    saved_humanoid_hp: int | None
    uses_remaining: int
    uses_max: int
    form: WildFormRead | None = None


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


def _get_session_or_404(session_id: str, db: DbSession) -> Session:
    entry = db.exec(select(Session).where(Session.id == session_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")
    return entry


def _require_active_session(entry: Session) -> None:
    if entry.status != SessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Session is not active")


def _require_joined_player(entry: Session, user: User, db: DbSession) -> PartyMember:
    if not entry.party_id:
        raise HTTPException(status_code=400, detail="Session has no party")
    party = db.exec(select(Party).where(Party.id == entry.party_id)).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    if party.gm_user_id == user.id:
        raise HTTPException(status_code=403, detail="Only players can use Wild Shape")
    member = db.exec(
        select(PartyMember).where(
            PartyMember.party_id == entry.party_id,
            PartyMember.user_id == user.id,
            PartyMember.status == PartyMemberStatus.JOINED,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a joined party member")
    return member


def _build_wild_shape_state(state_json: dict) -> WildShapeStateRead:
    ws: dict = state_json.get("wildShape") or {}
    form_key = ws.get("formKey")
    form_stats = get_form(form_key) if isinstance(form_key, str) else None
    return WildShapeStateRead(
        active=bool(ws.get("active", False)),
        form_key=form_key,
        form_current_hp=int(ws.get("formCurrentHP", 0)),
        saved_humanoid_hp=ws.get("savedHumanoidHP"),
        uses_remaining=int(ws.get("usesRemaining", 0)),
        uses_max=int(ws.get("usesMax", 2)),
        form=WildFormRead.from_stats(form_stats) if form_stats else None,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/sessions/{session_id}/wild-shape/forms",
    response_model=list[WildFormRead],
)
def get_available_forms(
    session_id: str,
    user: User = Depends(get_current_user),
    db: DbSession = Depends(get_session),
) -> list[WildFormRead]:
    """Return beast forms available to this player given their current druid level."""
    entry = _get_session_or_404(session_id, db)
    _require_active_session(entry)
    _require_joined_player(entry, user, db)

    state = _ensure_player_session_state(entry, user.id, db)
    state_json = state.state_json if isinstance(state.state_json, dict) else {}
    level = int(state_json.get("level", 1))

    return [WildFormRead.from_stats(f) for f in get_forms_for_level(level)]


@router.get(
    "/sessions/{session_id}/wild-shape/state",
    response_model=WildShapeStateRead,
)
def get_wild_shape_state(
    session_id: str,
    user: User = Depends(get_current_user),
    db: DbSession = Depends(get_session),
) -> WildShapeStateRead:
    """Return current Wild Shape state for the player."""
    entry = _get_session_or_404(session_id, db)
    _require_active_session(entry)
    _require_joined_player(entry, user, db)

    state = _ensure_player_session_state(entry, user.id, db)
    state_json = state.state_json if isinstance(state.state_json, dict) else {}
    return _build_wild_shape_state(state_json)


@router.post(
    "/sessions/{session_id}/wild-shape/transform",
    response_model=WildShapeStateRead,
)
async def wild_shape_transform(
    session_id: str,
    payload: WildShapeTransformRequest,
    user: User = Depends(get_current_user),
    db: DbSession = Depends(get_session),
) -> WildShapeStateRead:
    """Enter beast form. Consumes one Wild Shape use."""
    entry = _get_session_or_404(session_id, db)
    _require_active_session(entry)
    member = _require_joined_player(entry, user, db)

    state = _ensure_player_session_state(entry, user.id, db)
    try:
        next_state_json = transform(
            state.state_json if isinstance(state.state_json, dict) else {},
            payload.form_key,
        )
    except WildShapeError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    state.state_json = finalize_session_state_data(next_state_json)
    db.add(state)

    form = get_form(payload.form_key)
    record_session_activity(
        entry,
        "wild_shape_transform",
        db,
        member_id=str(member.id),
        user_id=user.id,
        actor_name=member.display_name,
        payload={
            "formKey": payload.form_key,
            "formName": form.display_name if form else payload.form_key,
            "formCurrentHP": next_state_json.get("wildShape", {}).get("formCurrentHP", 0),
        },
    )
    db.commit()
    db.refresh(state)

    state_json = state.state_json if isinstance(state.state_json, dict) else {}
    ws_read = _build_wild_shape_state(state_json)

    version = event_version(state.updated_at or state.created_at)
    event_data = {
        "sessionId": entry.id,
        "campaignId": entry.campaign_id,
        "partyId": entry.party_id,
        "playerUserId": user.id,
        "formKey": payload.form_key,
        "formName": form.display_name if form else payload.form_key,
        "formCurrentHP": ws_read.form_current_hp,
        "usesRemaining": ws_read.uses_remaining,
    }
    await centrifugo.publish(
        session_channel(entry.id),
        build_event("wild_shape_transform", event_data, version=version),
    )
    await centrifugo.publish(
        campaign_channel(entry.campaign_id),
        build_event("wild_shape_transform", event_data, version=version),
    )
    await _publish_session_state_realtime(
        entry,
        user.id,
        state.updated_at or state.created_at,
        state_json,
    )

    return ws_read


@router.post(
    "/sessions/{session_id}/wild-shape/revert",
    response_model=WildShapeStateRead,
)
async def wild_shape_revert(
    session_id: str,
    user: User = Depends(get_current_user),
    db: DbSession = Depends(get_session),
) -> WildShapeStateRead:
    """Leave beast form and restore humanoid HP."""
    entry = _get_session_or_404(session_id, db)
    _require_active_session(entry)
    member = _require_joined_player(entry, user, db)

    state = _ensure_player_session_state(entry, user.id, db)
    try:
        next_state_json = revert(
            state.state_json if isinstance(state.state_json, dict) else {}
        )
    except WildShapeError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    state.state_json = finalize_session_state_data(next_state_json)
    db.add(state)

    record_session_activity(
        entry,
        "wild_shape_revert",
        db,
        member_id=str(member.id),
        user_id=user.id,
        actor_name=member.display_name,
        payload={
            "restoredHP": next_state_json.get("currentHP", 0),
        },
    )
    db.commit()
    db.refresh(state)

    state_json = state.state_json if isinstance(state.state_json, dict) else {}
    ws_read = _build_wild_shape_state(state_json)

    version = event_version(state.updated_at or state.created_at)
    event_data = {
        "sessionId": entry.id,
        "campaignId": entry.campaign_id,
        "partyId": entry.party_id,
        "playerUserId": user.id,
        "restoredHP": state_json.get("currentHP", 0),
        "usesRemaining": ws_read.uses_remaining,
    }
    await centrifugo.publish(
        session_channel(entry.id),
        build_event("wild_shape_revert", event_data, version=version),
    )
    await centrifugo.publish(
        campaign_channel(entry.campaign_id),
        build_event("wild_shape_revert", event_data, version=version),
    )
    await _publish_session_state_realtime(
        entry,
        user.id,
        state.updated_at or state.created_at,
        state_json,
    )

    return ws_read
