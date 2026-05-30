from __future__ import annotations

from fastapi import HTTPException
from sqlmodel import select

from app.models.session_state import SessionState


async def remove_persisted_effect_for_player_impl(
    *,
    session,
    entry,
    session_id: str,
    actor_user,
    owner_player_user_id: str,
    effect_id: str,
    removed_by_gm: bool,
    ensure_session_state,
    remove_persisted_effect,
    finalize_session_state_data,
    clear_concentration_group_across_session,
    resolve_ooc_activity_actor,
    resolve_ooc_activity_target_display_name,
    record_session_activity,
    prune_out_of_combat_session_activity,
    publish_state_update,
    to_state_read,
    find_effect_by_id,
    derive_effect_label,
):
    state = session.exec(
        select(SessionState).where(
            SessionState.session_id == session_id,
            SessionState.player_user_id == owner_player_user_id,
        )
    ).first()
    state = ensure_session_state(state, session_id, owner_player_user_id, entry.party_id, session)
    if not state:
        raise HTTPException(status_code=404, detail="Session state not found")

    state_json = state.state_json if isinstance(state.state_json, dict) else {}
    removed_effect = find_effect_by_id(state_json, effect_id)
    effect_metadata = (
        removed_effect.get("metadata")
        if isinstance(removed_effect, dict) and isinstance(removed_effect.get("metadata"), dict)
        else None
    )
    source_spell_name = (
        effect_metadata.get("source_spell_name")
        if effect_metadata and isinstance(effect_metadata.get("source_spell_name"), str)
        else None
    )
    variant_label = (
        effect_metadata.get("selected_variant_label")
        if effect_metadata and isinstance(effect_metadata.get("selected_variant_label"), str)
        else None
    )
    concentration_group = (
        effect_metadata.get("concentration_group")
        if effect_metadata and isinstance(effect_metadata.get("concentration_group"), str)
        else None
    )
    was_concentration = bool(effect_metadata and effect_metadata.get("concentration") is True)
    broke_concentration_group = bool(was_concentration and concentration_group)
    effect_label = derive_effect_label(removed_effect, effect_id) if removed_effect else effect_id

    updated = remove_persisted_effect(state.state_json, effect_id)
    state.state_json = finalize_session_state_data(updated)
    session.add(state)

    affected_allies: list[SessionState] = []
    if effect_metadata:
        caster_id = effect_metadata.get("caster_player_user_id")
        target_id = effect_metadata.get("target_player_user_id")
        is_ally_target = caster_id is not None and target_id is not None and caster_id != target_id
        if was_concentration and is_ally_target and concentration_group:
            affected_allies = clear_concentration_group_across_session(
                session, session_id, concentration_group, exclude_user_id=owner_player_user_id
            )

    actor_member_id, actor_display_name = resolve_ooc_activity_actor(entry, actor_user, session)
    if removed_effect and actor_member_id:
        target_display_name = resolve_ooc_activity_target_display_name(entry, owner_player_user_id, session)
        record_session_activity(
            entry,
            "out_of_combat_effect_removed",
            session,
            member_id=actor_member_id,
            user_id=actor_user.id,
            actor_name=actor_display_name,
            payload={
                "actor_user_id": actor_user.id,
                "actor_player_user_id": actor_user.id,
                "actor_display_name": actor_display_name,
                "target_player_user_id": owner_player_user_id,
                "target_display_name": target_display_name,
                "removed_effect_id": effect_id,
                "effect_label": effect_label,
                "source_spell_name": source_spell_name,
                "variant_label": variant_label,
                "concentration_group": concentration_group,
                "broke_concentration_group": broke_concentration_group,
                "removed_by_gm": removed_by_gm,
            },
        )
        prune_out_of_combat_session_activity(session, session_id)

    session.commit()
    session.refresh(state)

    states_to_publish: dict[str, SessionState] = {owner_player_user_id: state}
    for ally in affected_allies:
        if ally.player_user_id not in states_to_publish:
            states_to_publish[ally.player_user_id] = ally

    for player_id, st in states_to_publish.items():
        await publish_state_update(
            entry,
            player_id,
            st.updated_at or st.created_at,
            st.state_json if isinstance(st.state_json, dict) else None,
        )
    return to_state_read(state)
