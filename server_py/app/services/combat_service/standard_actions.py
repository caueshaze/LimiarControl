from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app.models.combat import CombatState
from app.schemas.combat import CombatStandardActionRequest
from app.services.healing_consumables import (
    HealingConsumableError,
    build_consumable_used_payload,
    consume_inventory_item,
    publish_consumable_used_realtime,
    record_consumable_used_activity,
    resolve_healing_consumable,
    roll_healing_consumable,
)
from app.schemas.roll import RollActorStats
from app.services.roll_resolution import resolve_saving_throw, resolve_skill_check
from app.services.dragonborn_breath_weapon import (
    DRAGONBORN_BREATH_WEAPON_ACTION_ID,
    DRAGONBORN_BREATH_WEAPON_RESOURCE_KEY,
    apply_dragonborn_breath_weapon_canonical_state,
    resolve_dragonborn_breath_weapon_action_state,
)
from app.services.session_state_finalize import finalize_session_state_data

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
        was_overridden = cls._consume_turn_resource(
            actor, "action", is_gm=is_gm, override_resource_limit=req.override_resource_limit
        )

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
            await cls._emit_player_state_update(
                db,
                session_id,
                actor_player_user_id,
                actor_player_state,
            )
        if target_player_user_id and target_player_state is not None:
            await cls._emit_player_state_update(
                db,
                session_id,
                target_player_user_id,
                target_player_state,
            )
        elif (
            target_entity_ref_id
            and target_previous_hp is not None
            and result.get("new_hp") != target_previous_hp
        ):
            await cls._emit_entity_hp_update(
                db,
                session_id,
                target_entity_ref_id,
                target_previous_hp,
            )
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
        if consumable_payload and consumable_timestamp:
            session_entry = cls._get_session_entry(db, session_id)
            if not session_entry:
                raise CombatServiceError("Session not found", 404)
            await publish_consumable_used_realtime(
                session_entry,
                payload=consumable_payload,
                timestamp=consumable_timestamp,
            )

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
        if req.inventory_item_id:
            session_entry = cls._get_session_entry(db, session_id)
            if not session_entry:
                raise CombatServiceError("Session not found", 404)
            if actor.get("kind") != "player":
                raise CombatServiceError(
                    "Only players can use structured consumables in combat.",
                    400,
                )
            try:
                context = resolve_healing_consumable(
                    db,
                    session_entry=session_entry,
                    actor_user_id=actor["ref_id"],
                    inventory_item_id=req.inventory_item_id,
                )
                healing_roll = roll_healing_consumable(
                    context.item,
                    roll_source=req.roll_source,
                    manual_rolls=req.manual_rolls,
                )
            except HealingConsumableError as error:
                raise CombatServiceError(error.detail, error.status_code) from error

            target = cls._resolve_use_object_target(state, actor, req.target_participant_id)
            if not cls._is_friendly_use_object_target(actor, target):
                raise CombatServiceError(
                    "Healing consumables can only target yourself or an allied participant.",
                    400,
                )

            new_hp, effect_msg, previous_hp = cls._apply_healing_to_target(
                db,
                target["ref_id"],
                target["kind"],
                healing_roll.total_healing,
                state,
            )
            remaining_quantity = consume_inventory_item(db, context.inventory_item)
            timestamp = datetime.now(timezone.utc)

            target_player_user_id = target["ref_id"] if target["kind"] == "player" else None
            target_player_state = None
            max_hp = None
            if target["kind"] == "player":
                target_player_state, *_ = cls._get_stats(
                    db,
                    target["ref_id"],
                    target["kind"],
                    session_id,
                )
                max_hp = cls._safe_int(
                    cls._as_dict(target_player_state.state_json).get("maxHP"),
                    0,
                )
            else:
                session_entity, npc = cls._get_session_entity_and_campaign_entity(
                    db,
                    target["ref_id"],
                )
                max_hp = npc.max_hp if npc else session_entity.current_hp

            consumable_payload = build_consumable_used_payload(
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
            record_consumable_used_activity(
                db,
                context=context,
                payload=consumable_payload,
                created_at=timestamp,
            )

            return {
                "message": (
                    f"{actor['display_name']} uses {context.item.name} on "
                    f"{target['display_name']} and restores {healing_roll.total_healing} HP"
                    f"{effect_msg}."
                ),
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

    @classmethod
    def _precheck_dragonborn_breath_weapon(cls, db, session_id, state, actor, req) -> None:
        if actor.get("kind") != "player":
            raise CombatServiceError("Only players can use Dragonborn Breath Weapon.", 400)
        target = cls._resolve_required_hostile_target(state, actor, req.target_participant_id)
        attacker_state, *_ = cls._get_stats(db, actor["ref_id"], actor["kind"], session_id)
        attacker_data = apply_dragonborn_breath_weapon_canonical_state(
            cls._as_dict(attacker_state.state_json),
        )
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
        attacker_data = apply_dragonborn_breath_weapon_canonical_state(
            cls._as_dict(attacker_state.state_json),
        )
        action_state = resolve_dragonborn_breath_weapon_action_state(attacker_data)
        if action_state is None:
            raise CombatServiceError("Dragonborn Breath Weapon is not available for this actor.", 400)

        class_resources = (
            dict(attacker_data.get("classResources"))
            if isinstance(attacker_data.get("classResources"), dict)
            else {}
        )
        resource = (
            dict(class_resources.get(DRAGONBORN_BREATH_WEAPON_RESOURCE_KEY))
            if isinstance(class_resources.get(DRAGONBORN_BREATH_WEAPON_RESOURCE_KEY), dict)
            else {}
        )
        uses_max = cls._safe_int(resource.get("usesMax"), cls._safe_int(action_state.get("usesMax"), 1))
        uses_remaining = cls._safe_int(resource.get("usesRemaining"), uses_max)
        if uses_remaining <= 0:
            raise CombatServiceError("No Dragonborn Breath Weapon uses remaining.", 400)

        resource["usesMax"] = uses_max
        resource["usesRemaining"] = uses_remaining - 1
        class_resources[DRAGONBORN_BREATH_WEAPON_RESOURCE_KEY] = resource
        attacker_data["classResources"] = class_resources
        attacker_state.state_json = finalize_session_state_data(attacker_data)
        flag_modified(attacker_state, "state_json")
        db.add(attacker_state)

        roll_result = resolve_saving_throw(
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

        effect_rolls, base_damage = cls._resolve_damage_roll(action_state["damageDice"])
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
            f"{effect_msg}. Uses remaining: {resource['usesRemaining']}."
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
            "uses_remaining": resource["usesRemaining"],
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

    @classmethod
    def _resolve_use_object_target(
        cls,
        state: CombatState,
        actor: dict,
        target_participant_id: str | None,
    ) -> dict:
        if not target_participant_id:
            return actor
        target = next(
            (participant for participant in state.participants if participant["id"] == target_participant_id),
            None,
        )
        if not target:
            raise CombatServiceError("Target participant not found in combat.", 404)
        return target

    @classmethod
    def _resolve_required_hostile_target(
        cls,
        state: CombatState,
        actor: dict,
        target_participant_id: str | None,
    ) -> dict:
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
