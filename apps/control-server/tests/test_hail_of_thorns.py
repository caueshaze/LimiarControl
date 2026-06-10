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
    status: str = "active",
    team: str | None = None,
) -> dict:
    resolved_team = team or ("players" if kind == "player" else "enemies")
    return {
        "id": participant_id,
        "ref_id": ref_id,
        "kind": kind,
        "display_name": name or participant_id,
        "status": status,
        "team": resolved_team,
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


class HailOfThornsAutomationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.caster = _participant("caster-1", "player-1", actor_user_id="user-1", name="Ranger")
        self.target = _participant("target-1", "enemy-1", kind="session_entity", name="Goblin")
        self.ally = _participant("ally-1", "player-2", actor_user_id="user-2", name="Cleric", team="players")
        self.far_enemy = _participant("enemy-2", "enemy-2", kind="session_entity", name="Bandit")
        self.dead_enemy = _participant(
            "enemy-3",
            "enemy-3",
            kind="session_entity",
            name="Corpse",
            status="dead",
        )
        self.state = _combat_state([self.caster, self.target, self.ally, self.far_enemy, self.dead_enemy])

    def _spell_context(self, *, effect_dice: str = "1d10", save_dc: int = 14) -> dict:
        return {
            "spell_name": "Hail of Thorns",
            "spell_canonical_key": "hail_of_thorns",
            "spell_mode": "utility",
            "effect_kind": "damage",
            "effect_timing": "triggered",
            "selection_type": "none",
            "target_anchor": "trigger_target",
            "range_kind": "self",
            "attack_type": "none",
            "save_ability": "dexterity",
            "save_dc": save_dc,
            "concentration": True,
            "duration_seconds": 60,
            "effect_dice": effect_dice,
        }

    async def test_cast_arms_rider_and_concentration_marker(self) -> None:
        result = await CombatService._cast_hail_of_thorns_automation(
            MagicMock(),
            "session-1",
            attacker=self.caster,
            attacker_model=MagicMock(),
            actor_user_id="user-1",
            is_gm=False,
            req=SimpleNamespace(variant_key=None),
            state=self.state,
            spell_context=self._spell_context(effect_dice="2d10"),
            target_participant=None,
        )

        effects = self.caster["active_effects"]
        self.assertEqual(len(effects), 2)
        roles = {(effect.get("metadata") or {}).get("effect_role") for effect in effects}
        self.assertEqual(roles, {"concentration_marker", "next_weapon_hit_rider"})
        rider = next(
            effect
            for effect in effects
            if (effect.get("metadata") or {}).get("effect_role") == "next_weapon_hit_rider"
        )
        metadata = rider.get("metadata") or {}
        self.assertTrue(metadata["ranged_weapon_attack_only"])
        self.assertEqual(metadata["effect_dice"], "2d10")
        self.assertEqual(metadata["reactive_burst"]["radius_m"], 1.5)
        self.assertTrue(result["rider_armed"])

    async def test_melee_hit_does_not_consume_and_later_ranged_hit_consumes(self) -> None:
        await CombatService._cast_hail_of_thorns_automation(
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
        self.caster["pending_attack"] = {"is_weapon_attack": True, "is_ranged_weapon": False}

        melee_result = await CombatService.resolve_next_weapon_hit_riders(
            MagicMock(),
            "session-1",
            state=self.state,
            attacker=self.caster,
            target_participant=self.target,
            is_weapon_attack=True,
        )

        roles = {
            (effect.get("metadata") or {}).get("effect_role")
            for effect in self.caster["active_effects"]
        }
        self.assertEqual(roles, {"concentration_marker", "next_weapon_hit_rider"})
        self.assertEqual(melee_result, {"log_suffix": ""})

        self.caster["pending_attack"] = {"is_weapon_attack": True, "is_ranged_weapon": True}
        with patch(
            "app.services.combat_service.spells.automation._control_spells.resolve_saving_throw",
            return_value=SimpleNamespace(success=False, total=8, check_modifier_sources=[], is_gm_roll=False),
        ), patch(
            "app.services.combat_service.spells.automation._control_spells._roll_dice_expression",
            return_value=6,
        ), patch(
            "app.services.combat.CombatService._build_roll_actor_stats_for_save",
            return_value=SimpleNamespace(),
        ), patch(
            "app.services.combat.CombatService._apply_damage_to_target",
            return_value=(4, "", 10, None),
        ):
            ranged_result = await CombatService.resolve_next_weapon_hit_riders(
                MagicMock(),
                "session-1",
                state=self.state,
                attacker=self.caster,
                target_participant=self.target,
                is_weapon_attack=True,
            )

        self.assertEqual(self.caster["active_effects"], [])
        self.assertTrue(ranged_result["triggered"])

    async def test_ranged_weapon_hit_consumes_rider_and_hits_target_plus_ally(self) -> None:
        await CombatService._cast_hail_of_thorns_automation(
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
        self.caster["pending_attack"] = {"is_weapon_attack": True, "is_ranged_weapon": True}
        self.state.local_distances = {
            "enemy-1": {
                "player-2": 1.5,
                "enemy-2": 3.0,
            }
        }
        save_results = [
            SimpleNamespace(success=False, total=8, check_modifier_sources=[], is_gm_roll=False),
            SimpleNamespace(success=True, total=17, check_modifier_sources=[], is_gm_roll=False),
        ]

        with patch(
            "app.services.combat_service.spells.automation._control_spells.resolve_saving_throw",
            side_effect=save_results,
        ), patch(
            "app.services.combat_service.spells.automation._control_spells._roll_dice_expression",
            return_value=7,
        ), patch(
            "app.services.combat.CombatService._build_roll_actor_stats_for_save",
            return_value=SimpleNamespace(),
        ), patch(
            "app.services.combat.CombatService._apply_damage_to_target",
            side_effect=[(3, "", 10, None), (9, "", 12, None)],
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
        affected = result["affected_targets"]
        self.assertEqual([entry["target_ref_id"] for entry in affected], ["enemy-1", "player-2"])
        self.assertEqual(affected[0]["damage_applied"], 7)
        self.assertEqual(affected[1]["damage_applied"], 3)
        self.assertIn("Bandit", self.far_enemy["display_name"])
        self.assertEqual(len(result["hp_updates"]), 2)

    async def test_missing_distance_only_keeps_original_target(self) -> None:
        await CombatService._cast_hail_of_thorns_automation(
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
        self.caster["pending_attack"] = {"is_weapon_attack": True, "is_ranged_weapon": True}

        with patch(
            "app.services.combat_service.spells.automation._control_spells.resolve_saving_throw",
            return_value=SimpleNamespace(success=False, total=8, check_modifier_sources=[], is_gm_roll=False),
        ), patch(
            "app.services.combat_service.spells.automation._control_spells._roll_dice_expression",
            return_value=6,
        ), patch(
            "app.services.combat.CombatService._build_roll_actor_stats_for_save",
            return_value=SimpleNamespace(),
        ), patch(
            "app.services.combat.CombatService._apply_damage_to_target",
            return_value=(4, "", 10, None),
        ):
            result = await CombatService.resolve_next_weapon_hit_riders(
                MagicMock(),
                "session-1",
                state=self.state,
                attacker=self.caster,
                target_participant=self.target,
                is_weapon_attack=True,
            )

        self.assertEqual([entry["target_ref_id"] for entry in result["affected_targets"]], ["enemy-1"])
        self.assertIn("player-2", result["skipped_missing_distance"])
        self.assertIn("enemy-2", result["skipped_missing_distance"])
        self.assertNotIn("enemy-3", result["skipped_missing_distance"])

    async def test_concentration_lost_before_hit_removes_rider_and_later_hit_does_nothing(self) -> None:
        await CombatService._cast_hail_of_thorns_automation(
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
        CombatService._clear_concentration_for_source(
            self.state,
            source_participant_id=self.caster["id"],
        )
        self.caster["pending_attack"] = {"is_weapon_attack": True, "is_ranged_weapon": True}

        result = await CombatService.resolve_next_weapon_hit_riders(
            MagicMock(),
            "session-1",
            state=self.state,
            attacker=self.caster,
            target_participant=self.target,
            is_weapon_attack=True,
        )

        self.assertEqual(self.caster["active_effects"], [])
        self.assertEqual(result, {"log_suffix": ""})

    async def test_uses_effect_dice_captured_at_cast_time(self) -> None:
        await CombatService._cast_hail_of_thorns_automation(
            MagicMock(),
            "session-1",
            attacker=self.caster,
            attacker_model=MagicMock(),
            actor_user_id="user-1",
            is_gm=False,
            req=SimpleNamespace(variant_key=None),
            state=self.state,
            spell_context=self._spell_context(effect_dice="3d10"),
            target_participant=None,
        )
        self.caster["pending_attack"] = {"is_weapon_attack": True, "is_ranged_weapon": True}

        with patch(
            "app.services.combat_service.spells.automation._control_spells.resolve_saving_throw",
            return_value=SimpleNamespace(success=False, total=8, check_modifier_sources=[], is_gm_roll=False),
        ), patch(
            "app.services.combat_service.spells.automation._control_spells._roll_dice_expression",
            return_value=15,
        ) as roll_damage, patch(
            "app.services.combat.CombatService._build_roll_actor_stats_for_save",
            return_value=SimpleNamespace(),
        ), patch(
            "app.services.combat.CombatService._apply_damage_to_target",
            return_value=(0, "", 10, None),
        ):
            await CombatService.resolve_next_weapon_hit_riders(
                MagicMock(),
                "session-1",
                state=self.state,
                attacker=self.caster,
                target_participant=self.target,
                is_weapon_attack=True,
            )

        roll_damage.assert_called_once_with("3d10")


class HailOfThornsWeaponAttackIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_weapon_damage_can_drop_original_target_to_zero_before_burst(self) -> None:
        attacker = _participant("caster-1", "player-1", actor_user_id="user-1", name="Ranger")
        target = _participant("target-1", "enemy-1", kind="session_entity", name="Goblin")
        ally = _participant("ally-1", "player-2", actor_user_id="user-2", name="Cleric", team="players")
        state = _combat_state([attacker, target, ally])
        state.local_distances = {
            "enemy-1": {"player-2": 1.5},
        }

        marker = CombatService._build_hail_of_thorns_concentration_marker(
            caster_participant_id=attacker["id"],
            spell_name="Hail of Thorns",
            concentration_group="grp-1",
        )
        rider = CombatService._build_hail_of_thorns_rider_effect(
            caster_participant_id=attacker["id"],
            spell_name="Hail of Thorns",
            concentration_group="grp-1",
            save_dc=14,
            effect_dice="1d10",
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
            "is_ranged_weapon": True,
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
        save_results = [
            SimpleNamespace(success=False, total=8, check_modifier_sources=[], is_gm_roll=False),
            SimpleNamespace(success=False, total=9, check_modifier_sources=[], is_gm_roll=False),
        ]

        with patch("app.services.combat.CombatService.get_state", return_value=state), patch(
            "app.services.combat.CombatService._get_stats",
            return_value=(attacker_model, 10, 10, 10, 2, 3),
        ), patch(
            "app.services.combat.CombatService._get_target_hp_snapshot",
            return_value=(8, 8),
        ), patch(
            "app.services.combat.CombatService._resolve_damage_roll",
            return_value=([5], 5),
        ), patch(
            "app.services.combat_service.spells.automation._control_spells.resolve_saving_throw",
            side_effect=save_results,
        ), patch(
            "app.services.combat_service.spells.automation._control_spells._roll_dice_expression",
            return_value=6,
        ), patch(
            "app.services.combat.CombatService._build_roll_actor_stats_for_save",
            return_value=SimpleNamespace(),
        ), patch(
            "app.services.combat.CombatService._apply_damage_to_target",
            side_effect=[(0, "", 8, None), (0, "", 0, None), (3, "", 9, None)],
        ) as apply_damage, patch(
            "app.services.combat.CombatService._emit_state",
            new_callable=AsyncMock,
        ), patch(
            "app.services.combat.CombatService._emit_and_persist_log",
            new_callable=AsyncMock,
        ) as emit_log, patch(
            "app.services.combat.CombatService._emit_entity_hp_update",
            new_callable=AsyncMock,
        ), patch(
            "app.services.combat.CombatService._emit_player_state_update",
            new_callable=AsyncMock,
        ):
            result = await CombatService.attack_damage(
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

        self.assertEqual(apply_damage.call_count, 3)
        self.assertEqual(attacker["active_effects"], [])
        self.assertEqual(result["damage"], 8)
        self.assertEqual(result["damage_breakdown"]["total"], 8)
        log_payload = emit_log.await_args.args[4]
        self.assertIn("8 damage", log_payload["message"])
        self.assertIn("Hail of Thorns explodiu ao redor de Goblin", log_payload["message"])


if __name__ == "__main__":
    unittest.main()
