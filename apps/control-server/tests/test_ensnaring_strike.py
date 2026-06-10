from __future__ import annotations

import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.services.combat import CombatService


def _participant(
    participant_id: str,
    ref_id: str,
    *,
    kind: str = "player",
    name: str | None = None,
    actor_user_id: str | None = None,
) -> dict:
    return {
        "id": participant_id,
        "ref_id": ref_id,
        "kind": kind,
        "display_name": name or participant_id,
        "status": "active",
        "team": "players" if kind == "player" else "enemies",
        "visible": True,
        "actor_user_id": actor_user_id,
        "active_effects": [],
        "turn_resources": {
            "action_used": False,
            "bonus_action_used": False,
            "reaction_used": False,
        },
    }


def _combat_state(participants: list[dict]) -> CombatState:
    return CombatState(
        id="combat-1",
        session_id="session-1",
        phase=CombatPhase.active,
        round=1,
        current_turn_index=0,
        participants=participants,
        local_distances={},
        use_map=False,
    )


class EnsnaringStrikeAutomationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.caster = _participant("caster-1", "player-1", actor_user_id="user-1", name="Ranger")
        self.target = _participant("target-1", "enemy-1", kind="session_entity", name="Goblin")
        self.state = _combat_state([self.caster, self.target])

    def _spell_context(self) -> dict:
        return {
            "spell_name": "Ensnaring Strike",
            "spell_canonical_key": "ensnaring_strike",
            "spell_mode": "utility",
            "effect_kind": None,
            "effect_timing": "triggered",
            "selection_type": "none",
            "target_anchor": "trigger_target",
            "range_kind": "self",
            "attack_type": "none",
            "save_ability": "strength",
            "save_dc": 14,
            "concentration": True,
            "duration_seconds": 60,
        }

    async def test_cast_arms_rider_and_concentration_marker(self) -> None:
        result = await CombatService._cast_ensnaring_strike_automation(
            MagicMock(),
            "session-1",
            attacker=self.caster,
            attacker_model=MagicMock(),
            actor_user_id="user-1",
            is_gm=False,
            req=SimpleNamespace(variant_key=None),
            state=self.state,
            spell_context=self._spell_context(),
            target_participant=None,
        )

        effects = self.caster["active_effects"]
        self.assertEqual(len(effects), 2)
        roles = {(effect.get("metadata") or {}).get("effect_role") for effect in effects}
        self.assertEqual(roles, {"concentration_marker", "next_weapon_hit_rider"})
        groups = {
            (effect.get("metadata") or {}).get("concentration_group")
            for effect in effects
        }
        self.assertEqual(len(groups), 1)
        self.assertTrue(result["rider_armed"])

    async def test_successful_hit_and_failed_save_applies_target_effect(self) -> None:
        spell_context = self._spell_context()
        await CombatService._cast_ensnaring_strike_automation(
            MagicMock(),
            "session-1",
            attacker=self.caster,
            attacker_model=MagicMock(),
            actor_user_id="user-1",
            is_gm=False,
            req=SimpleNamespace(variant_key=None),
            state=self.state,
            spell_context=spell_context,
            target_participant=None,
        )

        roll_result = SimpleNamespace(success=False, total=9, check_modifier_sources=[], is_gm_roll=False)
        with patch(
            "app.services.combat_service.spells.automation._control_spells.resolve_saving_throw",
            return_value=roll_result,
        ), patch(
            "app.services.combat.CombatService._build_roll_actor_stats_for_save",
            return_value=SimpleNamespace(),
        ):
            result = await CombatService.resolve_next_weapon_hit_riders(
                MagicMock(),
                "session-1",
                state=self.state,
                attacker=self.caster,
                target_participant=self.target,
                is_weapon_attack=True,
            )

        caster_roles = {
            (effect.get("metadata") or {}).get("effect_role")
            for effect in self.caster["active_effects"]
        }
        self.assertEqual(caster_roles, {"concentration_marker"})
        target_effects = self.target["active_effects"]
        self.assertEqual(len(target_effects), 1)
        target_effect = target_effects[0]
        self.assertEqual(target_effect["kind"], "condition")
        self.assertEqual(target_effect["condition_type"], "restrained")
        self.assertEqual((target_effect.get("metadata") or {}).get("source_spell_key"), "ensnaring_strike")
        self.assertTrue(result["effect_applied"])

    async def test_successful_hit_and_successful_save_clears_group(self) -> None:
        spell_context = self._spell_context()
        await CombatService._cast_ensnaring_strike_automation(
            MagicMock(),
            "session-1",
            attacker=self.caster,
            attacker_model=MagicMock(),
            actor_user_id="user-1",
            is_gm=False,
            req=SimpleNamespace(variant_key=None),
            state=self.state,
            spell_context=spell_context,
            target_participant=None,
        )

        roll_result = SimpleNamespace(success=True, total=18, check_modifier_sources=[], is_gm_roll=False)
        with patch(
            "app.services.combat_service.spells.automation._control_spells.resolve_saving_throw",
            return_value=roll_result,
        ), patch(
            "app.services.combat.CombatService._build_roll_actor_stats_for_save",
            return_value=SimpleNamespace(),
        ):
            result = await CombatService.resolve_next_weapon_hit_riders(
                MagicMock(),
                "session-1",
                state=self.state,
                attacker=self.caster,
                target_participant=self.target,
                is_weapon_attack=True,
            )

        self.assertEqual(self.caster["active_effects"], [])
        self.assertEqual(self.target["active_effects"], [])
        self.assertTrue(result["is_saved"])

    async def test_losing_concentration_before_hit_removes_rider(self) -> None:
        spell_context = self._spell_context()
        await CombatService._cast_ensnaring_strike_automation(
            MagicMock(),
            "session-1",
            attacker=self.caster,
            attacker_model=MagicMock(),
            actor_user_id="user-1",
            is_gm=False,
            req=SimpleNamespace(variant_key=None),
            state=self.state,
            spell_context=spell_context,
            target_participant=None,
        )

        result = CombatService._clear_concentration_for_source(
            self.state,
            source_participant_id=self.caster["id"],
        )

        self.assertEqual(self.caster["active_effects"], [])
        self.assertEqual(self.target["active_effects"], [])
        self.assertEqual(len(result["removed_effects"]), 2)

    async def test_losing_concentration_before_hit_prevents_future_trigger(self) -> None:
        spell_context = self._spell_context()
        await CombatService._cast_ensnaring_strike_automation(
            MagicMock(),
            "session-1",
            attacker=self.caster,
            attacker_model=MagicMock(),
            actor_user_id="user-1",
            is_gm=False,
            req=SimpleNamespace(variant_key=None),
            state=self.state,
            spell_context=spell_context,
            target_participant=None,
        )

        CombatService._clear_concentration_for_source(
            self.state,
            source_participant_id=self.caster["id"],
        )

        result = await CombatService.resolve_next_weapon_hit_riders(
            MagicMock(),
            "session-1",
            state=self.state,
            attacker=self.caster,
            target_participant=self.target,
            is_weapon_attack=True,
        )

        self.assertEqual(self.caster["active_effects"], [])
        self.assertEqual(self.target["active_effects"], [])
        self.assertEqual(result, {"log_suffix": ""})

    async def test_unrelated_attacker_events_do_not_consume_caster_rider(self) -> None:
        spell_context = self._spell_context()
        await CombatService._cast_ensnaring_strike_automation(
            MagicMock(),
            "session-1",
            attacker=self.caster,
            attacker_model=MagicMock(),
            actor_user_id="user-1",
            is_gm=False,
            req=SimpleNamespace(variant_key=None),
            state=self.state,
            spell_context=spell_context,
            target_participant=None,
        )
        other_attacker = _participant("ally-1", "player-2", actor_user_id="user-2", name="Fighter")
        self.state.participants.append(other_attacker)

        result = await CombatService.resolve_next_weapon_hit_riders(
            MagicMock(),
            "session-1",
            state=self.state,
            attacker=other_attacker,
            target_participant=self.target,
            is_weapon_attack=True,
        )

        roles = {
            (effect.get("metadata") or {}).get("effect_role")
            for effect in self.caster["active_effects"]
        }
        self.assertEqual(roles, {"concentration_marker", "next_weapon_hit_rider"})
        self.assertEqual(result, {"log_suffix": ""})

    async def test_helper_escape_requires_adjacency_and_can_free_target(self) -> None:
        helper = _participant("helper-1", "player-2", actor_user_id="user-2", name="Cleric")
        self.state.participants.append(helper)
        self.state.current_turn_index = len(self.state.participants) - 1
        condition = CombatService._build_ensnaring_strike_target_effect(
            caster_participant_id=self.caster["id"],
            spell_name="Ensnaring Strike",
            concentration_group="grp-1",
            save_dc=14,
        )
        self.target["active_effects"] = [condition]
        self.state.local_distances = {
            "player-2": {"enemy-1": 1.5},
            "enemy-1": {"player-2": 1.5},
        }
        roll_result = SimpleNamespace(success=True, total=16, check_modifier_sources=[], is_gm_roll=False)

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
            "app.services.combat_service.effects_actions.resolve_ability_check",
            return_value=roll_result,
        ), patch(
            "app.services.combat.CombatService._build_roll_actor_stats_for_save",
            return_value=SimpleNamespace(),
        ), patch(
            "app.services.combat.CombatService._emit_state",
            new_callable=AsyncMock,
        ), patch(
            "app.services.combat.CombatService._emit_log",
            new_callable=AsyncMock,
        ):
            result = await CombatService.resolve_condition_escape_action(
                MagicMock(),
                "session-1",
                actor_participant_id=helper["id"],
                target_participant_id=self.target["id"],
                actor_user_id="user-2",
                is_gm=False,
                condition_type="restrained",
                source_effect_id=(condition.get("metadata") or {}).get("source_effect_id"),
            )

        self.assertEqual(self.target["active_effects"], [])
        self.assertTrue(result["conditionRemoved"])
        self.assertTrue(helper["turn_resources"]["action_used"])

    async def test_escape_removes_only_matching_source_effect(self) -> None:
        self.state.current_turn_index = 1
        ensnaring_condition = CombatService._build_ensnaring_strike_target_effect(
            caster_participant_id=self.caster["id"],
            spell_name="Ensnaring Strike",
            concentration_group="grp-1",
            save_dc=14,
        )
        other_condition = CombatService._build_active_effect(
            kind="condition",
            condition_type="restrained",
            source_participant_id="other-caster",
            duration_type="manual",
            metadata={
                "source_spell_key": "entangle",
                "source_spell_name": "Entangle",
                "escape_action": True,
                "escape_check_ability": "strength",
                "escape_check_dc": 12,
                "source_effect_id": "other-effect",
            },
            display_label="Restrained (Entangle)",
        )
        self.target["active_effects"] = [ensnaring_condition, other_condition]
        roll_result = SimpleNamespace(success=True, total=16, check_modifier_sources=[], is_gm_roll=False)

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
            "app.services.combat_service.effects_actions.resolve_ability_check",
            return_value=roll_result,
        ), patch(
            "app.services.combat.CombatService._build_roll_actor_stats_for_save",
            return_value=SimpleNamespace(),
        ), patch(
            "app.services.combat.CombatService._emit_state",
            new_callable=AsyncMock,
        ), patch(
            "app.services.combat.CombatService._emit_log",
            new_callable=AsyncMock,
        ):
            result = await CombatService.resolve_condition_escape_action(
                MagicMock(),
                "session-1",
                actor_participant_id=self.target["id"],
                actor_user_id="gm-not-used",
                is_gm=True,
                condition_type="restrained",
                source_effect_id=(ensnaring_condition.get("metadata") or {}).get("source_effect_id"),
            )

        self.assertTrue(result["conditionRemoved"])
        remaining_ids = {effect.get("id") for effect in self.target["active_effects"]}
        self.assertNotIn(ensnaring_condition.get("id"), remaining_ids)
        self.assertIn(other_condition.get("id"), remaining_ids)

    async def test_start_turn_recurring_damage_only_hits_matching_effect_instance(self) -> None:
        ensnaring_condition = CombatService._build_ensnaring_strike_target_effect(
            caster_participant_id=self.caster["id"],
            spell_name="Ensnaring Strike",
            concentration_group="grp-1",
            save_dc=14,
        )
        other_condition = CombatService._build_active_effect(
            kind="condition",
            condition_type="restrained",
            source_participant_id="other-caster",
            duration_type="manual",
            metadata={
                "source_spell_key": "entangle",
                "source_spell_name": "Entangle",
                "escape_action": True,
                "escape_check_ability": "strength",
                "escape_check_dc": 12,
                "source_effect_id": "other-effect",
            },
            display_label="Restrained (Entangle)",
        )
        self.target["active_effects"] = [ensnaring_condition, other_condition]

        with patch(
            "app.services.combat_service.spells.automation._control_spells._roll_dice_expression",
            return_value=4,
        ), patch(
            "app.services.combat.CombatService._apply_damage_to_target",
            return_value=(3, "", 7, None),
        ) as apply_damage, patch(
            "app.services.combat.CombatService._emit_log",
            new_callable=AsyncMock,
        ):
            results = await CombatService.resolve_ensnaring_strike_start_turn(
                MagicMock(),
                "session-1",
                state=self.state,
                participant=self.target,
            )

        self.assertEqual(len(results), 1)
        apply_damage.assert_called_once()
        self.assertEqual(results[0]["source_effect_id"], ensnaring_condition.get("id"))


class EnsnaringStrikeWeaponAttackIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_attack_damage_triggers_rider_on_weapon_hit(self) -> None:
        attacker = _participant("caster-1", "player-1", actor_user_id="user-1", name="Ranger")
        target = _participant("target-1", "enemy-1", kind="session_entity", name="Goblin")
        state = _combat_state([attacker, target])

        marker = CombatService._build_ensnaring_strike_concentration_marker(
            caster_participant_id=attacker["id"],
            spell_name="Ensnaring Strike",
            concentration_group="grp-1",
        )
        rider = CombatService._build_ensnaring_strike_rider_effect(
            caster_participant_id=attacker["id"],
            spell_name="Ensnaring Strike",
            concentration_group="grp-1",
            save_dc=14,
        )
        attacker["active_effects"] = [marker, rider]
        attacker["pending_attack"] = {
            "id": "pending-1",
            "type": "player_attack",
            "target_ref_id": target["ref_id"],
            "target_kind": target["kind"],
            "target_display_name": target["display_name"],
            "target_ac": 13,
            "weapon_name": "Longbow",
            "damage_dice": "1d8",
            "damage_bonus": 3,
            "attack_bonus": 5,
            "damage_type": "piercing",
            "inventory_item_id": "weapon-1",
            "is_magical_damage": False,
            "is_weapon_attack": True,
            "is_critical": False,
            "roll_result": {
                "event_id": "roll-1",
                "roll_type": "attack",
                "actor_kind": "player",
                "actor_ref_id": attacker["ref_id"],
                "actor_display_name": attacker["display_name"],
                "rolls": [13, 13],
                "selected_roll": 13,
                "advantage_mode": "normal",
                "modifier_used": 5,
                "override_used": False,
                "formula": "1d20 + 5",
                "total": 18,
                "target_ac": 13,
                "success": True,
                "check_modifier_sources": [],
                "roll_source": "system",
                "timestamp": datetime.now(UTC).isoformat(),
            },
            "roll": 18,
        }

        attacker_model = MagicMock()
        attacker_model.state_json = {}
        roll_result = SimpleNamespace(success=False, total=7, check_modifier_sources=[], is_gm_roll=False)

        with patch("app.services.combat.CombatService.get_state", return_value=state), patch(
            "app.services.combat.CombatService._get_stats",
            return_value=(attacker_model, 10, 10, 10, 2, 3),
        ), patch(
            "app.services.combat.CombatService._get_target_hp_snapshot",
            return_value=(12, 12),
        ), patch(
            "app.services.combat.CombatService._resolve_damage_roll",
            return_value=([4], 4),
        ), patch(
            "app.services.combat.CombatService._apply_damage_to_target",
            return_value=(8, "", 12, None),
        ), patch(
            "app.services.combat_service.spells.automation._control_spells.resolve_saving_throw",
            return_value=roll_result,
        ), patch(
            "app.services.combat.CombatService._build_roll_actor_stats_for_save",
            return_value=SimpleNamespace(),
        ), patch(
            "app.services.combat.CombatService._emit_state",
            new_callable=AsyncMock,
        ), patch(
            "app.services.combat.CombatService._emit_and_persist_log",
            new_callable=AsyncMock,
        ), patch(
            "app.services.combat.CombatService._emit_entity_hp_update",
            new_callable=AsyncMock,
        ):
            await CombatService.attack_damage(
                MagicMock(),
                "session-1",
                SimpleNamespace(
                    actor_participant_id=attacker["id"],
                    pending_attack_id="pending-1",
                    roll_source="system",
                    manual_rolls=None,
                    concentration_roll_source="system",
                    concentration_manual_roll=None,
                ),
                "user-1",
                False,
            )

        target_conditions = [
            effect
            for effect in target["active_effects"]
            if effect.get("kind") == "condition" and effect.get("condition_type") == "restrained"
        ]
        self.assertEqual(len(target_conditions), 1)
        caster_roles = {(effect.get("metadata") or {}).get("effect_role") for effect in attacker["active_effects"]}
        self.assertEqual(caster_roles, {"concentration_marker"})


if __name__ == "__main__":
    unittest.main()
