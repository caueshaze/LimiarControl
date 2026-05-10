from __future__ import annotations

from typing import Any

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app.models.combat import CombatState
from app.schemas.combat import CombatResolveSpellEffectRequest
from app.schemas.roll import RollResult

from ..exceptions import CombatServiceError


class CastAreaEffectMixin:

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
        guardrail_outcomes_payload = pending_spell.get("area_guardrail_outcomes")
        guardrail_outcomes = (
            [item for item in guardrail_outcomes_payload if isinstance(item, dict)]
            if isinstance(guardrail_outcomes_payload, list)
            else []
        )

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

        area_target_outcomes.extend(guardrail_outcomes)

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
        resolved_target_outcomes = [
            outcome for outcome in area_target_outcomes if not outcome.get("excluded_by_guardrail")
        ]
        guardrail_blocked_count = target_count - len(resolved_target_outcomes)
        saved_count = sum(1 for outcome in resolved_target_outcomes if outcome.get("is_saved"))
        failed_count = len(resolved_target_outcomes) - saved_count
        log_text = (
            f"{attacker['display_name']} resolveu {pending_spell.get('spell_name') or 'magia'} em area: "
            f"{target_count} alvo{'s' if target_count != 1 else ''}, "
            f"{failed_count} falhou/falharam no save, {saved_count} passou/passaram. "
            f"Dano rolado {rolled_effect_total}; dano total aplicado {total_damage}."
        )
        if guardrail_blocked_count > 0:
            log_text = (
                f"{log_text} {guardrail_blocked_count} alvo{'s' if guardrail_blocked_count != 1 else ''} "
                "foram excluídos por regras mecânicas."
            )
        if concentration_checks:
            summaries = [
                check.get("summary_text")
                for check in concentration_checks
                if isinstance(check.get("summary_text"), str)
            ]
            if summaries:
                log_text = f"{log_text} {' '.join(summaries)}".strip()

        await cls._emit_and_persist_log(db, session_id, actor_user_id, attacker.get("display_name"), {
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
