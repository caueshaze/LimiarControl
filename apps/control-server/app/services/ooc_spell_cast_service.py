"""Out-of-combat spell-cast orchestration (issue #396).

Extracted verbatim from ``app.api.routes.sessions.state`` so that module stays a
thin route layer. Behavior is unchanged. Import direction is one-way:
``state.py`` imports this service (lazily, in-function); this service must NEVER
depend on the route module ``state`` (that would re-create a circular import).
"""

import sys
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session as DbSession, select

from app.models.campaign import Campaign
from app.models.campaign_member import CampaignMember
from app.models.campaign_spell import CampaignSpell
from app.models.item import ItemType
from app.models.session_state import SessionState
from app.schemas.session_state import OutOfCombatCastRequest, SessionStateRead
from app.services.combat_service.persistent_effects import (
    clear_concentration_group_across_session,
    clear_persisted_concentration_effects,
    clear_warding_bonds_across_session,
)
from app.services.game_time import get_game_time_seconds
from app.services.goodberry_inventory import grant_catalog_item_to_player_inventory
from app.services.healing_consumables_types import _extract_hp_snapshot, _safe_int
from app.services.out_of_combat_cast import (
    build_concentration_marker,
    build_ooc_warding_bond_effects,
    build_persisted_effects,
    check_out_of_combat_cast_eligibility,
    collect_create_consumable_effects,
    collect_heal_effects,
    collect_temp_hp_effects,
    consume_spell_slot,
    roll_spell_heal_effects,
    roll_spell_temp_hp_effects,
)
from app.services.session_state_finalize import finalize_session_state_data
from app.services.spell_material_components import (
    SpellMaterialError,
    consume_spell_material,
    validate_spell_material,
)
from app.services.wild_shape_catalog import get_form
from app.services.wild_shape_service import apply_healing_to_form
from app.services.wild_shape_service import is_active as is_wild_shape_active
from app.api.routes.sessions._shared import (
    record_session_activity,
    _resolve_ooc_activity_actor,
    _resolve_ooc_activity_target_display_name,
    _require_session_participant,
    _prune_out_of_combat_session_activity,
)
from app.api.routes.sessions.state_common import (
    ensure_session_state,
    publish_state_update,
    resolve_owned_inventory_item,
    to_state_read,
)


_SHILLELAGH_ELIGIBLE_WEAPONS = {"club", "quarterstaff"}

# Sentinel for injectable dependencies on ``cast_spell_out_of_combat_for_player``
# (issue #396): distinguishes "caller did not inject" from a legitimately falsy
# override, so the unset case can be resolved from this module at call time.
_UNSET = object()


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


def _apply_temp_hp_to_state_dict(data: dict, amount: int) -> dict:
    """Apply temp HP to a state dict using keep-higher policy."""
    previous = max(0, int(data.get("tempHP") or 0))
    final = max(previous, amount)
    return {**data, "tempHP": final}


