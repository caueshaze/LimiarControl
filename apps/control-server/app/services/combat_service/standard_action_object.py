from __future__ import annotations

from datetime import datetime, timezone

from .exceptions import CombatServiceError


class CombatStandardObjectActionMixin:
    @classmethod
    async def _action_use_object(cls, db, session_id, state, actor, req):
        if req.inventory_item_id:
            from . import standard_actions as standard_actions_module

            session_entry = cls._get_session_entry(db, session_id)
            if not session_entry:
                raise CombatServiceError("Session not found", 404)
            if actor.get("kind") != "player":
                raise CombatServiceError("Only players can use structured consumables in combat.", 400)
            try:
                context = standard_actions_module.resolve_healing_consumable(db, session_entry=session_entry, actor_user_id=actor["ref_id"], inventory_item_id=req.inventory_item_id)
                healing_roll = standard_actions_module.roll_healing_consumable(context.item, roll_source=req.roll_source, manual_rolls=req.manual_rolls)
            except standard_actions_module.HealingConsumableError as error:
                raise CombatServiceError(error.detail, error.status_code) from error
            target = cls._resolve_use_object_target(state, actor, req.target_participant_id)
            if not cls._is_friendly_use_object_target(actor, target):
                raise CombatServiceError("Healing consumables can only target yourself or an allied participant.", 400)
            new_hp, effect_msg, previous_hp = cls._apply_healing_to_target(db, target["ref_id"], target["kind"], healing_roll.total_healing, state)
            remaining_quantity = standard_actions_module.consume_inventory_item(db, context.inventory_item)
            timestamp = datetime.now(timezone.utc)
            target_player_user_id = target["ref_id"] if target["kind"] == "player" else None
            target_player_state = None
            if target["kind"] == "player":
                target_player_state, *_ = cls._get_stats(db, target["ref_id"], target["kind"], session_id)
                max_hp = cls._safe_int(cls._as_dict(target_player_state.state_json).get("maxHP"), 0)
            else:
                session_entity, npc = cls._get_session_entity_and_campaign_entity(db, target["ref_id"])
                max_hp = npc.max_hp if npc else session_entity.current_hp
            consumable_payload = standard_actions_module.build_consumable_used_payload(
                context=context,
                target_kind=target["kind"],
                target_ref_id=target["ref_id"],
                target_user_id=target_player_user_id,
                target_display_name=target["display_name"],
                healing=healing_roll.total_healing,
                new_hp=new_hp,
                previous_hp=previous_hp,
                max_hp=max_hp,
                remaining_quantity=remaining_quantity,
                roll=healing_roll,
                timestamp=timestamp,
            )
            standard_actions_module.record_consumable_used_activity(db, context=context, payload=consumable_payload, created_at=timestamp)
            return {
                "message": f"{actor['display_name']} uses {context.item.name} on {target['display_name']} and restores {healing_roll.total_healing} HP{effect_msg}.",
                "effect_applied": True,
                "target_display_name": target["display_name"],
                "target_kind": target["kind"],
                "healing": healing_roll.total_healing,
                "new_hp": new_hp,
                "effect_dice": healing_roll.effect_dice,
                "effect_rolls": healing_roll.effect_rolls,
                "effect_roll_source": healing_roll.roll_source,
                "_target_player_user_id": target_player_user_id,
                "_target_player_state": target_player_state,
                "_target_entity_ref_id": target["ref_id"] if target["kind"] == "session_entity" else None,
                "_target_previous_hp": previous_hp,
                "_consumable_payload": consumable_payload,
                "_consumable_timestamp": timestamp,
            }
        desc = req.description or "an object"
        return {"message": f"{actor['display_name']} uses {desc}.", "effect_applied": False}

    @classmethod
    def _resolve_use_object_target(cls, state, actor: dict, target_participant_id: str | None) -> dict:
        if not target_participant_id:
            return actor
        target = next((participant for participant in state.participants if participant["id"] == target_participant_id), None)
        if not target:
            raise CombatServiceError("Target participant not found in combat.", 404)
        return target

    @classmethod
    def _resolve_required_hostile_target(cls, state, actor: dict, target_participant_id: str | None) -> dict:
        if not target_participant_id:
            raise CombatServiceError("This action requires a target participant.", 400)
        target = cls._resolve_use_object_target(state, actor, target_participant_id)
        cls._assert_hostile_action_allowed(actor, target, action_label="Dragonborn Breath Weapon")
        return target

    @classmethod
    def _is_friendly_use_object_target(cls, actor: dict, target: dict) -> bool:
        if actor.get("id") == target.get("id"):
            return True
        actor_team = actor.get("team")
        target_team = target.get("team")
        if actor_team in ("players", "allies"):
            return target_team in ("players", "allies")
        if actor_team == "enemies":
            return target_team == "enemies"
        return False
