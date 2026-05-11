from datetime import datetime, timedelta, timezone

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
from app.models.party_member import PartyMember, PartyMemberStatus
from app.models.session_command_event import SessionCommandEvent
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
from app.services.goodberry_inventory import grant_catalog_item_to_player_inventory
from app.services.healing_consumables_types import _extract_hp_snapshot, _safe_int
from app.services.out_of_combat_cast import (
    build_concentration_marker,
    build_persisted_effects,
    check_out_of_combat_cast_eligibility,
    collect_create_consumable_effects,
    collect_heal_effects,
    consume_spell_slot,
    has_castable_effects,
    roll_spell_heal_effects,
)
from app.services.wild_shape_catalog import get_form
from app.services.wild_shape_service import apply_healing_to_form
from app.services.wild_shape_service import is_active as is_wild_shape_active
from app.services.declarative_effect_lifecycle import remove_armor_don_effects_from_combat_participant
from app.services.session_rest import ensure_rest_state
from app.services.session_state_finalize import finalize_session_state_data
from app.services.spell_preparation import apply_prepared_spells_with_long_rest_tracking
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

OUT_OF_COMBAT_ACTIVITY_EVENT_TYPES = (
    "out_of_combat_spell_cast",
    "out_of_combat_effect_removed",
)
OUT_OF_COMBAT_ACTIVITY_CAP = 50


def _apply_heal_to_state_dict(data: dict, amount: int) -> dict:
    """Apply immediate healing to a state dict in place. Handles wild shape."""
    if is_wild_shape_active(data):
        form_key = (data.get("wildShape") or {}).get("formKey")
        form = get_form(form_key) if isinstance(form_key, str) else None
        if form is not None:
            return apply_healing_to_form(data, amount, form)
    current, max_hp = _extract_hp_snapshot(data)
    new_hp = min(max_hp, current + max(0, amount))
    return {**data, "currentHP": new_hp}


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


def _resolve_ooc_activity_actor(entry, user, session: DbSession) -> tuple[str | None, str]:
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    member_id = getattr(member, "id", None) if member else None
    actor_display_name = getattr(member, "display_name", None) if member else None
    resolved_member_id = member_id if isinstance(member_id, str) and member_id else None
    resolved_actor = actor_display_name if isinstance(actor_display_name, str) and actor_display_name else user.id
    return resolved_member_id, resolved_actor


def _resolve_ooc_activity_target_display_name(entry, player_user_id: str, session: DbSession) -> str:
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.user_id == player_user_id,
        )
    ).first()
    display_name = getattr(member, "display_name", None) if member else None
    if isinstance(display_name, str) and display_name.strip():
        return display_name.strip()
    return player_user_id


def _require_session_participant(entry, session: DbSession, player_user_id: str, *, label: str) -> None:
    if entry.party_id:
        party_member = session.exec(
            select(PartyMember).where(
                PartyMember.party_id == entry.party_id,
                PartyMember.user_id == player_user_id,
                PartyMember.status == PartyMemberStatus.JOINED,
            )
        ).first()
        if not party_member:
            raise HTTPException(status_code=400, detail=f"{label} is not a participant in this session")
        return

    campaign_member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.user_id == player_user_id,
        )
    ).first()
    if not campaign_member:
        raise HTTPException(status_code=400, detail=f"{label} is not a participant in this session")


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
        })
    return result


