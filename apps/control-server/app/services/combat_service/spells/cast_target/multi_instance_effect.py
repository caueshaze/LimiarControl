from __future__ import annotations

from typing import Any, TYPE_CHECKING

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app.models.combat import CombatState
from app.schemas.combat import CombatResolveSpellEffectRequest

from ...exceptions import CombatServiceError, _parse_dice
from ...host_protocol import CombatServiceHostProtocol


if TYPE_CHECKING:
    _CastMultiInstanceEffectBase = CombatServiceHostProtocol
else:
    _CastMultiInstanceEffectBase = object


class CastMultiInstanceEffectMixin(_CastMultiInstanceEffectBase):

    @classmethod
    async def _cast_multi_instance_spell_effect(
        cls,
        db: Session,
        session_id: str,
        req: CombatResolveSpellEffectRequest,
        *,
        attacker: dict,
        pending_spell: dict[str, Any],
        actor_user_id: str,
        is_gm: bool,
        state: CombatState,
    ) -> dict[str, Any]:
        instance_targets = pending_spell.get("instance_targets")
        if not isinstance(instance_targets, list) or not instance_targets:
            raise CombatServiceError("Pending multi-instance spell effect is missing instance information.", 400)

        effect_dice = pending_spell.get("effect_dice")
        if not isinstance(effect_dice, str) or not effect_dice.strip():
            raise CombatServiceError("Pending multi-instance spell effect is missing effect dice.", 400)
        effect_kind = pending_spell.get("effect_kind") or "damage"
        damage_type = pending_spell.get("damage_type")

        _, dice_count, dice_sides, _ = _parse_dice(effect_dice)
        if dice_count <= 0 or dice_sides <= 0:
            raise CombatServiceError("Pending multi-instance spell effect has invalid effect dice.", 400)

        manual_rolls = req.manual_rolls or []
        if req.roll_source == "manual":
            total_dice_needed = sum(
                dice_count * (2 if target.get("is_critical") else 1)
                for target in instance_targets
            )
            if len(manual_rolls) != total_dice_needed:
                raise CombatServiceError(
                    f"Manual damage roll requires exactly {total_dice_needed} result(s)."
                )

        all_outcomes_payload = pending_spell.get("all_instance_outcomes")
        outcomes_by_index: dict[int, dict[str, Any]] = {}
        if isinstance(all_outcomes_payload, list):
            for outcome in all_outcomes_payload:
                if isinstance(outcome, dict) and isinstance(outcome.get("instance_index"), int):
                    outcomes_by_index[outcome["instance_index"]] = dict(outcome)

        # Elemental Affinity adds the Charisma modifier to a single instance only
        # (RAW: "one damage roll of the spell" — e.g. one ray of Scorching Ray).
        affinity_bonus = cls._resolve_elemental_affinity_damage_bonus(pending_spell, effect_kind)
        affinity_applied = False

        total_damage = 0
        total_healing = 0
        concentration_checks: list[dict[str, Any]] = []
        player_state_ids_to_emit: set[str] = set()
        entity_hp_updates: list[tuple[str, int | None]] = []
        effect_rolls: list[int] = []

        manual_offset = 0
        for instance_target in instance_targets:
            instance_index = instance_target["instance_index"]
            target_ref_id = instance_target["target_ref_id"]
            target_kind = instance_target["target_kind"]
            is_critical = bool(instance_target.get("is_critical"))

            dice_needed = dice_count * (2 if is_critical else 1)
            if req.roll_source == "manual":
                instance_manual_rolls = manual_rolls[manual_offset:manual_offset + dice_needed]
                manual_offset += dice_needed
                rolls, total = cls._resolve_damage_roll(
                    effect_dice,
                    critical=is_critical,
                    roll_source="manual",
                    manual_rolls=instance_manual_rolls,
                )
            else:
                rolls, total = cls._resolve_damage_roll(
                    effect_dice,
                    critical=is_critical,
                    roll_source="system",
                )
            effect_rolls.extend(rolls)

            if affinity_bonus and not affinity_applied:
                total += affinity_bonus
                affinity_applied = True

            amount = max(0, total)
            new_hp = None
            previous_hp = None
            if amount > 0:
                new_hp, _, previous_hp, concentration_check = cls._apply_spell_effect(
                    db,
                    state,
                    target_ref_id,
                    target_kind,
                    effect_kind,
                    amount,
                    damage_type=damage_type,
                    is_critical=is_critical,
                    concentration_roll_source=req.concentration_roll_source,
                    concentration_manual_roll=req.concentration_manual_roll,
                    attacker_participant_id=attacker.get("id"),
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

            outcome = outcomes_by_index.get(instance_index, dict(instance_target))
            outcome.update({
                "instance_index": instance_index,
                "target_ref_id": target_ref_id,
                "target_kind": target_kind,
                "target_display_name": instance_target.get("target_display_name", outcome.get("target_display_name", "")),
                "damage": amount if effect_kind != "healing" else 0,
                "healing": amount if effect_kind == "healing" else 0,
                "is_critical": is_critical,
                "new_hp": new_hp,
                "needs_roll": False,
            })
            outcomes_by_index[instance_index] = outcome

        merged_outcomes = [
            outcomes_by_index.get(outcome.get("instance_index"), outcome)
            for outcome in (all_outcomes_payload if isinstance(all_outcomes_payload, list) else [])
        ]

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

        log_message = cls._build_multi_instance_log_message(
            attacker=attacker,
            spell_context={
                "spell_name": pending_spell.get("spell_name") or "Spell",
                "damage_type": damage_type,
            },
            outcomes=merged_outcomes,
            was_overridden=False,
            action_cost=pending_spell.get("action_cost") or "action",
        )
        await cls._emit_and_persist_log(db, session_id, actor_user_id, attacker.get("display_name"), {
            "message": log_message,
            "actorUserId": actor_user_id,
            "source": "gm_override" if is_gm else "player_turn",
        })

        first_outcome = merged_outcomes[0] if merged_outcomes else None
        primary_concentration_check = concentration_checks[0] if concentration_checks else None

        return {
            "spell_name": pending_spell.get("spell_name"),
            "spell_canonical_key": pending_spell.get("spell_canonical_key"),
            "action_kind": pending_spell.get("action_kind"),
            "effect_kind": effect_kind,
            "damage": total_damage,
            "healing": total_healing,
            "damage_type": damage_type,
            "is_critical": None,
            "is_hit": None,
            "is_saved": None,
            "new_hp": None,
            "roll": None,
            "roll_result": None,
            "target_ac": None,
            "target_display_name": first_outcome["target_display_name"] if first_outcome else "",
            "target_kind": first_outcome["target_kind"] if first_outcome else "session_entity",
            "save_ability": None,
            "save_dc": None,
            "save_success_outcome": None,
            "effect_dice": effect_dice,
            "effect_bonus": 0,
            "pending_spell_id": None,
            "pending_save_id": None,
            "effect_roll_required": False,
            "effect_rolls": effect_rolls,
            "base_effect": None,
            "effect_roll_source": req.roll_source,
            "action_cost": pending_spell.get("action_cost"),
            "summary_text": None,
            "inventory_refresh_required": False,
            "concentration_check": primary_concentration_check,
            "concentration_checks": concentration_checks,
            "area_shape": None,
            "affected_target_ref_ids": [],
            "affected_cells": [],
            "area_target_outcomes": [],
            "target_count": len(merged_outcomes),
            "elemental_affinity_eligible": bool(pending_spell.get("elemental_affinity_eligible")),
            "elemental_affinity_damage_type": pending_spell.get("elemental_affinity_damage_type"),
            "elemental_affinity_bonus": pending_spell.get("elemental_affinity_bonus"),
            "effect_instance_count": len(merged_outcomes),
            "effect_instance_dice": effect_dice,
            "base_effect_instance_count": None,
            "effect_instance_outcomes": merged_outcomes,
            "effect_instance_target_totals": cls._build_effect_instance_target_totals(merged_outcomes),
        }
