from __future__ import annotations

from sqlalchemy.orm.attributes import flag_modified

from app.schemas.roll import RollResult

from ..exceptions import CombatServiceError


class CastTargetEffectMixin:
    @classmethod
    async def cast_spell_effect(
        cls,
        db,
        session_id: str,
        req,
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

        ws_model, *_ = cls._get_stats(
            db, attacker["ref_id"], attacker["kind"], session_id
        )
        ws_data = cls._as_dict(ws_model.state_json)
        if cls._as_dict(ws_data.get("wildShape")).get("active"):
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
        target_participant = next(
            (
                participant
                for participant in state.participants
                if participant.get("ref_id") == target_ref_id and participant.get("kind") == target_kind
            ),
            None,
        )
        pending_spell_context = cls._build_pending_spell_context_from_payload(
            pending_spell,
            target_participant=target_participant,
        )
        manual_notes_by_target = pending_spell_context.get("manual_notes_by_target")
        applied_declarative_effects_by_target = None

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
            new_hp, effect_msg, previous_hp, concentration_check = cls._apply_spell_effect(
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
        if target_participant is not None and cls._spell_context_has_declarative_effects(
            pending_spell_context
        ):
            declarative_application = cls._apply_declarative_spell_effects(
                state=state,
                attacker=attacker,
                target_participant=target_participant,
                spell_context=pending_spell_context,
            )
            applied_declarative_effects_by_target = cls._build_applied_declarative_effects_by_target(
                declarative_application.get("applied_effects")
            )

        cls._clear_participant_pending_attack(attacker)
        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)

        if amount > 0 and target_kind == "player":
            target_state, *_ = cls._get_stats(db, target_ref_id, target_kind, session_id)
            await cls._emit_player_state_update(
                db, session_id, target_ref_id, target_state
            )
        elif amount > 0 and previous_hp != new_hp:
            await cls._emit_entity_hp_update(db, session_id, target_ref_id, previous_hp)
        await cls._emit_state(session_id, state)

        spell_name = pending_spell.get("spell_name") or "a spell"
        log_message = (
            f"{attacker['display_name']} resolved {spell_name} "
            f"on {target_display_name}: {amount} {effect_kind}."
        )
        if (
            pending_spell.get("action_kind") == "saving_throw"
            and effect_kind == "damage"
            and bool(pending_spell.get("is_saved"))
            and save_success_outcome == "half_damage"
        ):
            log_message = (
                f"{attacker['display_name']} resolved {spell_name} on {target_display_name}: "
                f"Dano rolado {rolled_effect_total}; dano aplicado {amount} de "
                f"{pending_spell.get('damage_type') or 'energia'}."
            )
        if effect_msg:
            log_message = f"{log_message} {effect_msg}".strip()
        if isinstance(concentration_check, dict) and isinstance(
            concentration_check.get("summary_text"), str
        ):
            log_message = f"{log_message} {concentration_check['summary_text']}".strip()
        log_message = (
            f"{log_message}"
            f"{cls._format_variant_assignments_for_log(pending_spell_context.get('target_variant_assignments'), manual_notes_by_target)}"
            f"{cls._format_manual_notes_for_log(manual_notes_by_target)}"
            f"{cls._format_concentration_group_for_log(pending_spell_context.get('concentration_group'))}"
        ).strip()

        await cls._emit_and_persist_log(
            db, session_id, actor_user_id, attacker.get("display_name"),
            {
                "message": log_message,
                "actorUserId": actor_user_id,
                "source": "gm_override" if is_gm else "player_turn",
            },
        )

        return {
            "spell_name": pending_spell.get("spell_name"),
            "spell_canonical_key": pending_spell.get("spell_canonical_key"),
            "selected_variant_key": pending_spell_context.get("selected_variant_key"),
            "selected_variant_label": pending_spell_context.get("selected_variant_label"),
            "context_origin": "pending_spell",
            "concentration_group": pending_spell_context.get("concentration_group"),
            "action_kind": pending_spell.get("action_kind"),
            "effect_kind": effect_kind,
            "damage": amount if effect_kind == "damage" else 0,
            "healing": amount if effect_kind == "healing" else 0,
            "damage_type": pending_spell.get("damage_type"),
            "is_critical": bool(pending_spell.get("is_critical")),
            "is_hit": None if pending_spell.get("action_kind") != "spell_attack" else True,
            "is_saved": pending_spell.get("is_saved"),
            "new_hp": new_hp,
            "roll": pending_spell.get("roll"),
            "roll_result": roll_result,
            "target_ac": pending_spell.get("target_ac"),
            "target_display_name": target_display_name,
            "target_kind": target_kind,
            "save_ability": pending_spell.get("save_ability"),
            "save_dc": pending_spell.get("save_dc"),
            "save_success_outcome": save_success_outcome,
            "effect_dice": effect_dice,
            "effect_bonus": effect_bonus,
            "pending_spell_id": None,
            "effect_roll_required": False,
            "base_effect": base_effect if effect_dice else None,
            "action_cost": pending_spell.get("action_cost"),
            "summary_text": None,
            "inventory_refresh_required": False,
            "concentration_check": concentration_check,
            "elemental_affinity_eligible": bool(
                pending_spell.get("elemental_affinity_eligible")
            ),
            "elemental_affinity_damage_type": pending_spell.get(
                "elemental_affinity_damage_type"
            ),
            "elemental_affinity_bonus": pending_spell.get("elemental_affinity_bonus"),
            "effect_rolls": effect_rolls,
            "effect_roll_source": req.roll_source,
            "target_variant_assignments": pending_spell_context.get("target_variant_assignments"),
            "manual_notes_by_target": manual_notes_by_target,
            "applied_declarative_effects_by_target": applied_declarative_effects_by_target,
        }
