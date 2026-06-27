from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy.orm.attributes import flag_modified

from app.schemas.roll import RollActorStats
from app.services.combat_service.condition_effects import resolve_attack_advantage, resolve_spell_attack_kind
from app.services.combat_service.condition_effects_predicates import target_wearing_metal_armor
from app.services.roll_resolution import resolve_attack_base

from ...cover_modifiers import resolve_cover_modifier
from ...exceptions import CombatServiceError
from ...host_protocol import CombatServiceHostProtocol
from ...targeting_result import TargetingResult


if TYPE_CHECKING:
    _CastTargetInstanceResolutionBase = CombatServiceHostProtocol
else:
    _CastTargetInstanceResolutionBase = object


class CastTargetInstanceResolutionMixin(_CastTargetInstanceResolutionBase):
    @classmethod
    def _build_delayed_damage_metadata_from_spell_context(
        cls,
        *,
        spell_context: dict,
        source_participant_id: str | None,
        target_participant_id: str | None,
        target_ref_id: str | None,
    ) -> dict | None:
        effects = spell_context.get("effects")
        if not isinstance(effects, list):
            return None
        for effect in effects:
            if not isinstance(effect, dict) or effect.get("type") != "delayed_damage":
                continue
            params = effect.get("params")
            if not isinstance(params, dict):
                continue
            damage_formula = spell_context.get("delayed_damage_preview") or params.get("dice")
            if not isinstance(damage_formula, str) or not damage_formula.strip():
                continue
            damage_type = params.get("damageType") or spell_context.get("damage_type")
            if not isinstance(damage_type, str) or not damage_type.strip():
                continue
            return {
                "source_spell_key": spell_context.get("spell_canonical_key"),
                "source_spell_name": spell_context.get("spell_name"),
                "delayed_damage": True,
                "timing": "target_turn_end",
                "damage_formula": damage_formula.strip(),
                "damage_type": damage_type.strip(),
                "remaining_triggers": 1,
                "created_slot_level": spell_context.get("slot_level"),
                "effect_target_participant_id": target_participant_id,
                "effect_target_ref_id": target_ref_id,
                "source_participant_id": source_participant_id,
            }
        return None

    @classmethod
    def _apply_spell_attack_delayed_damage_effect(
        cls,
        *,
        target_participant: dict[str, Any],
        spell_context: dict[str, Any],
        attacker: dict[str, Any],
    ) -> bool:
        metadata = cls._build_delayed_damage_metadata_from_spell_context(
            spell_context=spell_context,
            source_participant_id=attacker.get("id"),
            target_participant_id=target_participant.get("id"),
            target_ref_id=target_participant.get("ref_id"),
        )
        if metadata is None:
            return False
        cls._append_effect_to_participant(
            target_participant,
            cls._build_active_effect(
                kind="damage",
                source_participant_id=attacker.get("id"),
                duration_type="manual",
                metadata=metadata,
                display_label="Delayed Damage",
            ),
        )
        return True

    @classmethod
    def _validate_spell_target_creature_type_restriction(
        cls,
        db,
        session_id: str,
        *,
        spell_canonical_key: str,
        target_participant: dict,
    ) -> None:
        spell_key = cls._normalize_lookup(spell_canonical_key).replace(" ", "_")
        if spell_key not in {"hold_person", "charm_person", "crown_of_madness"}:
            return
        creature_type = cls.resolve_effective_creature_type(
            db,
            session_id,
            target_participant,
        )
        if creature_type is not None and creature_type != "humanoid":
            if spell_key == "hold_person":
                spell_name = "Hold Person"
            elif spell_key == "charm_person":
                spell_name = "Charm Person"
            else:
                spell_name = "Crown of Madness"
            raise CombatServiceError(f"{spell_name} can only target humanoids.", 400)

    @classmethod
    def _upsert_shield_temp_ac_effect(cls, participant: dict, *, source_participant_id: str | None) -> None:
        effects = cls._get_participant_effects(participant)
        kept = []
        for effect in effects:
            metadata = cls._as_dict(effect.get("metadata"))
            if effect.get("kind") == "temp_ac_bonus" and metadata.get("source_spell_key") == "shield":
                continue
            kept.append(effect)
        cls._set_participant_effects(participant, kept)
        cls._append_effect_to_participant(
            participant,
            cls._build_active_effect(
                kind="temp_ac_bonus",
                source_participant_id=source_participant_id,
                numeric_value=5,
                duration_type="until_turn_start",
                expires_at_participant_id=participant.get("id"),
                metadata={"source_spell_key": "shield"},
                display_label="Shield",
            ),
        )

    @classmethod
    def _is_shielded_for_magic_missile(cls, participant: dict | None) -> bool:
        if not isinstance(participant, dict):
            return False
        for effect in cls._get_participant_effects(participant):
            metadata = cls._as_dict(effect.get("metadata"))
            if effect.get("kind") == "temp_ac_bonus" and metadata.get("source_spell_key") == "shield":
                return True
        return False
    @classmethod
    def _resolve_instance_direct(cls, db, state, attacker, target_p, spell_context, req):
        instance_dice = spell_context.get("effect_instance_dice")
        if not instance_dice:
            raise CombatServiceError(
                "Multi-instance spell is missing effect_instance_dice.", 400
            )

        effect_kind = spell_context.get("effect_kind") or "damage"
        damage_type = spell_context.get("damage_type")
        _, raw_total = cls._resolve_damage_roll(
            instance_dice,
            roll_source="system",
        )
        amount = max(0, raw_total)
        new_hp = None
        previous_hp = None
        if amount > 0:
            new_hp, _, previous_hp, _ = cls._apply_spell_effect(
                db,
                state,
                target_p["ref_id"],
                target_p.get("kind", "session_entity"),
                effect_kind,
                amount,
                damage_type=damage_type,
                concentration_roll_source=req.concentration_roll_source,
                concentration_manual_roll=req.concentration_manual_roll,
                attacker_participant_id=attacker.get("id"),
            )

        return {
            "target_ref_id": target_p["ref_id"],
            "target_display_name": target_p.get("display_name", ""),
            "target_kind": target_p.get("kind", "session_entity"),
            "damage": amount if effect_kind != "healing" else 0,
            "healing": amount if effect_kind == "healing" else 0,
            "is_hit": None,
            "is_saved": None,
            "is_critical": False,
            "roll": amount,
            "roll_result": None,
            "new_hp": new_hp,
            "previous_hp": previous_hp,
            "needs_roll": False,
        }

    @classmethod
    def _resolve_instance_attack(
        cls, db, session_id, state, attacker, target_p, spell_context, req, is_gm,
        *,
        targeting_result: TargetingResult | None = None,
    ):
        instance_dice = spell_context.get("effect_instance_dice")
        if not instance_dice:
            raise CombatServiceError(
                "Multi-instance spell is missing effect_instance_dice.", 400
            )
        attack_bonus = cls._safe_int(spell_context.get("attack_bonus"), 0)

        _, target_ac_raw, *_ = cls._get_stats(
            db,
            target_p["ref_id"],
            target_p["kind"],
            session_id,
            combat_state=state,
        )
        cover = targeting_result.spatial_metadata.cover if targeting_result else None
        cover_modifier = resolve_cover_modifier(cover)
        base_ac = target_ac_raw if target_ac_raw is not None else 10
        target_ac = base_ac + cover_modifier

        adv_ctx = resolve_attack_advantage(attacker, target_p, resolve_spell_attack_kind())
        raw_adv_condition = spell_context.get("attack_advantage_condition")
        if isinstance(raw_adv_condition, dict) and raw_adv_condition.get("type") == "target_wearing_metal_armor":
            if target_wearing_metal_armor(target_p):
                adv_ctx.advantage_sources.append("target_wearing_metal_armor")
        has_adv = req.has_advantage or bool(adv_ctx.advantage_sources)
        has_dis = req.has_disadvantage or bool(adv_ctx.disadvantage_sources)
        adv_mode = (
            "advantage" if has_adv and not has_dis
            else "disadvantage" if has_dis and not has_adv
            else "normal"
        )

        from . import resolve_attack_base as _resolve_attack_base

        roll_result = _resolve_attack_base(
            RollActorStats(
                display_name=attacker["display_name"],
                abilities={},
                actor_kind="player",
                actor_ref_id=attacker["ref_id"],
            ),
            advantage_mode=adv_mode,
            bonus_override=attack_bonus,
            target_ac=target_ac,
            roll_source="system",
        )
        cls._apply_roll_bonus_dice_to_roll_result(
            participant=attacker,
            roll_result=roll_result,
            roll_type="attack",
        )
        roll_result.is_gm_roll = is_gm
        roll_result.roll_source = "system"
        if adv_ctx.consumed_effect_ids_on_roll:
            cls._consume_effect_ids(attacker, adv_ctx.consumed_effect_ids_on_roll)
            cls._consume_effect_ids(target_p, adv_ctx.consumed_effect_ids_on_roll)

        is_critical = roll_result.selected_roll == 20
        is_hit = bool(roll_result.success)

        flag_modified(state, "participants")

        return {
            "target_ref_id": target_p["ref_id"],
            "target_display_name": target_p.get("display_name", ""),
            "target_kind": target_p.get("kind", "session_entity"),
            "damage": 0,
            "healing": 0,
            "is_hit": is_hit,
            "is_saved": None,
            "is_critical": is_critical,
            "roll": roll_result.total,
            "roll_result": roll_result,
            "new_hp": None,
            "previous_hp": None,
            "cover": cover,
            "base_ac": base_ac,
            "effective_ac": target_ac,
            "cover_modifier": cover_modifier,
            "needs_roll": is_hit,
        }
