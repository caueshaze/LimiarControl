from __future__ import annotations

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app.schemas.combat import CombatResolveDamageRequest
from app.schemas.roll import RollResult
from app.services.combat_service.sanctuary_guard import break_sanctuary_if_active, resolve_sanctuary_guard
from app.services.roll_resolution import resolve_attack_base, resolve_saving_throw

from .combat_targeting import get_combat_targeting_service
from .exceptions import CombatServiceError, _roll_dice_expression
from .npc_action_commit import CombatNpcActionCommitMixin
from .npc_action_resolution import CombatNpcActionResolutionMixin
from .npc_action_steps import CombatNpcActionStepsMixin


class CombatNpcActionMixin(
    CombatNpcActionStepsMixin,
    CombatNpcActionResolutionMixin,
    CombatNpcActionCommitMixin,
):
    @classmethod
    def _generate_uuid(cls) -> str:
        from uuid import uuid4

        return str(uuid4())

    @classmethod
    async def entity_action(
        cls,
        db: Session,
        session_id: str,
        req,
        actor_user_id: str,
        is_gm: bool,
    ):
        context = cls._validate_npc_action_request(
            db, session_id, req, actor_user_id, is_gm
        )
        context["target_p"] = cls._resolve_npc_target_participant(
            context["state"],
            context["attacker"],
            req,
            context["action_kind"],
        )
        if context["target_p"] is not None and isinstance(
            context["resolved_action"].get("spellCanonicalKey"), str
        ):
            cls._validate_spell_automation_target(
                db,
                session_id,
                spell_canonical_key=context["resolved_action"].get("spellCanonicalKey"),
                target_participant=context["target_p"],
            )
        # Break attacker's own sanctuary when they declare a hostile attack.
        if context["action_kind"] in ("weapon_attack", "spell_attack") and context["target_p"] is not None:
            if cls._is_hostile_team_context(context["attacker"], context["target_p"]):
                break_sanctuary_if_active(context["attacker"], context["state"])
        # Check if the target is protected by Sanctuary for direct attacks.
        if context["action_kind"] in ("weapon_attack", "spell_attack") and context["target_p"] is not None:
            if cls._is_hostile_team_context(context["attacker"], context["target_p"]):
                sanctuary_block = resolve_sanctuary_guard(
                    db=db,
                    session_id=session_id,
                    attacker_participant=context["attacker"],
                    target_participant=context["target_p"],
                )
                if sanctuary_block:
                    target_name = context["target_p"].get("display_name", "")
                    attacker_name = context["attacker"].get("display_name", "")
                    flag_modified(context["state"], "participants")
                    db.add(context["state"])
                    db.commit()
                    db.refresh(context["state"])
                    await cls._emit_state(session_id, context["state"])
                    await cls._emit_and_persist_log(
                        db, session_id, actor_user_id, attacker_name,
                        {
                            "message": (
                                f"{attacker_name} falhou no teste de Sabedoria contra o Santuário de {target_name} "
                                f"(CD {sanctuary_block['guard_save_dc']}, resultado {sanctuary_block['save_roll']})."
                            ),
                            "actorUserId": actor_user_id,
                            "source": "gm_override" if is_gm else "entity_turn",
                            "is_override": False,
                        },
                    )
                    return {
                        "is_hit": False,
                        "damage": 0,
                        "is_critical": False,
                        "new_hp": None,
                        "action_name": context["action_name"],
                        "action_kind": context["action_kind"],
                        "target_display_name": target_name,
                        "blocked_by": "sanctuary",
                        "retarget_required": True,
                    }
        result = cls._resolve_npc_action_result(
            db,
            session_id,
            req,
            is_gm,
            state=context["state"],
            attacker=context["attacker"],
            resolved_action=context["resolved_action"],
            action_name=context["action_name"],
            action_kind=context["action_kind"],
            damage_type=context["damage_type"],
            target_p=context["target_p"],
        )
        return await cls._commit_npc_action_result(
            db,
            session_id,
            actor_user_id,
            state=context["state"],
            attacker=context["attacker"],
            resolved_action=context["resolved_action"],
            action_cost=context["action_cost"],
            was_overridden=context["was_overridden"],
            result=result,
        )

    @classmethod
    async def entity_action_damage(
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
        if attacker["kind"] != "session_entity":
            raise CombatServiceError("Only session entities can use combat actions.", 400)
        if not is_gm:
            raise CombatServiceError("Only GM can act for NPCs.", 403)
        cls._require_actor_status(
            attacker, ("active",), "You can only roll damage when active."
        )

        pending_attack = cls._require_pending_attack(
            attacker,
            req.pending_attack_id,
            expected_type="entity_attack",
        )
        damage_dice = pending_attack.get("damage_dice") or ""
        damage_rolls, base_damage = cls._resolve_damage_roll(
            damage_dice,
            critical=bool(pending_attack.get("is_critical")),
            roll_source=req.roll_source,
            manual_rolls=req.manual_rolls,
        )
        damage_bonus = cls._safe_int(pending_attack.get("damage_bonus"), 0)
        effect_damage_bonus = cls._sum_numeric_effects(attacker, "damage_bonus")
        damage = max(0, base_damage + damage_bonus + effect_damage_bonus)
        target_ref_id = pending_attack.get("target_ref_id")
        target_kind = pending_attack.get("target_kind")
        target_display_name = pending_attack.get("target_display_name") or "Target"
        if not isinstance(target_ref_id, str) or not isinstance(target_kind, str):
            raise CombatServiceError(
                "Pending damage roll is missing target information.", 400
            )

        new_hp = None
        previous_hp = None
        effect_msg = ""
        concentration_check = None
        if damage > 0:
            new_hp, effect_msg, previous_hp, concentration_check = cls._apply_damage_to_target(
                db,
                target_ref_id,
                target_kind,
                damage,
                damage_type=pending_attack.get("damage_type"),
                is_crit=bool(pending_attack.get("is_critical")),
                state=state,
                attacker_participant_id=attacker.get("id"),
                **cls._build_concentration_roll_kwargs(
                    req.concentration_roll_source,
                    req.concentration_manual_roll,
                ),
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
            target_state, *_ = cls._get_stats(db, target_ref_id, target_kind, session_id)
            await cls._emit_player_state_update(db, session_id, target_ref_id, target_state)
        elif damage > 0 and previous_hp != new_hp:
            await cls._emit_entity_hp_update(db, session_id, target_ref_id, previous_hp)
        await cls._emit_state(session_id, state)

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
                    f"{attacker['display_name']} used {pending_attack.get('action_name') or 'Combat Action'} "
                    f"on {target_display_name} and dealt {damage} damage.{effect_msg}{concentration_summary}"
                ),
                "actorUserId": actor_user_id,
                "source": "gm_override",
            },
        )

        return {
            "action_name": pending_attack.get("action_name") or "Combat Action",
            "action_kind": pending_attack.get("action_kind") or "weapon_attack",
            "damage": damage,
            "damage_type": pending_attack.get("damage_type"),
            "healing": 0,
            "is_critical": bool(pending_attack.get("is_critical")),
            "is_hit": True,
            "is_saved": None,
            "new_hp": new_hp,
            "roll": cls._safe_int(pending_attack.get("roll"), 0),
            "save_dc": None,
            "save_roll": None,
            "roll_result": roll_result,
            "target_ac": cls._safe_int(pending_attack.get("target_ac"), 10),
            "target_display_name": target_display_name,
            "damage_dice": damage_dice or None,
            "damage_bonus": damage_bonus,
            "attack_bonus": cls._safe_int(pending_attack.get("attack_bonus"), 0),
            "pending_attack_id": None,
            "damage_roll_required": False,
            "damage_rolls": damage_rolls,
            "base_damage": base_damage,
            "damage_roll_source": req.roll_source,
            "concentration_check": concentration_check,
        }
