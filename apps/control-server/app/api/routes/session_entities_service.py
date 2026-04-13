from __future__ import annotations

from uuid import uuid4

from fastapi import HTTPException
from app.api.deps import require_campaign_member
from app.api.routes.session_entities_common import (
    entity_event_payload,
    get_campaign_entity,
    get_campaign_entity_for_session_or_404,
    get_session_entry,
    get_session_entity_or_404,
    list_session_entity_pairs,
    publish_entity_event,
    require_identifier,
    require_session_gm,
    to_session_entity_player_read,
    to_session_entity_read,
    utcnow,
)
from app.api.routes.sessions._shared import record_session_activity
from app.models.session import SessionStatus
from app.models.session_entity import SessionEntity
from app.models.user import User
from app.schemas.session_entity import (
    SessionEntityCreate,
    SessionEntityPlayerRead,
    SessionEntityRead,
    SessionEntityUpdate,
)
from app.services.combat import CombatService
from sqlmodel import Session as DbSession


def list_session_entities_service(
    session_id: str,
    user: User,
    session: DbSession,
) -> list[SessionEntityRead]:
    session_entry = get_session_entry(session_id, session)
    require_session_gm(session_entry, user, session)
    return [
        to_session_entity_read(session_entity, campaign_entity)
        for session_entity, campaign_entity in list_session_entity_pairs(session_id, session)
    ]


async def add_session_entity_service(
    session_id: str,
    payload: SessionEntityCreate,
    user: User,
    session: DbSession,
) -> SessionEntityRead:
    session_entry = get_session_entry(session_id, session)
    gm_member = require_session_gm(session_entry, user, session)
    if session_entry.status != SessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Session is not active")

    campaign_entity = get_campaign_entity_for_session_or_404(
        payload.campaignEntityId,
        session_entry,
        session,
    )
    session_entity = SessionEntity(
        id=str(uuid4()),
        session_id=session_id,
        campaign_entity_id=payload.campaignEntityId,
        current_hp=payload.currentHp if payload.currentHp is not None else campaign_entity.max_hp,
        label=payload.label,
        revealed_at=None,
        created_at=utcnow(),
        updated_at=None,
    )
    session.add(session_entity)
    session.commit()
    session.refresh(session_entity)

    activity_payload = entity_event_payload(session_entry, session_entity, campaign_entity)
    record_session_activity(
        session_entry,
        "session_entity_added",
        session,
        member_id=require_identifier(gm_member.id, "GM member is missing an id"),
        user_id=require_identifier(user.id, "Authenticated user is missing an id"),
        actor_name=gm_member.display_name,
        payload=activity_payload,
        created_at=session_entity.created_at,
    )
    session.commit()
    await publish_entity_event(
        session_entry,
        "session_entity_added",
        activity_payload,
        session_entity.created_at,
    )
    return to_session_entity_read(session_entity, campaign_entity)


async def update_session_entity_service(
    session_id: str,
    session_entity_id_value: str,
    payload: SessionEntityUpdate,
    user: User,
    session: DbSession,
) -> SessionEntityRead:
    session_entry = get_session_entry(session_id, session)
    gm_member = require_session_gm(session_entry, user, session)
    session_entity = get_session_entity_or_404(session_id, session_entity_id_value, session)

    previous_hp = session_entity.current_hp
    hp_changed = False
    visibility_changed = False

    if payload.visibleToPlayers is not None and payload.visibleToPlayers != session_entity.visible_to_players:
        visibility_changed = True
        session_entity.visible_to_players = payload.visibleToPlayers
        session_entity.revealed_at = utcnow() if payload.visibleToPlayers else None
    if payload.currentHp is not None and payload.currentHp != session_entity.current_hp:
        hp_changed = True
        session_entity.current_hp = payload.currentHp
    if payload.label is not None:
        session_entity.label = payload.label
    if payload.overrides is not None:
        session_entity.overrides = payload.overrides

    session.add(session_entity)
    session.commit()

    combat_state = None
    if hp_changed:
        combat_state = CombatService.sync_participant_status_for_session(
            session,
            session_id,
            session_entity_id_value,
            "session_entity",
        )
        session.commit()

    session.refresh(session_entity)
    if combat_state:
        session.refresh(combat_state)

    campaign_entity = get_campaign_entity(session_entity.campaign_entity_id, session)
    payload_data = entity_event_payload(
        session_entry,
        session_entity,
        campaign_entity,
        previous_hp=previous_hp if hp_changed else None,
        hp_delta=(
            session_entity.current_hp - previous_hp
            if hp_changed and previous_hp is not None and session_entity.current_hp is not None
            else None
        ),
    )
    event_created_at = session_entity.updated_at or session_entity.created_at
    gm_member_id = require_identifier(gm_member.id, "GM member is missing an id")
    current_user_id = require_identifier(user.id, "Authenticated user is missing an id")

    if visibility_changed:
        event_type = "entity_revealed" if session_entity.visible_to_players else "entity_hidden"
        record_session_activity(
            session_entry,
            event_type,
            session,
            member_id=gm_member_id,
            user_id=current_user_id,
            actor_name=gm_member.display_name,
            payload=payload_data,
            created_at=event_created_at,
        )
    if hp_changed:
        record_session_activity(
            session_entry,
            "entity_hp_updated",
            session,
            member_id=gm_member_id,
            user_id=current_user_id,
            actor_name=gm_member.display_name,
            payload=payload_data,
            created_at=event_created_at,
        )
    if visibility_changed or hp_changed:
        session.commit()
    if visibility_changed:
        event_type = "entity_revealed" if session_entity.visible_to_players else "entity_hidden"
        await publish_entity_event(session_entry, event_type, payload_data, event_created_at)
    if hp_changed:
        await publish_entity_event(session_entry, "entity_hp_updated", payload_data, event_created_at)
        if combat_state:
            await CombatService._emit_state(session_id, combat_state)
    return to_session_entity_read(session_entity, campaign_entity)


