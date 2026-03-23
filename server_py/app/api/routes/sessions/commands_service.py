from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session as DbSession, select

from app.models.campaign_member import CampaignMember
from app.models.session import Session
from app.models.session_state import SessionState
from app.schemas.session import SessionCommandRequest
from app.services.session_rest import (
    SessionRestError,
    end_rest as end_rest_state,
    start_rest as start_rest_state,
)
from app.services.session_state_finalize import finalize_session_state_data
from ._shared import (
    get_or_create_session_runtime,
    get_session_rest_state,
    parse_expression,
    record_session_activity,
    require_identifier,
)
from .commands_common import (
    VALID_COMMANDS,
    build_base_event_payload,
    publish_command_event,
    publish_state_updates,
    require_active_gm_session,
    validate_roll_target,
)

AUTHORITATIVE_ROLL_TYPES = {"ability", "save", "skill", "initiative", "attack"}


def record_gm_activity(
    entry: Session,
    member: CampaignMember,
    user,
    command_type: str,
    payload: dict,
    issued_at: datetime,
    session: DbSession,
) -> None:
    record_session_activity(
        entry,
        command_type,
        session,
        member_id=require_identifier(member.id, "Campaign member is missing an id"),
        user_id=user.id,
        actor_name=member.display_name,
        payload=payload,
        created_at=issued_at,
    )


