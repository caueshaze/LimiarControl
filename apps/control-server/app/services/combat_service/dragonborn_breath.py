from __future__ import annotations

from typing import Any

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app.services.dragonborn_breath_weapon import (
    DRAGONBORN_BREATH_WEAPON_RESOURCE_KEY,
    apply_dragonborn_breath_weapon_canonical_state,
    resolve_dragonborn_breath_weapon_action_state,
)
from app.services.session_state_finalize import finalize_session_state_data
from app.services.wild_shape_service import is_active as is_wild_shape_active

from .exceptions import CombatServiceError
from .host_protocol import CombatServiceHostProtocol


def _encode_storage_dict(source: dict[str, Any] | dict[bytes, Any] | None) -> dict[bytes, Any]:
    encoded: dict[bytes, Any] = {}
    if not isinstance(source, dict):
        return encoded
    for key, value in source.items():
        if isinstance(key, str):
            encoded[key.encode("utf-8")] = value
        elif isinstance(key, (bytes, bytearray)):
            encoded[bytes(key)] = value
    return encoded


def _decode_storage_dict(source: dict[bytes, Any] | dict[str, Any] | None) -> dict[str, Any]:
    decoded: dict[str, Any] = {}
    if not isinstance(source, dict):
        return decoded
    for key, value in source.items():
        decoded_key = key.decode("utf-8") if isinstance(key, (bytes, bytearray)) else str(key)
        if isinstance(value, dict):
            decoded[decoded_key] = _decode_storage_dict(value)
        else:
            decoded[decoded_key] = value
    return decoded


