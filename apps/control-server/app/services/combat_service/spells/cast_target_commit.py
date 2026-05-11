from __future__ import annotations

from sqlalchemy.orm.attributes import flag_modified


class CastTargetCommitMixin:
    @classmethod
    async def _commit_cast_result(
        cls, db, session_id, state, attacker, spell_context,
        resolution, actor_user_id, is_gm,
    ):
        result = resolution["result"]
        spell_mode = resolution["spell_mode"]
        effect_kind = resolution["effect_kind"]
        effect_bonus = resolution["effect_bonus"]
        save_success_outcome = resolution["save_success_outcome"]
        slot_spent = resolution["slot_spent"]
        inventory_refresh_required = resolution["inventory_refresh_required"]
        summary_text = resolution["summary_text"]
        custom_log_message = resolution["custom_log_message"]
        automation_player_state_ids = resolution["automation_player_state_ids"]
        was_overridden = resolution["was_overridden"]
        action_cost = resolution["action_cost"]
        target_p = resolution["target_p"]
        automation_result = resolution["automation_result"]
        on_hit_applied_declarative_effects_by_target = resolution.get(
            "on_hit_applied_declarative_effects_by_target"
        )

        # Spell casts mutate nested participant JSON (turn resources, pending saves,
        # declarative active effects). Mark it dirty so the combat state persists.
        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)

        player_state_ids_to_emit = set(automation_player_state_ids or ())
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
        await cls._emit_and_persist_log(
            db, session_id, actor_user_id, attacker.get("display_name"),
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
            on_hit_applied_declarative_effects_by_target=on_hit_applied_declarative_effects_by_target,
        )
