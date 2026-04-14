from __future__ import annotations

from datetime import datetime, timezone
import logging
import random
from math import floor
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

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
from app.services.realtime import (
    build_event,
    campaign_channel,
    event_version,
    session_channel,
)
from app.services.session_state_finalize import finalize_session_state_data
from app.services.roll_resolution import resolve_attack_base, resolve_saving_throw
from app.schemas.roll import RollActorStats, RollResult
from app.services.combat_service.cover_modifiers import (
    cover_label,
    resolve_cover_modifier,
)
from app.services.combat_service.condition_effects import (
    get_attack_auto_crit,
    resolve_attack_advantage,
)
from app.services.combat_service.visibility import resolve_target_visibility

from ..combat_targeting import get_combat_targeting_service
from ..exceptions import CombatServiceError, _parse_dice
from ..targeting_requirements import (
    resolve_spell_targeting_requirements,
    resolve_weapon_targeting_requirements,
)
from ..targeting_intent import AreaTargetingIntent, SpellCastIntent, WeaponAttackIntent
from ..reach import resolve_weapon_attack_kind
from ..unit_conversion import meters_to_cells


class WeaponAttacksMixin:
    @classmethod
    async def attack(
        cls,
        db: Session,
        session_id: str,
        req: CombatAttackRequest,
        actor_user_id: str,
        is_gm: bool,
    ):
        state = cls.get_state(db, session_id)
        cls._require_active(state)
        attacker = cls._resolve_actor_participant(
            state,
            actor_user_id,
            is_gm,
            req.actor_participant_id,
        )
        cls._require_actor_status(
            attacker, ("active",), "You can only attack when active."
        )
        cls._require_action_capable(attacker)
        if attacker["kind"] != "player":
            raise CombatServiceError("Use entity actions for session entities.")

        # Wild Shape: regular weapon attacks are replaced by natural attacks
        attacker_model, _, _, _, _, _ = cls._get_stats(
            db, attacker["ref_id"], attacker["kind"], session_id
        )
        attacker_data = cls._as_dict(attacker_model.state_json)
        if cls._as_dict(attacker_data.get("wildShape")).get("active"):
            raise CombatServiceError(
                "Cannot use weapon attacks while in Wild Shape. Use wild-shape-attack instead.",
                400,
            )

        was_overridden = cls._consume_turn_resource(
            attacker,
            "action",
            is_gm=is_gm,
            override_resource_limit=req.override_resource_limit,
        )
        cls._clear_participant_pending_attack(attacker)
        attack_context = cls._build_player_attack_context(
            db,
            session_id,
            attacker["ref_id"],
            attacker_data,
            req.weapon_item_id,
        )
        damage_dice = attack_context["damage_dice"]
        weapon_targeting = resolve_weapon_targeting_requirements()

        # ── Spatial pre-resolution ────────────────────────────────────────────
        targeting_intent = WeaponAttackIntent(
            session_id=session_id,
            action_id=f"targeting:{uuid4()}",
            actor_ref_id=attacker["ref_id"],
            actor_kind=attacker["kind"],
            requested_target_ref_id=req.target_ref_id,
            weapon_item_id=req.weapon_item_id,
            weapon_canonical_key=attack_context.get("weapon_canonical_key"),
            range_meters=attack_context.get("range_meters"),
            range_long_meters=attack_context.get("range_long_meters"),
            weapon_range_type=attack_context.get("weapon_range_type"),
            has_reach=bool(attack_context.get("has_reach")),
            requires_sight=weapon_targeting.requires_target_sight,
            requires_effect=weapon_targeting.requires_target_effect,
        )
        targeting_result = get_combat_targeting_service(state.use_map).validate(
            targeting_intent, state
        )
        if not targeting_result.is_valid:
            _diag = targeting_result.diagnostics
            logger.info(
                "[attack] targeting failed session=%s actor=%s target=%s | %s",
                session_id,
                attacker.get("ref_id"),
                req.target_ref_id,
                _diag.compact_log() if _diag else targeting_result.failure_reason,
            )
            raise CombatServiceError(
                targeting_result.failure_reason or "Target not found in combat"
            )

        target_p = next(
            (
                p
                for p in state.participants
                if p["ref_id"] == targeting_result.validated_primary_target_ref_id
            ),
            None,
        )
        if not target_p:
            raise CombatServiceError("Target not found in combat")
        # ─────────────────────────────────────────────────────────────────────
        cls._assert_hostile_action_allowed(
            attacker,
            target_p,
            action_label="an attack",
        )

        _, target_ac, *_ = cls._get_stats(
            db, target_p["ref_id"], target_p["kind"], session_id
        )
        target_ac = target_ac or 10
        target_ac += cls._sum_numeric_effects(target_p, "temp_ac_bonus")
        cover = targeting_result.spatial_metadata.cover
        target_ac += resolve_cover_modifier(cover)
        attack_context["attack_bonus"] += cls._sum_numeric_effects(
            attacker, "attack_bonus"
        )
        # Condition-based advantage/disadvantage (Phase F1)
        _attack_kind = resolve_weapon_attack_kind(
            weapon_range_type=attack_context.get("weapon_range_type"),
            range_meters=attack_context.get("range_meters"),
            range_long_meters=attack_context.get("range_long_meters"),
            has_reach=bool(attack_context.get("has_reach")),
            distance_meters=targeting_result.spatial_metadata.distance_meters,
        )
        _adv_ctx = resolve_attack_advantage(attacker, target_p, _attack_kind)
        _vis_ctx = resolve_target_visibility(
            attacker,
            target_p,
            has_line_of_sight=bool(
                targeting_result.spatial_metadata.has_line_of_sight or True
            ),
        )
        has_adv = (
            req.has_advantage
            or cls._has_effect_kind(attacker, "advantage_on_attacks")
            or bool(_adv_ctx.advantage_sources)
        )
        has_dis = (
            req.has_disadvantage
            or cls._has_effect_kind(attacker, "disadvantage_on_attacks")
            or cls._has_effect_kind(target_p, "dodging")
            or bool(_adv_ctx.disadvantage_sources)
            or bool(targeting_result.spatial_metadata.is_in_long_range)
            or not _vis_ctx.is_directly_visible
        )
        # Consume advantage_on_attacks (Help) after first use
        if not req.has_advantage and cls._has_effect_kind(
            attacker, "advantage_on_attacks"
        ):
            cls._consume_first_effect(attacker, "advantage_on_attacks")
        adv_mode = (
            "advantage"
            if (has_adv and not has_dis)
            else ("disadvantage" if (has_dis and not has_adv) else "normal")
        )
        roll_result = resolve_attack_base(
            RollActorStats(
                display_name=attacker["display_name"],
                abilities={},
                actor_kind="player",
                actor_ref_id=attacker["ref_id"],
            ),
            advantage_mode=adv_mode,
            bonus_override=attack_context["attack_bonus"],
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

        # Phase F2: auto-crit for paralyzed/unconscious targets (melee only)
        auto_crit_source = (
            get_attack_auto_crit(attacker, target_p, _attack_kind)
            if is_hit and not is_crit
            else ""
        )
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
                    "target_kind": target_p["kind"],
                    "target_display_name": target_p["display_name"],
                    "target_ac": target_ac,
                    "weapon_name": attack_context["name"],
                    "damage_dice": damage_dice,
                    "damage_bonus": attack_context["damage_bonus"],
                    "attack_bonus": attack_context["attack_bonus"],
                    "damage_type": attack_context.get("damage_type"),
                    "inventory_item_id": attack_context.get("inventory_item_id"),
                    "is_weapon_attack": attack_context.get("inventory_item_id")
                    != "unarmed",
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
            hit_text = "CRITICALLY HIT" + (
                f" (auto-crit: {auto_crit_source})" if auto_crit_source else ""
            )
        if is_fail:
            hit_text = "CRITICALLY MISSED"
        message_suffix = " Damage roll pending." if is_hit else ""

        if was_overridden:
            hit_text = f"[OVERRIDE: Action limit ignored] {hit_text}"

        cover_text = f", {cover_label(cover)}" if cover_label(cover) else ""
        adv_ctx_desc = _adv_ctx.describe()
        adv_text = (
            f" [{adv_ctx_desc}]"
            if (_adv_ctx.advantage_sources or _adv_ctx.disadvantage_sources)
            else ""
        )
        vis_text = (
            f" [Target not directly visible: {_vis_ctx.describe()}]"
            if not _vis_ctx.is_directly_visible
            else ""
        )
        await cls._emit_log(
            session_id,
            {
                "message": (
                    f"{attacker['display_name']} {hit_text} {target_p['display_name']} "
                    f"(AC {target_ac}{cover_text}) with {attack_context['name']} and roll {atk_roll}{adv_text}{vis_text}.{message_suffix}"
                ),
                "actorUserId": actor_user_id,
                "source": source,
                "is_override": was_overridden,
                "overridden_resource": "action" if was_overridden else None,
            },
        )
        return {
            "roll": atk_roll,
            "is_hit": is_hit,
            "damage": 0,
            "is_critical": is_crit,
            "new_hp": None,
            "roll_result": roll_result,
            "target_ac": target_ac,
            "target_display_name": target_p["display_name"],
            "target_kind": target_p["kind"],
            "weapon_name": attack_context["name"],
            "damage_dice": damage_dice,
            "damage_bonus": attack_context["damage_bonus"],
            "attack_bonus": attack_context["attack_bonus"],
            "damage_type": attack_context.get("damage_type"),
            "pending_attack_id": pending_attack_id,
            "damage_roll_required": is_hit,
        }

    @classmethod
    async def attack_damage(
        cls,
        db: Session,
        session_id: str,
        req: CombatResolveDamageRequest,
        actor_user_id: str,
        is_gm: bool,
    ):
        state = cls.get_state(db, session_id)
        cls._require_active(state)
        attacker = cls._resolve_actor_participant(
            state,
            actor_user_id,
            is_gm,
            req.actor_participant_id,
        )
        cls._require_actor_status(
            attacker, ("active",), "You can only roll damage when active."
        )
        if attacker["kind"] != "player":
            raise CombatServiceError("Use entity actions for session entities.")

        pending_attack = cls._require_pending_attack(
            attacker,
            req.pending_attack_id,
            expected_type="player_attack",
        )
        damage_dice = pending_attack.get("damage_dice") or "unarmed"
        damage_rolls, base_damage = cls._resolve_damage_roll(
            damage_dice,
            critical=bool(pending_attack.get("is_critical")),
            roll_source=req.roll_source,
            manual_rolls=req.manual_rolls,
        )
        damage_bonus = cls._safe_int(pending_attack.get("damage_bonus"), 0)
        effect_damage_bonus = cls._sum_numeric_effects(attacker, "damage_bonus")
        damage = max(1, base_damage + damage_bonus + effect_damage_bonus)
        target_ref_id = pending_attack.get("target_ref_id")
        target_kind = pending_attack.get("target_kind")
        target_display_name = pending_attack.get("target_display_name") or "Target"
        if not isinstance(target_ref_id, str) or not isinstance(target_kind, str):
            raise CombatServiceError(
                "Pending damage roll is missing target information.", 400
            )
        target_participant = cls._get_participant_by_ref(state, target_ref_id)

        attacker_model, *_ = cls._get_stats(
            db, attacker["ref_id"], attacker["kind"], session_id
        )
        attacker_data = cls._as_dict(attacker_model.state_json)
        target_current_hp, target_max_hp = cls._get_target_hp_snapshot(
            db,
            session_id,
            target_ref_id,
            target_kind,
        )
        extra_damage = 0
        extra_damage_rolls: list[int] = []
        extra_damage_label = ""
        turn_resources = cls._get_turn_resources(attacker)
        is_weapon_attack = pending_attack.get("is_weapon_attack") is True

        hunters_mark_effect = (
            cls._get_hunters_mark_effect_for_target(
                attacker,
                target_participant_id=target_participant.get("id", "")
                if target_participant
                else "",
            )
            if is_weapon_attack
            else None
        )
        if hunters_mark_effect is not None:
            hm_rolls, hm_damage = cls._resolve_damage_roll(
                "1d6",
                roll_source="system",
            )
            extra_damage += hm_damage
            extra_damage_rolls.extend(hm_rolls)
            extra_damage_label += " Hunter's Mark: +1d6."

        can_use_colossus_slayer = (
            cls._player_has_colossus_slayer(attacker_data)
            and target_current_hp is not None
            and target_max_hp is not None
            and target_current_hp < target_max_hp
            and not turn_resources.get("colossus_slayer_used")
        )
        if can_use_colossus_slayer:
            colossus_rolls, colossus_damage = cls._resolve_damage_roll(
                "1d8",
                roll_source="system",
            )
            extra_damage_rolls.extend(colossus_rolls)
            extra_damage += colossus_damage
            turn_resources["colossus_slayer_used"] = True
            attacker["turn_resources"] = turn_resources
            extra_damage_label += " Assassino de Colossos: +1d8."

        new_hp = None
        effect_msg = ""
        previous_hp = None
        concentration_check = None
        if damage > 0:
            new_hp, effect_msg, previous_hp, concentration_check = (
                cls._apply_damage_to_target(
                    db,
                    target_ref_id,
                    target_kind,
                    damage + extra_damage,
                    damage_type=pending_attack.get("damage_type"),
                    is_crit=bool(pending_attack.get("is_critical")),
                    state=state,
                    **cls._build_concentration_roll_kwargs(
                        req.concentration_roll_source,
                        req.concentration_manual_roll,
                    ),
                )
            )

        roll_result_data = pending_attack.get("roll_result")
        roll_result = (
            RollResult.model_validate(roll_result_data)
            if isinstance(roll_result_data, dict)
            else None
        )
        cls._clear_participant_pending_attack(attacker)
        flag_modified(state, "participants")

        db.add(state)
        db.commit()
        db.refresh(state)

        if damage > 0 and target_kind == "player":
            target_state, *_ = cls._get_stats(
                db, target_ref_id, target_kind, session_id
            )
            await cls._emit_player_state_update(
                db, session_id, target_ref_id, target_state
            )
        elif damage > 0 and previous_hp != new_hp:
            await cls._emit_entity_hp_update(db, session_id, target_ref_id, previous_hp)
        await cls._emit_state(session_id, state)

        source = "gm_override" if is_gm else "player_turn"
        concentration_summary = (
            f" {concentration_check['summary_text']}"
            if isinstance(concentration_check, dict)
            and isinstance(concentration_check.get("summary_text"), str)
            else ""
        )
        await cls._emit_log(
            session_id,
            {
                "message": (
                    f"{attacker['display_name']} rolled damage with {pending_attack.get('weapon_name') or 'Attack'} "
                    f"against {target_display_name}: {damage + extra_damage} damage.{extra_damage_label}{effect_msg}"
                    f"{concentration_summary}"
                ),
                "actorUserId": actor_user_id,
                "source": source,
            },
        )

        return {
            "roll": cls._safe_int(pending_attack.get("roll"), 0),
            "is_hit": True,
            "damage": damage + extra_damage,
            "is_critical": bool(pending_attack.get("is_critical")),
            "new_hp": new_hp,
            "roll_result": roll_result,
            "target_ac": cls._safe_int(pending_attack.get("target_ac"), 10),
            "target_display_name": target_display_name,
            "target_kind": target_kind,
            "weapon_name": pending_attack.get("weapon_name") or "Attack",
            "damage_dice": damage_dice,
            "damage_bonus": damage_bonus,
            "attack_bonus": cls._safe_int(pending_attack.get("attack_bonus"), 0),
            "damage_type": pending_attack.get("damage_type"),
            "pending_attack_id": None,
            "damage_roll_required": False,
            "damage_rolls": damage_rolls,
            "base_damage": base_damage,
            "extra_damage_rolls": extra_damage_rolls,
            "extra_damage": extra_damage,
            "damage_roll_source": req.roll_source,
            "concentration_check": concentration_check,
        }
