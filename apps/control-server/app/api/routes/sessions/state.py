from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session as DbSession, select

from app.api.deps import get_current_user
from app.db.session import get_session
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
    clear_persisted_concentration_effects,
    remove_persisted_effect,
)
from app.services.out_of_combat_cast import (
    build_persisted_effects,
    check_out_of_combat_cast_eligibility,
    consume_spell_slot,
    has_castable_effects,
)
from app.services.session_rest import ensure_rest_state
from app.services.session_state_finalize import finalize_session_state_data
from app.services.spell_preparation import apply_prepared_spells
from ._shared import record_session_activity, require_identifier
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

router = APIRouter()


@router.get("/sessions/{session_id}/state/me", response_model=SessionStateRead)
def get_my_session_state(
    session_id: str,
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
    return to_state_read(state)


@router.get("/sessions/{session_id}/state/{player_user_id}", response_model=SessionStateRead)
def get_player_session_state(
    session_id: str,
    player_user_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = get_session_entry(session_id, session)
    require_session_view_access(entry, user, session, player_user_id)
    state = session.exec(
        select(SessionState).where(
            SessionState.session_id == session_id,
            SessionState.player_user_id == player_user_id,
        )
    ).first()
    state = ensure_session_state(state, session_id, player_user_id, entry.party_id, session)
    if not state:
        raise HTTPException(status_code=404, detail="Session state not found")
    return to_state_read(state)


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
    next_state = finalize_session_state_data(payload.state)
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
        if tier_changed:
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

    updated = clear_persisted_concentration_effects(
        state.state_json,
        concentration_group=payload.concentrationGroup,
    )
    state.state_json = finalize_session_state_data(updated)
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


@router.delete("/sessions/{session_id}/state/me/effects/{effect_id}", response_model=SessionStateRead)
async def remove_my_persisted_effect(
    session_id: str,
    effect_id: str,
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

    updated = remove_persisted_effect(state.state_json, effect_id)
    state.state_json = finalize_session_state_data(updated)
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

    state.state_json = apply_prepared_spells(state.state_json, payload.preparedSpellIds)
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

    result = []
    for s in player_spells:
        if not isinstance(s, dict):
            continue
        if s.get("canonicalKey") not in eligible_keys:
            continue
        cs = next((c for c in campaign_spells if c.canonical_key == s.get("canonicalKey")), None)
        if not cs:
            continue
        result.append({
            "id": s.get("id"),
            "canonicalKey": cs.canonical_key,
            "nameEn": cs.name_en,
            "namePt": cs.name_pt,
            "level": cs.level,
            "concentration": cs.concentration,
            "prepared": s.get("prepared", False),
            "variants": cs.variants_json or [],
            "effects": cs.effects_json or [],
        })
    return result


@router.post("/sessions/{session_id}/state/me/spells/cast", response_model=SessionStateRead)
async def cast_spell_out_of_combat(
    session_id: str,
    req: OutOfCombatCastRequest,
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

    state_json = state.state_json or {}
    spellcasting = state_json.get("spellcasting") or {}
    player_spells = spellcasting.get("spells") or []
    player_spell = next(
        (s for s in player_spells if isinstance(s, dict) and s.get("id") == req.spellId),
        None,
    )
    if player_spell is None:
        raise HTTPException(status_code=400, detail=f"Spell not found in character spell list: {req.spellId!r}")

    canonical_key = player_spell.get("canonicalKey")
    if not canonical_key:
        raise HTTPException(status_code=400, detail="Spell entry is missing canonicalKey")

    spell_level = player_spell.get("level", 0)
    if spell_level > 0 and player_spell.get("prepared") is False:
        raise HTTPException(status_code=400, detail="Spell is not prepared")

    campaign_spell = session.exec(
        select(CampaignSpell).where(
            CampaignSpell.campaign_id == entry.campaign_id,
            CampaignSpell.canonical_key == canonical_key,
            CampaignSpell.is_enabled == True,  # noqa: E712
        )
    ).first()
    if not campaign_spell:
        raise HTTPException(status_code=400, detail=f"Spell not found in campaign catalog: {canonical_key!r}")

    ok, rejection = check_out_of_combat_cast_eligibility(
        spell=campaign_spell,
        state_json=state_json,
        slot_level=req.slotLevel,
        variant_key=req.variantKey,
    )
    if not ok:
        raise HTTPException(status_code=400, detail=rejection)

    updated = dict(state_json)

    if spell_level > 0 and req.slotLevel is not None:
        try:
            updated = consume_spell_slot(updated, req.slotLevel)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    new_effects = build_persisted_effects(
        spell=campaign_spell,
        caster_user_id=user.id,
        variant_key=req.variantKey,
    )
    if not new_effects:
        raise HTTPException(status_code=400, detail="No persistable effects could be created for this spell")

    if campaign_spell.concentration:
        updated = clear_persisted_concentration_effects(updated)

    existing_effects = list(updated.get("active_spell_effects") or [])
    existing_effects.extend(new_effects)
    updated["active_spell_effects"] = existing_effects

    state.state_json = finalize_session_state_data(updated)
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
