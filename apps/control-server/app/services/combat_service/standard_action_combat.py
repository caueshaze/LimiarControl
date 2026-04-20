from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified
from app.schemas.roll import RollActorStats
from app.services.dragonborn_breath_weapon import DRAGONBORN_BREATH_WEAPON_ACTION_ID
from app.services.roll_resolution import resolve_skill_check

from .exceptions import CombatServiceError
from .standard_action_object import CombatStandardObjectActionMixin


class CombatStandardCombatActionMixin(CombatStandardObjectActionMixin):
    @classmethod
    async def standard_action(cls, db, session_id: str, req, actor_user_id: str, is_gm: bool) -> dict:
        state = cls.get_state(db, session_id)
        cls._require_active(state)
        actor = cls._resolve_actor_participant(state, actor_user_id, is_gm, req.actor_participant_id)
        cls._require_actor_status(actor, ("active",), "You can only use actions when active.")
        cls._require_action_capable(actor)
        dispatch = {
            "dodge": cls._action_dodge,
            "help": cls._action_help,
            "hide": cls._action_hide,
            "dash": cls._action_dash,
            "disengage": cls._action_disengage,
            "use_object": cls._action_use_object,
            DRAGONBORN_BREATH_WEAPON_ACTION_ID: cls._action_dragonborn_breath_weapon,
        }
        handler = dispatch.get(req.action)
        if not handler:
            raise CombatServiceError(f"Unknown standard action: {req.action}")
        if req.action == DRAGONBORN_BREATH_WEAPON_ACTION_ID:
            cls._precheck_dragonborn_breath_weapon(db, session_id, state, actor, req)
        was_overridden = cls._consume_turn_resource(actor, "action", is_gm=is_gm, override_resource_limit=req.override_resource_limit)
        result = await handler(db, session_id, state, actor, req)
        actor_player_user_id = result.pop("_actor_player_user_id", None)
        actor_player_state = result.pop("_actor_player_state", None)
        target_player_user_id = result.pop("_target_player_user_id", None)
        target_player_state = result.pop("_target_player_state", None)
        target_entity_ref_id = result.pop("_target_entity_ref_id", None)
        target_previous_hp = result.pop("_target_previous_hp", None)
        consumable_payload = result.pop("_consumable_payload", None)
        consumable_timestamp = result.pop("_consumable_timestamp", None)
        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        if actor_player_state is not None:
            db.refresh(actor_player_state)
        if target_player_state is not None:
            db.refresh(target_player_state)
        db.refresh(state)
        if actor_player_user_id and actor_player_state is not None:
            await cls._emit_player_state_update(db, session_id, actor_player_user_id, actor_player_state)
        if target_player_user_id and target_player_state is not None:
            await cls._emit_player_state_update(db, session_id, target_player_user_id, target_player_state)
        elif target_entity_ref_id and target_previous_hp is not None and result.get("new_hp") != target_previous_hp:
            await cls._emit_entity_hp_update(db, session_id, target_entity_ref_id, target_previous_hp)
        await cls._emit_state(session_id, state)
        message = result["message"]
        if was_overridden:
            message = f"[OVERRIDE: Limit for 'action' ignored] {message}"
        await cls._emit_log(session_id, {"message": message, "source": "gm_override" if is_gm else "player_turn", "is_override": was_overridden, "overridden_resource": "action" if was_overridden else None})
        if consumable_payload and consumable_timestamp:
            from . import standard_actions as standard_actions_module

            session_entry = cls._get_session_entry(db, session_id)
            if not session_entry:
                raise CombatServiceError("Session not found", 404)
            await standard_actions_module.publish_consumable_used_realtime(session_entry, payload=consumable_payload, timestamp=consumable_timestamp)
        return {"action": req.action, "actor_name": actor["display_name"], **result}

    @classmethod
    async def _action_dodge(cls, db, session_id, state, actor, req):
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
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        effects = cls._get_participant_effects(actor)
        effects.append(effect)
        cls._set_participant_effects(actor, effects)
        return {"message": f"{actor['display_name']} takes the Dodge action.", "effect_applied": True}

    @classmethod
    async def _action_help(cls, db, session_id, state, actor, req):
        if not req.target_participant_id:
            raise CombatServiceError("Help requires a target participant.", 400)
        target = next((participant for participant in state.participants if participant["id"] == req.target_participant_id), None)
        if not target:
            raise CombatServiceError("Target participant not found in combat.", 404)
        effect = {
            "id": str(uuid4()),
            "source_participant_id": actor["id"],
            "kind": "advantage_on_attacks",
            "condition_type": None,
            "numeric_value": None,
            "duration_type": "until_turn_start",
            "remaining_rounds": None,
            "expires_on": "turn_start",
            "expires_at_participant_id": target["id"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        effects = cls._get_participant_effects(target)
        effects.append(effect)
        cls._set_participant_effects(target, effects)
        return {"message": f"{actor['display_name']} helps {target['display_name']} with their next attack.", "effect_applied": True}

    @classmethod
    async def _action_hide(cls, db, session_id, state, actor, req):
        roll_result = resolve_skill_check(
            cls._build_roll_actor_stats_for_skill(db, session_id, actor["ref_id"], actor["kind"], actor["display_name"]),
            "stealth",
            roll_source=req.roll_source,
            manual_roll=req.manual_roll,
            manual_rolls=req.manual_rolls,
        )
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
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        effects = cls._get_participant_effects(actor)
        effects.append(effect)
        cls._set_participant_effects(actor, effects)
        return {"message": f"{actor['display_name']} attempts to hide (Stealth: {roll_result.total if hasattr(roll_result, 'total') else None}).", "effect_applied": True, "roll_result": roll_result}

    @classmethod
    async def _action_dash(cls, db, session_id, state, actor, req):
        return {"message": f"{actor['display_name']} takes the Dash action.", "effect_applied": False}

    @classmethod
    async def _action_disengage(cls, db, session_id, state, actor, req):
        return {"message": f"{actor['display_name']} takes the Disengage action.", "effect_applied": False}

    @classmethod
    def _build_roll_actor_stats_for_skill(cls, db, session_id: str, ref_id: str, kind: str, display_name: str) -> RollActorStats:
        if kind == "player":
            target_model, _, _, _, prof_bonus, _ = cls._get_stats(db, ref_id, kind, session_id)
            data = cls._as_dict(target_model.state_json)
            abilities = {name: cls._safe_int(value, 10) for name, value in cls._as_dict(data.get("abilities")).items() if name in cls._ENTITY_ABILITY_ALIASES}
            skills = cls._as_dict(data.get("skills"))
            return RollActorStats(display_name=display_name, abilities=abilities, skills=skills or None, proficiency_bonus=prof_bonus, actor_kind="player", actor_ref_id=ref_id)
        session_entity, npc = cls._get_session_entity_and_campaign_entity(db, ref_id)
        overrides = cls._as_dict(session_entity.overrides)
        abilities = {name: cls._get_entity_ability_score(cls._as_dict(npc.abilities), overrides, name) for name in cls._ENTITY_ABILITY_ALIASES}
        _, _, _, _, prof_bonus, _ = cls._get_stats(db, ref_id, kind, session_id)
        return RollActorStats(display_name=display_name, abilities=abilities, skills=cls._get_entity_skill_overrides(npc, overrides) or None, proficiency_bonus=prof_bonus, actor_kind="session_entity", actor_ref_id=ref_id)