async def _cast_spell_out_of_combat_for_player(
    *,
    entry,
    session_id: str,
    req: OutOfCombatCastRequest,
    actor_user,
    caster_user_id: str,
    session: DbSession,
    cast_by_gm: bool,
    enforce_target_membership: bool = False,
) -> SessionStateRead:
    # --- Load caster state ---
    caster_state = session.exec(
        select(SessionState).where(
            SessionState.session_id == session_id,
            SessionState.player_user_id == caster_user_id,
        )
    ).first()
    caster_state = ensure_session_state(caster_state, session_id, caster_user_id, entry.party_id, session)
    if not caster_state:
        raise HTTPException(status_code=404, detail="Session state not found")

    # --- Resolve target ---
    target_user_id = req.targetPlayerUserId or caster_user_id
    is_ally_target = target_user_id != caster_user_id

    target_state: SessionState | None = None
    if is_ally_target:
        if enforce_target_membership:
            _require_session_participant(entry, session, target_user_id, label="Target")
        target_state = session.exec(
            select(SessionState).where(
                SessionState.session_id == session_id,
                SessionState.player_user_id == target_user_id,
            )
        ).first()
        if not target_state:
            raise HTTPException(status_code=400, detail="Target is not a participant in this session")

    # --- Validate spell ---
    state_json = caster_state.state_json or {}
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

    if campaign_spell.out_of_combat_target == "ally" and not req.targetPlayerUserId:
        raise HTTPException(status_code=400, detail="Spell requires an ally target")

    if is_ally_target and campaign_spell.out_of_combat_target not in ("ally", "self_or_ally"):
        raise HTTPException(status_code=400, detail="Spell cannot target allies out of combat")

    target_state_json_for_check = (
        target_state.state_json if target_state and isinstance(target_state.state_json, dict)
        else state_json
    )
    ok, rejection = check_out_of_combat_cast_eligibility(
        spell=campaign_spell,
        state_json=state_json,
        slot_level=req.slotLevel,
        variant_key=req.variantKey,
        out_of_combat_target=campaign_spell.out_of_combat_target,
        target_user_id=target_user_id,
        caster_user_id=caster_user_id,
        target_state_json=target_state_json_for_check,
    )
    if not ok:
        raise HTTPException(status_code=400, detail=rejection)

    # --- Capture previous concentration metadata BEFORE any mutation ---
    previous_concentration_metadata = next(
        (
            metadata
            for effect in (state_json.get("active_spell_effects") or [])
            if isinstance(effect, dict)
            for metadata in [effect.get("metadata")]
            if isinstance(metadata, dict) and metadata.get("concentration")
        ),
        None,
    )
    old_group = (
        previous_concentration_metadata.get("concentration_group")
        if isinstance(previous_concentration_metadata, dict)
        and isinstance(previous_concentration_metadata.get("concentration_group"), str)
        else None
    )
    previous_spell_name = (
        previous_concentration_metadata.get("source_spell_name")
        if isinstance(previous_concentration_metadata, dict)
        and isinstance(previous_concentration_metadata.get("source_spell_name"), str)
        else None
    )
    previous_variant_label = (
        previous_concentration_metadata.get("selected_variant_label")
        if isinstance(previous_concentration_metadata, dict)
        and isinstance(previous_concentration_metadata.get("selected_variant_label"), str)
        else None
    )

    # --- Spend slot and clear caster concentration ---
    updated_caster_json = dict(state_json)

    if spell_level > 0 and req.slotLevel is not None:
        try:
            updated_caster_json = consume_spell_slot(updated_caster_json, req.slotLevel)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    affected_allies: list[SessionState] = []
    if campaign_spell.concentration:
        updated_caster_json = clear_persisted_concentration_effects(updated_caster_json)
        if old_group:
            affected_allies = clear_concentration_group_across_session(
                session, session_id, old_group, exclude_user_id=caster_user_id
            )

    current_game_time_seconds = get_game_time_seconds(session_id, session)

    # --- Build target effects ---
    new_target_effects = build_persisted_effects(
        spell=campaign_spell,
        caster_user_id=caster_user_id,
        target_user_id=target_user_id,
        variant_key=req.variantKey,
        game_time_seconds=current_game_time_seconds,
    )

    # --- Grant consumable items (create_consumable effects) ---
    consumable_effects = collect_create_consumable_effects(campaign_spell, req.variantKey)
    consumables_granted_count = 0
    if consumable_effects:
        campaign = session.exec(select(Campaign).where(Campaign.id == entry.campaign_id)).first()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        spell_name_for_notes = campaign_spell.name_pt or campaign_spell.name_en or campaign_spell.canonical_key
        for ce in consumable_effects:
            params = ce.get("params") or {}
            canonical_key = params.get("canonical_key")
            raw_qty = params.get("quantity", 1)
            quantity = raw_qty if isinstance(raw_qty, int) else 1
            expires_in_seconds = params.get("expires_in_seconds")
            if not canonical_key:
                continue
            expires_at = (
                datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
                if isinstance(expires_in_seconds, int) and expires_in_seconds > 0
                else None
            )
            grant_catalog_item_to_player_inventory(
                session,
                session_entry=entry,
                player_user_id=caster_user_id,
                system=campaign.system,
                canonical_key=canonical_key,
                quantity=quantity,
                notes=f"Criado por {spell_name_for_notes}",
                expires_at=expires_at,
                source_spell_canonical_key=campaign_spell.canonical_key,
            )
            consumables_granted_count += quantity

    # --- Precompute immediate healing (heal effects) ---
    heal_effects = collect_heal_effects(campaign_spell, req.variantKey)
    heal_rolled = (
        roll_spell_heal_effects(heal_effects, campaign_spell, req.slotLevel, state_json)
        if heal_effects
        else []
    )

    if not new_target_effects and not consumables_granted_count and not heal_rolled:
        raise HTTPException(status_code=400, detail="No persistable effects could be created for this spell")

    group_id: str | None = (
        (new_target_effects[0].get("metadata") or {}).get("concentration_group")
        if new_target_effects else None
    )

    # --- Apply effects ---
    if is_ally_target:
        # Concentration marker on the caster (no gameplay bonus)
        if campaign_spell.concentration and group_id:
            timed_marker_effect = next(
                (
                    effect for effect in new_target_effects
                    if effect.get("duration_type") == "timed"
                ),
                None,
            )
            marker = build_concentration_marker(
                spell=campaign_spell,
                caster_user_id=caster_user_id,
                target_user_id=target_user_id,
                concentration_group=group_id,
                variant_key=req.variantKey,
                duration_type=(
                    timed_marker_effect.get("duration_type")
                    if isinstance(timed_marker_effect, dict)
                    and isinstance(timed_marker_effect.get("duration_type"), str)
                    else "until_long_rest"
                ),
                created_at_game_time_seconds=(
                    timed_marker_effect.get("created_at_game_time_seconds")
                    if isinstance(timed_marker_effect, dict)
                    and isinstance(timed_marker_effect.get("created_at_game_time_seconds"), int)
                    else None
                ),
                expires_at_game_time_seconds=(
                    timed_marker_effect.get("expires_at_game_time_seconds")
                    if isinstance(timed_marker_effect, dict)
                    and isinstance(timed_marker_effect.get("expires_at_game_time_seconds"), int)
                    else None
                ),
            )
            caster_effects = list(updated_caster_json.get("active_spell_effects") or [])
            caster_effects.append(marker)
            updated_caster_json["active_spell_effects"] = caster_effects
            marker_effect_id = marker.get("id") if isinstance(marker.get("id"), str) else None
        else:
            marker_effect_id = None

        # Buff effects land on the target
        target_json = dict(target_state.state_json or {})  # type: ignore[union-attr]
        target_effects = list(target_json.get("active_spell_effects") or [])
        target_effects.extend(new_target_effects)
        target_json["active_spell_effects"] = target_effects
        # Immediate healing on ally target
        for hr in heal_rolled:
            if hr.get("target") == "caster":
                updated_caster_json = _apply_heal_to_state_dict(updated_caster_json, hr["amount"])
            else:
                target_json = _apply_heal_to_state_dict(target_json, hr["amount"])
        target_state.state_json = finalize_session_state_data(  # type: ignore[union-attr]
            target_json,
            game_time_seconds=current_game_time_seconds,
        )
        flag_modified(target_state, "state_json")
        session.add(target_state)
    else:
        # Self-target: original behaviour unchanged
        existing_effects = list(updated_caster_json.get("active_spell_effects") or [])
        existing_effects.extend(new_target_effects)
        updated_caster_json["active_spell_effects"] = existing_effects
        marker_effect_id = None
        # Immediate healing on self (target == caster)
        for hr in heal_rolled:
            updated_caster_json = _apply_heal_to_state_dict(updated_caster_json, hr["amount"])

    # --- Persist caster state ---
    caster_state.state_json = finalize_session_state_data(
        updated_caster_json,
        game_time_seconds=current_game_time_seconds,
    )
    flag_modified(caster_state, "state_json")
    session.add(caster_state)

    actor_member_id, actor_display_name = _resolve_ooc_activity_actor(entry, actor_user, session)
    if actor_member_id:
        spell_name = (
            campaign_spell.name_pt
            or campaign_spell.name_en
            or campaign_spell.canonical_key
        )
        variant_label = (
            (new_target_effects[0].get("metadata") or {}).get("selected_variant_label")
            if new_target_effects
            and isinstance(new_target_effects[0], dict)
            and isinstance(new_target_effects[0].get("metadata"), dict)
            else None
        )
        created_effect_ids = [
            effect_id
            for effect_id in (
                [effect.get("id") for effect in new_target_effects]
                + ([marker_effect_id] if marker_effect_id else [])
            )
            if isinstance(effect_id, str) and effect_id
        ]
        replaced_concentration = bool(campaign_spell.concentration and previous_concentration_metadata)
        activity_payload: dict = {
            "actor_user_id": actor_user.id,
            "actor_player_user_id": actor_user.id,  # legacy compatibility
            "actor_display_name": actor_display_name,
            "caster_player_user_id": caster_user_id,
            "caster_display_name": (
                actor_display_name if caster_user_id == actor_user.id else caster_user_id
            ),
            "target_player_user_id": target_user_id,
            "target_display_name": (
                actor_display_name if target_user_id == actor_user.id else target_user_id
            ),
            "spell_key": campaign_spell.canonical_key,
            "spell_name": spell_name,
            "variant_key": req.variantKey,
            "variant_label": variant_label,
            "created_effect_ids": created_effect_ids,
            "concentration_group": group_id,
            "replaced_concentration": replaced_concentration,
            "previous_concentration_group": old_group,
            "new_concentration_group": group_id if campaign_spell.concentration else None,
            "previous_spell_name": previous_spell_name,
            "previous_variant_label": previous_variant_label,
            "cast_by_gm": cast_by_gm,
        }
        if req.slotLevel is not None:
            activity_payload["slot_level"] = req.slotLevel
        if consumables_granted_count:
            activity_payload["consumables_granted_count"] = consumables_granted_count
            activity_payload["inventory_refresh_required"] = True
        if heal_rolled:
            total_healed = sum(hr["amount"] for hr in heal_rolled)
            activity_payload["healing_applied"] = total_healed
            activity_payload["healing_rolls"] = [
                {"dice": hr["effective_dice"], "rolls": hr["rolls"], "modifier": hr["modifier"], "total": hr["amount"]}
                for hr in heal_rolled
            ]
        record_session_activity(
            entry,
            "out_of_combat_spell_cast",
            session,
            member_id=actor_member_id,
            user_id=actor_user.id,
            actor_name=actor_display_name,
            payload=activity_payload,
        )
        _prune_out_of_combat_session_activity(session, session_id)

    # --- Single commit ---
    session.commit()
    session.refresh(caster_state)
    if is_ally_target and target_state is not None:
        session.refresh(target_state)

    # --- Publish updates (deduped by player_user_id) ---
    states_to_publish: dict[str, SessionState] = {caster_user_id: caster_state}
    if is_ally_target and target_state is not None:
        states_to_publish[target_user_id] = target_state
    for ally in affected_allies:
        if ally.player_user_id not in states_to_publish:
            states_to_publish[ally.player_user_id] = ally

    for player_id, state in states_to_publish.items():
        await publish_state_update(
            entry,
            player_id,
            state.updated_at or state.created_at,
            state.state_json if isinstance(state.state_json, dict) else None,
        )

    return to_state_read(caster_state)