async def remove_session_entity_service(
    session_id: str,
    session_entity_id_value: str,
    user: User,
    session: DbSession,
) -> None:
    session_entry = get_session_entry(session_id, session)
    gm_member = require_session_gm(session_entry, user, session)
    session_entity = get_session_entity_or_404(session_id, session_entity_id_value, session)
    campaign_entity = get_campaign_entity(session_entity.campaign_entity_id, session)
    payload_data = entity_event_payload(session_entry, session_entity, campaign_entity)

    session.delete(session_entity)
    session.commit()
    record_session_activity(
        session_entry,
        "session_entity_removed",
        session,
        member_id=require_identifier(gm_member.id, "GM member is missing an id"),
        user_id=require_identifier(user.id, "Authenticated user is missing an id"),
        actor_name=gm_member.display_name,
        payload=payload_data,
    )
    session.commit()
    await publish_entity_event(session_entry, "session_entity_removed", payload_data)


async def reveal_session_entity_service(
    session_id: str,
    session_entity_id_value: str,
    user: User,
    session: DbSession,
) -> SessionEntityRead:
    session_entry = get_session_entry(session_id, session)
    gm_member = require_session_gm(session_entry, user, session)
    session_entity = get_session_entity_or_404(session_id, session_entity_id_value, session)
    session_entity.visible_to_players = True
    session_entity.revealed_at = utcnow()
    session.add(session_entity)
    session.commit()
    session.refresh(session_entity)

    campaign_entity = get_campaign_entity(session_entity.campaign_entity_id, session)
    payload_data = entity_event_payload(session_entry, session_entity, campaign_entity)
    record_session_activity(
        session_entry,
        "entity_revealed",
        session,
        member_id=require_identifier(gm_member.id, "GM member is missing an id"),
        user_id=require_identifier(user.id, "Authenticated user is missing an id"),
        actor_name=gm_member.display_name,
        payload=payload_data,
        created_at=session_entity.revealed_at,
    )
    session.commit()
    await publish_entity_event(
        session_entry,
        "entity_revealed",
        payload_data,
        session_entity.revealed_at,
    )
    return to_session_entity_read(session_entity, campaign_entity)


async def hide_session_entity_service(
    session_id: str,
    session_entity_id_value: str,
    user: User,
    session: DbSession,
) -> SessionEntityRead:
    session_entry = get_session_entry(session_id, session)
    gm_member = require_session_gm(session_entry, user, session)
    session_entity = get_session_entity_or_404(session_id, session_entity_id_value, session)
    session_entity.visible_to_players = False
    session_entity.revealed_at = None
    session.add(session_entity)
    session.commit()
    session.refresh(session_entity)

    campaign_entity = get_campaign_entity(session_entity.campaign_entity_id, session)
    payload_data = entity_event_payload(session_entry, session_entity, campaign_entity)
    event_created_at = session_entity.updated_at or session_entity.created_at
    record_session_activity(
        session_entry,
        "entity_hidden",
        session,
        member_id=require_identifier(gm_member.id, "GM member is missing an id"),
        user_id=require_identifier(user.id, "Authenticated user is missing an id"),
        actor_name=gm_member.display_name,
        payload=payload_data,
        created_at=event_created_at,
    )
    session.commit()
    await publish_entity_event(
        session_entry,
        "entity_hidden",
        payload_data,
        event_created_at,
    )
    return to_session_entity_read(session_entity, campaign_entity)


def list_visible_session_entities_service(
    session_id: str,
    user: User,
    session: DbSession,
) -> list[SessionEntityPlayerRead]:
    session_entry = get_session_entry(session_id, session)
    require_campaign_member(session_entry.campaign_id, user, session)
    return [
        to_session_entity_player_read(session_entity, campaign_entity)
        for session_entity, campaign_entity in list_session_entity_pairs(
            session_id,
            session,
            visible_only=True,
        )
    ]
