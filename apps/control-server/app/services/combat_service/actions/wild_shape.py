from __future__ import annotations

from datetime import datetime, timezone
import logging
import random
from math import floor

logger = logging.getLogger(__name__)
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
from app.services.combat_service.condition_effects import get_attack_auto_crit, resolve_attack_advantage

from ..combat_targeting import get_combat_targeting_service
from ..exceptions import CombatServiceError, _parse_dice
from ..targeting_requirements import (
    resolve_spell_targeting_requirements,
    resolve_weapon_targeting_requirements,
)
from ..targeting_intent import AreaTargetingIntent, SpellCastIntent, WeaponAttackIntent
from ..unit_conversion import meters_to_cells



class WildShapeMixin:
    async def wild_shape_attack(
        cls,
        db: Session,
        session_id: str,
        req,  # CombatWildShapeAttackRequest — imported at call site to avoid circular import
        actor_user_id: str,
        is_gm: bool,
    ):
        """Perform a natural weapon attack while in Wild Shape.

        Unlike regular attacks this method builds the attack context from the
        beast catalog instead of the player's inventory.
        """
        from app.services.wild_shape_catalog import get_form

        state = cls.get_state(db, session_id)
        cls._require_active(state)
        attacker = cls._resolve_actor_participant(
            state, actor_user_id, is_gm, req.actor_participant_id
        )
        cls._require_actor_status(attacker, ("active",), "You can only attack when active.")
        if attacker["kind"] != "player":
            raise CombatServiceError("Wild Shape attack is only for players.")

        attacker_model, _, str_score, dex_score, prof_bonus, _ = cls._get_stats(
            db, attacker["ref_id"], attacker["kind"], session_id
        )
        attacker_data = cls._as_dict(attacker_model.state_json)
        ws = cls._as_dict(attacker_data.get("wildShape"))
        if not ws.get("active"):
            raise CombatServiceError("Not in Wild Shape.", 400)

        form_key = ws.get("formKey")
        form = get_form(form_key) if isinstance(form_key, str) else None
        if form is None:
            raise CombatServiceError(f"Unknown Wild Shape form: {form_key!r}", 400)

        attack_index = cls._safe_int(getattr(req, "attack_index", 0), 0)
        if attack_index < 0 or attack_index >= len(form.natural_attacks):
            raise CombatServiceError(
                f"Invalid attack_index {attack_index} for form {form_key!r} "
                f"(has {len(form.natural_attacks)} natural attack(s))",
                400,
            )
        natural_attack = form.natural_attacks[attack_index]

        was_overridden = cls._consume_turn_resource(
            attacker, "action", is_gm=is_gm, override_resource_limit=req.override_resource_limit
        )
        cls._clear_participant_pending_attack(attacker)
        weapon_targeting = resolve_weapon_targeting_requirements()

        # ── Spatial pre-resolution ────────────────────────────────────────────
        targeting_intent = WeaponAttackIntent(
            session_id=session_id,
            action_id=f"targeting:{uuid4()}",
            actor_ref_id=attacker["ref_id"],
            actor_kind=attacker["kind"],
            requested_target_ref_id=req.target_ref_id,
            is_wild_shape=True,
            weapon_range_type=BaseItemWeaponRangeType.MELEE.value,
            has_reach=natural_attack.has_reach,
            actor_effective_size=attacker.get("effective_size") or attacker.get("base_size"),
            requires_sight=weapon_targeting.requires_target_sight,
            requires_effect=weapon_targeting.requires_target_effect,
        )
        targeting_result = get_combat_targeting_service(state.use_map).validate(targeting_intent, state)
        if not targeting_result.is_valid:
            _diag = targeting_result.diagnostics
            logger.info(
                "[wild_shape_attack] targeting failed session=%s actor=%s target=%s | %s",
                session_id,
                attacker.get("ref_id"),
                req.target_ref_id,
                _diag.compact_log() if _diag else targeting_result.failure_reason,
            )
            raise CombatServiceError(targeting_result.failure_reason or "Target not found in combat")

        target_p = next(
            (p for p in state.participants if p["ref_id"] == targeting_result.validated_primary_target_ref_id),
            None,
        )
        if not target_p:
            raise CombatServiceError("Target not found in combat")
        target_kind = "session_entity" if target_p.get("kind") == "entity" else target_p.get("kind")
        # ─────────────────────────────────────────────────────────────────────

        _, target_ac, *_ = cls._get_stats(
            db,
            target_p["ref_id"],
            target_p["kind"],
            session_id,
            combat_state=state,
        )
        target_ac = target_ac or 10

        # Build attack bonus: beast's fixed attack_bonus (includes STR/DEX mod + prof)
        attack_bonus = natural_attack.attack_bonus
        attack_bonus += cls._sum_numeric_effects(attacker, "attack_bonus")

        # Condition-based advantage/disadvantage (Phase F1) — wild shape is always melee
        _adv_ctx = resolve_attack_advantage(attacker, target_p, "melee")
        has_adv = req.has_advantage or cls._has_effect_kind(attacker, "advantage_on_attacks") or bool(_adv_ctx.advantage_sources)
        has_dis = req.has_disadvantage or cls._has_effect_kind(attacker, "disadvantage_on_attacks") or cls._has_effect_kind(target_p, "dodging") or bool(_adv_ctx.disadvantage_sources)
        if not req.has_advantage and cls._has_effect_kind(attacker, "advantage_on_attacks"):
            cls._consume_first_effect(attacker, "advantage_on_attacks")
        if _adv_ctx.consumed_effect_ids_on_roll:
            cls._consume_effect_ids(target_p, _adv_ctx.consumed_effect_ids_on_roll)
        adv_mode = "advantage" if (has_adv and not has_dis) else (
            "disadvantage" if (has_dis and not has_adv) else "normal"
        )

        roll_result = resolve_attack_base(
            RollActorStats(
                display_name=attacker["display_name"],
                abilities={},
                actor_kind="player",
                actor_ref_id=attacker["ref_id"],
            ),
            advantage_mode=adv_mode,
            bonus_override=attack_bonus,
            target_ac=target_ac,
            roll_source=req.roll_source,
            manual_roll=req.manual_roll,
            manual_rolls=req.manual_rolls,
        )
        roll_result.is_gm_roll = is_gm
        roll_result.roll_source = req.roll_source

        is_crit = roll_result.selected_roll == 20
        is_fail = roll_result.selected_roll == 1
        atk_roll = roll_result.total
        is_hit = bool(roll_result.success)

        # Phase F2: auto-crit for paralyzed/unconscious targets (wild shape is always melee)
        auto_crit_source = get_attack_auto_crit(attacker, target_p, "melee") if is_hit and not is_crit else ""
        if auto_crit_source:
            is_crit = True

        pending_attack_id = None
        if is_hit:
            pending_attack_id = cls._create_pending_attack(
                state,
                attacker,
                {
                    "type": "player_attack",
                    "target_ref_id": target_p["ref_id"],
                    "target_kind": target_kind,
                    "target_display_name": target_p["display_name"],
                    "target_ac": target_ac,
                    "weapon_name": natural_attack.name,
                    "damage_dice": natural_attack.damage_dice,
                    "damage_bonus": natural_attack.damage_bonus,
                    "attack_bonus": attack_bonus,
                    "damage_type": natural_attack.damage_type,
                    "is_critical": is_crit,
                    "roll_result": roll_result.model_dump(mode="json"),
                    "roll": atk_roll,
                },
            )
        else:
            flag_modified(state, "participants")

        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_state(session_id, state)

        source = "gm_override" if is_gm else "player_turn"
        hit_text = "HIT" if is_hit else "MISSED"
        if is_crit:
            hit_text = "CRITICALLY HIT" + (f" (auto-crit: {auto_crit_source})" if auto_crit_source else "")
        if is_fail:
            hit_text = "CRITICALLY MISSED"
        message_suffix = " Damage roll pending." if is_hit else ""
        if was_overridden:
            hit_text = f"[OVERRIDE: Action limit ignored] {hit_text}"

        adv_ctx_desc = _adv_ctx.describe()
        adv_text = f" [{adv_ctx_desc}]" if (_adv_ctx.advantage_sources or _adv_ctx.disadvantage_sources) else ""
        await cls._emit_log(session_id, {
            "message": (
                f"{attacker['display_name']} ({form.display_name}) {hit_text} "
                f"{target_p['display_name']} (AC {target_ac}) "
                f"with {natural_attack.name} and roll {atk_roll}{adv_text}.{message_suffix}"
            ),
            "actorUserId": actor_user_id,
            "source": source,
            "is_override": was_overridden,
            "overridden_resource": "action" if was_overridden else None,
        })
        return {
            "roll": atk_roll,
            "is_hit": is_hit,
            "damage": 0,
            "is_critical": is_crit,
            "new_hp": None,
            "roll_result": roll_result,
            "target_ac": target_ac,
            "target_display_name": target_p["display_name"],
            "target_kind": target_kind,
            "weapon_name": natural_attack.name,
            "damage_dice": natural_attack.damage_dice,
            "damage_bonus": natural_attack.damage_bonus,
            "attack_bonus": attack_bonus,
            "damage_type": natural_attack.damage_type,
            "pending_attack_id": pending_attack_id,
            "damage_roll_required": is_hit,
        }