def _prune_out_of_combat_session_activity(session: DbSession, session_id: str) -> None:
    stale_event_ids = [
        event_id
        for event_id in session.exec(
            select(SessionCommandEvent.id)
            .where(
                SessionCommandEvent.session_id == session_id,
                SessionCommandEvent.command_type.in_(OUT_OF_COMBAT_ACTIVITY_EVENT_TYPES),  # type: ignore[arg-type]
            )
            .order_by(SessionCommandEvent.created_at.desc(), SessionCommandEvent.id.desc())
            .offset(OUT_OF_COMBAT_ACTIVITY_CAP)
        ).all()
        if isinstance(event_id, str) and event_id
    ]
    if not stale_event_ids:
        return
    session.exec(
        delete(SessionCommandEvent).where(
            SessionCommandEvent.id.in_(stale_event_ids),  # type: ignore[arg-type]
        )
    )


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
    state = session.exec(
        select(SessionState).where(
            SessionState.session_id == session_id,
            SessionState.player_user_id == owner_player_user_id,
        )
    ).first()
    state = ensure_session_state(state, session_id, owner_player_user_id, entry.party_id, session)
    if not state:
        raise HTTPException(status_code=404, detail="Session state not found")

    # Capture effect payload BEFORE mutation (used for activity log + concentration break semantics).
    state_json = state.state_json if isinstance(state.state_json, dict) else {}
    removed_effect = _find_effect_by_id(state_json, effect_id)
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
    effect_label = _derive_effect_label(removed_effect, effect_id) if removed_effect else effect_id

    updated = remove_persisted_effect(state.state_json, effect_id)
    state.state_json = finalize_session_state_data(updated)
    session.add(state)

    # Cross-clear concentration group for ally-target effects
    affected_allies: list[SessionState] = []
    if effect_metadata:
        caster_id = effect_metadata.get("caster_player_user_id")
        target_id = effect_metadata.get("target_player_user_id")
        is_ally_target = caster_id is not None and target_id is not None and caster_id != target_id
        if was_concentration and is_ally_target and concentration_group:
            affected_allies = clear_concentration_group_across_session(
                session, session_id, concentration_group, exclude_user_id=owner_player_user_id
            )

    actor_member_id, actor_display_name = _resolve_ooc_activity_actor(entry, actor_user, session)
    if removed_effect and actor_member_id:
        target_display_name = _resolve_ooc_activity_target_display_name(
            entry,
            owner_player_user_id,
            session,
        )
        record_session_activity(
            entry,
            "out_of_combat_effect_removed",
            session,
            member_id=actor_member_id,
            user_id=actor_user.id,
            actor_name=actor_display_name,
            payload={
                "actor_user_id": actor_user.id,
                "actor_player_user_id": actor_user.id,  # legacy compatibility
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
        _prune_out_of_combat_session_activity(session, session_id)

    session.commit()
    session.refresh(state)

    # Publish updates for all modified players (deduped by player_user_id)
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
    entry = get_session_entry(session_id, session)
    require_session_view_access(entry, user, session, user.id)
    return _list_out_of_combat_castable_spells_for_player(
        entry=entry,
        session_id=session_id,
        caster_user_id=user.id,
        session=session,
    )


@router.get("/sessions/{session_id}/state/{player_user_id}/spells/castable-out-of-combat")
def list_out_of_combat_castable_spells_for_player(
    session_id: str,
    player_user_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = get_session_entry(session_id, session)
    require_session_gm(entry, user, session)
    _require_session_participant(entry, session, player_user_id, label="Caster")
    return _list_out_of_combat_castable_spells_for_player(
        entry=entry,
        session_id=session_id,
        caster_user_id=player_user_id,
        session=session,
    )


@router.post("/sessions/{session_id}/state/me/spells/cast", response_model=SessionStateRead)
async def cast_spell_out_of_combat(
    session_id: str,
    req: OutOfCombatCastRequest,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = get_session_entry(session_id, session)
    require_session_view_access(entry, user, session, user.id)
    return await _cast_spell_out_of_combat_for_player(
        entry=entry,
        session_id=session_id,
        req=req,
        actor_user=user,
        caster_user_id=user.id,
        session=session,
        cast_by_gm=False,
    )


@router.post("/sessions/{session_id}/state/{player_user_id}/spells/cast", response_model=SessionStateRead)
async def cast_spell_out_of_combat_for_player(
    session_id: str,
    player_user_id: str,
    req: OutOfCombatCastRequest,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = get_session_entry(session_id, session)
    require_session_gm(entry, user, session)
    _require_session_participant(entry, session, player_user_id, label="Caster")
    return await _cast_spell_out_of_combat_for_player(
        entry=entry,
        session_id=session_id,
        req=req,
        actor_user=user,
        caster_user_id=player_user_id,
        session=session,
        cast_by_gm=True,
        enforce_target_membership=True,
    )
