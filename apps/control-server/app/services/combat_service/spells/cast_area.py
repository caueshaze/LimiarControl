from __future__ import annotations

from datetime import datetime, timezone
import random
from math import floor
from typing import Any
from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select

from app.core.config import settings
from app.integrations import LimiarMapClient, LimiarMapClientError
from app.models.base_item import BaseItemKind, BaseItemWeaponRangeType
from app.models.campaign import Campaign, SystemType
from app.models.campaign_member import CampaignMember
from app.models.combat import CombatPhase, CombatState
from app.models.session import Session as CampaignSession
from app.models.session_entity import SessionEntity
from app.models.session_state import SessionState
from app.models.campaign_entity import CampaignEntity
from app.models.inventory import InventoryItem
from app.models.item import Item, ItemType
from app.schemas.combat import (
    CombatApplyDamageRequest,
    CombatApplyHealingRequest,
    CombatAreaPreviewRequest,
    CombatAttackRequest,
    CombatCastSpellRequest,
    CombatEntityActionRequest,
    CombatMapPreviewState,
    CombatResolveDamageRequest,
    CombatResolveSpellEffectRequest,
    CombatSetInitiativeRequest,
    CombatStartRequest,
)
from app.schemas.campaign_entity import (
    SKILL_ABILITY_MAP,
    CombatAction,
    ability_modifier as derive_ability_modifier,
    resolve_initiative_bonus as resolve_entity_initiative_bonus,
    resolve_saving_throw_bonus as resolve_entity_saving_throw_bonus,
    resolve_skill_bonus as resolve_entity_skill_bonus,
)
from app.services.base_items import get_base_item_by_canonical_key
from app.services.base_spells import get_base_spell_by_canonical_key
from app.services.centrifugo import centrifugo
from app.services.draconic_ancestry import resolve_elemental_affinity
from app.services.magic_item_effects import (
    consume_inventory_item_charge,
    get_magic_item_effect,
    get_inventory_item_charges_current,
    get_magic_item_spell_key,
)
from app.services.realtime import build_event, campaign_channel, event_version, session_channel
from app.services.session_state_finalize import finalize_session_state_data
from app.services.roll_resolution import resolve_attack_base, resolve_saving_throw
from app.schemas.roll import RollActorStats, RollResult

from ..combat_targeting import get_combat_targeting_service
from ..exceptions import CombatServiceError, _parse_dice
from ..targeting_requirements import (
    resolve_spell_targeting_requirements,
    resolve_weapon_targeting_requirements,
)
from ..targeting_intent import AreaTargetingIntent, SpellCastIntent, WeaponAttackIntent
from ..unit_conversion import meters_to_cells



