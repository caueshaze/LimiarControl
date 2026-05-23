"""Tests for Magic Missile (Mísseis Mágicos).

Covers:
- Seed contract: level=1, 3d4+3 force, auto-hit, upcast.mode=additional_effect_instances, baseEffectInstances=3
- Auto-hit: no attack roll — damage is direct (spell_mode=direct_damage)
- Shield interaction: shielded target receives 0 damage from all missile instances
- Upcast instance count: slot 1=3, slot 2=4, slot 3=5 darts
- Multi-target: darts distributed between targets independently
"""

from __future__ import annotations

import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.services.combat import CombatService
from app.services.combat_service.spell_dice_math import CombatSpellDiceMathMixin


def _make_participant(pid: str, ref_id: str, team: str = "players", shield: bool = False) -> dict:
    effects = []
    if shield:
        effects = [{"kind": "temp_ac_bonus", "numeric_value": 5, "metadata": {"source_spell_key": "shield"}}]
    return {
        "id": pid, "ref_id": ref_id, "kind": "player",
        "display_name": ref_id.capitalize(), "status": "active",
        "team": team, "turn_resources": {}, "active_effects": effects,
    }


def _spell_context() -> dict:
    return {
        "spell_canonical_key": "magic_missile",
        "spell_mode": "direct_damage",
        "action_cost": "action",
        "effect_kind": "damage",
        "source_kind": "spell",
        "slot_level": 1,
        "spell_name": "Magic Missile",
    }


def _apply_upcast(slot_level: int) -> dict:
    return CombatSpellDiceMathMixin._apply_structured_spell_upcast(
        spell_level=1,
        slot_level=slot_level,
        effect_kind="damage",
        effect_dice="3d4+3",
        effect_bonus=3,
        upcast={"mode": "additional_effect_instances", "dice": "1d4+1", "perLevel": 1, "baseEffectInstances": 3},
    )


# ---------------------------------------------------------------------------
# Seed tests
# ---------------------------------------------------------------------------

class MagicMissileSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.services.seed_paths import resolve_base_seed_path
        seed_path = resolve_base_seed_path(__file__, "base_spells.seed.json")
        with open(seed_path) as f:
            raw = json.load(f)
        spells = raw["spells"] if isinstance(raw, dict) else raw
        cls.entry = next(
            (s for s in spells if isinstance(s, dict) and s.get("canonicalKey") == "magic_missile"),
            None,
        )

    def test_entry_exists(self):
        self.assertIsNotNone(self.entry, "magic_missile not found in seed")

    def test_contract_fields(self):
        e = self.entry
        self.assertEqual(e["level"], 1)
        self.assertEqual(e["school"], "evocation")
        self.assertEqual(e["castingTimeType"], "action")
        self.assertEqual(e["rangeMeters"], 36)
        self.assertEqual(e["damageDice"], "3d4+3")
        self.assertEqual(e["damageType"], "Force")
        self.assertEqual(e["attackType"], "none")
        self.assertFalse(e["concentration"])

    def test_max_targets_is_3(self):
        self.assertEqual(self.entry.get("maxTargets"), 3)

    def test_upcast_mode_additional_effect_instances(self):
        up = self.entry.get("upcast")
        self.assertIsNotNone(up)
        self.assertEqual(up["mode"], "additional_effect_instances")
        self.assertEqual(up.get("baseEffectInstances"), 3)
        self.assertEqual(up.get("dice"), "1d4+1")

    def test_no_saving_throw(self):
        self.assertIsNone(self.entry.get("savingThrow"))

    def test_no_cantrip_scaling(self):
        self.assertIsNone(self.entry.get("cantripScaling"))


# ---------------------------------------------------------------------------
# Shield interaction
# ---------------------------------------------------------------------------

