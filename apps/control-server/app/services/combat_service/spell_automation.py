from __future__ import annotations

import logging
from datetime import datetime, timezone
from dataclasses import dataclass
from uuid import uuid4
from typing import Any

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app.models.combat import CombatState
from app.services.roll_resolution import resolve_saving_throw
from app.services.spell_effect_factories import SpellEffectBuildContext
from app.services.spell_keys import normalize_spell_key
from app.services.wild_shape_service import force_revert
from app.services.combat_service.condition_effects_predicates import is_reaction_blocked
from app.services.combat_service.condition_effects_saves import modify_saving_throw

from .condition_effects import resolve_spell_attack_kind
from .exceptions import CombatServiceError, _roll_dice_expression
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
        "ensnaring_strike": SpellAutomationSpec(
            canonical_key="ensnaring_strike",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_ensnaring_strike_automation",
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
    def _list_reaction_opportunities(cls, state: CombatState) -> list[dict]:
        opportunities = getattr(state, "reaction_opportunities", None)
        if not isinstance(opportunities, list):
            state.reaction_opportunities = []
            return state.reaction_opportunities
        return opportunities

    @classmethod
    def _find_reaction_opportunity(
        cls,
        state: CombatState,
        *,
        opportunity_id: str,
    ) -> dict | None:
        for opportunity in cls._list_reaction_opportunities(state):
            if isinstance(opportunity, dict) and opportunity.get("id") == opportunity_id:
                return opportunity
        return None

    @classmethod
    def _create_hellish_rebuke_opportunity(
        cls,
        state: CombatState,
        *,
        actor_participant: dict,
        source_participant: dict,
        damage_event_id: str,
        damage_taken: int,
    ) -> dict:
        opportunity = {
            "id": str(uuid4()),
            "kind": "damage_taken",
            "spell_key": "hellish_rebuke",
            "actor_participant_id": actor_participant.get("id"),
            "actor_ref_id": actor_participant.get("ref_id"),
            "source_participant_id": source_participant.get("id"),
            "source_ref_id": source_participant.get("ref_id"),
            "damage_event_id": damage_event_id,
            "damage_taken": max(0, cls._safe_int(damage_taken, 0)),
            "round": cls._safe_int(getattr(state, "round", 0), 0),
            "turn_index": cls._safe_int(getattr(state, "current_turn_index", 0), 0),
            "status": "available",
        }
        cls._list_reaction_opportunities(state).append(opportunity)
        return opportunity

    @classmethod
    def _expire_reaction_opportunities_turn_boundary(
        cls,
        state: CombatState,
    ) -> bool:
        existing = cls._list_reaction_opportunities(state)
        if not existing:
            return False
        kept = [
            opportunity
            for opportunity in existing
            if not isinstance(opportunity, dict)
            or opportunity.get("status") != "available"
        ]
        if len(kept) == len(existing):
            return False
        state.reaction_opportunities = kept
        return True

    @classmethod
    def _expire_reaction_opportunities_for_actor(
        cls,
        state: CombatState,
        *,
        actor_participant_id: str,
    ) -> bool:
        existing = cls._list_reaction_opportunities(state)
        if not existing:
            return False
        kept = []
        removed = False
        for opportunity in existing:
            if (
                isinstance(opportunity, dict)
                and opportunity.get("status") == "available"
                and opportunity.get("actor_participant_id") == actor_participant_id
            ):
                removed = True
                continue
            kept.append(opportunity)
        if not removed:
            return False
        state.reaction_opportunities = kept
        return True

    @classmethod
    def _maybe_create_hellish_rebuke_reaction_opportunity(
        cls,
        state: CombatState | None,
        *,
        target_participant: dict | None,
        source_participant_id: str | None,
        damage_taken: int,
        damage_event_id: str,
    ) -> bool:
        if state is None or not isinstance(target_participant, dict):
            return False
        if cls._safe_int(damage_taken, 0) <= 0:
            return False
        if str(target_participant.get("status") or "").strip().lower() != "active":
            return False
        if not isinstance(source_participant_id, str) or not source_participant_id:
            return False
        source_participant = next(
            (participant for participant in (state.participants or []) if participant.get("id") == source_participant_id),
            None,
        )
        if not isinstance(source_participant, dict):
            return False
        resources = cls._get_turn_resources(target_participant)
        if resources.get("reaction_used") is True:
            return False
        if is_reaction_blocked(target_participant):
            return False
        cls._create_hellish_rebuke_opportunity(
            state,
            actor_participant=target_participant,
            source_participant=source_participant,
            damage_event_id=damage_event_id,
            damage_taken=damage_taken,
        )
        return True

    @classmethod
    async def resolve_hellish_rebuke_reaction(
        cls,
        db: Session,
        session_id: str,
        *,
        actor_user_id: str,
        is_gm: bool,
        reaction_opportunity_id: str,
        slot_level: int,
        actor_participant_id: str | None,
        override_resource_limit: bool = False,
    ) -> dict:
        state = cls.get_state(db, session_id)
        if state is None:
            raise CombatServiceError("No combat active for this session", 404)
        cls._require_active(state)
        actor = cls._resolve_actor_participant(state, actor_user_id, is_gm, actor_participant_id)
        opportunity = cls._find_reaction_opportunity(state, opportunity_id=reaction_opportunity_id)
        if not isinstance(opportunity, dict):
            raise CombatServiceError("Reaction opportunity not found.", 404)
        if opportunity.get("status") != "available":
            raise CombatServiceError("Reaction opportunity is not available.", 400)
        if opportunity.get("kind") != "damage_taken" or opportunity.get("spell_key") != "hellish_rebuke":
            raise CombatServiceError("Reaction opportunity is not compatible with Hellish Rebuke.", 400)
        if opportunity.get("actor_participant_id") != actor.get("id"):
            raise CombatServiceError("Reaction opportunity belongs to another participant.", 403)
        if slot_level < 1:
            raise CombatServiceError("Hellish Rebuke requires slot level 1 or higher.", 400)

        source_participant_id = opportunity.get("source_participant_id")
        source = next(
            (participant for participant in (state.participants or []) if participant.get("id") == source_participant_id),
            None,
        )
        if not isinstance(source, dict):
            raise CombatServiceError("Damage source no longer exists in combat.", 400)

        if str(actor.get("status") or "").strip().lower() != "active":
            raise CombatServiceError("Only active participants can cast Hellish Rebuke.", 400)
        cls._ensure_turn_resource_available(
            actor,
            "reaction",
            is_gm=is_gm,
            override_resource_limit=override_resource_limit,
        )

        actor_model, _ac, _atk_bonus, _spell_mod, _prof, spell_save_dc = cls._get_stats(
            db,
            actor.get("ref_id"),
            actor.get("kind"),
            session_id,
            combat_state=state,
        )
        actor_data = cls._as_dict(getattr(actor_model, "state_json", None))
        spells = actor_data.get("spellcasting", {}).get("spells") or []
        spell_entry = next(
            (
                spell
                for spell in spells
                if isinstance(spell, dict)
                and cls._normalize_spell_automation_key(spell.get("canonicalKey")) == "hellish_rebuke"
            ),
            None,
        )
        if spell_entry is None:
            raise CombatServiceError("Caster does not know Hellish Rebuke.", 400)
        if cls._safe_int(spell_entry.get("level"), 0) > 0 and spell_entry.get("prepared") is False:
            raise CombatServiceError("Hellish Rebuke is not prepared.", 400)

        cls._ensure_player_spell_slot_available(actor_model, slot_level)
        distance = None
        local_distances = state.local_distances if isinstance(state.local_distances, dict) else {}
        from_ref = actor.get("ref_id")
        to_ref = source.get("ref_id")
        if isinstance(from_ref, str) and isinstance(to_ref, str):
            source_map = local_distances.get(from_ref)
            if isinstance(source_map, dict):
                distance = source_map.get(to_ref)
        if isinstance(distance, (int, float)) and distance > 18:
            raise CombatServiceError("Damage source is out of range for Hellish Rebuke.", 400)

        was_overridden = cls._consume_turn_resource(
            actor,
            "reaction",
            is_gm=is_gm,
            override_resource_limit=override_resource_limit,
        )
        cls._consume_player_spell_slot(actor_model, slot_level)
        db.add(actor_model)

        save_mod = modify_saving_throw(
            source,
            "dexterity",
            source_participant=actor,
            source_kind="participant",
        )
        roll_result = resolve_saving_throw(
            cls._build_roll_actor_stats_for_save(
                db,
                session_id,
                source.get("ref_id"),
                source.get("kind"),
                source.get("display_name") or "Alvo",
            ),
            ability="dexterity",
            advantage_mode=save_mod.result,
            dc=cls._safe_int(spell_save_dc, 10),
            roll_source="system",
        )
        roll_result.check_modifier_sources = [
            *save_mod.advantage_source_details,
            *save_mod.disadvantage_source_details,
            *(roll_result.check_modifier_sources or []),
        ]
        is_saved = False if save_mod.auto_fail else bool(roll_result.success)
        damage_dice_count = 2 + max(0, slot_level - 1)
        damage_dice = f"{damage_dice_count}d10"
        _rolls, rolled_total = _roll_dice_expression(damage_dice)
        final_damage = rolled_total if not is_saved else rolled_total // 2

        new_hp, effect_msg, previous_hp, concentration_check = cls._apply_damage_to_target(
            db,
            state,
            source.get("ref_id"),
            source.get("kind"),
            final_damage,
            attacker_participant_id=actor.get("id"),
            damage_type="fire",
        )

        opportunity["status"] = "used"
        opportunity["used_by_spell_key"] = "hellish_rebuke"
        opportunity["slot_level"] = slot_level
        opportunity["save_success"] = is_saved
        opportunity["rolled_damage"] = rolled_total
        opportunity["applied_damage"] = final_damage
        opportunity["resolved_at_round"] = cls._safe_int(getattr(state, "round", 0), 0)
        cls._expire_reaction_opportunities_for_actor(
            state,
            actor_participant_id=str(actor.get("id")),
        )
        flag_modified(state, "participants")
        flag_modified(state, "reaction_opportunities")
        db.add(state)
        db.commit()
        db.refresh(state)

        await cls._emit_state(session_id, state)
        await cls._emit_and_persist_log(
            db,
            session_id,
            actor_user_id,
            actor.get("display_name"),
            {
                "message": (
                    f"{actor.get('display_name', 'Conjurador')} lançou Repreensão Infernal contra "
                    f"{source.get('display_name', 'alvo')}: {final_damage} de dano de fogo."
                    f"{effect_msg}"
                ),
                "source": "hellish_rebuke",
                "is_override": was_overridden,
                "overridden_resource": "reaction" if was_overridden else None,
            },
        )
        return {
            "spell_key": "hellish_rebuke",
            "slot_level": slot_level,
            "target_ref_id": source.get("ref_id"),
            "target_kind": source.get("kind"),
            "target_display_name": source.get("display_name"),
            "save_ability": "dexterity",
            "save_dc": cls._safe_int(spell_save_dc, 10),
            "is_saved": is_saved,
            "roll_result": roll_result,
            "damage_dice": damage_dice,
            "rolled_damage": rolled_total,
            "applied_damage": final_damage,
            "new_hp": new_hp,
            "previous_hp": previous_hp,
            "concentration_check": concentration_check,
            "reaction_opportunity_id": reaction_opportunity_id,
            "reaction_consumed": True,
            "slot_consumed": True,
        }

    @classmethod
    def _list_active_area_effects(cls, state: CombatState) -> list[dict]:
        effects = getattr(state, "active_area_effects", None)
        if not isinstance(effects, list):
            state.active_area_effects = []
            return state.active_area_effects
        return effects

    @classmethod
    def _find_active_area_effect(
        cls,
        state: CombatState,
        *,
        effect_id: str,
    ) -> dict | None:
        for effect in cls._list_active_area_effects(state):
            if isinstance(effect, dict) and effect.get("id") == effect_id:
                return effect
        return None

    @classmethod
    def _is_participant_in_area_effect(
        cls,
        effect: dict[str, Any],
        participant: dict[str, Any],
    ) -> bool:
        affected = effect.get("affected_cells")
        if not isinstance(affected, list) or not affected:
            return False
        position = participant.get("position")
        if not isinstance(position, dict):
            return False
        x = position.get("x")
        y = position.get("y")
        if not isinstance(x, int) or not isinstance(y, int):
            return False
        return any(
            isinstance(cell, dict)
            and isinstance(cell.get("x"), int)
            and isinstance(cell.get("y"), int)
            and cell.get("x") == x
            and cell.get("y") == y
            for cell in affected
        )

    @classmethod
    def _moonbeam_dedup_key(
        cls,
        *,
        target_participant_id: str,
        round_value: int,
        turn_index: int,
        trigger: str,
    ) -> str:
        return f"{target_participant_id}:{round_value}:{turn_index}:{trigger}"

    @classmethod
    def _moonbeam_has_applied_this_turn(
        cls,
        effect: dict[str, Any],
        *,
        target_participant_id: str,
        round_value: int,
        turn_index: int,
        trigger: str,
    ) -> bool:
        turn_applied = effect.get("turn_applied")
        if not isinstance(turn_applied, dict):
            return False
        key = cls._moonbeam_dedup_key(
            target_participant_id=target_participant_id,
            round_value=round_value,
            turn_index=turn_index,
            trigger=trigger,
        )
        return bool(turn_applied.get(key))

    @classmethod
    def _moonbeam_mark_applied(
        cls,
        effect: dict[str, Any],
        *,
        target_participant_id: str,
        round_value: int,
        turn_index: int,
        trigger: str,
    ) -> None:
        turn_applied = effect.get("turn_applied")
        if not isinstance(turn_applied, dict):
            turn_applied = {}
            effect["turn_applied"] = turn_applied
        key = cls._moonbeam_dedup_key(
            target_participant_id=target_participant_id,
            round_value=round_value,
            turn_index=turn_index,
            trigger=trigger,
        )
        turn_applied[key] = True

    @classmethod
    def _is_shapechanger_participant(cls, participant: dict[str, Any]) -> bool:
        creature_type = str(participant.get("creature_type") or "").strip().lower()
        if creature_type == "shapechanger":
            return True
        tags = participant.get("tags")
        if isinstance(tags, list):
            for value in tags:
                if isinstance(value, str) and value.strip().lower() == "shapechanger":
                    return True
        metadata = participant.get("metadata")
        if isinstance(metadata, dict) and metadata.get("shapechanger") is True:
            return True
        return False

    @classmethod
    def _has_participant_concentration_for_spell(
        cls,
        participant: dict[str, Any],
        *,
        source_spell_key: str,
        concentration_group: object,
    ) -> bool:
        expected_group = str(concentration_group).strip() if isinstance(concentration_group, str) else ""
        expected_key = normalize_spell_key(source_spell_key)
        for effect in cls._get_participant_effects(participant):
            metadata = cls._get_effect_metadata(effect)
            if metadata.get("concentration") is not True:
                continue
            if normalize_spell_key(metadata.get("source_spell_key")) != expected_key:
                continue
            group_value = metadata.get("concentration_group")
            if expected_group and isinstance(group_value, str) and group_value == expected_group:
                return True
        return False

    @classmethod
    async def _resolve_moonbeam_damage_trigger(
        cls,
        db: Session,
        session_id: str,
        *,
        state: CombatState,
        effect: dict[str, Any],
        target_participant: dict[str, Any],
        trigger: str,
        actor_user_id: str | None,
    ) -> dict | None:
        if trigger not in {"start_turn", "enter_first_time_on_turn"}:
            raise CombatServiceError("Invalid Moonbeam trigger.", 400)
        target_participant_id = str(target_participant.get("id") or "")
        if not target_participant_id:
            return None

        round_value = cls._safe_int(getattr(state, "round", 0), 0)
        turn_index = cls._safe_int(getattr(state, "current_turn_index", 0), 0)
        if cls._moonbeam_has_applied_this_turn(
            effect,
            target_participant_id=target_participant_id,
            round_value=round_value,
            turn_index=turn_index,
            trigger=trigger,
        ):
            return None

        caster = next(
            (
                participant
                for participant in (state.participants or [])
                if participant.get("id") == effect.get("caster_participant_id")
            ),
            None,
        )
        if not isinstance(caster, dict):
            return None

        _actor_model, _ac, _atk_bonus, _spell_mod, _prof, spell_save_dc = cls._get_stats(
            db,
            caster.get("ref_id"),
            caster.get("kind"),
            session_id,
            combat_state=state,
        )
        save_mod = modify_saving_throw(
            target_participant,
            "constitution",
            source_participant=caster,
            source_kind="participant",
        )
        advantage_mode = save_mod.result
        is_shapechanger = cls._is_shapechanger_participant(target_participant)
        if is_shapechanger:
            if advantage_mode == "advantage":
                advantage_mode = "normal"
            elif advantage_mode == "normal":
                advantage_mode = "disadvantage"
        roll_result = resolve_saving_throw(
            cls._build_roll_actor_stats_for_save(
                db,
                session_id,
                target_participant.get("ref_id"),
                target_participant.get("kind"),
                target_participant.get("display_name") or "Alvo",
            ),
            ability="constitution",
            advantage_mode=advantage_mode,
            dc=cls._safe_int(spell_save_dc, 10),
            roll_source="system",
        )
        roll_result.check_modifier_sources = [
            *save_mod.advantage_source_details,
            *save_mod.disadvantage_source_details,
            *(roll_result.check_modifier_sources or []),
        ]
        is_saved = False if save_mod.auto_fail else bool(roll_result.success)
        slot_level = max(2, cls._safe_int(effect.get("slot_level"), 2))
        damage_dice_count = 2 + max(0, slot_level - 2)
        damage_dice = f"{damage_dice_count}d10"
        _rolls, rolled_total = _roll_dice_expression(damage_dice)
        applied_damage = rolled_total if not is_saved else rolled_total // 2
        new_hp, effect_msg, previous_hp, concentration_check = cls._apply_damage_to_target(
            db,
            state,
            target_participant.get("ref_id"),
            target_participant.get("kind"),
            applied_damage,
            attacker_participant_id=caster.get("id"),
            damage_type="radiant",
        )
        shapechanger_effect: dict[str, Any] | None = None
        if is_shapechanger and not is_saved:
            existing_lock = None
            for effect_entry in cls._get_participant_effects(target_participant):
                metadata = cls._get_effect_metadata(effect_entry)
                if (
                    metadata.get("moonbeam_shapechange_lock") is True
                    and metadata.get("source_effect_id") == effect.get("id")
                ):
                    existing_lock = effect_entry
                    break
            if existing_lock is None:
                cls._append_effect_to_participant(
                    target_participant,
                    cls._build_active_effect(
                        kind="spell_effect",
                        source_participant_id=caster.get("id"),
                        duration_type="manual",
                        metadata={
                            "source_spell_key": "moonbeam",
                            "source_effect_id": effect.get("id"),
                            "moonbeam_shapechange_lock": True,
                            "blocks_shapechange": True,
                        },
                        display_label="Moonbeam Shapechange Lock",
                    ),
                )
            if target_participant.get("kind") == "player":
                target_model, *_ = cls._get_stats(
                    db,
                    target_participant.get("ref_id"),
                    target_participant.get("kind"),
                    session_id,
                    combat_state=state,
                )
                data = cls._as_dict(getattr(target_model, "state_json", None))
                target_model.state_json = force_revert(data)
                db.add(target_model)
            shapechanger_effect = {
                "applied": True,
                "reverted_to_original_form": target_participant.get("kind") == "player",
                "blocks_shapechange_until_exit": True,
            }
        cls._moonbeam_mark_applied(
            effect,
            target_participant_id=target_participant_id,
            round_value=round_value,
            turn_index=turn_index,
            trigger=trigger,
        )
        await cls._emit_log(
            session_id,
            {
                "message": (
                    f"{target_participant.get('display_name', 'Alvo')} sofreu {applied_damage} de dano radiante "
                    f"de Raio Lunar ({trigger}).{effect_msg}"
                ),
                "source": "moonbeam",
                "actorUserId": actor_user_id,
                "spellCanonicalKey": "moonbeam",
                "effectId": effect.get("id"),
                "trigger": trigger,
            },
        )
        return {
            "target_ref_id": target_participant.get("ref_id"),
            "target_display_name": target_participant.get("display_name"),
            "is_saved": is_saved,
            "save_dc": cls._safe_int(spell_save_dc, 10),
            "damage_dice": damage_dice,
            "rolled_damage": rolled_total,
            "applied_damage": applied_damage,
            "new_hp": new_hp,
            "previous_hp": previous_hp,
            "concentration_check": concentration_check,
            "roll_result": roll_result,
            "trigger": trigger,
            "shapechanger_effect": shapechanger_effect,
        }

    @classmethod
    async def resolve_moonbeam_start_turn(
        cls,
        db: Session,
        session_id: str,
        *,
        state: CombatState,
        participant: dict[str, Any],
    ) -> list[dict]:
        results: list[dict] = []
        for effect in cls._list_active_area_effects(state):
            if not isinstance(effect, dict):
                continue
            if effect.get("effect_kind") != "moonbeam":
                continue
            if not cls._is_participant_in_area_effect(effect, participant):
                continue
            outcome = await cls._resolve_moonbeam_damage_trigger(
                db,
                session_id,
                state=state,
                effect=effect,
                target_participant=participant,
                trigger="start_turn",
                actor_user_id=None,
            )
            if isinstance(outcome, dict):
                results.append(outcome)
        if results:
            flag_modified(state, "active_area_effects")
            flag_modified(state, "participants")
            db.add(state)
            db.commit()
            db.refresh(state)
            await cls._emit_state(session_id, state)
        return results

    @classmethod
    async def resolve_moonbeam_enter_trigger(
        cls,
        db: Session,
        session_id: str,
        *,
        actor_user_id: str,
        is_gm: bool,
        area_effect_id: str,
        target_ref_id: str,
        actor_participant_id: str | None = None,
    ) -> dict:
        state = cls.get_state(db, session_id)
        if state is None:
            raise CombatServiceError("No combat active for this session", 404)
        cls._require_active(state)
        _actor = cls._resolve_actor_participant(state, actor_user_id, is_gm, actor_participant_id)

        effect = cls._find_active_area_effect(state, effect_id=area_effect_id)
        if not isinstance(effect, dict) or effect.get("effect_kind") != "moonbeam":
            raise CombatServiceError("Moonbeam area effect not found.", 404)
        target = next(
            (
                participant
                for participant in (state.participants or [])
                if participant.get("ref_id") == target_ref_id
            ),
            None,
        )
        if not isinstance(target, dict):
            raise CombatServiceError("Moonbeam target not found.", 404)
        if not cls._is_participant_in_area_effect(effect, target):
            raise CombatServiceError("Moonbeam target is not inside the area.", 400)

        outcome = await cls._resolve_moonbeam_damage_trigger(
            db,
            session_id,
            state=state,
            effect=effect,
            target_participant=target,
            trigger="enter_first_time_on_turn",
            actor_user_id=actor_user_id,
        )
        if outcome is None:
            return {
                "spell_key": "moonbeam",
                "area_effect_id": area_effect_id,
                "target_ref_id": target_ref_id,
                "skipped": True,
                "reason": "already_applied_for_trigger_on_turn",
            }

        flag_modified(state, "active_area_effects")
        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_state(session_id, state)
        return {
            "spell_key": "moonbeam",
            "area_effect_id": area_effect_id,
            **outcome,
        }

    @classmethod
    async def resolve_moonbeam_move(
        cls,
        db: Session,
        session_id: str,
        *,
        actor_user_id: str,
        is_gm: bool,
        area_effect_id: str,
        new_point: dict[str, Any],
        actor_participant_id: str | None = None,
        override_resource_limit: bool = False,
    ) -> dict:
        state = cls.get_state(db, session_id)
        if state is None:
            raise CombatServiceError("No combat active for this session", 404)
        cls._require_active(state)
        actor = cls._resolve_actor_participant(state, actor_user_id, is_gm, actor_participant_id)
        if not is_gm:
            active_participant = state.participants[state.current_turn_index] if state.participants else None
            if not isinstance(active_participant, dict) or active_participant.get("id") != actor.get("id"):
                raise CombatServiceError("Only the active participant can move Moonbeam on this turn.", 403)

        effect = cls._find_active_area_effect(state, effect_id=area_effect_id)
        if not isinstance(effect, dict) or effect.get("effect_kind") != "moonbeam":
            raise CombatServiceError("Moonbeam area effect not found.", 404)
        if effect.get("caster_participant_id") != actor.get("id") and not is_gm:
            raise CombatServiceError("Only the caster can move this Moonbeam.", 403)
        if not cls._has_participant_concentration_for_spell(
            actor,
            source_spell_key="moonbeam",
            concentration_group=effect.get("concentration_group"),
        ):
            raise CombatServiceError("Caster is not concentrating on this Moonbeam.", 400)

        x = new_point.get("x") if isinstance(new_point, dict) else None
        y = new_point.get("y") if isinstance(new_point, dict) else None
        if not isinstance(x, int) or not isinstance(y, int):
            raise CombatServiceError("Moonbeam destination point must use integer x/y.", 400)

        origin = effect.get("origin_point")
        if not isinstance(origin, dict):
            raise CombatServiceError("Moonbeam origin point is missing.", 400)
        ox = origin.get("x")
        oy = origin.get("y")
        if not isinstance(ox, int) or not isinstance(oy, int):
            raise CombatServiceError("Moonbeam origin point is invalid.", 400)
        dx = x - ox
        dy = y - oy
        distance_cells = max(abs(dx), abs(dy))
        distance_meters = distance_cells * 1.5
        if distance_meters > 18:
            raise CombatServiceError("Moonbeam can only move up to 18 meters.", 400)

        was_overridden = cls._consume_turn_resource(
            actor,
            "action",
            is_gm=is_gm,
            override_resource_limit=override_resource_limit,
        )

        effect["origin_point"] = {"x": x, "y": y}
        effect["anchor_cell"] = {"x": x, "y": y}
        affected_cells = effect.get("affected_cells")
        if isinstance(affected_cells, list):
            shifted_cells: list[dict[str, int]] = []
            for cell in affected_cells:
                if not isinstance(cell, dict):
                    continue
                cx = cell.get("x")
                cy = cell.get("y")
                if isinstance(cx, int) and isinstance(cy, int):
                    shifted_cells.append({"x": cx + dx, "y": cy + dy})
            effect["affected_cells"] = shifted_cells

        flag_modified(state, "participants")
        flag_modified(state, "active_area_effects")
        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_state(session_id, state)
        await cls._emit_log(
            session_id,
            {
                "message": f"{actor.get('display_name', 'Conjurador')} moveu o Raio Lunar.",
                "source": "moonbeam_move",
                "spellCanonicalKey": "moonbeam",
                "effectId": area_effect_id,
                "is_override": was_overridden,
                "overridden_resource": "action" if was_overridden else None,
            },
        )
        return {
            "spell_key": "moonbeam",
            "area_effect_id": area_effect_id,
            "new_origin_point": {"x": x, "y": y},
            "action_consumed": True,
        }

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
    def _interrupt_pending_spell_cast_after_damage(
        cls,
        state: CombatState,
        *,
        participant_id: str | None,
        concentration_check: dict | None,
        new_hp: int | None,
    ) -> bool:
        if not participant_id:
            return False
        should_interrupt = False
        if isinstance(concentration_check, dict) and concentration_check.get("success") is False:
            should_interrupt = True
        if isinstance(new_hp, int) and new_hp <= 0:
            should_interrupt = True
        if not should_interrupt:
            return False
        pending_ids = [
            str(pending.get("id"))
            for pending in cls._list_pending_spell_casts(state)
            if isinstance(pending, dict)
            and pending.get("status") == "casting"
            and pending.get("caster_participant_id") == participant_id
            and pending.get("requires_concentration_during_casting") is True
        ]
        if not pending_ids:
            return False
        for pending_id in pending_ids:
            cls._cancel_pending_spell_cast(
                state,
                pending_cast_id=pending_id,
                reason="concentration_failed_or_zero_hp",
            )
        return True

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

    @classmethod
    async def _start_prayer_of_healing_long_cast(
        cls,
        db: Session,
        session_id: str,
        *,
        req,
        state: CombatState,
        attacker: dict,
        attacker_model,
        spell_context: dict,
        actor_user_id: str,
        is_gm: bool,
        targets: list[dict],
    ) -> dict:
        spell_key = cls._normalize_spell_automation_key(spell_context.get("spell_canonical_key"))
        if spell_key != "prayer_of_healing":
            raise CombatServiceError("Long-cast start helper only supports Prayer of Healing.", 400)
        if len(targets) < 1 or len(targets) > 6:
            raise CombatServiceError("Prayer of Healing requires 1 to 6 targets.", 400)

        target_ref_ids: list[str] = [str(p.get("ref_id")) for p in targets if isinstance(p.get("ref_id"), str)]
        if len(target_ref_ids) != len(targets):
            raise CombatServiceError("All targets must have valid combat references.", 400)
        if len(set(target_ref_ids)) != len(target_ref_ids):
            raise CombatServiceError("Prayer of Healing targets cannot repeat.", 400)
        if any(
            isinstance(pending, dict)
            and pending.get("status") == "casting"
            and pending.get("spell_key") == spell_key
            and pending.get("caster_participant_id") == attacker.get("id")
            for pending in cls._list_pending_spell_casts(state)
        ):
            raise CombatServiceError("Caster already has an active Prayer of Healing cast.", 400)

        slot_level = cls._safe_int(spell_context.get("slot_level"), 0)
        if slot_level < 2:
            raise CombatServiceError("Prayer of Healing requires a level 2 or higher spell slot.", 400)

        action_cost = spell_context.get("action_cost") or "action"
        cls._ensure_turn_resource_available(
            attacker,
            action_cost,
            is_gm=is_gm,
            override_resource_limit=req.override_resource_limit,
        )
        cls._ensure_player_spell_slot_available(attacker_model, slot_level)
        was_overridden = cls._consume_turn_resource(
            attacker,
            action_cost,
            is_gm=is_gm,
            override_resource_limit=req.override_resource_limit,
        )
        cls._consume_player_spell_slot(attacker_model, slot_level)
        db.add(attacker_model)

        pending_cast = cls._create_pending_spell_cast(
            state,
            spell_key=spell_key,
            spell_name=spell_context.get("spell_name") or "Prayer of Healing",
            caster_participant_id=str(attacker.get("id")),
            caster_ref_id=str(attacker.get("ref_id")),
            target_ref_ids=target_ref_ids,
            slot_level=slot_level,
            required_rounds=100,
            completed_rounds=1,
            requires_action_each_turn=True,
            requires_concentration_during_casting=True,
            maintained_this_turn=True,
            metadata={
                "started_round": state.round,
                "started_turn_index": state.current_turn_index,
            },
        )

        flag_modified(state, "participants")
        flag_modified(state, "pending_spell_casts")
        db.add(state)
        db.commit()
        db.refresh(state)

        caster_state, *_ = cls._get_stats(db, attacker["ref_id"], "player", session_id)
        await cls._emit_player_state_update(db, session_id, attacker["ref_id"], caster_state)
        await cls._emit_state(session_id, state)
        await cls._emit_and_persist_log(
            db,
            session_id,
            actor_user_id,
            attacker.get("display_name"),
            {
                "message": (
                    f"{attacker.get('display_name', 'Conjurador')} iniciou a conjuração longa de "
                    f"{spell_context.get('spell_name') or 'Prayer of Healing'} "
                    f"(100 rounds; {len(target_ref_ids)} alvo(s))."
                ),
                "source": "long_casting",
                "is_override": was_overridden,
                "overridden_resource": action_cost if was_overridden else None,
            },
        )

        return {
            "spell_name": spell_context.get("spell_name") or "Prayer of Healing",
            "spell_canonical_key": spell_key,
            "selected_variant_key": None,
            "selected_variant_label": None,
            "context_origin": "initial_cast",
            "concentration_group": None,
            "action_kind": "utility",
            "effect_kind": "healing",
            "damage": 0,
            "healing": 0,
            "damage_type": None,
            "is_critical": None,
            "is_hit": None,
            "is_saved": None,
            "new_hp": None,
            "roll": None,
            "roll_result": None,
            "target_ac": None,
            "target_display_name": f"{len(target_ref_ids)} alvos",
            "target_kind": "session_entity",
            "save_ability": None,
            "save_dc": None,
            "save_success_outcome": None,
            "effect_dice": None,
            "effect_bonus": 0,
            "pending_spell_id": None,
            "pending_save_id": None,
            "effect_roll_required": False,
            "base_effect": None,
            "action_cost": action_cost,
            "summary_text": "Conjuração longa iniciada; manutenção por ação a cada turno é necessária.",
            "inventory_refresh_required": False,
            "concentration_check": None,
            "concentration_checks": [],
            "pending_cast": {
                "id": pending_cast.get("id"),
                "required_rounds": 100,
                "completed_rounds": pending_cast.get("completed_rounds"),
                "remaining_rounds": pending_cast.get("remaining_rounds"),
                "status": pending_cast.get("status"),
            },
            "affected_target_ref_ids": target_ref_ids,
            "affected_cells": [],
            "area_target_outcomes": [],
            "target_count": len(target_ref_ids),
        }

    @classmethod
    async def resolve_pending_spell_cast_maintain(
        cls,
        db: Session,
        session_id: str,
        *,
        actor_user_id: str,
        is_gm: bool,
        actor_participant_id: str | None,
        pending_cast_id: str,
        override_resource_limit: bool = False,
    ) -> dict:
        state = cls.get_state(db, session_id)
        if state is None:
            raise CombatServiceError("No combat active for this session", 404)
        cls._require_active(state)
        actor = cls._resolve_actor_participant(state, actor_user_id, is_gm, actor_participant_id)
        cls._require_actor_status(actor, ("active",), "Only active participants can maintain a spell cast.")
        pending = cls._find_pending_spell_cast(state, pending_cast_id=pending_cast_id)
        if not isinstance(pending, dict) or pending.get("status") != "casting":
            raise CombatServiceError("Pending spell cast not found.", 404)
        if cls._normalize_spell_automation_key(pending.get("spell_key")) != "prayer_of_healing":
            raise CombatServiceError("Pending spell cast type is not supported by this endpoint yet.", 400)

        caster_participant_id = str(pending.get("caster_participant_id") or "")
        caster = next((p for p in (state.participants or []) if p.get("id") == caster_participant_id), None)
        if not isinstance(caster, dict):
            raise CombatServiceError("Pending spell cast has an invalid caster.", 400)
        if actor.get("id") != caster_participant_id and not is_gm:
            raise CombatServiceError("Only the original caster can maintain this spell cast.", 403)
        current_participant = cls._get_current_participant(state)
        if current_participant.get("id") != caster_participant_id:
            raise CombatServiceError("Pending spell cast can only be maintained on the caster's turn.", 400)
        cls._require_actor_status(caster, ("active",), "Caster must be active to maintain the spell cast.")
        cls._require_action_capable(caster)
        if pending.get("maintained_this_turn") is True:
            raise CombatServiceError("This pending cast was already maintained this turn.", 400)

        was_overridden = cls._consume_turn_resource(
            caster,
            "action",
            is_gm=is_gm,
            override_resource_limit=override_resource_limit,
        )
        required_rounds = max(1, cls._safe_int(pending.get("required_rounds"), 100))
        completed_rounds = min(required_rounds, cls._safe_int(pending.get("completed_rounds"), 0) + 1)
        pending["completed_rounds"] = completed_rounds
        pending["remaining_rounds"] = max(0, required_rounds - completed_rounds)
        pending["maintained_this_turn"] = True
        pending["status"] = "casting"

        completion_payload = None
        if pending["remaining_rounds"] == 0:
            completion_payload = cls._complete_prayer_of_healing_long_cast(
                db,
                session_id,
                state=state,
                pending=pending,
            )

        flag_modified(state, "participants")
        flag_modified(state, "pending_spell_casts")
        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_state(session_id, state)
        await cls._emit_log(
            session_id,
            {
                "message": (
                    f"{caster.get('display_name', 'Conjurador')} manteve a conjuração de "
                    f"{pending.get('spell_name') or 'magia'} ({pending['completed_rounds']}/{required_rounds})."
                ),
                "source": "long_casting",
                "is_override": was_overridden,
                "overridden_resource": "action" if was_overridden else None,
            },
        )
        response = {
            "maintained": True,
            "actionConsumed": True,
            "isOverride": was_overridden,
            "pendingCastId": pending_cast_id,
            "spellKey": pending.get("spell_key"),
            "status": pending.get("status"),
            "requiredRounds": required_rounds,
            "completedRounds": pending["completed_rounds"],
            "remainingRounds": pending["remaining_rounds"],
        }
        if completion_payload is not None:
            response["completion"] = completion_payload
        return response

    @classmethod
    def _complete_prayer_of_healing_long_cast(
        cls,
        db: Session,
        session_id: str,
        *,
        state: CombatState,
        pending: dict,
    ) -> dict:
        caster_ref_id = str(pending.get("caster_ref_id") or "")
        caster_participant = next(
            (participant for participant in (state.participants or []) if participant.get("id") == pending.get("caster_participant_id")),
            None,
        )
        if not isinstance(caster_participant, dict) or not caster_ref_id:
            raise CombatServiceError("Pending cast has invalid caster context.", 400)
        caster_model, *_stats = cls._get_stats(db, caster_ref_id, "player", session_id)
        spell_mod = cls._safe_int(_stats[3] if len(_stats) >= 4 else 0, 0)
        slot_level = max(2, cls._safe_int(pending.get("slot_level"), 2))
        dice_count = 2 + max(0, slot_level - 2)
        healing_dice = f"{dice_count}d8"
        healing_rolls, rolled_total = _roll_dice_expression(healing_dice)
        healing_total = max(0, rolled_total + spell_mod)

        affected: list[str] = []
        healing_by_target: dict[str, dict[str, int]] = {}
        unaffected: dict[str, str] = {}
        out_of_range_target_ref_ids: list[str] = []
        local_distances = state.local_distances if isinstance(state.local_distances, dict) else {}
        caster_distances = local_distances.get(caster_ref_id) if isinstance(local_distances.get(caster_ref_id), dict) else {}
        target_ref_ids = [ref_id for ref_id in (pending.get("target_ref_ids") or []) if isinstance(ref_id, str)]

        for target_ref_id in target_ref_ids:
            target_participant = next(
                (participant for participant in (state.participants or []) if participant.get("ref_id") == target_ref_id),
                None,
            )
            if not isinstance(target_participant, dict):
                unaffected[target_ref_id] = "target_missing"
                continue
            distance = caster_distances.get(target_ref_id) if isinstance(caster_distances, dict) else None
            if isinstance(distance, (int, float)) and distance > 9:
                unaffected[target_ref_id] = "out_of_range"
                out_of_range_target_ref_ids.append(target_ref_id)
                continue
            creature_type = cls.resolve_effective_creature_type(db, session_id, target_participant)
            if creature_type in {"undead", "construct"}:
                unaffected[target_ref_id] = f"excluded_creature_type:{creature_type}"
                continue

            target_kind = str(target_participant.get("kind") or "")
            if target_kind != "player":
                unaffected[target_ref_id] = "unsupported_target_kind"
                continue
            target_model, *_ = cls._get_stats(db, target_ref_id, target_kind, session_id)
            data = cls._as_dict(target_model.state_json)
            previous_hp = max(0, cls._safe_int(data.get("currentHP"), 0))
            max_hp = max(previous_hp, cls._safe_int(data.get("maxHP"), previous_hp))
            new_hp = min(max_hp, previous_hp + healing_total)
            healed = max(0, new_hp - previous_hp)
            data["currentHP"] = new_hp
            target_model.state_json = data
            db.add(target_model)
            affected.append(target_ref_id)
            healing_by_target[target_ref_id] = {
                "previous_hp": previous_hp,
                "new_hp": new_hp,
                "max_hp": max_hp,
                "healed": healed,
            }

        cls._complete_pending_spell_cast(state, pending_cast_id=str(pending.get("id")))
        flag_modified(state, "pending_spell_casts")
        return {
            "spell_key": "prayer_of_healing",
            "healing_dice": healing_dice,
            "healing_rolls": healing_rolls,
            "spellcasting_modifier": spell_mod,
            "healing_total": healing_total,
            "affected_target_ref_ids": affected,
            "healing_by_target": healing_by_target,
            "unaffected_targets": unaffected,
            "range_validation": "best_effort",
            "out_of_range_target_ref_ids": out_of_range_target_ref_ids,
        }

    @classmethod
    def _reset_pending_spell_cast_maintenance_turn_start(
        cls,
        state: CombatState,
        *,
        participant_id: str,
    ) -> bool:
        changed = False
        for pending in cls._list_pending_spell_casts(state):
            if not isinstance(pending, dict):
                continue
            if pending.get("status") != "casting":
                continue
            if pending.get("caster_participant_id") != participant_id:
                continue
            if pending.get("requires_action_each_turn") is not True:
                continue
            if pending.get("maintained_this_turn") is True:
                pending["maintained_this_turn"] = False
                changed = True
        return changed

    @classmethod
    async def _resolve_pending_spell_cast_maintenance_on_turn_end(
        cls,
        session_id: str,
        state: CombatState,
        outgoing: dict,
    ) -> None:
        outgoing_participant_id = outgoing.get("id")
        if not isinstance(outgoing_participant_id, str) or not outgoing_participant_id:
            return
        to_cancel: list[str] = []
        for pending in cls._list_pending_spell_casts(state):
            if not isinstance(pending, dict):
                continue
            if pending.get("status") != "casting":
                continue
            if pending.get("caster_participant_id") != outgoing_participant_id:
                continue
            if pending.get("requires_action_each_turn") is not True:
                continue
            if pending.get("maintained_this_turn") is True:
                continue
            to_cancel.append(str(pending.get("id")))
        if not to_cancel:
            return
        for pending_cast_id in to_cancel:
            cls._cancel_pending_spell_cast(
                state,
                pending_cast_id=pending_cast_id,
                reason="missed_maintain_action",
            )
        flag_modified(state, "pending_spell_casts")
        await cls._emit_log(
            session_id,
            {
                "message": (
                    f"{outgoing.get('display_name', 'Conjurador')} perdeu a manutenção de conjuração longa, "
                    "encerrando a magia."
                ),
                "source": "long_casting",
            },
        )