class CastAreaMixin:
    @classmethod
    async def _cast_area_spell(
        cls,
        db: Session,
        session_id: str,
        req: CombatCastSpellRequest,
        *,
        attacker: dict,
        attacker_model: SessionState,
        actor_user_id: str,
        is_gm: bool,
        state: CombatState,
        spell_context: dict[str, Any],
        area_spec: dict[str, int | str],
    ) -> dict[str, Any]:
        targeting_intent = AreaTargetingIntent(
            session_id=session_id,
            action_id=f"targeting:{uuid4()}",
            actor_ref_id=attacker["ref_id"],
            actor_kind=attacker["kind"],
            requested_target_ref_id=req.target_ref_id,
            spell_canonical_key=spell_context["spell_canonical_key"],
            spell_mode=spell_context["spell_mode"],
            shape=str(area_spec["shape"]),
            size_meters=cls._safe_int(area_spec.get("size_meters"), 0),
            range_meters=cls._safe_optional_int(area_spec.get("range_meters")),
            target_mode=spell_context.get("target_mode"),
            origin_cell=req.origin_cell.model_dump() if req.origin_cell is not None else None,
            anchor_cell=req.anchor_cell.model_dump() if req.anchor_cell is not None else None,
            requires_sight=bool(spell_context.get("requires_point_sight")),
            requires_effect=bool(spell_context.get("requires_point_effect")),
        )
        targeting_result = get_combat_targeting_service().validate(targeting_intent, state)
        if not targeting_result.is_valid:
            raise CombatServiceError(
                targeting_result.failure_reason or "Area targeting could not be resolved.",
                400,
            )

        anchor_target = next(
            (p for p in state.participants if p["ref_id"] == req.target_ref_id),
            None,
        ) if isinstance(req.target_ref_id, str) else None

        if spell_context["spell_mode"] != "saving_throw" or spell_context["effect_kind"] != "damage":
            raise CombatServiceError(
                "This area spell flow currently supports only saving throw damage spells.",
                400,
            )

        action_cost = spell_context.get("action_cost") or "action"
        was_overridden = cls._consume_turn_resource(
            attacker,
            action_cost,
            is_gm=is_gm,
            override_resource_limit=req.override_resource_limit,
        )

        slot_spent = False
        if spell_context.get("source_kind") == "magic_item":
            inventory_item = spell_context.get("inventory_item")
            source_item = spell_context.get("source_item")
            if not isinstance(inventory_item, InventoryItem):
                raise CombatServiceError("Magic item inventory entry is missing.", 400)
            try:
                consume_inventory_item_charge(inventory_item, source_item)
            except ValueError as exc:
                raise CombatServiceError(str(exc), 400) from exc
            db.add(inventory_item)
        elif isinstance(spell_context.get("slot_level"), int):
            cls._consume_player_spell_slot(attacker_model, spell_context["slot_level"])
            db.add(attacker_model)
            slot_spent = True

        affected_participants = [
            participant
            for participant in state.participants
            if participant["ref_id"] in targeting_result.affected_target_ref_ids
        ]
        for target_participant in affected_participants:
            cls._assert_hostile_action_allowed(
                attacker,
                target_participant,
                action_label="a hostile spell",
            )
            cls._validate_spell_automation_target(
                db,
                session_id,
                spell_canonical_key=spell_context["spell_canonical_key"],
                target_participant=target_participant,
            )
        area_target_outcomes: list[dict[str, Any]] = []
        target_results_for_pending: list[dict[str, Any]] = []
        for target_participant in affected_participants:
            roll_result = resolve_saving_throw(
                cls._build_roll_actor_stats_for_save(
                    db,
                    session_id,
                    target_participant["ref_id"],
                    target_participant["kind"],
                    target_participant["display_name"],
                ),
                ability=spell_context["save_ability"],
                dc=cls._safe_int(spell_context.get("save_dc"), 0),
            )
            roll_result.is_gm_roll = is_gm
            is_saved = bool(roll_result.success)
            outcome = {
                "target_ref_id": target_participant["ref_id"],
                "target_display_name": target_participant["display_name"],
                "target_kind": target_participant["kind"],
                "is_saved": is_saved,
                "roll": roll_result.total,
                "roll_result": roll_result,
                "damage_applied": None,
                "healing_applied": None,
                "new_hp": None,
            }
            area_target_outcomes.append(outcome)
            target_results_for_pending.append(
                {
                    "target_ref_id": target_participant["ref_id"],
                    "target_kind": target_participant["kind"],
                    "target_display_name": target_participant["display_name"],
                    "is_saved": is_saved,
                    "roll": roll_result.total,
                    "roll_result": roll_result.model_dump(mode="json"),
                }
            )

        primary_result_target = (
            anchor_target
            or (affected_participants[0] if affected_participants else None)
        )
        primary_target_ref_id = (
            primary_result_target["ref_id"]
            if primary_result_target is not None
            else req.target_ref_id
        )
        primary_target_kind = (
            primary_result_target["kind"]
            if primary_result_target is not None
            else "session_entity"
        )
        primary_target_display_name = (
            primary_result_target["display_name"]
            if primary_result_target is not None
            else "Area target"
        )

        pending_spell_id = cls._create_pending_spell_effect(
            state,
            attacker,
            {
                "spell_name": spell_context["spell_name"],
                "spell_canonical_key": spell_context["spell_canonical_key"],
                "action_kind": spell_context["spell_mode"],
                "effect_kind": spell_context["effect_kind"],
                "effect_dice": spell_context["effect_dice"],
                "effect_bonus": cls._safe_int(spell_context.get("effect_bonus"), 0),
                "damage_type": spell_context.get("damage_type"),
                "elemental_affinity_eligible": spell_context.get("elemental_affinity_eligible"),
                "elemental_affinity_damage_type": spell_context.get("elemental_affinity_damage_type"),
                "elemental_affinity_bonus": spell_context.get("elemental_affinity_bonus"),
                "target_ref_id": primary_target_ref_id,
                "target_kind": primary_target_kind,
                "target_display_name": primary_target_display_name,
                "save_ability": spell_context.get("save_ability"),
                "save_dc": spell_context.get("save_dc"),
                "save_success_outcome": spell_context.get("save_success_outcome"),
                "is_saved": False,
                "is_critical": False,
                "roll": None,
                "roll_result": None,
                "area_shape": area_spec["shape"],
                "affected_cells": list(targeting_result.spatial_metadata.affected_cells),
                "affected_target_ref_ids": list(targeting_result.affected_target_ref_ids),
                "affected_token_ids": list(targeting_result.spatial_metadata.affected_token_ids),
                "area_targets": target_results_for_pending,
            },
        )

        db.add(state)
        db.commit()
        db.refresh(state)

        if slot_spent:
            target_state, *_ = cls._get_stats(db, attacker["ref_id"], "player", session_id)
            await cls._emit_player_state_update(db, session_id, attacker["ref_id"], target_state)
        await cls._emit_state(session_id, state)

        target_count = len(area_target_outcomes)
        area_label = f"Area ({target_count} alvo{'s' if target_count != 1 else ''})"
        log_message = (
            f"{attacker['display_name']} lancou {spell_context['spell_name']} em area "
            f"({area_spec['shape']}): {target_count} alvo{'s' if target_count != 1 else ''} afetado{'s' if target_count != 1 else ''}. "
            "Efeito pendente."
        )
        if was_overridden:
            log_message = f"[OVERRIDE: Limit for '{action_cost}' ignored] {log_message}"

        await cls._emit_log(session_id, {
            "message": log_message,
            "actorUserId": actor_user_id,
            "source": "gm_override" if is_gm else "player_turn",
            "is_override": was_overridden,
            "overridden_resource": action_cost if was_overridden else None,
        })

        return {
            "spell_name": spell_context["spell_name"],
            "spell_canonical_key": spell_context["spell_canonical_key"],
            "action_kind": spell_context["spell_mode"],
            "effect_kind": spell_context["effect_kind"],
            "damage": 0,
            "healing": 0,
            "damage_type": spell_context.get("damage_type"),
            "is_critical": False,
            "is_hit": None,
            "is_saved": None,
            "new_hp": None,
            "roll": None,
            "roll_result": None,
            "target_ac": None,
            "target_display_name": area_label,
            "target_kind": primary_target_kind,
            "save_ability": spell_context.get("save_ability"),
            "save_dc": spell_context.get("save_dc"),
            "save_success_outcome": spell_context.get("save_success_outcome"),
            "effect_dice": spell_context.get("effect_dice"),
            "effect_bonus": cls._safe_int(spell_context.get("effect_bonus"), 0),
            "pending_spell_id": pending_spell_id,
            "effect_roll_required": True,
            "base_effect": None,
            "action_cost": action_cost,
            "summary_text": None,
            "inventory_refresh_required": spell_context.get("source_kind") == "magic_item",
            "concentration_check": None,
            "concentration_checks": [],
            "area_shape": area_spec["shape"],
            "affected_target_ref_ids": list(targeting_result.affected_target_ref_ids),
            "affected_cells": list(targeting_result.spatial_metadata.affected_cells),
            "area_target_outcomes": area_target_outcomes,
            "target_count": target_count,
            "elemental_affinity_eligible": bool(spell_context.get("elemental_affinity_eligible")),
            "elemental_affinity_damage_type": spell_context.get("elemental_affinity_damage_type"),
            "elemental_affinity_bonus": spell_context.get("elemental_affinity_bonus"),
        }

    @classmethod
    async def _cast_area_spell_effect(
        cls,
        db: Session,
        session_id: str,
        req: CombatResolveSpellEffectRequest,
        *,
        attacker: dict,
        pending_spell: dict[str, Any],
        effect_kind: str,
        effect_dice: Any,
        effect_bonus: int,
        actor_user_id: str,
        is_gm: bool,
        state: CombatState,
    ) -> dict[str, Any]:
        area_targets_payload = pending_spell.get("area_targets")
        if not isinstance(area_targets_payload, list) or not area_targets_payload:
            raise CombatServiceError("Pending area spell effect is missing target information.", 400)

        effect_rolls: list[int] = []
        base_effect = 0
        if isinstance(effect_dice, str) and effect_dice.strip():
            effect_rolls, base_effect = cls._resolve_damage_roll(
                effect_dice,
                critical=bool(pending_spell.get("is_critical")) and effect_kind == "damage",
                roll_source=req.roll_source,
                manual_rolls=req.manual_rolls,
            )
        rolled_effect_total = max(0, base_effect + effect_bonus)
        save_success_outcome = cls._normalize_save_success_outcome(
            pending_spell.get("save_success_outcome")
        )

        total_damage = 0
        total_healing = 0
        concentration_checks: list[dict[str, Any]] = []
        player_state_ids_to_emit: set[str] = set()
        entity_hp_updates: list[tuple[str, int | None]] = []
        area_target_outcomes: list[dict[str, Any]] = []

        for raw_target in area_targets_payload:
            if not isinstance(raw_target, dict):
                continue
            target_ref_id = raw_target.get("target_ref_id")
            target_kind = raw_target.get("target_kind")
            target_display_name = raw_target.get("target_display_name") or "Target"
            if not isinstance(target_ref_id, str) or not isinstance(target_kind, str):
                continue
            is_saved = bool(raw_target.get("is_saved"))
            amount = (
                cls._resolve_save_damage_amount(
                    rolled_effect_total,
                    is_saved=is_saved,
                    save_success_outcome=save_success_outcome,
                )
                if pending_spell.get("action_kind") == "saving_throw" and effect_kind == "damage"
                else rolled_effect_total
            )

            new_hp = None
            previous_hp = None
            concentration_check = None
            if amount > 0:
                new_hp, _, previous_hp, concentration_check = cls._apply_spell_effect(
                    db,
                    state,
                    target_ref_id,
                    target_kind,
                    effect_kind,
                    amount,
                    damage_type=pending_spell.get("damage_type"),
                    is_critical=bool(pending_spell.get("is_critical")),
                    concentration_roll_source=req.concentration_roll_source,
                    concentration_manual_roll=req.concentration_manual_roll,
                )
                if effect_kind == "healing":
                    total_healing += amount
                else:
                    total_damage += amount
                if target_kind == "player":
                    player_state_ids_to_emit.add(target_ref_id)
                elif target_kind == "session_entity" and previous_hp != new_hp:
                    entity_hp_updates.append((target_ref_id, previous_hp))
                if isinstance(concentration_check, dict):
                    concentration_checks.append(concentration_check)

            raw_roll_result = raw_target.get("roll_result")
            roll_result = (
                RollResult.model_validate(raw_roll_result)
                if isinstance(raw_roll_result, dict)
                else None
            )
            area_target_outcomes.append(
                {
                    "target_ref_id": target_ref_id,
                    "target_display_name": target_display_name,
                    "target_kind": target_kind,
                    "is_saved": is_saved,
                    "roll": cls._safe_optional_int(raw_target.get("roll")),
                    "roll_result": roll_result,
                    "damage_applied": amount if effect_kind != "healing" else None,
                    "healing_applied": amount if effect_kind == "healing" else None,
                    "new_hp": new_hp,
                }
            )

        cls._clear_participant_pending_attack(attacker)
        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)

        for player_ref_id in player_state_ids_to_emit:
            target_state, *_ = cls._get_stats(db, player_ref_id, "player", session_id)
            await cls._emit_player_state_update(db, session_id, player_ref_id, target_state)
        for entity_ref_id, previous_hp in entity_hp_updates:
            await cls._emit_entity_hp_update(db, session_id, entity_ref_id, previous_hp)
        await cls._emit_state(session_id, state)

        target_count = len(area_target_outcomes)
        saved_count = sum(1 for outcome in area_target_outcomes if outcome.get("is_saved"))
        failed_count = target_count - saved_count
        log_text = (
            f"{attacker['display_name']} resolveu {pending_spell.get('spell_name') or 'magia'} em area: "
            f"{target_count} alvo{'s' if target_count != 1 else ''}, "
            f"{failed_count} falhou/falharam no save, {saved_count} passou/passaram. "
            f"Dano rolado {rolled_effect_total}; dano total aplicado {total_damage}."
        )
        if concentration_checks:
            summaries = [
                check.get("summary_text")
                for check in concentration_checks
                if isinstance(check.get("summary_text"), str)
            ]
            if summaries:
                log_text = f"{log_text} {' '.join(summaries)}".strip()

        await cls._emit_log(session_id, {
            "message": log_text,
            "actorUserId": actor_user_id,
            "source": "gm_override" if is_gm else "player_turn",
        })

        primary_concentration_check = concentration_checks[0] if concentration_checks else None
        target_display_name = f"Area ({target_count} alvo{'s' if target_count != 1 else ''})"
        return {
            "spell_name": pending_spell.get("spell_name") or "Spell",
            "spell_canonical_key": pending_spell.get("spell_canonical_key"),
            "action_kind": pending_spell.get("action_kind") or "direct_damage",
            "effect_kind": effect_kind,
            "damage": total_damage if effect_kind != "healing" else 0,
            "healing": total_healing if effect_kind == "healing" else 0,
            "damage_type": pending_spell.get("damage_type"),
            "is_critical": bool(pending_spell.get("is_critical")),
            "is_hit": None,
            "is_saved": None,
            "new_hp": None,
            "roll": None,
            "roll_result": None,
            "target_ac": None,
            "target_display_name": target_display_name,
            "target_kind": pending_spell.get("target_kind") or "session_entity",
            "save_ability": pending_spell.get("save_ability"),
            "save_dc": cls._safe_optional_int(pending_spell.get("save_dc")),
            "save_success_outcome": save_success_outcome,
            "effect_dice": effect_dice,
            "effect_bonus": effect_bonus,
            "pending_spell_id": None,
            "effect_roll_required": False,
            "effect_rolls": effect_rolls,
            "base_effect": base_effect,
            "effect_roll_source": req.roll_source,
            "concentration_check": primary_concentration_check,
            "concentration_checks": concentration_checks,
            "area_shape": pending_spell.get("area_shape"),
            "affected_target_ref_ids": list(pending_spell.get("affected_target_ref_ids") or []),
            "affected_cells": list(pending_spell.get("affected_cells") or []),
            "area_target_outcomes": area_target_outcomes,
            "target_count": target_count,
            "elemental_affinity_eligible": bool(pending_spell.get("elemental_affinity_eligible")),
            "elemental_affinity_damage_type": pending_spell.get("elemental_affinity_damage_type"),
            "elemental_affinity_bonus": pending_spell.get("elemental_affinity_bonus"),
        }
