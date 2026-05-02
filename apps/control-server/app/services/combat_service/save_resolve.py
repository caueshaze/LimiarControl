from __future__ import annotations

import logging
from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified

from app.services.combat_service.condition_effects_saves import modify_saving_throw
from app.services.roll_resolution import resolve_saving_throw

from .exceptions import CombatServiceError

logger = logging.getLogger(__name__)


class CombatSaveResolveMixin:
    @classmethod
    async def resolve_pending_save(cls, db, session_id: str, req, actor_user_id: str, is_gm: bool):
        state = cls.get_state(db, session_id)
        cls._require_active(state)

        target_p = next(
            (p for p in state.participants if p["id"] == req.target_participant_id),
            None,
        )
        if not target_p:
            raise CombatServiceError("Target participant not found.", 404)
        if not is_gm and not (
            target_p.get("kind") == "player" and target_p.get("actor_user_id") == actor_user_id
        ):
            raise CombatServiceError("Only the target player or GM can resolve this save.", 403)

        pending_save = target_p.get("pending_save")
        if not isinstance(pending_save, dict) or pending_save.get("id") != req.pending_save_id:
            raise CombatServiceError("Pending save not found.", 404)
        if pending_save.get("status") != "pending":
            raise CombatServiceError("Save has already been resolved.", 400)

        save_ability = pending_save["save_ability"]
        save_dc = cls._safe_int(pending_save.get("save_dc"), 0)
        save_mod = modify_saving_throw(target_p, save_ability)

        roll_result = resolve_saving_throw(
            cls._build_roll_actor_stats_for_save(
                db, session_id, target_p["ref_id"], target_p["kind"], target_p["display_name"]
            ),
            ability=save_ability,
            advantage_mode=save_mod.result,
            dc=save_dc,
            roll_source=req.roll_source,
            manual_roll=req.manual_roll,
            manual_rolls=req.manual_rolls,
        )
        roll_result.is_gm_roll = True
        is_saved = False if save_mod.auto_fail else bool(roll_result.success)

        effect_kind = pending_save.get("effect_kind") or "damage"
        effect_bonus = cls._safe_int(pending_save.get("effect_bonus"), 0)
        effect_dice = pending_save.get("effect_dice")
        effect_roll_required = bool(pending_save.get("effect_roll_required"))
        save_success_outcome = cls._normalize_save_success_outcome(
            pending_save.get("save_success_outcome")
        )
        damage_type = pending_save.get("damage_type")
        attacker_ref_id = pending_save.get("attacker_ref_id")
        attacker_participant_id = pending_save.get("attacker_participant_id")
        attacker_display_name = pending_save.get("attacker_display_name", "Unknown")

        pending_save["status"] = "resolved"
        target_p.pop("pending_save", None)
        flag_modified(state, "participants")

        pending_spell_id = None
        effect_rolls: list[int] = []
        base_effect: int | None = None
        amount = 0
        new_hp = None
        effect_msg = ""
        previous_hp = None
        concentration_check = None

        attacker = next(
            (p for p in state.participants if p["id"] == attacker_participant_id),
            None,
        )
        pending_spell_context = cls._build_pending_spell_context_from_payload(
            pending_save,
            target_participant=target_p,
        )
        manual_notes_by_target = pending_spell_context.get("manual_notes_by_target")
        applied_declarative_effects_by_target = None

        if effect_roll_required and (not is_saved or save_success_outcome == "half_damage"):
            if attacker:
                pending_spell_id = cls._create_pending_spell_effect(
                    state,
                    attacker,
                    {
                        "spell_name": pending_save.get("spell_name", "Spell"),
                        "spell_canonical_key": pending_save.get("spell_canonical_key"),
                        "action_kind": "saving_throw",
                        "effect_kind": effect_kind,
                        "effect_dice": effect_dice,
                        "effect_bonus": effect_bonus,
                        "damage_type": damage_type,
                        "elemental_affinity_eligible": pending_save.get("elemental_affinity_eligible"),
                        "elemental_affinity_damage_type": pending_save.get("elemental_affinity_damage_type"),
                        "elemental_affinity_bonus": pending_save.get("elemental_affinity_bonus"),
                        "target_ref_id": target_p["ref_id"],
                        "target_kind": target_p["kind"],
                        "target_display_name": target_p["display_name"],
                        "save_ability": save_ability,
                        "save_dc": save_dc,
                        "is_saved": is_saved,
                        "is_critical": False,
                        "roll": roll_result.total,
                        "roll_result": roll_result.model_dump(mode="json"),
                        "save_success_outcome": save_success_outcome,
                        "variant_scope": pending_save.get("variant_scope"),
                        "selected_variant_key": pending_spell_context.get("selected_variant_key"),
                        "selected_variant_label": pending_spell_context.get("selected_variant_label"),
                        "context_origin": "pending_save",
                        "concentration_group": pending_spell_context.get("concentration_group"),
                        "target_variant_assignments": pending_spell_context.get("target_variant_assignments"),
                        "manual_notes_by_target": manual_notes_by_target,
                        "effects": pending_spell_context.get("effects"),
                        "on_end_effects": pending_spell_context.get("on_end_effects"),
                    },
                )
        elif not is_saved or save_success_outcome == "half_damage":
            if isinstance(effect_dice, str) and effect_dice.strip():
                effect_rolls, base_effect = cls._resolve_damage_roll(
                    effect_dice,
                    critical=False,
                    roll_source="system",
                )
                rolled_total = max(0, (base_effect or 0) + effect_bonus)
            else:
                rolled_total = max(0, effect_bonus)

            if effect_kind == "damage" and pending_save.get("action_kind") != "spell_attack":
                amount = cls._resolve_save_damage_amount(
                    rolled_total, is_saved=is_saved, save_success_outcome=save_success_outcome
                )
            else:
                amount = rolled_total

            if amount > 0:
                concentration_roll_source = pending_save.get("concentration_roll_source") or "system"
                new_hp, effect_msg, previous_hp, concentration_check = cls._apply_spell_effect(
                    db, state, target_p["ref_id"], target_p["kind"], effect_kind, amount,
                    damage_type=damage_type,
                    concentration_roll_source=concentration_roll_source,
                )

        db.add(state)
        db.commit()
        db.refresh(state)

        refreshed_attacker = next(
            (p for p in state.participants if p["id"] == attacker_participant_id),
            None,
        )
        if refreshed_attacker:
            refreshed_attacker["last_save_resolution"] = {
                "spell_name": pending_save.get("spell_name", "Spell"),
                "pending_save_id": req.pending_save_id,
                "target_display_name": target_p["display_name"],
                "save_ability": save_ability,
                "save_dc": save_dc,
                "is_saved": is_saved,
                "roll_total": roll_result.total,
                "damage": amount if effect_kind == "damage" else 0,
                "healing": amount if effect_kind == "healing" else 0,
                "damage_type": damage_type,
                "effect_kind": effect_kind,
                "new_hp": new_hp,
                "roll_result": roll_result.model_dump(mode="json"),
                "pending_spell_id": pending_spell_id,
                "selected_variant_key": pending_spell_context.get("selected_variant_key"),
                "selected_variant_label": pending_spell_context.get("selected_variant_label"),
                "context_origin": "pending_save",
                "concentration_group": pending_spell_context.get("concentration_group"),
                "target_variant_assignments": pending_spell_context.get("target_variant_assignments"),
                "manual_notes_by_target": manual_notes_by_target,
                "applied_declarative_effects_by_target": applied_declarative_effects_by_target,
            }
            flag_modified(state, "participants")
            db.add(state)
            db.commit()
            db.refresh(state)

        if amount > 0 and target_p["kind"] == "session_entity" and previous_hp != new_hp:
            await cls._emit_entity_hp_update(db, session_id, target_p["ref_id"], previous_hp)
        await cls._emit_state(session_id, state)

        save_text = "passou" if is_saved else "falhou"
        spell_name = pending_save.get("spell_name", "a spell")
        target_name = target_p["display_name"]
        log_message = (
            f"{target_name} {save_text} no teste de {save_ability} contra CD {save_dc} "
            f"para {spell_name} (lancado por {attacker_display_name})."
        )
        if amount > 0:
            log_message += f" {amount} de {effect_kind} de {damage_type or 'energia'}{effect_msg}"
        if pending_spell_id:
            log_message += " Efeito pendente."
        log_message = (
            f"{log_message}"
            f"{cls._format_variant_assignments_for_log(pending_spell_context.get('target_variant_assignments'), manual_notes_by_target)}"
            f"{cls._format_manual_notes_for_log(manual_notes_by_target)}"
            f"{cls._format_concentration_group_for_log(pending_spell_context.get('concentration_group'))}"
        ).strip()
        await cls._emit_log(session_id, {
            "message": log_message,
            "actorUserId": actor_user_id,
            "source": "gm_save_resolve",
        })

        return {
            "spell_name": spell_name,
            "spell_canonical_key": pending_save.get("spell_canonical_key"),
            "action_kind": "saving_throw",
            "effect_kind": effect_kind,
            "damage": amount if effect_kind == "damage" else 0,
            "healing": amount if effect_kind == "healing" else 0,
            "damage_type": damage_type,
            "selected_variant_key": pending_spell_context.get("selected_variant_key"),
            "selected_variant_label": pending_spell_context.get("selected_variant_label"),
            "context_origin": "pending_save",
            "concentration_group": pending_spell_context.get("concentration_group"),
            "is_critical": False,
            "is_hit": None,
            "is_saved": is_saved,
            "new_hp": new_hp,
            "roll": roll_result.total,
            "roll_result": roll_result,
            "target_ac": None,
            "target_display_name": target_p["display_name"],
            "target_kind": target_p["kind"],
            "save_ability": save_ability,
            "save_dc": save_dc,
            "save_success_outcome": save_success_outcome,
            "effect_dice": effect_dice,
            "effect_bonus": effect_bonus,
            "pending_spell_id": pending_spell_id,
            "pending_save_id": None,
            "effect_roll_required": bool(pending_spell_id),
            "base_effect": base_effect if effect_dice else None,
            "action_cost": None,
            "summary_text": None,
            "inventory_refresh_required": False,
            "concentration_check": concentration_check,
            "elemental_affinity_eligible": bool(pending_save.get("elemental_affinity_eligible")),
            "elemental_affinity_damage_type": pending_save.get("elemental_affinity_damage_type"),
            "elemental_affinity_bonus": pending_save.get("elemental_affinity_bonus"),
            "effect_rolls": effect_rolls,
            "effect_roll_source": req.roll_source,
            "target_variant_assignments": pending_spell_context.get("target_variant_assignments"),
            "manual_notes_by_target": manual_notes_by_target,
            "applied_declarative_effects_by_target": applied_declarative_effects_by_target,
        }
