from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app.models.combat import CombatState
from app.schemas.combat import CombatStandardActionRequest
from app.schemas.roll import RollActorStats
from app.services.roll_resolution import resolve_skill_check

from .exceptions import CombatServiceError


class CombatStandardActionMixin:

    @classmethod
    async def standard_action(
        cls,
        db: Session,
        session_id: str,
        req: CombatStandardActionRequest,
        actor_user_id: str,
        is_gm: bool,
    ) -> dict:
        state = cls.get_state(db, session_id)
        cls._require_active(state)
        actor = cls._resolve_actor_participant(
            state, actor_user_id, is_gm, req.actor_participant_id,
        )
        cls._require_actor_status(actor, ("active",), "You can only use actions when active.")
        was_overridden = cls._consume_turn_resource(
            actor, "action", is_gm=is_gm, override_resource_limit=req.override_resource_limit
        )

        dispatch = {
            "dodge": cls._action_dodge,
            "help": cls._action_help,
            "hide": cls._action_hide,
            "dash": cls._action_dash,
            "disengage": cls._action_disengage,
            "use_object": cls._action_use_object,
        }
        handler = dispatch.get(req.action)
        if not handler:
            raise CombatServiceError(f"Unknown standard action: {req.action}")

        result = await handler(db, session_id, state, actor, req)

        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_state(session_id, state)
        log_message = result["message"]
        if was_overridden:
            log_message = f"[OVERRIDE: Limit for 'action' ignored] {log_message}"

        await cls._emit_log(session_id, {
            "message": log_message,
            "source": "gm_override" if is_gm else "player_turn",
            "is_override": was_overridden,
            "overridden_resource": "action" if was_overridden else None,
        })

        return {
            "action": req.action,
            "actor_name": actor["display_name"],
            **result,
        }

    # ---- individual actions ----

    @classmethod
    async def _action_dodge(cls, db, session_id, state, actor, req):
        now = datetime.now(timezone.utc).isoformat()
        effect = {
            "id": str(uuid4()),
            "source_participant_id": actor["id"],
            "kind": "dodging",
            "condition_type": None,
            "numeric_value": None,
            "duration_type": "until_turn_start",
            "remaining_rounds": None,
            "expires_on": "turn_start",
            "expires_at_participant_id": actor["id"],
            "created_at": now,
        }
        effects = cls._get_participant_effects(actor)
        effects.append(effect)
        cls._set_participant_effects(actor, effects)

        return {
            "message": f"{actor['display_name']} takes the Dodge action.",
            "effect_applied": True,
        }

    @classmethod
    async def _action_help(cls, db, session_id, state, actor, req):
        if not req.target_participant_id:
            raise CombatServiceError("Help requires a target participant.", 400)

        target_p = next(
            (p for p in state.participants if p["id"] == req.target_participant_id),
            None,
        )
        if not target_p:
            raise CombatServiceError("Target participant not found in combat.", 404)

        now = datetime.now(timezone.utc).isoformat()
        effect = {
            "id": str(uuid4()),
            "source_participant_id": actor["id"],
            "kind": "advantage_on_attacks",
            "condition_type": None,
            "numeric_value": None,
            "duration_type": "until_turn_start",
            "remaining_rounds": None,
            "expires_on": "turn_start",
            "expires_at_participant_id": target_p["id"],
            "created_at": now,
        }
        effects = cls._get_participant_effects(target_p)
        effects.append(effect)
        cls._set_participant_effects(target_p, effects)

        return {
            "message": f"{actor['display_name']} helps {target_p['display_name']} with their next attack.",
            "effect_applied": True,
        }

    @classmethod
    async def _action_hide(cls, db, session_id, state, actor, req):
        roll_stats = cls._build_roll_actor_stats_for_skill(
            db, session_id, actor["ref_id"], actor["kind"], actor["display_name"],
        )
        roll_result = resolve_skill_check(
            roll_stats,
            "stealth",
            roll_source=req.roll_source,
            manual_roll=req.manual_roll,
            manual_rolls=req.manual_rolls,
        )

        now = datetime.now(timezone.utc).isoformat()
        effect = {
            "id": str(uuid4()),
            "source_participant_id": actor["id"],
            "kind": "hidden",
            "condition_type": None,
            "numeric_value": None,
            "duration_type": "manual",
            "remaining_rounds": None,
            "expires_on": None,
            "expires_at_participant_id": None,
            "created_at": now,
        }
        effects = cls._get_participant_effects(actor)
        effects.append(effect)
        cls._set_participant_effects(actor, effects)

        total = roll_result.total if hasattr(roll_result, "total") else None
        return {
            "message": f"{actor['display_name']} attempts to hide (Stealth: {total}).",
            "effect_applied": True,
            "roll_result": roll_result,
        }

    @classmethod
    async def _action_use_object(cls, db, session_id, state, actor, req):
        desc = req.description or "an object"
        return {
            "message": f"{actor['display_name']} uses {desc}.",
            "effect_applied": False,
        }

    @classmethod
    async def _action_dash(cls, db, session_id, state, actor, req):
        return {
            "message": f"{actor['display_name']} takes the Dash action.",
            "effect_applied": False,
        }

    @classmethod
    async def _action_disengage(cls, db, session_id, state, actor, req):
        return {
            "message": f"{actor['display_name']} takes the Disengage action.",
            "effect_applied": False,
        }

    # ---- helpers ----

    @classmethod
    def _build_roll_actor_stats_for_skill(
        cls,
        db: Session,
        session_id: str,
        ref_id: str,
        kind: str,
        display_name: str,
    ) -> RollActorStats:
        if kind == "player":
            target_model, _, _, _, prof_bonus, _ = cls._get_stats(db, ref_id, kind, session_id)
            data = cls._as_dict(target_model.state_json)
            abilities = {
                ability_name: cls._safe_int(value, 10)
                for ability_name, value in cls._as_dict(data.get("abilities")).items()
                if ability_name in cls._ENTITY_ABILITY_ALIASES
            }
            skills = cls._as_dict(data.get("skills"))
            return RollActorStats(
                display_name=display_name,
                abilities=abilities,
                skills=skills or None,
                proficiency_bonus=prof_bonus,
                actor_kind="player",
                actor_ref_id=ref_id,
            )

        session_entity, npc = cls._get_session_entity_and_campaign_entity(db, ref_id)
        overrides = cls._as_dict(session_entity.overrides)
        abilities = {
            ability_name: cls._get_entity_ability_score(cls._as_dict(npc.abilities), overrides, ability_name)
            for ability_name in cls._ENTITY_ABILITY_ALIASES
        }
        skills = cls._get_entity_skill_overrides(npc, overrides) or None
        _, _, _, _, prof_bonus, _ = cls._get_stats(db, ref_id, kind, session_id)
        return RollActorStats(
            display_name=display_name,
            abilities=abilities,
            skills=skills,
            proficiency_bonus=prof_bonus,
            actor_kind="session_entity",
            actor_ref_id=ref_id,
        )
