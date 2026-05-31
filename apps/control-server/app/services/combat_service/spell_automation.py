from __future__ import annotations

import logging
from datetime import datetime, timezone
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app.models.combat import CombatState
from app.services.roll_resolution import resolve_saving_throw
from app.services.spell_effect_factories import SpellEffectBuildContext
from app.services.spell_keys import normalize_spell_key

from .condition_effects import resolve_spell_attack_kind
from .exceptions import CombatServiceError
from .host_protocol import CombatServiceHostProtocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SpellAutomationSpec:
    canonical_key: str
    default_mode: str
    requires_effect_payload: bool
    handler_name: str


class CombatSpellAutomationMixin(CombatServiceHostProtocol):
    _SPELL_AUTOMATION_REGISTRY: dict[str, SpellAutomationSpec] = {
        "animal_friendship": SpellAutomationSpec(
            canonical_key="animal_friendship",
            default_mode="saving_throw",
            requires_effect_payload=False,
            handler_name="_cast_animal_friendship_automation",
        ),
        "charm_person": SpellAutomationSpec(
            canonical_key="charm_person",
            default_mode="saving_throw",
            requires_effect_payload=False,
            handler_name="_cast_charm_person_automation",
        ),
        "hunters_mark": SpellAutomationSpec(
            canonical_key="hunters_mark",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_hunters_mark_automation",
        ),
        "goodberry": SpellAutomationSpec(
            canonical_key="goodberry",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_goodberry_automation",
        ),
        "purify_food_and_drink": SpellAutomationSpec(
            canonical_key="purify_food_and_drink",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_purify_food_and_drink_automation",
        ),
        "chill_touch": SpellAutomationSpec(
            canonical_key="chill_touch",
            default_mode="spell_attack",
            requires_effect_payload=False,
            handler_name="_cast_chill_touch_automation",
        ),
        "true_strike": SpellAutomationSpec(
            canonical_key="true_strike",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_true_strike_automation",
        ),
        "shillelagh": SpellAutomationSpec(
            canonical_key="shillelagh",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_shillelagh_automation",
        ),
        "jump": SpellAutomationSpec(
            canonical_key="jump",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_jump_automation",
        ),
        "spider_climb": SpellAutomationSpec(
            canonical_key="spider_climb",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_spider_climb_automation",
        ),
        "barkskin": SpellAutomationSpec(
            canonical_key="barkskin",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_barkskin_automation",
        ),
        "blur": SpellAutomationSpec(
            canonical_key="blur",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_blur_automation",
        ),
        "lesser_restoration": SpellAutomationSpec(
            canonical_key="lesser_restoration",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_lesser_restoration_automation",
        ),
        "command": SpellAutomationSpec(
            canonical_key="command",
            default_mode="save",
            requires_effect_payload=False,
            handler_name="_cast_command_automation",
        ),
        "compelled_duel": SpellAutomationSpec(
            canonical_key="compelled_duel",
            default_mode="save",
            requires_effect_payload=False,
            handler_name="_cast_compelled_duel_automation",
        ),
        "entangle": SpellAutomationSpec(
            canonical_key="entangle",
            default_mode="area_save",
            requires_effect_payload=False,
            handler_name="_cast_entangle_automation",
        ),
        "faerie_fire": SpellAutomationSpec(
            canonical_key="faerie_fire",
            default_mode="area_save",
            requires_effect_payload=False,
            handler_name="_cast_faerie_fire_automation",
        ),
        "crown_of_madness": SpellAutomationSpec(
            canonical_key="crown_of_madness",
            default_mode="save",
            requires_effect_payload=False,
            handler_name="_cast_crown_of_madness_automation",
        ),
        "protection_from_evil_and_good": SpellAutomationSpec(
            canonical_key="protection_from_evil_and_good",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_protection_from_evil_and_good_automation",
        ),
        "sanctuary": SpellAutomationSpec(
            canonical_key="sanctuary",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_sanctuary_automation",
        ),
        "warding_bond": SpellAutomationSpec(
            canonical_key="warding_bond",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_warding_bond_automation",
        ),
        "feather_fall": SpellAutomationSpec(
            canonical_key="feather_fall",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_feather_fall_automation",
        ),
        "spiritual_weapon": SpellAutomationSpec(
            canonical_key="spiritual_weapon",
            default_mode="spell_attack",
            requires_effect_payload=True,
            handler_name="_cast_spiritual_weapon_automation",
        ),
        "mage_hand": SpellAutomationSpec(
            canonical_key="mage_hand",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_mage_hand_automation",
        ),
        "minor_illusion": SpellAutomationSpec(
            canonical_key="minor_illusion",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_minor_illusion_automation",
        ),
        "prestidigitation": SpellAutomationSpec(
            canonical_key="prestidigitation",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_prestidigitation_automation",
        ),
        "mending": SpellAutomationSpec(
            canonical_key="mending",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_mending_automation",
        ),
        "light": SpellAutomationSpec(
            canonical_key="light",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_light_automation",
        ),
        "detect_magic": SpellAutomationSpec(
            canonical_key="detect_magic",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_detect_magic_automation",
        ),
        "detect_poison_disease": SpellAutomationSpec(
            canonical_key="detect_poison_disease",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_detect_poison_disease_automation",
        ),
        "detect_evil_and_good": SpellAutomationSpec(
            canonical_key="detect_evil_and_good",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_detect_evil_and_good_automation",
        ),
        "comprehend_languages": SpellAutomationSpec(
            canonical_key="comprehend_languages",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_comprehend_languages_automation",
        ),
        "druidcraft": SpellAutomationSpec(
            canonical_key="druidcraft",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_druidcraft_automation",
        ),
        "thaumaturgy": SpellAutomationSpec(
            canonical_key="thaumaturgy",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_thaumaturgy_automation",
        ),
        "produce_flame": SpellAutomationSpec(
            canonical_key="produce_flame",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_produce_flame_automation",
        ),
        "spare_the_dying": SpellAutomationSpec(
            canonical_key="spare_the_dying",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_spare_the_dying_automation",
        ),
    }

    @classmethod
    def _normalize_spell_automation_key(cls, value: object) -> str:
        return normalize_spell_key(value)

    @classmethod
    def _list_pending_spell_casts(cls, state: CombatState) -> list[dict]:
        pending = getattr(state, "pending_spell_casts", None)
        if not isinstance(pending, list):
            state.pending_spell_casts = []
            return state.pending_spell_casts
        return pending

    @classmethod
    def _find_pending_spell_cast(
        cls,
        state: CombatState,
        *,
        pending_cast_id: str,
    ) -> dict | None:
        for pending in cls._list_pending_spell_casts(state):
            if isinstance(pending, dict) and pending.get("id") == pending_cast_id:
                return pending
        return None

    @classmethod
    def _create_pending_spell_cast(
        cls,
        state: CombatState,
        *,
        spell_key: str,
        spell_name: str,
        caster_participant_id: str,
        caster_ref_id: str,
        target_ref_ids: list[str],
        slot_level: int,
        required_rounds: int,
        completed_rounds: int = 0,
        requires_action_each_turn: bool = True,
        requires_concentration_during_casting: bool = True,
        maintained_this_turn: bool = False,
        metadata: dict | None = None,
    ) -> dict:
        safe_required_rounds = max(1, int(required_rounds))
        safe_completed_rounds = max(0, min(int(completed_rounds), safe_required_rounds))
        pending_cast = {
            "id": str(uuid4()),
            "effect_kind": "pending_spell_cast",
            "spell_key": spell_key,
            "spell_name": spell_name,
            "caster_participant_id": caster_participant_id,
            "caster_ref_id": caster_ref_id,
            "target_ref_ids": list(target_ref_ids),
            "slot_level": int(slot_level),
            "required_rounds": safe_required_rounds,
            "completed_rounds": safe_completed_rounds,
            "remaining_rounds": max(0, safe_required_rounds - safe_completed_rounds),
            "requires_action_each_turn": bool(requires_action_each_turn),
            "requires_concentration_during_casting": bool(requires_concentration_during_casting),
            "maintained_this_turn": bool(maintained_this_turn),
            "status": "casting",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": dict(metadata or {}),
        }
        cls._list_pending_spell_casts(state).append(pending_cast)
        return pending_cast

    @classmethod
    def _cancel_pending_spell_cast(
        cls,
        state: CombatState,
        *,
        pending_cast_id: str,
        reason: str,
    ) -> dict | None:
        pending = cls._find_pending_spell_cast(state, pending_cast_id=pending_cast_id)
        if not isinstance(pending, dict):
            return None
        pending["status"] = "cancelled"
        pending["cancel_reason"] = reason
        casts = [
            entry
            for entry in cls._list_pending_spell_casts(state)
            if not isinstance(entry, dict) or entry.get("id") != pending_cast_id
        ]
        state.pending_spell_casts = casts
        return pending

    @classmethod
    def _complete_pending_spell_cast(
        cls,
        state: CombatState,
        *,
        pending_cast_id: str,
    ) -> dict | None:
        pending = cls._find_pending_spell_cast(state, pending_cast_id=pending_cast_id)
        if not isinstance(pending, dict):
            return None
        pending["status"] = "completed"
        pending["remaining_rounds"] = 0
        casts = [
            entry
            for entry in cls._list_pending_spell_casts(state)
            if not isinstance(entry, dict) or entry.get("id") != pending_cast_id
        ]
        state.pending_spell_casts = casts
        return pending

    @classmethod
    def _build_combat_spell_effect_context(
        cls,
        *,
        spell_key: str,
        spell_name: str,
        caster_participant_id: str,
        target_participant_id: str,
        game_time_seconds: int,
        duration_seconds: int,
        concentration: bool,
        concentration_group: str | None,
        extra_metadata: dict | None = None,
        spell_save_dc: int | None = None,
    ) -> SpellEffectBuildContext:
        return SpellEffectBuildContext(
            spell_key=spell_key,
            spell_name=spell_name,
            game_time_seconds=game_time_seconds,
            duration_seconds=duration_seconds,
            concentration=concentration,
            concentration_group=concentration_group,
            source_participant_id=caster_participant_id,
            owner_participant_id=target_participant_id,
            created_by_participant_id=caster_participant_id,
            context_origin="combat",
            extra_metadata=extra_metadata or {},
            spell_save_dc=spell_save_dc,
        )

    @classmethod
    def _apply_factory_spell_effect_to_target(
        cls,
        *,
        state: CombatState,
        target_participant: dict,
        effect: dict,
        source_spell_key: str,
        replace_existing: bool = True,
    ) -> None:
        active_effects = target_participant.get("active_effects")
        if not isinstance(active_effects, list):
            active_effects = []
            target_participant["active_effects"] = active_effects
        if replace_existing:
            expected_key = normalize_spell_key(source_spell_key)
            target_participant["active_effects"] = [
                e
                for e in active_effects
                if normalize_spell_key(
                    (cls._get_effect_metadata(e) or {}).get("source_spell_key")
                ) != expected_key
            ]
        cls._append_effect_to_participant(target_participant, effect)
        flag_modified(state, "participants")

    @classmethod
    def _get_spell_automation_spec(
        cls, canonical_key: object
    ) -> SpellAutomationSpec | None:
        return cls._SPELL_AUTOMATION_REGISTRY.get(
            cls._normalize_spell_automation_key(canonical_key)
        )

    @classmethod
    def _spell_requires_effect_payload(cls, canonical_key: object) -> bool:
        spec = cls._get_spell_automation_spec(canonical_key)
        if spec is None:
            return True
        return spec.requires_effect_payload

    @classmethod
    def _spell_default_mode_override(cls, canonical_key: object) -> str | None:
        spec = cls._get_spell_automation_spec(canonical_key)
        if spec is None:
            return None
        return spec.default_mode

    @classmethod
    def _validate_spell_automation_target(
        cls,
        db: Session,
        session_id: str,
        *,
        spell_canonical_key: str,
        target_participant: dict,
    ) -> None:
        spell_key = cls._normalize_spell_automation_key(spell_canonical_key)
        if spell_key == "animal_friendship":
            creature_type = cls.resolve_effective_creature_type(
                db,
                session_id,
                target_participant,
            )
            if creature_type != "beast":
                raise CombatServiceError("Animal Friendship can only target beasts.", 400)
        elif spell_key == "spare_the_dying":
            creature_type = cls.resolve_effective_creature_type(
                db,
                session_id,
                target_participant,
            )
            if creature_type in ("undead", "construct"):
                raise CombatServiceError(
                    "Poupar os Moribundos não afeta mortos-vivos ou constructos.",
                    400,
                )

    @classmethod
    def _is_hostile_team_context(cls, attacker: dict, target_participant: dict) -> bool:
        attacker_team = str(attacker.get("team") or "").strip().lower()
        target_team = str(target_participant.get("team") or "").strip().lower()
        if attacker_team in {"players", "allies"}:
            return target_team == "enemies"
        if attacker_team == "enemies":
            return target_team in {"players", "allies"}
        return False

    @staticmethod
    def _base_spell_result(
        *,
        spell_name: str,
        spell_context: dict,
        target_display_name: str,
        target_kind: str,
        action_kind: str = "utility",
        summary_text: str = "",
        log_message: str = "",
        inventory_refresh_required: bool = False,
        extra: dict | None = None,
    ) -> dict:
        result: dict = {
            "spell_name": spell_name,
            "spell_canonical_key": spell_context["spell_canonical_key"],
            "selected_variant_key": spell_context.get("selected_variant_key"),
            "selected_variant_label": spell_context.get("selected_variant_label"),
            "context_origin": spell_context.get("context_origin") or "initial_cast",
            "concentration_group": spell_context.get("concentration_group"),
            "action_kind": action_kind,
            "effect_kind": None, "damage": 0, "healing": 0, "damage_type": None,
            "is_critical": False, "is_hit": None, "is_saved": None, "new_hp": None,
            "roll": None, "roll_result": None, "target_ac": None,
            "target_display_name": target_display_name, "target_kind": target_kind,
            "save_ability": None, "save_dc": None, "save_success_outcome": None,
            "effect_dice": None, "effect_bonus": None, "pending_spell_id": None,
            "effect_roll_required": False, "summary_text": summary_text,
            "applied_declarative_effects_by_target": None,
            "inventory_refresh_required": inventory_refresh_required,
            "__log_message": log_message, "__player_state_ids_to_emit": set(),
            "__entity_hp_update_target": None, "__entity_previous_hp": None,
        }
        if extra:
            result.update(extra)
        return result

    @classmethod
    async def _cast_spell_via_automation(
        cls, db: Session, session_id: str, *, attacker: dict, attacker_model,
        actor_user_id: str, is_gm: bool, req, state: CombatState,
        spell_context: dict, target_participant: dict,
    ) -> dict | None:
        spec = cls._get_spell_automation_spec(spell_context.get("spell_canonical_key"))
        if spec is None:
            return None
        handler = getattr(cls, spec.handler_name, None)
        if handler is None:
            return None
        logger.info(
            "[spell:automation] spell=%s pipeline=special_handler handler=%s session=%s actor=%s",
            spell_context.get("spell_canonical_key"),
            spec.handler_name,
            session_id,
            attacker.get("ref_id"),
        )
        return await handler(
            db,
            session_id,
            attacker=attacker,
            attacker_model=attacker_model,
            actor_user_id=actor_user_id,
            is_gm=is_gm,
            req=req,
            state=state,
            spell_context=spell_context,
            target_participant=target_participant,
        )