async def cast_spell_out_of_combat_for_player(
    *,
    entry,
    session_id: str,
    req: OutOfCombatCastRequest,
    actor_user,
    caster_user_id: str,
    session: DbSession,
    cast_by_gm: bool,
    enforce_target_membership: bool = False,
    # --- Injected dependencies (issue #396): tests call this function directly and
    # pass fakes by keyword instead of patching `app.api.routes.sessions.state.X`.
    # Each kwarg reuses the exact name the body already calls, so the local
    # parameter shadows the module global with no body changes. Unset kwargs are
    # resolved from the module at call time (see below) so existing
    # `@patch("...state.X")` tests and the live endpoints keep working. ---
    ensure_session_state=_UNSET,
    finalize_session_state_data=_UNSET,
    publish_state_update=_UNSET,
    to_state_read=_UNSET,
    clear_concentration_group_across_session=_UNSET,
    clear_persisted_concentration_effects=_UNSET,
    build_ooc_warding_bond_effects=_UNSET,
    get_game_time_seconds=_UNSET,
    record_session_activity=_UNSET,
    _resolve_ooc_activity_actor=_UNSET,
    _resolve_ooc_activity_target_display_name=_UNSET,
    _prune_out_of_combat_session_activity=_UNSET,
) -> SessionStateRead:
    # Resolve any dependency left unset to the current module attribute, so that
    # callers who don't inject (live endpoints) and tests that still
    # `@patch("...state.X")` observe the patched value at call time.
    _mod = sys.modules[__name__]
    if ensure_session_state is _UNSET:
        ensure_session_state = _mod.ensure_session_state
    if finalize_session_state_data is _UNSET:
        finalize_session_state_data = _mod.finalize_session_state_data
    if publish_state_update is _UNSET:
        publish_state_update = _mod.publish_state_update
    if to_state_read is _UNSET:
        to_state_read = _mod.to_state_read
    if clear_concentration_group_across_session is _UNSET:
        clear_concentration_group_across_session = _mod.clear_concentration_group_across_session
    if clear_persisted_concentration_effects is _UNSET:
        clear_persisted_concentration_effects = _mod.clear_persisted_concentration_effects
    if build_ooc_warding_bond_effects is _UNSET:
        build_ooc_warding_bond_effects = _mod.build_ooc_warding_bond_effects
    if get_game_time_seconds is _UNSET:
        get_game_time_seconds = _mod.get_game_time_seconds
    if record_session_activity is _UNSET:
        record_session_activity = _mod.record_session_activity
    if _resolve_ooc_activity_actor is _UNSET:
        _resolve_ooc_activity_actor = _mod._resolve_ooc_activity_actor
    if _resolve_ooc_activity_target_display_name is _UNSET:
        _resolve_ooc_activity_target_display_name = _mod._resolve_ooc_activity_target_display_name
    if _prune_out_of_combat_session_activity is _UNSET:
        _prune_out_of_combat_session_activity = _mod._prune_out_of_combat_session_activity

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
    requested_spell_id = req.spellId.strip() if isinstance(req.spellId, str) and req.spellId.strip() else None
    requested_canonical_key = (
        req.canonicalKey.strip().lower()
        if isinstance(req.canonicalKey, str) and req.canonicalKey.strip()
        else None
    )
    if not requested_spell_id and not requested_canonical_key:
        raise HTTPException(status_code=400, detail="spellId or canonicalKey is required")

    player_spell_by_id = next(
        (
            s
            for s in player_spells
            if isinstance(s, dict)
            and requested_spell_id is not None
            and s.get("id") == requested_spell_id
        ),
        None,
    )
    if requested_spell_id is not None and player_spell_by_id is None:
        raise HTTPException(
            status_code=400,
            detail=f"Spell not found in character spell list: {requested_spell_id!r}",
        )

    player_spell_by_key = next(
        (
            s
            for s in player_spells
            if isinstance(s, dict)
            and requested_canonical_key is not None
            and isinstance(s.get("canonicalKey"), str)
            and s.get("canonicalKey", "").strip().lower() == requested_canonical_key
        ),
        None,
    )
    if requested_canonical_key is not None and player_spell_by_key is None:
        raise HTTPException(
            status_code=400,
            detail=f"Spell not found in character spell list by canonicalKey: {requested_canonical_key!r}",
        )

    if (
        requested_spell_id is not None
        and requested_canonical_key is not None
        and player_spell_by_id is not None
        and player_spell_by_key is not None
        and player_spell_by_id.get("id") != player_spell_by_key.get("id")
    ):
        raise HTTPException(
            status_code=400,
            detail="spellId and canonicalKey refer to different spells.",
        )

    player_spell = player_spell_by_id or player_spell_by_key
    if player_spell is None:
        raise HTTPException(status_code=400, detail="Spell not found in character spell list")

    canonical_key = player_spell.get("canonicalKey")
    if not canonical_key:
        raise HTTPException(status_code=400, detail="Spell entry is missing canonicalKey")
    canonical_key = str(canonical_key).strip().lower()

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

    weapon_item_id = (
        req.weapon_item_id.strip()
        if isinstance(req.weapon_item_id, str) and req.weapon_item_id.strip()
        else None
    )
    shillelagh_weapon_item = None
    shillelagh_weapon_catalog_item = None
    if canonical_key == "shillelagh":
        if is_ally_target:
            raise HTTPException(status_code=400, detail="Bordão Místico só pode afetar uma arma do próprio conjurador.")
        if not weapon_item_id:
            raise HTTPException(status_code=400, detail="Bordão Místico exige uma arma alvo.")
        caster_member = session.exec(
            select(CampaignMember).where(
                CampaignMember.campaign_id == entry.campaign_id,
                CampaignMember.user_id == caster_user_id,
            )
        ).first()
        if not caster_member:
            raise HTTPException(status_code=400, detail="Bordão Místico só pode afetar uma arma do próprio conjurador.")
        resolved_weapon = resolve_owned_inventory_item(
            session_entry=entry,
            member=caster_member,
            db=session,
            inventory_item_id=weapon_item_id,
            expected_type=ItemType.WEAPON,
        )
        if resolved_weapon is None:
            raise HTTPException(status_code=400, detail="Arma alvo não encontrada.")
        shillelagh_weapon_item, shillelagh_weapon_catalog_item = resolved_weapon
        if not getattr(shillelagh_weapon_item, "is_equipped", False):
            raise HTTPException(status_code=400, detail="Bordão Místico exige uma arma equipada/empunhada.")
        normalized_weapon_key = str(
            getattr(shillelagh_weapon_catalog_item, "canonical_key_snapshot", "") or ""
        ).strip().lower()
        if normalized_weapon_key not in _SHILLELAGH_ELIGIBLE_WEAPONS:
            raise HTTPException(status_code=400, detail="Bordão Místico só pode afetar porrete ou bordão.")

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

    try:
        validate_spell_material(
            session,
            session_id=session_id,
            caster_user_id=caster_user_id,
            spell=campaign_spell,
            consumable_material_key=req.consumable_material_key,
        )
    except SpellMaterialError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

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
    replaced_shillelagh = False
    replaced_jump = False
    replaced_spider_climb = False
    replaced_barkskin = False
    updated_target_json: dict | None = None
    if canonical_key == "shillelagh":
        existing_effects = list(updated_caster_json.get("active_spell_effects") or [])
        filtered_effects = []
        for effect in existing_effects:
            metadata = effect.get("metadata") if isinstance(effect, dict) else None
            if isinstance(metadata, dict) and str(metadata.get("source_spell_key") or "").strip().lower() == "shillelagh":
                replaced_shillelagh = True
                continue
            filtered_effects.append(effect)
        if filtered_effects:
            updated_caster_json["active_spell_effects"] = filtered_effects
        else:
            updated_caster_json.pop("active_spell_effects", None)
    elif canonical_key == "jump":
        base_target_json = (
            dict(target_state.state_json or {})
            if is_ally_target and target_state is not None
            else dict(updated_caster_json)
        )
        existing_effects = list(base_target_json.get("active_spell_effects") or [])
        filtered_effects = []
        for effect in existing_effects:
            metadata = effect.get("metadata") if isinstance(effect, dict) else None
            if isinstance(metadata, dict) and str(metadata.get("source_spell_key") or "").strip().lower() == "jump":
                replaced_jump = True
                continue
            filtered_effects.append(effect)
        if filtered_effects:
            base_target_json["active_spell_effects"] = filtered_effects
        else:
            base_target_json.pop("active_spell_effects", None)
        updated_target_json = base_target_json
    elif canonical_key == "spider_climb":
        base_target_json = (
            dict(target_state.state_json or {})
            if is_ally_target and target_state is not None
            else dict(updated_caster_json)
        )
        existing_effects = list(base_target_json.get("active_spell_effects") or [])
        filtered_effects = []
        for effect in existing_effects:
            metadata = effect.get("metadata") if isinstance(effect, dict) else None
            if isinstance(metadata, dict) and str(metadata.get("source_spell_key") or "").strip().lower() == "spider_climb":
                replaced_spider_climb = True
                continue
            filtered_effects.append(effect)
        if filtered_effects:
            base_target_json["active_spell_effects"] = filtered_effects
        else:
            base_target_json.pop("active_spell_effects", None)
        updated_target_json = base_target_json
    elif canonical_key == "barkskin":
        base_target_json = (
            dict(target_state.state_json or {})
            if is_ally_target and target_state is not None
            else dict(updated_caster_json)
        )
        existing_effects = list(base_target_json.get("active_spell_effects") or [])
        filtered_effects = []
        for effect in existing_effects:
            metadata = effect.get("metadata") if isinstance(effect, dict) else None
            if isinstance(metadata, dict) and str(metadata.get("source_spell_key") or "").strip().lower() == "barkskin":
                replaced_barkskin = True
                continue
            filtered_effects.append(effect)
        if filtered_effects:
            base_target_json["active_spell_effects"] = filtered_effects
        else:
            base_target_json.pop("active_spell_effects", None)
        updated_target_json = base_target_json

    if spell_level > 0 and req.slotLevel is not None:
        try:
            updated_caster_json = consume_spell_slot(updated_caster_json, req.slotLevel)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        material_result = consume_spell_material(
            session,
            session_id=session_id,
            caster_user_id=caster_user_id,
            spell=campaign_spell,
            consumable_material_key=req.consumable_material_key,
        )
    except SpellMaterialError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    affected_allies: list[SessionState] = []
    if campaign_spell.concentration:
        updated_caster_json = clear_persisted_concentration_effects(updated_caster_json)
        if old_group:
            affected_allies = clear_concentration_group_across_session(
                session, session_id, old_group, exclude_user_id=caster_user_id
            )

    current_game_time_seconds = get_game_time_seconds(session_id, session)

    # --- Warding Bond: two linked effects across caster and target (OOC) ---
    if canonical_key == "warding_bond":
        if not is_ally_target or target_state is None:
            raise HTTPException(
                status_code=400,
                detail="Vínculo de Proteção deve ser conjurado em outra criatura voluntária.",
            )

        # Recast: end any prior bond involving the caster or the target across the
        # whole session — the other end of a prior bond may be a third creature.
        # This stages removals on every store; the caster/target stores are then
        # fully rebuilt below (with the slot already consumed) and override it.
        clear_warding_bonds_across_session(
            session, session_id, [caster_user_id, target_user_id]
        )

        def _strip_warding_bond(effects: list | None) -> list:
            return [
                e
                for e in (effects or [])
                if not (
                    isinstance(e, dict)
                    and str(((e.get("metadata") or {}).get("source_spell_key")) or "").strip().lower()
                    == "warding_bond"
                )
            ]

        # updated_caster_json already has the spell slot consumed.
        wb_caster_json = dict(updated_caster_json)
        wb_target_json = dict(target_state.state_json or {})

        wb_target_effect, wb_caster_effect = build_ooc_warding_bond_effects(
            spell=campaign_spell,
            caster_user_id=caster_user_id,
            target_user_id=target_user_id,
            game_time_seconds=current_game_time_seconds,
        )

        wb_target_effects = _strip_warding_bond(wb_target_json.get("active_spell_effects"))
        wb_target_effects.append(wb_target_effect)
        wb_target_json["active_spell_effects"] = wb_target_effects
        target_state.state_json = finalize_session_state_data(
            wb_target_json, game_time_seconds=current_game_time_seconds
        )
        flag_modified(target_state, "state_json")
        session.add(target_state)

        wb_caster_effects = _strip_warding_bond(wb_caster_json.get("active_spell_effects"))
        wb_caster_effects.append(wb_caster_effect)
        wb_caster_json["active_spell_effects"] = wb_caster_effects
        caster_state.state_json = finalize_session_state_data(
            wb_caster_json, game_time_seconds=current_game_time_seconds
        )
        flag_modified(caster_state, "state_json")
        session.add(caster_state)

        spell_name = campaign_spell.name_pt or campaign_spell.name_en or campaign_spell.canonical_key
        actor_member_id, actor_display_name = _resolve_ooc_activity_actor(entry, actor_user, session)
        if actor_member_id:
            record_session_activity(
                entry,
                "out_of_combat_spell_cast",
                session,
                member_id=actor_member_id,
                user_id=actor_user.id,
                actor_name=actor_display_name,
                payload={
                    "actor_user_id": actor_user.id,
                    "actor_player_user_id": actor_user.id,
                    "actor_display_name": actor_display_name,
                    "caster_player_user_id": caster_user_id,
                    "target_player_user_id": target_user_id,
                    "spell_key": "warding_bond",
                    "spell_name": spell_name,
                    "variant_key": None,
                    "variant_label": None,
                    "created_effect_ids": [
                        eid
                        for eid in (wb_target_effect.get("id"), wb_caster_effect.get("id"))
                        if isinstance(eid, str) and eid
                    ],
                    "concentration_group": None,
                    "replaced_concentration": False,
                    "previous_concentration_group": None,
                    "new_concentration_group": None,
                    "previous_spell_name": None,
                    "previous_variant_label": None,
                    "cast_by_gm": cast_by_gm,
                    "bond_group": (wb_target_effect.get("metadata") or {}).get("bond_group"),
                },
            )
            _prune_out_of_combat_session_activity(session, session_id)

        session.commit()
        session.refresh(caster_state)
        session.refresh(target_state)

        states_to_publish: dict[str, SessionState] = {
            caster_user_id: caster_state,
            target_user_id: target_state,
        }
        for player_id, publish_state in states_to_publish.items():
            await publish_state_update(
                entry,
                player_id,
                publish_state.updated_at or publish_state.created_at,
                publish_state.state_json if isinstance(publish_state.state_json, dict) else None,
            )

        return to_state_read(caster_state)

    # --- Build target effects ---
    caster_spell_save_dc = int(
        (state_json.get("spellcasting") or {}).get("saveDc") or 0
    )
    try:
        new_target_effects = build_persisted_effects(
            spell=campaign_spell,
            caster_user_id=caster_user_id,
            target_user_id=target_user_id,
            variant_key=req.variantKey,
            game_time_seconds=current_game_time_seconds,
            weapon_item_id=weapon_item_id,
            weapon_canonical_key=(
                getattr(shillelagh_weapon_catalog_item, "canonical_key_snapshot", None)
                if shillelagh_weapon_catalog_item is not None
                else None
            ),
            weapon_name=(
                getattr(shillelagh_weapon_catalog_item, "name", None)
                if shillelagh_weapon_catalog_item is not None
                else None
            ),
            spell_save_dc=caster_spell_save_dc if caster_spell_save_dc > 0 else None,
            slot_level=req.slotLevel,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

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
            consumable_canonical_key = params.get("canonical_key")
            raw_qty = params.get("quantity", 1)
            quantity = raw_qty if isinstance(raw_qty, int) else 1
            expires_in_seconds = params.get("expires_in_seconds")
            if not consumable_canonical_key:
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
                canonical_key=consumable_canonical_key,
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

    # --- Precompute temporary HP (grant_temp_hp effects) ---
    temp_hp_effects = collect_temp_hp_effects(campaign_spell, req.variantKey)
    temp_hp_rolled = (
        roll_spell_temp_hp_effects(temp_hp_effects, campaign_spell, req.slotLevel)
        if temp_hp_effects
        else []
    )

    # --- Spare the Dying: stabilize target at 0 HP (OOC) ---
    if canonical_key == "spare_the_dying":
        if is_ally_target and target_state is not None:
            std_target_json = target_state.state_json if isinstance(target_state.state_json, dict) else {}
        else:
            std_target_json = updated_caster_json

        std_current_hp = _safe_int(std_target_json.get("currentHP"), 0)
        if std_current_hp > 0:
            raise HTTPException(status_code=400, detail="Poupar os Moribundos só pode afetar criaturas com 0 HP.")

        std_death_saves = std_target_json.get("deathSaves")
        if not isinstance(std_death_saves, dict):
            std_death_saves = {"successes": 0, "failures": 0}
        std_failures = _safe_int(std_death_saves.get("failures"), 0)
        if std_failures >= 3:
            raise HTTPException(status_code=400, detail="Poupar os Moribundos não afeta criaturas mortas.")

        std_target_json = dict(std_target_json)
        std_target_json["deathSaves"] = {"successes": 3, "failures": 0}

        if is_ally_target and target_state is not None:
            target_state.state_json = finalize_session_state_data(
                std_target_json,
                game_time_seconds=current_game_time_seconds,
            )
            flag_modified(target_state, "state_json")
            session.add(target_state)
        else:
            updated_caster_json = std_target_json
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
            record_session_activity(
                entry,
                "out_of_combat_spell_cast",
                session,
                member_id=actor_member_id,
                user_id=actor_user.id,
                actor_name=actor_display_name,
                payload={
                    "actor_user_id": actor_user.id,
                    "actor_player_user_id": actor_user.id,
                    "actor_display_name": actor_display_name,
                    "caster_player_user_id": caster_user_id,
                    "caster_display_name": (
                        actor_display_name if caster_user_id == actor_user.id else caster_user_id
                    ),
                    "target_player_user_id": target_user_id,
                    "target_display_name": (
                        actor_display_name if target_user_id == actor_user.id else target_user_id
                    ),
                    "spell_key": "spare_the_dying",
                    "spell_name": spell_name,
                    "variant_key": None,
                    "variant_label": None,
                    "created_effect_ids": [],
                    "concentration_group": None,
                    "replaced_concentration": False,
                    "previous_concentration_group": None,
                    "new_concentration_group": None,
                    "previous_spell_name": None,
                    "previous_variant_label": None,
                    "cast_by_gm": cast_by_gm,
                    "spare_the_dying_stabilized": True,
                },
            )
            _prune_out_of_combat_session_activity(session, session_id)

        session.commit()
        session.refresh(caster_state)
        if is_ally_target and target_state is not None:
            session.refresh(target_state)

        states_to_publish: dict[str, SessionState] = {caster_user_id: caster_state}
        if is_ally_target and target_state is not None:
            states_to_publish[target_user_id] = target_state

        for player_id, publish_state in states_to_publish.items():
            await publish_state_update(
                entry,
                player_id,
                publish_state.updated_at or publish_state.created_at,
                publish_state.state_json if isinstance(publish_state.state_json, dict) else None,
            )

        return to_state_read(caster_state)

    # --- Lesser Restoration: remove a condition/disease (OOC) ---
    if canonical_key == "lesser_restoration":
        from app.services.combat_service.condition_effects_predicates import LESSER_RESTORATION_CONDITIONS

        lr_variant_key = str(req.variantKey or "").strip().lower()
        if not lr_variant_key:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Especifique o que remover via variantKey "
                    "(ex: 'poisoned', 'blinded', 'deafened', 'paralyzed', 'disease')."
                ),
            )
        if lr_variant_key not in LESSER_RESTORATION_CONDITIONS and lr_variant_key != "disease":
            raise HTTPException(
                status_code=400,
                detail=f"lesser_restoration não pode remover '{lr_variant_key}'.",
            )

        lr_target_json: dict = (
            dict(target_state.state_json or {})
            if is_ally_target and target_state is not None
            else dict(updated_caster_json)
        )
        lr_active = lr_target_json.get("active_spell_effects") or []

        if lr_variant_key == "disease":
            def _lr_is_removable_disease(e: dict) -> bool:
                if e.get("kind") != "condition":
                    return False
                meta = e.get("metadata") or {}
                return meta.get("removable_by_lesser_restoration") is True or meta.get("disease") is True
            lr_matching = [e for e in lr_active if _lr_is_removable_disease(e)]
        else:
            lr_matching = [
                e for e in lr_active
                if e.get("kind") == "condition" and e.get("condition_type") == lr_variant_key
            ]

        if not lr_matching:
            raise HTTPException(
                status_code=400,
                detail=f"Alvo não possui a condição '{lr_variant_key}' para ser removida.",
            )

        lr_matching_ids = {id(e) for e in lr_matching}
        lr_target_json["active_spell_effects"] = [e for e in lr_active if id(e) not in lr_matching_ids]

        spell_name = campaign_spell.name_pt or campaign_spell.name_en or campaign_spell.canonical_key

        if is_ally_target and target_state is not None:
            target_state.state_json = finalize_session_state_data(
                lr_target_json,
                game_time_seconds=current_game_time_seconds,
            )
            flag_modified(target_state, "state_json")
            session.add(target_state)
        else:
            updated_caster_json = lr_target_json
            caster_state.state_json = finalize_session_state_data(
                updated_caster_json,
                game_time_seconds=current_game_time_seconds,
            )
            flag_modified(caster_state, "state_json")
            session.add(caster_state)

        actor_member_id, actor_display_name = _resolve_ooc_activity_actor(entry, actor_user, session)
        if actor_member_id:
            record_session_activity(
                entry,
                "out_of_combat_spell_cast",
                session,
                member_id=actor_member_id,
                user_id=actor_user.id,
                actor_name=actor_display_name,
                payload={
                    "actor_user_id": actor_user.id,
                    "actor_player_user_id": actor_user.id,
                    "actor_display_name": actor_display_name,
                    "caster_player_user_id": caster_user_id,
                    "target_player_user_id": target_user_id,
                    "spell_key": "lesser_restoration",
                    "spell_name": spell_name,
                    "variant_key": lr_variant_key,
                    "removed_condition": lr_variant_key,
                    "cast_by_gm": cast_by_gm,
                },
            )
            _prune_out_of_combat_session_activity(session, session_id)

        session.commit()
        session.refresh(caster_state)
        if is_ally_target and target_state is not None:
            session.refresh(target_state)

        states_to_publish: dict[str, SessionState] = {caster_user_id: caster_state}
        if is_ally_target and target_state is not None:
            states_to_publish[target_user_id] = target_state

        for player_id, publish_state in states_to_publish.items():
            await publish_state_update(
                entry,
                player_id,
                publish_state.updated_at or publish_state.created_at,
                publish_state.state_json if isinstance(publish_state.state_json, dict) else None,
            )

        return to_state_read(caster_state)

    if not new_target_effects and not consumables_granted_count and not heal_rolled and not temp_hp_rolled:
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
        target_json = (
            dict(updated_target_json)
            if isinstance(updated_target_json, dict)
            else dict(target_state.state_json or {})
        )  # type: ignore[union-attr]
        target_effects = list(target_json.get("active_spell_effects") or [])
        target_effects.extend(new_target_effects)
        target_json["active_spell_effects"] = target_effects
        # Immediate healing on ally target
        for hr in heal_rolled:
            if hr.get("target") == "caster":
                updated_caster_json = _apply_heal_to_state_dict(updated_caster_json, hr["amount"])
            else:
                target_json = _apply_heal_to_state_dict(target_json, hr["amount"])
        for thr in temp_hp_rolled:
            updated_caster_json = _apply_temp_hp_to_state_dict(updated_caster_json, thr["amount"])
        target_state.state_json = finalize_session_state_data(  # type: ignore[union-attr]
            target_json,
            game_time_seconds=current_game_time_seconds,
        )
        flag_modified(target_state, "state_json")
        session.add(target_state)
    else:
        # Self-target: original behaviour unchanged
        existing_effects = list(
            (updated_target_json if isinstance(updated_target_json, dict) else updated_caster_json).get("active_spell_effects") or []
        )
        existing_effects.extend(new_target_effects)
        updated_caster_json["active_spell_effects"] = existing_effects
        marker_effect_id = None
        # Immediate healing on self (target == caster)
        for hr in heal_rolled:
            updated_caster_json = _apply_heal_to_state_dict(updated_caster_json, hr["amount"])
        for thr in temp_hp_rolled:
            updated_caster_json = _apply_temp_hp_to_state_dict(updated_caster_json, thr["amount"])

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
        if material_result.required:
            activity_payload["material_consumed"] = material_result.consumed
            activity_payload["material_key"] = material_result.material_key
            activity_payload["material_label"] = material_result.material_label
            activity_payload["material_quantity"] = material_result.quantity
            activity_payload["material_inventory_item_id"] = material_result.inventory_item_id
            activity_payload["inventory_refresh_required"] = True
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
        if temp_hp_rolled:
            total_temp_hp = sum(thr["amount"] for thr in temp_hp_rolled)
            activity_payload["temp_hp_applied"] = total_temp_hp
            activity_payload["temp_hp_rolls"] = [
                {"base_dice": thr["base_dice"], "upcast_bonus": thr["upcast_bonus"], "total": thr["amount"]}
                for thr in temp_hp_rolled
            ]
        if canonical_key == "shillelagh":
            activity_payload["replaced_shillelagh"] = replaced_shillelagh
            activity_payload["weapon_item_id"] = weapon_item_id
            activity_payload["weapon_canonical_key"] = (
                getattr(shillelagh_weapon_catalog_item, "canonical_key_snapshot", None)
                if shillelagh_weapon_catalog_item is not None
                else None
            )
            activity_payload["weapon_name"] = (
                getattr(shillelagh_weapon_catalog_item, "name", None)
                if shillelagh_weapon_catalog_item is not None
                else None
            )
        if canonical_key == "jump":
            activity_payload["replaced_jump"] = replaced_jump
            activity_payload["jump_distance_multiplier"] = 3
            activity_payload["duration_seconds"] = 60
        if canonical_key == "spider_climb":
            activity_payload["replaced_spider_climb"] = replaced_spider_climb
            activity_payload["movement_mode"] = "spider_climb"
            activity_payload["duration_seconds"] = 3600
        if canonical_key == "barkskin":
            activity_payload["replaced_barkskin"] = replaced_barkskin
            activity_payload["armor_class_floor"] = 16
            activity_payload["duration_seconds"] = 3600
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
