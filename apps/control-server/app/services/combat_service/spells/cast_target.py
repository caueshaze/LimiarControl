from __future__ import annotations

from dataclasses import dataclass, field
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
from app.services.realtime import (
    build_event,
    campaign_channel,
    event_version,
    session_channel,
)
from app.services.session_state_finalize import finalize_session_state_data
from app.services.roll_resolution import resolve_attack_base, resolve_saving_throw
from app.schemas.roll import RollActorStats, RollResult
from app.services.combat_service.condition_effects import (
    resolve_attack_advantage,
    resolve_spell_attack_kind,
)
from app.services.combat_service.visibility import resolve_target_visibility
from app.services.combat_service.cover_modifiers import (
    cover_label,
    resolve_cover_modifier,
    resolve_cover_save_modifier,
    should_cover_apply_to_save,
)

from ..combat_targeting import get_combat_targeting_service
from ..exceptions import CombatServiceError, _parse_dice
from ..targeting_requirements import (
    resolve_spell_targeting_requirements,
    resolve_weapon_targeting_requirements,
)
from ..targeting_intent import AreaTargetingIntent, SpellCastIntent, WeaponAttackIntent
from ..unit_conversion import meters_to_cells


@dataclass
class SpellResolutionResult:
    roll_result: RollResult | None = None
    roll_total: int | None = None
    is_critical: bool = False
    is_hit: bool | None = None
    is_saved: bool | None = None
    target_ac: int | None = None
    cover: object = None
    effective_dc: int = 0
    pending_spell_id: str | None = None
    damage: int = 0
    healing: int = 0
    new_hp: int | None = None
    effect_msg: str = ""
    previous_hp: int | None = None
    concentration_check: dict | None = None
    rolled_effect_total: int | None = None
    adv_ctx: object = None
    vis_ctx: object = None


