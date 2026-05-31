from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import delete
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session as DbSession, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.campaign import Campaign
from app.models.campaign_member import CampaignMember
from app.models.campaign_spell import CampaignSpell
from app.models.item import ItemType
from app.models.session_state import SessionState
from app.schemas.session_state import (
    ClearConcentrationRequest,
    OutOfCombatCastRequest,
    PrepareSpellsRequest,
    SessionStateLoadoutUpdate,
    SessionStateRead,
    SessionStateUpdate,
)
from app.services.combat import CombatService
from app.services.combat_service.persistent_effects import (
    clear_concentration_group_across_session,
    clear_persisted_concentration_effects,
    remove_persisted_effect,
)
from app.services.game_time import get_game_time_seconds
from app.services.out_of_combat_cast import (
    build_healing_preview,
    has_castable_effects,
)
from app.services.declarative_effect_lifecycle import remove_armor_don_effects_from_combat_participant
from app.services.session_rest import ensure_rest_state
from app.services.session_state_finalize import finalize_session_state_data
from app.services.spell_preparation import apply_prepared_spells_with_long_rest_tracking
from ._shared import (
    record_session_activity,
    require_identifier,
    _resolve_ooc_activity_actor,
    _resolve_ooc_activity_target_display_name,
    _require_session_participant,
    _prune_out_of_combat_session_activity,
)
from .state_common import (
    ensure_session_state,
    get_session_entry,
    publish_state_update,
    require_campaign_member,
    require_session_gm,
    require_session_view_access,
    resolve_owned_inventory_item,
    serialize_equipped_armor,
    to_state_read,
)
from .state_read_routes import get_my_session_state_impl, get_player_session_state_impl
from .state_effect_routes import remove_persisted_effect_for_player_impl
from .state_ooc_cast_routes import (
    cast_ooc_player_impl,
    cast_ooc_self_impl,
    list_castable_spells_player_impl,
    list_castable_spells_self_impl,
)
from .state_update_routes import clear_my_concentration_impl, publish_and_return_state

router = APIRouter()


def _find_effect_by_id(state_json: dict | None, effect_id: str) -> dict | None:
    effects = (state_json or {}).get("active_spell_effects")
    if not isinstance(effects, list):
        return None
    for effect in effects:
        if isinstance(effect, dict) and effect.get("id") == effect_id:
            return effect
    return None


def _derive_effect_label(effect: dict, fallback_effect_id: str) -> str:
    display_label = effect.get("display_label")
    if isinstance(display_label, str) and display_label.strip():
        return display_label.strip()
    metadata = effect.get("metadata") if isinstance(effect.get("metadata"), dict) else {}
    spell_name = metadata.get("source_spell_name")
    variant_label = metadata.get("selected_variant_label")
    if isinstance(spell_name, str) and spell_name.strip():
        if isinstance(variant_label, str) and variant_label.strip():
            return f"{spell_name.strip()} — {variant_label.strip()}"
        return spell_name.strip()
    return fallback_effect_id


def _list_out_of_combat_castable_spells_for_player(
    *,
    entry,
    session_id: str,
    caster_user_id: str,
    session: DbSession,
) -> list[dict]:
    state = session.exec(
        select(SessionState).where(
            SessionState.session_id == session_id,
            SessionState.player_user_id == caster_user_id,
        )
    ).first()
    state = ensure_session_state(state, session_id, caster_user_id, entry.party_id, session)
    if not state:
        return []

    spellcasting = (state.state_json or {}).get("spellcasting") or {}
    player_spells = spellcasting.get("spells") or []

    canonical_keys = [
        s.get("canonicalKey") for s in player_spells
        if isinstance(s, dict) and s.get("canonicalKey")
    ]
    if not canonical_keys:
        return []

    campaign_spells = session.exec(
        select(CampaignSpell).where(
            CampaignSpell.campaign_id == entry.campaign_id,
            CampaignSpell.canonical_key.in_(canonical_keys),
            CampaignSpell.out_of_combat_castable == True,  # noqa: E712
            CampaignSpell.is_enabled == True,  # noqa: E712
        )
    ).all()

    campaign_spells = [cs for cs in campaign_spells if has_castable_effects(cs)]
    eligible_keys = {cs.canonical_key for cs in campaign_spells}

    result: list[dict] = []
    for player_spell in player_spells:
        if not isinstance(player_spell, dict):
            continue
        spell_key = player_spell.get("canonicalKey")
        if spell_key not in eligible_keys:
            continue
        campaign_spell = next((c for c in campaign_spells if c.canonical_key == spell_key), None)
        if not campaign_spell:
            continue
        healing_preview = build_healing_preview(
            campaign_spell,
            state.state_json if isinstance(state.state_json, dict) else {},
        )
        result.append({
            "id": player_spell.get("id"),
            "canonicalKey": campaign_spell.canonical_key,
            "nameEn": campaign_spell.name_en,
            "namePt": campaign_spell.name_pt,
            "level": campaign_spell.level,
            "concentration": campaign_spell.concentration,
            "prepared": player_spell.get("prepared", False),
            "variants": campaign_spell.variants_json or [],
            "effects": campaign_spell.effects_json or [],
            "outOfCombatTarget": campaign_spell.out_of_combat_target,
            "healingPreview": healing_preview,
        })
    return result


