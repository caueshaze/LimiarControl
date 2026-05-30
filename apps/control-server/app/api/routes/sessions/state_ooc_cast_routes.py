from __future__ import annotations


def list_castable_spells_self_impl(*, session_id: str, user, session, get_session_entry, require_session_view_access, list_for_player):
    entry = get_session_entry(session_id, session)
    require_session_view_access(entry, user, session, user.id)
    return list_for_player(entry=entry, session_id=session_id, caster_user_id=user.id, session=session)


def list_castable_spells_player_impl(*, session_id: str, player_user_id: str, user, session, get_session_entry, require_session_gm, require_session_participant, list_for_player):
    entry = get_session_entry(session_id, session)
    require_session_gm(entry, user, session)
    require_session_participant(entry, session, player_user_id, label="Caster")
    return list_for_player(entry=entry, session_id=session_id, caster_user_id=player_user_id, session=session)


async def cast_ooc_self_impl(*, session_id: str, req, user, session, get_session_entry, require_session_view_access, cast_for_player):
    entry = get_session_entry(session_id, session)
    require_session_view_access(entry, user, session, user.id)
    return await cast_for_player(
        entry=entry,
        session_id=session_id,
        req=req,
        actor_user=user,
        caster_user_id=user.id,
        session=session,
        cast_by_gm=False,
    )


async def cast_ooc_player_impl(*, session_id: str, player_user_id: str, req, user, session, get_session_entry, require_session_gm, require_session_participant, cast_for_player):
    entry = get_session_entry(session_id, session)
    require_session_gm(entry, user, session)
    require_session_participant(entry, session, player_user_id, label="Caster")
    return await cast_for_player(
        entry=entry,
        session_id=session_id,
        req=req,
        actor_user=user,
        caster_user_id=player_user_id,
        session=session,
        cast_by_gm=True,
        enforce_target_membership=True,
    )