class CombatDragonbornBreathMixin(CombatServiceHostProtocol):

    @classmethod
    def _precheck_dragonborn_breath_weapon(cls, db, session_id, state, actor, req) -> None:
        if actor.get("kind") != "player":
            raise CombatServiceError("Only players can use Dragonborn Breath Weapon.", 400)
        target = cls._resolve_required_hostile_target(state, actor, req.target_participant_id)
        attacker_state, *_ = cls._get_stats(db, actor["ref_id"], actor["kind"], session_id)
        attacker_state_json = attacker_state.state_json if attacker_state is not None else None
        attacker_data = apply_dragonborn_breath_weapon_canonical_state(
            cls._as_dict(attacker_state_json) if attacker_state_json is not None else {},
        )
        if is_wild_shape_active(attacker_data):
            raise CombatServiceError("Cannot use Dragonborn Breath Weapon while in Wild Shape.", 400)
        action_state = resolve_dragonborn_breath_weapon_action_state(attacker_data)
        if action_state is None:
            raise CombatServiceError("Dragonborn Breath Weapon is not available for this actor.", 400)
        if cls._safe_int(action_state.get("usesRemaining"), 0) <= 0:
            raise CombatServiceError("No Dragonborn Breath Weapon uses remaining.", 400)
        cls._assert_hostile_action_allowed(
            actor,
            target,
            action_label="Dragonborn Breath Weapon",
        )

    @classmethod
    async def _action_dragonborn_breath_weapon(cls, db, session_id, state, actor, req):
        if actor.get("kind") != "player":
            raise CombatServiceError("Only players can use Dragonborn Breath Weapon.", 400)

        target = cls._resolve_required_hostile_target(state, actor, req.target_participant_id)
        attacker_state, *_ = cls._get_stats(db, actor["ref_id"], actor["kind"], session_id)
        attacker_state_json = attacker_state.state_json if attacker_state is not None else None
        attacker_data = apply_dragonborn_breath_weapon_canonical_state(
            cls._as_dict(attacker_state_json) if attacker_state_json is not None else {},
        )
        if is_wild_shape_active(attacker_data):
            raise CombatServiceError("Cannot use Dragonborn Breath Weapon while in Wild Shape.", 400)
        action_state = resolve_dragonborn_breath_weapon_action_state(attacker_data)
        if action_state is None:
            raise CombatServiceError("Dragonborn Breath Weapon is not available for this actor.", 400)

        class_resources_source = attacker_data.get("classResources")
        class_resources = _encode_storage_dict(class_resources_source if isinstance(class_resources_source, dict) else None)
        resource_key = DRAGONBORN_BREATH_WEAPON_RESOURCE_KEY.encode("utf-8")
        resource_source = class_resources.get(resource_key)
        resource = _encode_storage_dict(resource_source if isinstance(resource_source, dict) else None)
        uses_max_key = b"usesMax"
        uses_remaining_key = b"usesRemaining"
        uses_max = cls._safe_int(
            resource.get(uses_max_key),
            cls._safe_int(action_state.get("usesMax"), 1),
        )
        uses_remaining = cls._safe_int(resource.get(uses_remaining_key), uses_max)
        if uses_remaining <= 0:
            raise CombatServiceError("No Dragonborn Breath Weapon uses remaining.", 400)

        resource[uses_max_key] = uses_max
        resource[uses_remaining_key] = uses_remaining - 1
        class_resources[resource_key] = resource
        attacker_data["classResources"] = _decode_storage_dict(class_resources)
        attacker_state.state_json = finalize_session_state_data(attacker_data)
        flag_modified(attacker_state, "state_json")
        db.add(attacker_state)

        from . import standard_actions as standard_actions_module

        roll_result = standard_actions_module.resolve_saving_throw(
            cls._build_roll_actor_stats_for_save(
                db,
                session_id,
                target["ref_id"],
                target["kind"],
                target["display_name"],
            ),
            ability=action_state["saveType"],
            dc=cls._safe_int(action_state.get("dc"), 0),
            roll_source=req.roll_source,
            manual_roll=req.manual_roll,
            manual_rolls=req.manual_rolls,
        )
        roll_result.is_gm_roll = False
        roll_total = roll_result.total
        is_saved = bool(roll_result.success)

        damage_dice = action_state.get("damageDice")
        if not isinstance(damage_dice, str) or not damage_dice.strip():
            raise CombatServiceError("Dragonborn Breath Weapon damage dice is missing.", 400)
        effect_rolls, base_damage = cls._resolve_damage_roll(
            damage_dice,
            roll_source="system",
            manual_rolls=None,
        )
        rolled_damage = max(0, base_damage)
        damage = cls._resolve_save_damage_amount(
            rolled_damage,
            is_saved=is_saved,
            save_success_outcome="half_damage",
        )

        applied_damage = damage
        new_hp = None
        effect_msg = ""
        previous_hp = None
        concentration_check = None
        if damage > 0:
            new_hp, effect_msg, previous_hp, concentration_check = cls._apply_damage_to_target(
                db,
                target["ref_id"],
                target["kind"],
                damage,
                False,
                state,
                damage_type=action_state.get("damageType"),
                attacker_participant_id=actor.get("id"),
            )
            if previous_hp is not None and new_hp is not None:
                applied_damage = max(0, previous_hp - new_hp)
        else:
            flag_modified(state, "participants")

        save_text = "passes" if is_saved else "fails"
        damage_type = action_state.get("damageType") or "energy"
        message = (
            f"{actor['display_name']} uses Dragonborn Breath Weapon on {target['display_name']}. "
            f"{target['display_name']} {save_text} the {action_state.get('saveType')} save "
            f"(roll {roll_total} vs DC {action_state.get('dc')}) and takes {applied_damage} {damage_type} damage"
            f"{effect_msg}. Uses remaining: {resource[uses_remaining_key]}."
        )

        return {
            "message": message,
            "effect_applied": True,
            "target_display_name": target["display_name"],
            "target_kind": target["kind"],
            "damage": applied_damage,
            "damage_type": action_state.get("damageType"),
            "new_hp": new_hp,
            "roll_result": roll_result,
            "save_ability": action_state.get("saveType"),
            "save_dc": action_state.get("dc"),
            "is_saved": is_saved,
            "save_success_outcome": "half_damage",
            "effect_dice": action_state["damageDice"],
            "effect_rolls": effect_rolls,
            "effect_roll_source": "system",
            "uses_remaining": resource[uses_remaining_key],
            "concentration_check": concentration_check,
            "_actor_player_user_id": actor["ref_id"],
            "_actor_player_state": attacker_state,
            "_target_player_user_id": target["ref_id"] if target["kind"] == "player" else None,
            "_target_player_state": cls._get_stats(db, target["ref_id"], target["kind"], session_id)[0]
            if target["kind"] == "player" and damage > 0
            else None,
            "_target_entity_ref_id": target["ref_id"] if target["kind"] == "session_entity" and damage > 0 else None,
            "_target_previous_hp": previous_hp,
        }