@router.get("/sessions/{session_id}/state/me", response_model=SessionStateRead)
def get_my_session_state(
    session_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    return get_my_session_state_impl(
        session_id=session_id,
        user=user,
        session=session,
        get_session_entry=get_session_entry,
        require_session_view_access=require_session_view_access,
        ensure_session_state=ensure_session_state,
        to_state_read=to_state_read,
    )


@router.get("/sessions/{session_id}/state/{player_user_id}", response_model=SessionStateRead)
def get_player_session_state(
    session_id: str,
    player_user_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    return get_player_session_state_impl(
        session_id=session_id,
        player_user_id=player_user_id,
        user=user,
        session=session,
        get_session_entry=get_session_entry,
        require_session_view_access=require_session_view_access,
        ensure_session_state=ensure_session_state,
        to_state_read=to_state_read,
    )


@router.put("/sessions/{session_id}/state/me/loadout", response_model=SessionStateRead)
async def update_my_session_loadout(
    session_id: str,
    payload: SessionStateLoadoutUpdate,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = get_session_entry(session_id, session)
    require_session_view_access(entry, user, session, user.id)
    member = require_campaign_member(entry, user, session)
    state = session.exec(
        select(SessionState).where(
            SessionState.session_id == session_id,
            SessionState.player_user_id == user.id,
        )
    ).first()
    state = ensure_session_state(state, session_id, user.id, entry.party_id, session)
    if not state:
        raise HTTPException(status_code=404, detail="Session state not found")

    weapon_item = resolve_owned_inventory_item(
        session_entry=entry,
        member=member,
        db=session,
        inventory_item_id=payload.currentWeaponId,
        expected_type=ItemType.WEAPON,
    )
    armor_item = resolve_owned_inventory_item(
        session_entry=entry,
        member=member,
        db=session,
        inventory_item_id=payload.equippedArmorItemId,
        expected_type=ItemType.ARMOR,
        allow_shield=False,
    )

    next_state = finalize_session_state_data({
        **ensure_rest_state(state.state_json),
        "currentWeaponId": require_identifier(weapon_item[0].id, "Inventory item is missing an id")
        if weapon_item
        else None,
        "equippedArmorItemId": require_identifier(armor_item[0].id, "Inventory item is missing an id")
        if armor_item
        else None,
        "equippedArmor": serialize_equipped_armor(armor_item[1] if armor_item else None),
    })
    state.state_json = next_state
    session.add(state)

    combat_state_for_loadout = CombatService.get_state(session, session_id)
    if combat_state_for_loadout is not None:
        if remove_armor_don_effects_from_combat_participant(combat_state_for_loadout, user.id):
            flag_modified(combat_state_for_loadout, "participants")
            session.add(combat_state_for_loadout)

    session.commit()
    session.refresh(state)

    await publish_state_update(
        entry,
        user.id,
        state.updated_at or state.created_at,
        state.state_json if isinstance(state.state_json, dict) else None,
    )
    return to_state_read(state)


@router.put("/sessions/{session_id}/state/{player_user_id}", response_model=SessionStateRead)
async def update_player_session_state(
    session_id: str,
    player_user_id: str,
    payload: SessionStateUpdate,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = get_session_entry(session_id, session)
    require_session_gm(entry, user, session)
    state = session.exec(
        select(SessionState).where(
            SessionState.session_id == session_id,
            SessionState.player_user_id == player_user_id,
        )
    ).first()
    state = ensure_session_state(state, session_id, player_user_id, entry.party_id, session)
    if not state:
        raise HTTPException(status_code=404, detail="Session state not found")

    previous_state = state.state_json if isinstance(state.state_json, dict) else {}
    actor_member = require_campaign_member(entry, user, session)
    next_state = finalize_session_state_data(
        payload.state,
        game_time_seconds=get_game_time_seconds(session_id, session),
    )
    state.state_json = next_state
    combat_state = CombatService.sync_participant_status_for_session(
        session,
        session_id,
        player_user_id,
        "player",
    )
    if combat_state:
        tier_changed = CombatService.recompute_participant_encumbrance_tier(
            session, session_id, combat_state, player_user_id,
        )
        armor_don_removed = remove_armor_don_effects_from_combat_participant(combat_state, player_user_id)
        if tier_changed or armor_don_removed:
            flag_modified(combat_state, "participants")
            session.add(combat_state)
    session.add(state)
    previous_hp = previous_state.get("currentHP") if isinstance(previous_state.get("currentHP"), int) else None
    current_hp = state.state_json.get("currentHP") if isinstance(state.state_json.get("currentHP"), int) else None
    if previous_hp is not None and current_hp is not None and previous_hp != current_hp:
        target_member = session.exec(
            select(CampaignMember).where(
                CampaignMember.campaign_id == entry.campaign_id,
                CampaignMember.user_id == player_user_id,
            )
        ).first()
        record_session_activity(
            entry,
            "player_hp_updated",
            session,
            member_id=require_identifier(actor_member.id, "Campaign member is missing an id"),
            user_id=user.id,
            actor_name=actor_member.display_name,
            payload={
                "targetUserId": player_user_id,
                "targetDisplayName": target_member.display_name if target_member else player_user_id,
                "previousHp": previous_hp,
                "currentHp": current_hp,
                "delta": current_hp - previous_hp,
                "maxHp": state.state_json.get("maxHP")
                if isinstance(state.state_json.get("maxHP"), int)
                else None,
            },
        )
    session.commit()
    session.refresh(state)
    if combat_state:
        session.refresh(combat_state)

    await publish_state_update(
        entry,
        player_user_id,
        state.updated_at or state.created_at,
        state.state_json if isinstance(state.state_json, dict) else None,
    )
    if combat_state:
        await CombatService._emit_state(session_id, combat_state)
    return to_state_read(state)


@router.post("/sessions/{session_id}/state/me/concentration/clear", response_model=SessionStateRead)
async def clear_my_concentration(
    session_id: str,
    payload: ClearConcentrationRequest = Body(default_factory=ClearConcentrationRequest),
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry, state, to_read_fn, publish_fn = clear_my_concentration_impl(
        session_id=session_id,
        payload=payload,
        user=user,
        session=session,
        get_session_entry=get_session_entry,
        require_session_view_access=require_session_view_access,
        ensure_session_state=ensure_session_state,
        clear_persisted_concentration_effects=clear_persisted_concentration_effects,
        finalize_session_state_data=finalize_session_state_data,
        publish_state_update=publish_state_update,
        to_state_read=to_state_read,
    )
    return await publish_and_return_state(
        entry=entry,
        user_id=user.id,
        state=state,
        publish_state_update=publish_fn,
        to_state_read=to_read_fn,
    )


@router.delete("/sessions/{session_id}/state/me/effects/{effect_id}", response_model=SessionStateRead)
async def remove_my_persisted_effect(
    session_id: str,
    effect_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = get_session_entry(session_id, session)
    require_session_view_access(entry, user, session, user.id)
    return await _remove_persisted_effect_for_player(
        session=session,
        entry=entry,
        session_id=session_id,
        actor_user=user,
        owner_player_user_id=user.id,
        effect_id=effect_id,
        removed_by_gm=False,
    )


async def _remove_persisted_effect_for_player(
    *,
    session: DbSession,
    entry,
    session_id: str,
    actor_user,
    owner_player_user_id: str,
    effect_id: str,
    removed_by_gm: bool,
) -> SessionStateRead:
    return await remove_persisted_effect_for_player_impl(
        session=session,
        entry=entry,
        session_id=session_id,
        actor_user=actor_user,
        owner_player_user_id=owner_player_user_id,
        effect_id=effect_id,
        removed_by_gm=removed_by_gm,
        ensure_session_state=ensure_session_state,
        remove_persisted_effect=remove_persisted_effect,
        finalize_session_state_data=finalize_session_state_data,
        clear_concentration_group_across_session=clear_concentration_group_across_session,
        resolve_ooc_activity_actor=_resolve_ooc_activity_actor,
        resolve_ooc_activity_target_display_name=_resolve_ooc_activity_target_display_name,
        record_session_activity=record_session_activity,
        prune_out_of_combat_session_activity=_prune_out_of_combat_session_activity,
        publish_state_update=publish_state_update,
        to_state_read=to_state_read,
        find_effect_by_id=_find_effect_by_id,
        derive_effect_label=_derive_effect_label,
    )


@router.delete("/sessions/{session_id}/state/{player_user_id}/effects/{effect_id}", response_model=SessionStateRead)
async def remove_player_persisted_effect(
    session_id: str,
    player_user_id: str,
    effect_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = get_session_entry(session_id, session)
    require_session_gm(entry, user, session)
    _require_session_participant(entry, session, player_user_id, label="Target")
    return await _remove_persisted_effect_for_player(
        session=session,
        entry=entry,
        session_id=session_id,
        actor_user=user,
        owner_player_user_id=player_user_id,
        effect_id=effect_id,
        removed_by_gm=True,
    )


@router.post("/sessions/{session_id}/state/me/spells/prepare", response_model=SessionStateRead)
async def prepare_my_spells(
    session_id: str,
    payload: PrepareSpellsRequest,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = get_session_entry(session_id, session)
    require_session_view_access(entry, user, session, user.id)

    state = session.exec(
        select(SessionState).where(
            SessionState.session_id == session_id,
            SessionState.player_user_id == user.id,
        )
    ).first()
    state = ensure_session_state(state, session_id, user.id, entry.party_id, session)
    if not state:
        raise HTTPException(status_code=404, detail="Session state not found")

    pending = (state.state_json or {}).get("pending_spell_preparation")
    if not pending:
        raise HTTPException(status_code=400, detail="No pending spell preparation.")

    spellcasting = (state.state_json or {}).get("spellcasting")
    spells = spellcasting.get("spells", []) if isinstance(spellcasting, dict) else []
    spell_id_set = {s.get("id") for s in spells if isinstance(s, dict)}

    for sid in payload.preparedSpellIds:
        if sid not in spell_id_set:
            raise HTTPException(status_code=400, detail=f"Unknown spell id: {sid}")

    leveled_count = sum(
        1
        for s in spells
        if isinstance(s, dict)
        and s.get("id") in payload.preparedSpellIds
        and s.get("level", 0) > 0
    )
    limit = pending.get("prepared_limit", 0)
    if leveled_count > limit:
        raise HTTPException(
            status_code=400,
            detail=f"Prepared spell count ({leveled_count}) exceeds limit ({limit}).",
        )

    was_initial_setup = (pending or {}).get("source") == "initial_setup"
    state.state_json = apply_prepared_spells_with_long_rest_tracking(state.state_json, payload.preparedSpellIds)
    if was_initial_setup:
        state.state_json["spell_preparation_initial_completed"] = True
    state.state_json = finalize_session_state_data(state.state_json)
    flag_modified(state, "state_json")
    session.add(state)
    session.commit()
    session.refresh(state)

    await publish_state_update(
        entry,
        user.id,
        state.updated_at or state.created_at,
        state.state_json if isinstance(state.state_json, dict) else None,
    )
    return to_state_read(state)


@router.get("/sessions/{session_id}/state/me/spells/castable-out-of-combat")
def list_out_of_combat_castable_spells(
    session_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    return list_castable_spells_self_impl(
        session_id=session_id,
        user=user,
        session=session,
        get_session_entry=get_session_entry,
        require_session_view_access=require_session_view_access,
        list_for_player=_list_out_of_combat_castable_spells_for_player,
    )


@router.get("/sessions/{session_id}/state/{player_user_id}/spells/castable-out-of-combat")
def list_out_of_combat_castable_spells_for_player(
    session_id: str,
    player_user_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    return list_castable_spells_player_impl(
        session_id=session_id,
        player_user_id=player_user_id,
        user=user,
        session=session,
        get_session_entry=get_session_entry,
        require_session_gm=require_session_gm,
        require_session_participant=_require_session_participant,
        list_for_player=_list_out_of_combat_castable_spells_for_player,
    )


@router.post("/sessions/{session_id}/state/me/spells/cast", response_model=SessionStateRead)
async def cast_spell_out_of_combat(
    session_id: str,
    req: OutOfCombatCastRequest,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    # Lazy import: keeps state.py → service one-directional (importing the service
    # at module top would re-create a circular import via the sessions package).
    from app.services.ooc_spell_cast_service import (
        cast_spell_out_of_combat_for_player as _cast_spell_out_of_combat_for_player,
    )
    return await cast_ooc_self_impl(
        session_id=session_id,
        req=req,
        user=user,
        session=session,
        get_session_entry=get_session_entry,
        require_session_view_access=require_session_view_access,
        cast_for_player=_cast_spell_out_of_combat_for_player,
    )


@router.post("/sessions/{session_id}/state/{player_user_id}/spells/cast", response_model=SessionStateRead)
async def cast_spell_out_of_combat_for_player(
    session_id: str,
    player_user_id: str,
    req: OutOfCombatCastRequest,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    # Lazy import: keeps state.py → service one-directional (see cast_spell_out_of_combat).
    from app.services.ooc_spell_cast_service import (
        cast_spell_out_of_combat_for_player as _cast_spell_out_of_combat_for_player,
    )
    return await cast_ooc_player_impl(
        session_id=session_id,
        player_user_id=player_user_id,
        req=req,
        user=user,
        session=session,
        get_session_entry=get_session_entry,
        require_session_gm=require_session_gm,
        require_session_participant=_require_session_participant,
        cast_for_player=_cast_spell_out_of_combat_for_player,
    )