class MagicMissileShieldTests(unittest.TestCase):
    def test_shielded_participant_is_detected(self):
        participant = _make_participant("p1", "target", shield=True)
        self.assertTrue(CombatService._is_shielded_for_magic_missile(participant))

    def test_unshielded_participant_not_detected(self):
        participant = _make_participant("p1", "target", shield=False)
        self.assertFalse(CombatService._is_shielded_for_magic_missile(participant))

    def test_shield_effect_without_source_key_not_detected(self):
        participant = _make_participant("p1", "target")
        participant["active_effects"] = [{"kind": "temp_ac_bonus", "numeric_value": 5, "metadata": {}}]
        self.assertFalse(CombatService._is_shielded_for_magic_missile(participant))


class MagicMissileShieldBlocksInstancesTests(unittest.IsolatedAsyncioTestCase):
    async def test_shielded_target_instances_receive_zero_damage(self):
        state = CombatState(
            id="c1", session_id="s1", phase=CombatPhase.active,
            round=1, current_turn_index=0,
            participants=[
                _make_participant("p1", "caster"),
                _make_participant("p2", "lia", shield=True),
                _make_participant("p3", "theo"),
            ],
        )
        validated_targets = [
            {"instance_index": 1, "target_ref_id": "lia", "participant": state.participants[1]},
            {"instance_index": 2, "target_ref_id": "lia", "participant": state.participants[1]},
            {"instance_index": 3, "target_ref_id": "theo", "participant": state.participants[2]},
        ]

        with (
            patch.object(CombatService, "_consume_turn_resource", return_value=False),
            patch.object(CombatService, "_consume_player_spell_slot"),
            patch.object(CombatService, "_resolve_instance_direct", side_effect=[
                {"target_ref_id": "lia", "target_display_name": "Lia", "target_kind": "player", "damage": 4, "healing": 0, "new_hp": 10, "previous_hp": 14},
                {"target_ref_id": "lia", "target_display_name": "Lia", "target_kind": "player", "damage": 3, "healing": 0, "new_hp": 7, "previous_hp": 10},
                {"target_ref_id": "theo", "target_display_name": "Theo", "target_kind": "player", "damage": 5, "healing": 0, "new_hp": 8, "previous_hp": 13},
            ]),
            patch.object(CombatService, "_emit_player_state_update"),
            patch.object(CombatService, "_emit_state"),
            patch.object(CombatService, "_emit_and_persist_log"),
            patch.object(CombatService, "_get_stats", return_value=(MagicMock(), 10, None, None, None, None)),
        ):
            result = await CombatService._resolve_multi_instance_cast(
                db=MagicMock(),
                session_id="s1",
                req=MagicMock(override_resource_limit=False),
                state=state,
                attacker=state.participants[0],
                attacker_model=MagicMock(),
                spell_context=_spell_context(),
                actor_user_id="u1",
                is_gm=False,
                validated_targets=validated_targets,
            )

        outcomes = result["effect_instance_outcomes"]
        # Lia (shielded) receives 0 for both instances
        self.assertEqual(outcomes[0]["damage"], 0)
        self.assertEqual(outcomes[1]["damage"], 0)
        # Theo (unshielded) receives full damage
        self.assertEqual(outcomes[2]["damage"], 5)


# ---------------------------------------------------------------------------
# Upcast instance count
# ---------------------------------------------------------------------------

class MagicMissileUpcastTests(unittest.TestCase):
    def test_slot_1_no_extra_instances(self):
        result = _apply_upcast(1)
        self.assertEqual(result["upcast_added_instances"], 0)
        self.assertFalse(result["upcast_applied"])

    def test_slot_2_adds_one_instance(self):
        result = _apply_upcast(2)
        self.assertEqual(result["upcast_added_instances"], 1)
        self.assertTrue(result["upcast_applied"])

    def test_slot_3_adds_two_instances(self):
        result = _apply_upcast(3)
        self.assertEqual(result["upcast_added_instances"], 2)

    def test_slot_4_adds_three_instances(self):
        result = _apply_upcast(4)
        self.assertEqual(result["upcast_added_instances"], 3)

    def test_slot_5_adds_four_instances(self):
        result = _apply_upcast(5)
        self.assertEqual(result["upcast_added_instances"], 4)

    def test_upcast_instance_dice_is_1d4_plus_1(self):
        result = _apply_upcast(2)
        self.assertEqual(result["upcast_instance_effect_dice"], "1d4+1")