async def send_session_command_service(
    session_id: str,
    payload: SessionCommandRequest,
    user,
    session: DbSession,
) -> dict[str, bool]:
    entry, member = require_active_gm_session(session_id, user, session)
    if payload.type not in VALID_COMMANDS:
        raise HTTPException(status_code=400, detail="Invalid command")

    entry_id = require_identifier(entry.id, "Session is missing an id")
    runtime = get_or_create_session_runtime(entry_id, session)
    current_rest_state = get_session_rest_state(entry_id, session)
    issued_at = datetime.now(timezone.utc)
    payload_data = payload.payload or {}
    activity_payload: dict = {}
    event_payload = build_base_event_payload(entry, member, issued_at)
    event_type = payload.type

    if payload.type == "request_roll":
        expression = payload_data.get("expression")
        roll_type = payload_data.get("rollType")
        if roll_type is not None:
            if not isinstance(roll_type, str) or roll_type not in AUTHORITATIVE_ROLL_TYPES:
                raise HTTPException(status_code=400, detail="Invalid roll type")
            activity_payload["rollType"] = roll_type

        if expression is None and roll_type:
            cleaned_expression = "d20"
        elif not isinstance(expression, str) or not expression.strip():
            raise HTTPException(status_code=400, detail="Missing dice expression")
        else:
            cleaned_expression = expression.strip()

        if not parse_expression(cleaned_expression):
            raise HTTPException(status_code=400, detail="Invalid dice expression")
        activity_payload["expression"] = cleaned_expression

        if roll_type in {"ability", "save"}:
            ability = payload_data.get("ability")
            if not isinstance(ability, str) or not ability.strip():
                raise HTTPException(status_code=400, detail="Ability roll requests require an ability")
            activity_payload["ability"] = ability.strip()

        if roll_type == "skill":
            skill = payload_data.get("skill")
            if not isinstance(skill, str) or not skill.strip():
                raise HTTPException(status_code=400, detail="Skill roll requests require a skill")
            activity_payload["skill"] = skill.strip()

        dc = payload_data.get("dc")
        if dc is not None:
            if not isinstance(dc, int) or dc <= 0:
                raise HTTPException(status_code=400, detail="DC must be a positive integer")
            activity_payload["dc"] = dc

        reason = payload_data.get("reason")
        if reason is not None:
            if not isinstance(reason, str):
                raise HTTPException(status_code=400, detail="Reason must be a string")
            cleaned_reason = reason.strip()
            if cleaned_reason:
                activity_payload["reason"] = cleaned_reason

        mode = payload_data.get("mode")
        if mode is not None:
            if mode not in {"advantage", "disadvantage"}:
                raise HTTPException(status_code=400, detail="Invalid roll mode")
            activity_payload["mode"] = mode

        target = validate_roll_target(entry, payload_data.get("targetUserId"), session)
        if target:
            activity_payload["targetUserId"] = target[0]
            activity_payload["targetDisplayName"] = target[1]

        event_type = "roll_requested"
        event_payload.update(activity_payload)
        record_gm_activity(
            entry,
            member,
            user,
            "request_roll",
            activity_payload,
            issued_at,
            session,
        )
        session.commit()
        await publish_command_event(entry, event_type, event_payload, issued_at)
        return {"ok": True}

    if payload.type == "open_shop":
        runtime.shop_open = True
        activity_payload["shopOpen"] = True
        record_gm_activity(entry, member, user, "open_shop", activity_payload, issued_at, session)
        session.add(runtime)
        session.commit()
        event_type = "shop_opened"
        event_payload["shopOpen"] = True
        await publish_command_event(entry, event_type, event_payload, issued_at)
        return {"ok": True}

    if payload.type == "close_shop":
        runtime.shop_open = False
        activity_payload["shopOpen"] = False
        record_gm_activity(entry, member, user, "close_shop", activity_payload, issued_at, session)
        session.add(runtime)
        session.commit()
        event_type = "shop_closed"
        event_payload["shopOpen"] = False
        await publish_command_event(entry, event_type, event_payload, issued_at)
        return {"ok": True}

    if payload.type == "start_combat":
        if current_rest_state != "exploration":
            raise HTTPException(status_code=400, detail="Cannot start combat during a rest")
        runtime.combat_active = True
        note = payload_data.get("note")
        if note is not None:
            if not isinstance(note, str):
                raise HTTPException(status_code=400, detail="Combat note must be a string")
            cleaned_note = note.strip()
            if cleaned_note:
                activity_payload["note"] = cleaned_note
        record_gm_activity(
            entry,
            member,
            user,
            "start_combat",
            activity_payload,
            issued_at,
            session,
        )
        session.add(runtime)
        session.commit()
        event_type = "combat_started"
        event_payload["combatActive"] = True
        event_payload.update(activity_payload)
        await publish_command_event(entry, event_type, event_payload, issued_at)
        return {"ok": True}

    if payload.type == "end_combat":
        runtime.combat_active = False
        note = payload_data.get("note")
        if note is not None:
            if not isinstance(note, str):
                raise HTTPException(status_code=400, detail="Combat note must be a string")
            cleaned_note = note.strip()
            if cleaned_note:
                activity_payload["note"] = cleaned_note
        record_gm_activity(
            entry,
            member,
            user,
            "end_combat",
            activity_payload,
            issued_at,
            session,
        )
        session.add(runtime)
        session.commit()
        event_type = "combat_ended"
        event_payload["combatActive"] = False
        event_payload.update(activity_payload)
        await publish_command_event(entry, event_type, event_payload, issued_at)
        return {"ok": True}

    if payload.type in {"start_short_rest", "start_long_rest"}:
        if runtime.combat_active:
            raise HTTPException(status_code=400, detail="Cannot start a rest during combat")
        if current_rest_state != "exploration":
            raise HTTPException(status_code=400, detail="A rest is already active")

        target_rest_type = "short_rest" if payload.type == "start_short_rest" else "long_rest"
        activity_payload["restType"] = target_rest_type
        record_gm_activity(entry, member, user, payload.type, activity_payload, issued_at, session)

        states = list(
            session.exec(select(SessionState).where(SessionState.session_id == entry_id)).all()
        )
        if not states:
            raise HTTPException(status_code=400, detail="Session has no player states")

        for state in states:
            try:
                state.state_json = finalize_session_state_data(
                    start_rest_state(state.state_json, target_rest_type)
                )
            except SessionRestError as error:
                raise HTTPException(status_code=400, detail=str(error)) from error
            session.add(state)

        session.commit()
        for state in states:
            session.refresh(state)

        event_type = "rest_started"
        event_payload["restType"] = target_rest_type
        event_payload["issuedAt"] = issued_at.isoformat()
        await publish_state_updates(entry, states, issued_at)
        await publish_command_event(entry, event_type, event_payload, issued_at)
        return {"ok": True}

    if current_rest_state == "exploration":
        raise HTTPException(status_code=400, detail="No rest is active")

    activity_payload["restType"] = current_rest_state
    record_gm_activity(entry, member, user, "end_rest", activity_payload, issued_at, session)

    states = list(
        session.exec(select(SessionState).where(SessionState.session_id == entry_id)).all()
    )
    if not states:
        raise HTTPException(status_code=400, detail="Session has no player states")

    ended_rest_type = current_rest_state
    for state in states:
        try:
            state.state_json, ended_rest_type = end_rest_state(state.state_json)
        except SessionRestError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        session.add(state)

    session.commit()
    for state in states:
        session.refresh(state)

    event_type = "rest_ended"
    event_payload["restType"] = ended_rest_type
    event_payload["issuedAt"] = issued_at.isoformat()
    await publish_state_updates(entry, states, issued_at)
    await publish_command_event(entry, event_type, event_payload, issued_at)
    return {"ok": True}
