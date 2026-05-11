from __future__ import annotations

from .exceptions import CombatServiceError
from .targeting_intent import SpellCastIntent, WeaponAttackIntent
from .targeting_requirements import resolve_spell_targeting_requirements


class CombatNpcActionStepsMixin:
    @classmethod
    def _resolve_npc_weapon_targeting_requirements(
        cls, resolved_action: dict
    ) -> object:
        from .targeting_requirements import TargetingRequirements

        requires_sight = resolved_action.get("requiresTargetSight")
        requires_effect = resolved_action.get("requiresTargetEffect")
        return TargetingRequirements(
            requires_target_sight=True if requires_sight is None else requires_sight,
            requires_target_effect=True if requires_effect is None else requires_effect,
            requires_point_sight=False,
            requires_point_effect=False,
        )

    @classmethod
    def _validate_npc_action_request(
        cls,
        db,
        session_id: str,
        req,
        actor_user_id: str,
        is_gm: bool,
    ) -> dict:
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
            attacker, ("active",), "You can only use combat actions when active."
        )
        cls._require_action_capable(attacker)

        _, npc, action = cls._get_combat_action_for_entity(
            db, attacker["ref_id"], req.combat_action_id
        )
        resolved_action = cls._resolve_entity_combat_action(db, session_id, npc, action)
        action_cost = resolved_action.get("actionCost") or "action"
        was_overridden = cls._consume_turn_resource(
            attacker,
            action_cost,
            is_gm=is_gm,
            override_resource_limit=req.override_resource_limit,
        )
        return {
            "state": state,
            "attacker": attacker,
            "resolved_action": resolved_action,
            "action_cost": action_cost,
            "was_overridden": was_overridden,
            "action_name": resolved_action.get("name")
            if isinstance(resolved_action.get("name"), str)
            else "Combat Action",
            "action_kind": resolved_action.get("kind")
            if isinstance(resolved_action.get("kind"), str)
            else "utility",
            "damage_type": resolved_action.get("damageType")
            if isinstance(resolved_action.get("damageType"), str)
            else None,
        }

    @classmethod
    def _resolve_npc_target_participant(
        cls,
        state,
        attacker: dict,
        req,
        action_kind: str,
    ) -> dict | None:
        target_p = None
        if req.target_ref_id:
            target_p = next(
                (p for p in state.participants if p["ref_id"] == req.target_ref_id),
                None,
            )
            if not target_p:
                raise CombatServiceError("Target not found in combat")
        if action_kind != "utility" and not target_p:
            raise CombatServiceError("This combat action requires a target")
        if action_kind in ("weapon_attack", "spell_attack", "saving_throw"):
            cls._assert_hostile_action_allowed(
                attacker,
                target_p,
                action_label="a hostile action",
            )
        return target_p

    @classmethod
    def _build_npc_targeting_intent(
        cls,
        session_id: str,
        attacker: dict,
        target_p: dict,
        action_kind: str,
        resolved_action: dict,
    ):
        if action_kind == "weapon_attack":
            weapon_targeting = cls._resolve_npc_weapon_targeting_requirements(
                resolved_action
            )
            return WeaponAttackIntent(
                session_id=session_id,
                action_id=f"targeting:{cls._generate_uuid()}",
                actor_ref_id=attacker["ref_id"],
                actor_kind=attacker["kind"],
                requested_target_ref_id=target_p["ref_id"],
                weapon_item_id=None,
                weapon_canonical_key=None,
                range_meters=cls._safe_int(resolved_action.get("rangeMeters"), None),
                range_long_meters=cls._safe_int(resolved_action.get("rangeLongMeters"), None),
                weapon_range_type=resolved_action.get("rangeType"),
                has_reach=bool(resolved_action.get("hasReach")),
                actor_effective_size=attacker.get("effective_size") or attacker.get("base_size"),
                requires_sight=weapon_targeting.requires_target_sight,
                requires_effect=weapon_targeting.requires_target_effect,
            )

        spell_targeting = resolve_spell_targeting_requirements(
            {
                "target_type": resolved_action.get("targetType"),
                "area_shape": resolved_action.get("areaShape"),
                "spell_mode": action_kind,
                "requires_target_sight": resolved_action.get("requiresTargetSight"),
                "requires_target_effect": resolved_action.get("requiresTargetEffect"),
            },
            spell_mode=action_kind,
        )
        return SpellCastIntent(
            session_id=session_id,
            action_id=f"targeting:{cls._generate_uuid()}",
            actor_ref_id=attacker["ref_id"],
            actor_kind=attacker["kind"],
            requested_target_ref_id=target_p["ref_id"],
            spell_canonical_key=resolved_action.get("spellCanonicalKey") or "",
            spell_mode=action_kind,
            target_type=resolved_action.get("targetType"),
            area_shape=resolved_action.get("areaShape"),
            range_meters=cls._safe_int(resolved_action.get("rangeMeters"), None),
            requires_sight=spell_targeting.requires_target_sight,
            requires_effect=spell_targeting.requires_target_effect,
        )