class CastTargetMixin:
    @classmethod
    def _apply_spell_effect(
        cls,
        db: Session,
        state: CombatState,
        target_ref_id: str,
        target_kind: str,
        effect_kind: str,
        amount: int,
        *,
        damage_type: str | None = None,
        is_critical: bool = False,
        concentration_roll_source: str = "system",
        concentration_manual_roll: int | None = None,
    ) -> tuple[int | None, str, int | None, dict | None]:
        if amount <= 0:
            return None, "", None, None
        if effect_kind == "healing":
            new_hp, effect_msg, previous_hp = cls._apply_healing_to_target(
                db,
                target_ref_id,
                target_kind,
                amount,
                state,
            )
            return new_hp, effect_msg, previous_hp, None
        return cls._apply_damage_to_target(
            db,
            target_ref_id,
            target_kind,
            amount,
            damage_type=damage_type,
            is_crit=is_critical,
            state=state,
            **cls._build_concentration_roll_kwargs(
                concentration_roll_source,
                concentration_manual_roll,
            ),
        )

    @classmethod
    def _build_pending_spell_payload(
        cls,
        spell_context: dict,
        target_p: dict,
        *,
        action_kind: str,
        effect_kind: str | None,
        effect_bonus: int,
        save_success_outcome: str | None = None,
        is_saved: bool | None = None,
        is_critical: bool = False,
        roll_total: int | None = None,
        roll_result: RollResult | None = None,
        target_ac: int | None = None,
        effective_dc: int | None = None,
    ) -> dict:
        base = {
            "spell_name": spell_context["spell_name"],
            "spell_canonical_key": spell_context["spell_canonical_key"],
            "action_kind": action_kind,
            "effect_kind": effect_kind,
            "effect_dice": spell_context["effect_dice"],
            "effect_bonus": effect_bonus,
            "damage_type": spell_context.get("damage_type"),
            "elemental_affinity_eligible": spell_context.get(
                "elemental_affinity_eligible"
            ),
            "elemental_affinity_damage_type": spell_context.get(
                "elemental_affinity_damage_type"
            ),
            "elemental_affinity_bonus": spell_context.get("elemental_affinity_bonus"),
            "target_ref_id": target_p["ref_id"],
            "target_kind": target_p["kind"],
            "target_display_name": target_p["display_name"],
            "save_ability": spell_context.get("save_ability"),
            "save_dc": effective_dc
            if effective_dc is not None
            else spell_context.get("save_dc"),
            "is_critical": is_critical,
            "roll": roll_total,
            "roll_result": roll_result.model_dump(mode="json") if roll_result else None,
        }
        if target_ac is not None:
            base["target_ac"] = target_ac
        if save_success_outcome is not None:
            base["save_success_outcome"] = save_success_outcome
        if is_saved is not None:
            base["is_saved"] = is_saved
        return base

    @classmethod
    def _resolve_spell_attack(
        cls,
        db: Session,
        session_id: str,
        *,
        state: CombatState,
        attacker: dict,
        target_p: dict,
        spell_context: dict,
        req: CombatCastSpellRequest,
        is_gm: bool,
        spell_mode: str,
        effect_kind: str | None,
        effect_bonus: int,
        effect_roll_required: bool,
        targeting_result,
    ) -> SpellResolutionResult:
        result = SpellResolutionResult()
        _, result.target_ac, *_ = cls._get_stats(
            db, target_p["ref_id"], target_p["kind"], session_id
        )
        result.cover = targeting_result.spatial_metadata.cover
        result.target_ac = (result.target_ac or 10) + resolve_cover_modifier(
            result.cover
        )
        result.adv_ctx = resolve_attack_advantage(
            attacker, target_p, resolve_spell_attack_kind()
        )
        result.vis_ctx = resolve_target_visibility(
            attacker,
            target_p,
            has_line_of_sight=bool(
                targeting_result.spatial_metadata.has_line_of_sight or True
            ),
        )
        _has_adv = req.has_advantage or bool(result.adv_ctx.advantage_sources)
        _has_dis = (
            req.has_disadvantage
            or bool(result.adv_ctx.disadvantage_sources)
            or not result.vis_ctx.is_directly_visible
        )
        adv_mode = (
            "advantage"
            if (_has_adv and not _has_dis)
            else ("disadvantage" if (_has_dis and not _has_adv) else "normal")
        )
        result.roll_result = resolve_attack_base(
            RollActorStats(
                display_name=attacker["display_name"],
                abilities={},
                actor_kind="player",
                actor_ref_id=attacker["ref_id"],
            ),
            advantage_mode=adv_mode,
            bonus_override=cls._safe_int(spell_context.get("attack_bonus"), 0),
            target_ac=result.target_ac or 10,
            roll_source=req.roll_source,
            manual_roll=req.manual_roll,
            manual_rolls=req.manual_rolls,
        )
        result.roll_result.is_gm_roll = is_gm
        result.roll_result.roll_source = req.roll_source
        result.roll_total = result.roll_result.total
        result.is_critical = result.roll_result.selected_roll == 20
        result.is_hit = bool(result.roll_result.success)

        if result.is_hit and effect_roll_required:
            payload = cls._build_pending_spell_payload(
                spell_context,
                target_p,
                action_kind=spell_mode,
                effect_kind=effect_kind,
                effect_bonus=effect_bonus,
                is_critical=result.is_critical,
                roll_total=result.roll_total,
                roll_result=result.roll_result,
                target_ac=result.target_ac or 10,
            )
            result.pending_spell_id = cls._create_pending_spell_effect(
                state,
                attacker,
                payload,
            )
        elif result.is_hit:
            amount = max(0, effect_bonus)
            (
                result.new_hp,
                result.effect_msg,
                result.previous_hp,
                result.concentration_check,
            ) = cls._apply_spell_effect(
                db,
                state,
                target_p["ref_id"],
                target_p["kind"],
                effect_kind,
                amount,
                damage_type=spell_context.get("damage_type"),
                is_critical=result.is_critical,
                concentration_roll_source=req.concentration_roll_source,
                concentration_manual_roll=req.concentration_manual_roll,
            )
            if effect_kind == "healing":
                result.healing = amount
            else:
                result.damage = amount
        else:
            flag_modified(state, "participants")

        return result

    @classmethod
    def _resolve_saving_throw_spell(
        cls,
        db: Session,
        session_id: str,
        *,
        state: CombatState,
        attacker: dict,
        target_p: dict,
        spell_context: dict,
        req: CombatCastSpellRequest,
        is_gm: bool,
        spell_mode: str,
        effect_kind: str | None,
        effect_bonus: int,
        effect_roll_required: bool,
        save_success_outcome: str | None,
        targeting_result,
    ) -> SpellResolutionResult:
        result = SpellResolutionResult()
        result.cover = targeting_result.spatial_metadata.cover
        save_dc_base = cls._safe_int(spell_context.get("save_dc"), 0)
        if should_cover_apply_to_save(
            spell_context.get("cover_applies_to_save"),
            spell_context.get("save_ability"),
        ):
            result.effective_dc = max(
                0, save_dc_base - resolve_cover_save_modifier(result.cover)
            )
        else:
            result.effective_dc = save_dc_base

        result.roll_result = resolve_saving_throw(
            cls._build_roll_actor_stats_for_save(
                db,
                session_id,
                target_p["ref_id"],
                target_p["kind"],
                target_p["display_name"],
            ),
            ability=spell_context["save_ability"],
            dc=result.effective_dc,
        )
        result.roll_result.is_gm_roll = is_gm
        result.roll_total = result.roll_result.total
        result.is_saved = bool(result.roll_result.success)

        if effect_roll_required and (
            not result.is_saved or save_success_outcome == "half_damage"
        ):
            payload = cls._build_pending_spell_payload(
                spell_context,
                target_p,
                action_kind=spell_mode,
                effect_kind=effect_kind,
                effect_bonus=effect_bonus,
                save_success_outcome=save_success_outcome,
                is_saved=result.is_saved,
                roll_total=result.roll_total,
                roll_result=result.roll_result,
                effective_dc=result.effective_dc,
            )
            result.pending_spell_id = cls._create_pending_spell_effect(
                state,
                attacker,
                payload,
            )
        elif not result.is_saved or save_success_outcome == "half_damage":
            result.rolled_effect_total = max(0, effect_bonus)
            amount = cls._resolve_save_damage_amount(
                result.rolled_effect_total,
                is_saved=result.is_saved,
                save_success_outcome=save_success_outcome,
            )
            (
                result.new_hp,
                result.effect_msg,
                result.previous_hp,
                result.concentration_check,
            ) = cls._apply_spell_effect(
                db,
                state,
                target_p["ref_id"],
                target_p["kind"],
                effect_kind,
                amount,
                damage_type=spell_context.get("damage_type"),
                concentration_roll_source=req.concentration_roll_source,
                concentration_manual_roll=req.concentration_manual_roll,
            )
            if effect_kind == "healing":
                result.healing = amount
            else:
                result.damage = amount
        else:
            flag_modified(state, "participants")

        return result

    @classmethod
    def _resolve_direct_effect_spell(
        cls,
        db: Session,
        state: CombatState,
        *,
        attacker: dict,
        target_p: dict,
        spell_context: dict,
        req,
        spell_mode: str,
        effect_kind: str | None,
        effect_bonus: int,
        effect_roll_required: bool,
    ) -> SpellResolutionResult:
        result = SpellResolutionResult()

        if effect_roll_required:
            payload = cls._build_pending_spell_payload(
                spell_context,
                target_p,
                action_kind=spell_mode,
                effect_kind=effect_kind,
                effect_bonus=effect_bonus,
            )
            result.pending_spell_id = cls._create_pending_spell_effect(
                state,
                attacker,
                payload,
            )
        else:
            amount = max(0, effect_bonus)
            (
                result.new_hp,
                result.effect_msg,
                result.previous_hp,
                result.concentration_check,
            ) = cls._apply_spell_effect(
                db,
                state,
                target_p["ref_id"],
                target_p["kind"],
                effect_kind,
                amount,
                damage_type=spell_context.get("damage_type"),
                concentration_roll_source=req.concentration_roll_source,
                concentration_manual_roll=req.concentration_manual_roll,
            )
            if effect_kind == "healing":
                result.healing = amount
            else:
                result.damage = amount

        return result

    @classmethod
    def _build_cast_log_message(
        cls,
        *,
        attacker: dict,
        target_p: dict,
        spell_context: dict,
        spell_mode: str,
        effect_kind: str | None,
        result: SpellResolutionResult,
        save_success_outcome: str | None,
        was_overridden: bool,
        action_cost: str,
        custom_log_message: str | None,
    ) -> str:
        if isinstance(custom_log_message, str) and custom_log_message.strip():
            log_message = custom_log_message.strip()
        elif spell_mode == "spell_attack":
            cover_text = (
                f" ({cover_label(result.cover)})" if cover_label(result.cover) else ""
            )
            adv_text = ""
            if result.adv_ctx is not None and (
                result.adv_ctx.advantage_sources or result.adv_ctx.disadvantage_sources
            ):
                adv_text = f" [{result.adv_ctx.describe()}]"
            vis_text = ""
            if result.vis_ctx is not None and not result.vis_ctx.is_directly_visible:
                vis_text = (
                    f" [Target not directly visible: {result.vis_ctx.describe()}]"
                )
            if result.is_hit:
                log_message = (
                    f"{attacker['display_name']} conjurou {spell_context['spell_name']} em {target_p['display_name']}: "
                    f"{result.roll_total} total vs AC {result.target_ac or 10}{cover_text}{adv_text}{vis_text} - acerto."
                )
                if result.pending_spell_id:
                    log_message += " Efeito pendente."
                elif result.damage > 0:
                    log_message += f" {result.damage} de dano de {spell_context.get('damage_type') or 'energia'}{result.effect_msg}"
                elif result.healing > 0:
                    log_message += (
                        f" {result.healing} HP restaurados{result.effect_msg}"
                    )
            else:
                log_message = (
                    f"{attacker['display_name']} conjurou {spell_context['spell_name']} em {target_p['display_name']}: "
                    f"{result.roll_total} total vs AC {result.target_ac or 10}{cover_text}{adv_text}{vis_text} - errou."
                )
        elif spell_mode == "saving_throw":
            save_text = "passou" if result.is_saved else "falhou"
            cover_text = (
                f" ({cover_label(result.cover)})" if cover_label(result.cover) else ""
            )
            log_message = (
                f"{attacker['display_name']} lancou {spell_context['spell_name']} em {target_p['display_name']}: "
                f"alvo {save_text} no save de {spell_context['save_ability']} contra CD {result.effective_dc}{cover_text}."
            )
            if result.pending_spell_id:
                if result.is_saved and save_success_outcome == "half_damage":
                    log_message += " Dano pendente para aplicar metade."
                else:
                    log_message += " Efeito pendente."
            elif effect_kind == "damage":
                if result.is_saved and save_success_outcome == "half_damage":
                    log_message += (
                        f" Dano rolado {result.rolled_effect_total or 0}; dano aplicado {result.damage} de "
                        f"{spell_context.get('damage_type') or 'energia'}{result.effect_msg}"
                    )
                elif result.damage > 0:
                    log_message += f" {result.damage} de dano de {spell_context.get('damage_type') or 'energia'}{result.effect_msg}"
                else:
                    log_message += " Nenhum dano aplicado."
        elif effect_kind == "healing":
            log_message = f"{attacker['display_name']} conjurou {spell_context['spell_name']} em {target_p['display_name']}."
            if result.pending_spell_id:
                log_message += " Cura pendente."
            else:
                log_message += f" {result.healing} HP restaurados{result.effect_msg}"
        else:
            log_message = f"{attacker['display_name']} conjurou {spell_context['spell_name']} em {target_p['display_name']}."
            if result.pending_spell_id:
                log_message += " Dano pendente."
            else:
                log_message += f" {result.damage} de dano de {spell_context.get('damage_type') or 'energia'}{result.effect_msg}"

        if isinstance(result.concentration_check, dict) and isinstance(
            result.concentration_check.get("summary_text"), str
        ):
            log_message = (
                f"{log_message} {result.concentration_check['summary_text']}".strip()
            )

        if was_overridden:
            log_message = f"[OVERRIDE: Limit for '{action_cost}' ignored] {log_message}"

        return log_message

    @classmethod
    def _build_cast_response(
        cls,
        *,
        spell_context: dict,
        spell_mode: str,
        effect_kind: str | None,
        effect_bonus: int,
        save_success_outcome: str | None,
        result: SpellResolutionResult,
        automation_result: dict | None,
        target_p: dict,
        action_cost: str,
        summary_text: str | None,
        inventory_refresh_required: bool,
        was_overridden: bool,
    ) -> dict:
        damage_type = (
            automation_result.get("damage_type")
            if automation_result is not None
            else spell_context.get("damage_type")
        )
        target_display_name = (
            automation_result.get("target_display_name")
            if automation_result is not None
            else target_p["display_name"]
        )
        target_kind = (
            automation_result.get("target_kind")
            if automation_result is not None
            else target_p["kind"]
        )
        effect_dice = (
            automation_result.get("effect_dice")
            if automation_result is not None
            else spell_context.get("effect_dice")
        )
        resp_effect_bonus = (
            automation_result.get("effect_bonus")
            if automation_result is not None
            else effect_bonus
        )

        return {
            "spell_name": spell_context["spell_name"],
            "spell_canonical_key": spell_context["spell_canonical_key"],
            "action_kind": spell_mode,
            "effect_kind": effect_kind,
            "damage": result.damage,
            "healing": result.healing,
            "damage_type": damage_type,
            "is_critical": result.is_critical,
            "is_hit": result.is_hit,
            "is_saved": result.is_saved,
            "new_hp": result.new_hp,
            "roll": result.roll_total,
            "roll_result": result.roll_result,
            "target_ac": result.target_ac,
            "target_display_name": target_display_name,
            "target_kind": target_kind,
            "save_ability": spell_context.get("save_ability"),
            "save_dc": spell_context.get("save_dc"),
            "save_success_outcome": save_success_outcome,
            "effect_dice": effect_dice,
            "effect_bonus": resp_effect_bonus,
            "pending_spell_id": result.pending_spell_id,
            "effect_roll_required": bool(result.pending_spell_id),
            "base_effect": (
                automation_result.get("base_effect")
                if automation_result is not None
                else (None if spell_context.get("effect_dice") else 0)
            ),
            "action_cost": action_cost,
            "summary_text": summary_text,
            "inventory_refresh_required": inventory_refresh_required,
            "concentration_check": result.concentration_check,
            "elemental_affinity_eligible": bool(
                spell_context.get("elemental_affinity_eligible")
            ),
            "elemental_affinity_damage_type": spell_context.get(
                "elemental_affinity_damage_type"
            ),
            "elemental_affinity_bonus": spell_context.get("elemental_affinity_bonus"),
        }

    @classmethod
    async def cast_spell(
        cls,
        db: Session,
        session_id: str,
        req: CombatCastSpellRequest,
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
            attacker, ("active",), "You can only cast a spell when active."
        )
        cls._require_action_capable(attacker)
        if attacker["kind"] != "player":
            raise CombatServiceError(
                "Only players can use this spell casting flow.", 400
            )

        # Wild Shape blocks spellcasting (PHB: beast form cannot cast spells)
        attacker_state_check, *_ = cls._get_stats(
            db, attacker["ref_id"], attacker["kind"], session_id
        )
        attacker_data_check = cls._as_dict(attacker_state_check.state_json)
        ws_check = cls._as_dict(attacker_data_check.get("wildShape"))
        if ws_check.get("active"):
            raise CombatServiceError("Cannot cast spells while in Wild Shape.", 400)

        had_pending = isinstance(attacker.get("pending_attack"), dict)
        cls._clear_participant_pending_attack(attacker)
        if had_pending:
            flag_modified(state, "participants")

        attacker_model, _, _, _, _, _ = cls._get_stats(
            db, attacker["ref_id"], attacker["kind"], session_id
        )
        spell_context = cls._resolve_player_spell_context(
            db,
            session_id,
            attacker,
            attacker_model,
            req,
        )
        area_spell_spec = cls._resolve_supported_area_spell_spec(spell_context)
        if cls._normalize_area_shape(spell_context.get("target_mode")) is not None:
            if area_spell_spec is None:
                raise CombatServiceError(
                    "This area spell is not configured for map targeting yet.",
                    400,
                )
            logger.info(
                "[cast_spell] pipeline=generic_area spell=%s session=%s actor=%s",
                spell_context["spell_canonical_key"],
                session_id,
                attacker.get("ref_id"),
            )
            return await cls._cast_area_spell(
                db,
                session_id,
                req,
                attacker=attacker,
                attacker_model=attacker_model,
                actor_user_id=actor_user_id,
                is_gm=is_gm,
                state=state,
                spell_context=spell_context,
                area_spec=area_spell_spec,
            )

        # ── Spatial pre-resolution ────────────────────────────────────────────
        targeting_intent = SpellCastIntent(
            session_id=session_id,
            action_id=f"targeting:{uuid4()}",
            actor_ref_id=attacker["ref_id"],
            actor_kind=attacker["kind"],
            requested_target_ref_id=req.target_ref_id,
            spell_canonical_key=spell_context["spell_canonical_key"],
            spell_mode=spell_context["spell_mode"],
            target_mode=spell_context.get("target_mode"),
            range_meters=spell_context.get("range_meters"),
            requires_sight=bool(spell_context.get("requires_target_sight")),
            requires_effect=bool(spell_context.get("requires_target_effect")),
        )
        targeting_result = get_combat_targeting_service(state.use_map).validate(
            targeting_intent, state
        )
        if not targeting_result.is_valid:
            _diag = targeting_result.diagnostics
            logger.info(
                "[cast_spell] targeting failed session=%s actor=%s target=%s | %s",
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
        is_hostile_spell = (
            spell_context["spell_mode"]
            in (
                "spell_attack",
                "saving_throw",
                "direct_damage",
            )
            or spell_context["spell_canonical_key"] == "hunters_mark"
        )
        if is_hostile_spell:
            cls._assert_hostile_action_allowed(
                attacker,
                target_p,
                action_label="a hostile spell",
            )
        cls._validate_spell_automation_target(
            db,
            session_id,
            spell_canonical_key=spell_context["spell_canonical_key"],
            target_participant=target_p,
        )
        if spell_context.get("source_kind") == "magic_item":
            inventory_item = spell_context.get("inventory_item")
            source_item = spell_context.get("source_item")
            if not isinstance(inventory_item, InventoryItem):
                raise CombatServiceError("Magic item inventory entry is missing.", 400)
            remaining_charges = get_inventory_item_charges_current(
                inventory_item, source_item
            )
            if isinstance(remaining_charges, int) and remaining_charges <= 0:
                raise CombatServiceError("This item has no charges remaining.", 400)
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

        effect_roll_required = spell_context["effect_dice"] is not None
        spell_mode = spell_context["spell_mode"]
        effect_kind = spell_context["effect_kind"]
        effect_bonus = cls._safe_int(spell_context.get("effect_bonus"), 0)
        save_success_outcome = spell_context.get("save_success_outcome")
        inventory_refresh_required = spell_context.get("source_kind") == "magic_item"
        summary_text = None
        custom_log_message = None

        automation_result = await cls._cast_spell_via_automation(
            db,
            session_id,
            attacker=attacker,
            attacker_model=attacker_model,
            actor_user_id=actor_user_id,
            is_gm=is_gm,
            req=req,
            state=state,
            spell_context=spell_context,
            target_participant=target_p,
        )
        if automation_result is not None:
            spell_mode = automation_result["action_kind"]
            effect_kind = automation_result["effect_kind"]
            result = SpellResolutionResult(
                roll_result=automation_result["roll_result"],
                roll_total=automation_result["roll"],
                target_ac=automation_result["target_ac"],
                is_critical=automation_result["is_critical"],
                is_hit=automation_result["is_hit"],
                is_saved=automation_result["is_saved"],
                new_hp=automation_result["new_hp"],
                pending_spell_id=automation_result["pending_spell_id"],
                damage=automation_result["damage"],
                healing=automation_result["healing"],
            )
            effect_roll_required = automation_result["effect_roll_required"]
            summary_text = automation_result.get("summary_text")
            inventory_refresh_required = inventory_refresh_required or bool(
                automation_result.get("inventory_refresh_required")
            )
            custom_log_message = automation_result.get("__log_message")
            automation_player_state_ids = (
                automation_result.get("__player_state_ids_to_emit") or set()
            )
        elif spell_mode == "spell_attack":
            result = cls._resolve_spell_attack(
                db,
                session_id,
                state=state,
                attacker=attacker,
                target_p=target_p,
                spell_context=spell_context,
                req=req,
                is_gm=is_gm,
                spell_mode=spell_mode,
                effect_kind=effect_kind,
                effect_bonus=effect_bonus,
                effect_roll_required=effect_roll_required,
                targeting_result=targeting_result,
            )
        elif spell_mode == "saving_throw":
            result = cls._resolve_saving_throw_spell(
                db,
                session_id,
                state=state,
                attacker=attacker,
                target_p=target_p,
                spell_context=spell_context,
                req=req,
                is_gm=is_gm,
                spell_mode=spell_mode,
                effect_kind=effect_kind,
                effect_bonus=effect_bonus,
                effect_roll_required=effect_roll_required,
                save_success_outcome=save_success_outcome,
                targeting_result=targeting_result,
            )
        else:
            result = cls._resolve_direct_effect_spell(
                db,
                state,
                attacker=attacker,
                target_p=target_p,
                spell_context=spell_context,
                req=req,
                spell_mode=spell_mode,
                effect_kind=effect_kind,
                effect_bonus=effect_bonus,
                effect_roll_required=effect_roll_required,
            )

        db.add(state)
        db.commit()
        db.refresh(state)

        player_state_ids_to_emit = (
            set(automation_player_state_ids) if automation_result is not None else set()
        )
        if slot_spent:
            player_state_ids_to_emit.add(attacker["ref_id"])
        if (result.damage > 0 or result.healing > 0) and target_p["kind"] == "player":
            player_state_ids_to_emit.add(target_p["ref_id"])

        for player_ref_id in player_state_ids_to_emit:
            target_state, *_ = cls._get_stats(db, player_ref_id, "player", session_id)
            await cls._emit_player_state_update(
                db, session_id, player_ref_id, target_state
            )
        if (
            (result.damage > 0 or result.healing > 0)
            and target_p["kind"] == "session_entity"
            and result.previous_hp != result.new_hp
        ):
            await cls._emit_entity_hp_update(
                db, session_id, target_p["ref_id"], result.previous_hp
            )
        await cls._emit_state(session_id, state)

        source = "gm_override" if is_gm else "player_turn"
        log_message = cls._build_cast_log_message(
            attacker=attacker,
            target_p=target_p,
            spell_context=spell_context,
            spell_mode=spell_mode,
            effect_kind=effect_kind,
            result=result,
            save_success_outcome=save_success_outcome,
            was_overridden=was_overridden,
            action_cost=action_cost,
            custom_log_message=custom_log_message,
        )

        await cls._emit_log(
            session_id,
            {
                "message": log_message,
                "actorUserId": actor_user_id,
                "source": source,
                "is_override": was_overridden,
                "overridden_resource": action_cost if was_overridden else None,
            },
        )
        return cls._build_cast_response(
            spell_context=spell_context,
            spell_mode=spell_mode,
            effect_kind=effect_kind,
            effect_bonus=effect_bonus,
            save_success_outcome=save_success_outcome,
            result=result,
            automation_result=automation_result,
            target_p=target_p,
            action_cost=action_cost,
            summary_text=summary_text,
            inventory_refresh_required=inventory_refresh_required,
            was_overridden=was_overridden,
        )

    @classmethod
    async def cast_spell_effect(
        cls,
        db: Session,
        session_id: str,
        req: CombatResolveSpellEffectRequest,
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
            attacker, ("active",), "You can only resolve spell effects when active."
        )
        if attacker["kind"] != "player":
            raise CombatServiceError(
                "Only players can use this spell casting flow.", 400
            )

        # Wild Shape blocks all spell-related actions
        _ws_model, *_ = cls._get_stats(
            db, attacker["ref_id"], attacker["kind"], session_id
        )
        _ws_data = cls._as_dict(_ws_model.state_json)
        if cls._as_dict(_ws_data.get("wildShape")).get("active"):
            raise CombatServiceError(
                "Cannot resolve spell effects while in Wild Shape.", 400
            )

        pending_spell = cls._require_pending_spell_effect(
            attacker, req.pending_spell_id
        )
        effect_kind = pending_spell.get("effect_kind") or "damage"
        effect_dice = pending_spell.get("effect_dice")
        effect_bonus = cls._safe_int(pending_spell.get("effect_bonus"), 0)
        area_targets_payload = pending_spell.get("area_targets")
        roll_result_data = pending_spell.get("roll_result")
        roll_result = (
            RollResult.model_validate(roll_result_data)
            if isinstance(roll_result_data, dict)
            else None
        )
        target_ref_id = pending_spell.get("target_ref_id")
        target_kind = pending_spell.get("target_kind")
        target_display_name = pending_spell.get("target_display_name") or "Target"
        if isinstance(area_targets_payload, list):
            return await cls._cast_area_spell_effect(
                db,
                session_id,
                req,
                attacker=attacker,
                pending_spell=pending_spell,
                effect_kind=effect_kind,
                effect_dice=effect_dice,
                effect_bonus=effect_bonus,
                actor_user_id=actor_user_id,
                is_gm=is_gm,
                state=state,
            )
        if not isinstance(target_ref_id, str) or not isinstance(target_kind, str):
            raise CombatServiceError(
                "Pending spell effect is missing target information.", 400
            )

        effect_rolls: list[int] = []
        base_effect = 0
        if isinstance(effect_dice, str) and effect_dice.strip():
            effect_rolls, base_effect = cls._resolve_damage_roll(
                effect_dice,
                critical=bool(pending_spell.get("is_critical"))
                and effect_kind == "damage",
                roll_source=req.roll_source,
                manual_rolls=req.manual_rolls,
            )
        rolled_effect_total = max(0, base_effect + effect_bonus)
        is_saved = bool(pending_spell.get("is_saved"))
        save_success_outcome = cls._normalize_save_success_outcome(
            pending_spell.get("save_success_outcome")
        )
        amount = (
            cls._resolve_save_damage_amount(
                rolled_effect_total,
                is_saved=is_saved,
                save_success_outcome=save_success_outcome,
            )
            if pending_spell.get("action_kind") == "saving_throw"
            and effect_kind == "damage"
            else rolled_effect_total
        )
        new_hp = None
        effect_msg = ""
        previous_hp = None
        concentration_check = None
        if amount > 0:
            new_hp, effect_msg, previous_hp, concentration_check = (
                cls._apply_spell_effect(
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
            )

        cls._clear_participant_pending_attack(attacker)
        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)

        if amount > 0 and target_kind == "player":
            target_state, *_ = cls._get_stats(db, target_ref_id, "player", session_id)
            await cls._emit_player_state_update(
                db, session_id, target_ref_id, target_state
            )
        elif amount > 0 and target_kind == "session_entity" and previous_hp != new_hp:
            await cls._emit_entity_hp_update(db, session_id, target_ref_id, previous_hp)
        await cls._emit_state(session_id, state)

        if (
            pending_spell.get("action_kind") == "saving_throw"
            and effect_kind == "damage"
        ):
            save_text = "passou" if is_saved else "falhou"
            if is_saved and save_success_outcome == "half_damage":
                log_text = (
                    f"{attacker['display_name']} resolveu {pending_spell.get('spell_name') or 'magia'} em "
                    f"{target_display_name}: alvo {save_text} no save de {pending_spell.get('save_ability')} "
                    f"contra CD {pending_spell.get('save_dc')}. Dano rolado {rolled_effect_total}; "
                    f"dano aplicado {amount} de {pending_spell.get('damage_type') or 'energia'}{effect_msg}"
                )
            elif is_saved:
                log_text = (
                    f"{attacker['display_name']} resolveu {pending_spell.get('spell_name') or 'magia'} em "
                    f"{target_display_name}: alvo {save_text} no save de {pending_spell.get('save_ability')} "
                    f"contra CD {pending_spell.get('save_dc')} e evitou o dano."
                )
            else:
                log_text = (
                    f"{attacker['display_name']} resolveu {pending_spell.get('spell_name') or 'magia'} em "
                    f"{target_display_name}: alvo {save_text} no save de {pending_spell.get('save_ability')} "
                    f"contra CD {pending_spell.get('save_dc')} e sofreu {amount} de "
                    f"{pending_spell.get('damage_type') or 'energia'}{effect_msg}"
                )
        else:
            amount_label = (
                "HP restaurados"
                if effect_kind == "healing"
                else f"de dano de {pending_spell.get('damage_type') or 'energia'}"
            )
            log_text = (
                f"{attacker['display_name']} resolveu {pending_spell.get('spell_name') or 'magia'} em "
                f"{target_display_name}: {amount} {amount_label}{effect_msg}"
            )
        await cls._emit_log(
            session_id,
            {
                "message": (
                    f"{log_text} {concentration_check['summary_text']}".strip()
                    if isinstance(concentration_check, dict)
                    and isinstance(concentration_check.get("summary_text"), str)
                    else log_text
                ),
                "actorUserId": actor_user_id,
                "source": "gm_override" if is_gm else "player_turn",
            },
        )

        return {
            "spell_name": pending_spell.get("spell_name") or "Spell",
            "spell_canonical_key": pending_spell.get("spell_canonical_key"),
            "action_kind": pending_spell.get("action_kind") or "direct_damage",
            "effect_kind": effect_kind,
            "damage": amount if effect_kind != "healing" else 0,
            "healing": amount if effect_kind == "healing" else 0,
            "damage_type": pending_spell.get("damage_type"),
            "is_critical": bool(pending_spell.get("is_critical")),
            "is_hit": True
            if pending_spell.get("action_kind") == "spell_attack"
            else None,
            "is_saved": is_saved
            if pending_spell.get("action_kind") == "saving_throw"
            else None,
            "new_hp": new_hp,
            "roll": cls._safe_int(pending_spell.get("roll"), 0)
            if pending_spell.get("roll") is not None
            else None,
            "roll_result": roll_result,
            "target_ac": cls._safe_optional_int(pending_spell.get("target_ac")),
            "target_display_name": target_display_name,
            "target_kind": target_kind,
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
            "concentration_check": concentration_check,
            "elemental_affinity_eligible": bool(
                pending_spell.get("elemental_affinity_eligible")
            ),
            "elemental_affinity_damage_type": pending_spell.get(
                "elemental_affinity_damage_type"
            ),
            "elemental_affinity_bonus": pending_spell.get("elemental_affinity_bonus"),
        }
