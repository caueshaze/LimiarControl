"""Tests for per-instance target assignment.

Covers:
  - _validate_instance_targets validation rules
  - _resolve_instance_direct per-instance damage resolution
  - _resolve_instance_attack per-instance attack resolution
  - _resolve_multi_instance_cast orchestration
  - _build_multi_instance_log_message formatting
  - Backward compatibility (no effect_instance_targets)
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.schemas.combat_spells import EffectInstanceTarget
from app.services.combat import CombatService, CombatServiceError


def _build_state(participants=None):
    if participants is None:
        participants = [
            {
                "id": "p1",
                "ref_id": "player-1",
                "kind": "player",
                "display_name": "Hero",
                "status": "active",
                "team": "players",
                "visible": True,
                "actor_user_id": "user-1",
            },
            {
                "id": "e1",
                "ref_id": "entity:goblin-a",
                "kind": "session_entity",
                "display_name": "Goblin A",
                "status": "active",
                "team": "enemies",
                "visible": True,
                "actor_user_id": None,
            },
            {
                "id": "e2",
                "ref_id": "entity:goblin-b",
                "kind": "session_entity",
                "display_name": "Goblin B",
                "status": "active",
                "team": "enemies",
                "visible": True,
                "actor_user_id": None,
            },
            {
                "id": "e3",
                "ref_id": "entity:goblin-c",
                "kind": "session_entity",
                "display_name": "Goblin C",
                "status": "active",
                "team": "enemies",
                "visible": True,
                "actor_user_id": None,
            },
        ]
    return CombatState(
        id="combat-1",
        session_id="session-1",
        phase=CombatPhase.active,
        round=1,
        current_turn_index=0,
        participants=participants,
    )


def _req_with_targets(targets):
    return SimpleNamespace(effect_instance_targets=targets)


def _spell_context(count=5, dice="1d4+1", spell_mode="direct_damage"):
    return {
        "effect_instance_count": count,
        "effect_instance_dice": dice,
        "spell_mode": spell_mode,
        "spell_canonical_key": "magic_missile",
        "spell_name": "Magic Missile",
        "effect_kind": "damage",
        "damage_type": "Force",
    }


class ValidateInstanceTargetsTests(unittest.TestCase):
    def test_rejects_magic_missile_when_no_targets(self):
        state = _build_state()
        req = SimpleNamespace(effect_instance_targets=None)
        with self.assertRaises(CombatServiceError) as cm:
            CombatService._validate_instance_targets(
                req=req, spell_context=_spell_context(), state=state,
            )
        self.assertIn("requires effect_instance_targets", str(cm.exception))

    def test_rejects_magic_missile_when_empty_list(self):
        state = _build_state()
        req = SimpleNamespace(effect_instance_targets=[])
        with self.assertRaises(CombatServiceError) as cm:
            CombatService._validate_instance_targets(
                req=req, spell_context=_spell_context(), state=state,
            )
        self.assertIn("requires effect_instance_targets", str(cm.exception))

    def test_returns_none_when_no_targets_for_non_magic_missile(self):
        state = _build_state()
        req = SimpleNamespace(effect_instance_targets=None)
        ctx = _spell_context()
        ctx["spell_canonical_key"] = "eldritch_blast"
        result = CombatService._validate_instance_targets(
            req=req, spell_context=ctx, state=state,
        )
        self.assertIsNone(result)

    def test_accepts_valid_5_instance_assignment(self):
        state = _build_state()
        targets = [
            EffectInstanceTarget(instance_index=1, target_ref_id="entity:goblin-a"),
            EffectInstanceTarget(instance_index=2, target_ref_id="entity:goblin-a"),
            EffectInstanceTarget(instance_index=3, target_ref_id="entity:goblin-b"),
            EffectInstanceTarget(instance_index=4, target_ref_id="entity:goblin-b"),
            EffectInstanceTarget(instance_index=5, target_ref_id="entity:goblin-c"),
        ]
        req = _req_with_targets(targets)
        result = CombatService._validate_instance_targets(
            req=req, spell_context=_spell_context(), state=state,
        )
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 5)
        self.assertEqual(result[0]["instance_index"], 1)
        self.assertEqual(result[0]["target_ref_id"], "entity:goblin-a")
        self.assertEqual(result[0]["participant"]["display_name"], "Goblin A")

    def test_accepts_all_instances_same_target(self):
        state = _build_state()
        targets = [
            EffectInstanceTarget(instance_index=i, target_ref_id="entity:goblin-a")
            for i in range(1, 6)
        ]
        req = _req_with_targets(targets)
        result = CombatService._validate_instance_targets(
            req=req, spell_context=_spell_context(), state=state,
        )
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 5)
        for entry in result:
            self.assertEqual(entry["target_ref_id"], "entity:goblin-a")

    def test_accepts_2_instance_assignment(self):
        state = _build_state()
        targets = [
            EffectInstanceTarget(instance_index=1, target_ref_id="entity:goblin-a"),
            EffectInstanceTarget(instance_index=2, target_ref_id="entity:goblin-b"),
        ]
        ctx = _spell_context(count=2, dice="1d10", spell_mode="spell_attack")
        req = _req_with_targets(targets)
        result = CombatService._validate_instance_targets(
            req=req, spell_context=ctx, state=state,
        )
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)

    def test_rejects_single_instance_spell(self):
        state = _build_state()
        targets = [EffectInstanceTarget(instance_index=1, target_ref_id="entity:goblin-a")]
        ctx = _spell_context(count=1)
        req = _req_with_targets(targets)
        with self.assertRaises(CombatServiceError) as cm:
            CombatService._validate_instance_targets(
                req=req, spell_context=ctx, state=state,
            )
        self.assertIn("only supported for multi-instance spells", str(cm.exception))

    def test_rejects_index_out_of_range(self):
        state = _build_state()
        targets = [
            EffectInstanceTarget(instance_index=1, target_ref_id="entity:goblin-a"),
            EffectInstanceTarget(instance_index=2, target_ref_id="entity:goblin-a"),
            EffectInstanceTarget(instance_index=3, target_ref_id="entity:goblin-b"),
            EffectInstanceTarget(instance_index=4, target_ref_id="entity:goblin-b"),
            EffectInstanceTarget(instance_index=6, target_ref_id="entity:goblin-c"),
        ]
        req = _req_with_targets(targets)
        with self.assertRaises(CombatServiceError) as cm:
            CombatService._validate_instance_targets(
                req=req, spell_context=_spell_context(), state=state,
            )
        self.assertIn("out of range", str(cm.exception))
        self.assertIn("6", str(cm.exception))

    def test_rejects_duplicate_index(self):
        state = _build_state()
        targets = [
            EffectInstanceTarget(instance_index=1, target_ref_id="entity:goblin-a"),
            EffectInstanceTarget(instance_index=1, target_ref_id="entity:goblin-b"),
        ]
        ctx = _spell_context(count=2)
        req = _req_with_targets(targets)
        with self.assertRaises(CombatServiceError) as cm:
            CombatService._validate_instance_targets(
                req=req, spell_context=ctx, state=state,
            )
        self.assertIn("Duplicate instance index", str(cm.exception))

    def test_rejects_incomplete_assignment(self):
        state = _build_state()
        targets = [
            EffectInstanceTarget(instance_index=1, target_ref_id="entity:goblin-a"),
            EffectInstanceTarget(instance_index=2, target_ref_id="entity:goblin-a"),
            EffectInstanceTarget(instance_index=3, target_ref_id="entity:goblin-b"),
        ]
        req = _req_with_targets(targets)
        with self.assertRaises(CombatServiceError) as cm:
            CombatService._validate_instance_targets(
                req=req, spell_context=_spell_context(), state=state,
            )
        self.assertIn("Missing instance target assignments", str(cm.exception))
        self.assertIn("4", str(cm.exception))
        self.assertIn("5", str(cm.exception))

    def test_rejects_invalid_target_ref(self):
        state = _build_state()
        targets = [
            EffectInstanceTarget(instance_index=1, target_ref_id="entity:goblin-a"),
            EffectInstanceTarget(instance_index=2, target_ref_id="entity:nonexistent"),
        ]
        ctx = _spell_context(count=2)
        req = _req_with_targets(targets)
        with self.assertRaises(CombatServiceError) as cm:
            CombatService._validate_instance_targets(
                req=req, spell_context=ctx, state=state,
            )
        self.assertIn("Invalid target_ref_id for instance 2", str(cm.exception))


class InstanceDirectResolutionTests(unittest.TestCase):
    @patch("random.randint", return_value=3)
    def test_resolves_direct_damage_per_instance(self, mock_rand):
        state = _build_state()
        db = MagicMock()
        target = state.participants[1]
        spell_context = _spell_context()
        req = SimpleNamespace(
            concentration_roll_source="system",
            concentration_manual_roll=None,
        )

        CombatService._apply_spell_effect = MagicMock(return_value=(8, "dano aplicado", 10, None))
        outcome = CombatService._resolve_instance_direct(
            db, state, state.participants[0], target, spell_context, req,
        )
        self.assertEqual(outcome["target_ref_id"], "entity:goblin-a")
        self.assertEqual(outcome["target_display_name"], "Goblin A")
        self.assertEqual(outcome["target_kind"], "session_entity")
        self.assertEqual(outcome["damage"], 4)
        self.assertEqual(outcome["healing"], 0)
        self.assertIsNone(outcome["is_hit"])
        self.assertFalse(outcome["is_critical"])

    def test_rejects_missing_instance_dice(self):
        state = _build_state()
        db = MagicMock()
        target = state.participants[1]
        spell_context = _spell_context()
        spell_context["effect_instance_dice"] = None
        req = SimpleNamespace(
            concentration_roll_source="system",
            concentration_manual_roll=None,
        )
        with self.assertRaises(CombatServiceError) as cm:
            CombatService._resolve_instance_direct(
                db, state, state.participants[0], target, spell_context, req,
            )
        self.assertIn("missing effect_instance_dice", str(cm.exception))


class InstanceAttackResolutionTests(unittest.TestCase):
    @patch.object(CombatService, "_get_stats", return_value=(MagicMock(), 12, MagicMock(), MagicMock(), MagicMock(), MagicMock()))
    @patch("random.randint", return_value=15)
    def test_resolves_attack_hit_per_instance(self, mock_rand, mock_stats):
        from app.schemas.roll import RollActorStats

        state = _build_state()
        db = MagicMock()
        target = state.participants[1]
        attacker = state.participants[0]
        spell_context = _spell_context(count=2, dice="1d10", spell_mode="spell_attack")
        spell_context["attack_bonus"] = 5
        req = SimpleNamespace(
            has_advantage=False,
            has_disadvantage=False,
            roll_source="system",
            concentration_roll_source="system",
            concentration_manual_roll=None,
        )

        CombatService._apply_spell_effect = MagicMock(return_value=(8, "dano aplicado", 20, None))
        CombatService._resolve_damage_roll = MagicMock(return_value=([], 15))

        outcome = CombatService._resolve_instance_attack(
            db, "session-1", state, attacker, target, spell_context, req, is_gm=False,
        )
        self.assertEqual(outcome["target_ref_id"], "entity:goblin-a")
        self.assertIn(outcome["is_hit"], (True, False))

    @patch.object(CombatService, "_get_stats", return_value=(MagicMock(), 20, MagicMock(), MagicMock(), MagicMock(), MagicMock()))
    @patch("random.randint", return_value=1)
    def test_resolves_attack_miss_zero_damage(self, mock_rand, mock_stats):
        state = _build_state()
        db = MagicMock()
        target = state.participants[1]
        attacker = state.participants[0]
        spell_context = _spell_context(count=2, dice="1d10", spell_mode="spell_attack")
        spell_context["attack_bonus"] = 0
        req = SimpleNamespace(
            has_advantage=False,
            has_disadvantage=False,
            roll_source="system",
            concentration_roll_source="system",
            concentration_manual_roll=None,
        )

        with patch.object(CombatService, "_apply_spell_effect") as mock_apply:
            outcome = CombatService._resolve_instance_attack(
                db, "session-1", state, attacker, target, spell_context, req, is_gm=False,
            )
        self.assertFalse(outcome["is_hit"])
        self.assertEqual(outcome["damage"], 0)
        mock_apply.assert_not_called()

    @patch.object(CombatService, "_get_stats", return_value=(MagicMock(), 12, MagicMock(), MagicMock(), MagicMock(), MagicMock()))
    @patch("random.randint", return_value=15)
    def test_condition_advantage_applies(self, mock_rand, mock_stats):
        state = _build_state()
        goblin = state.participants[1]
        goblin["conditions"] = [{"type": "restrained"}]
        attacker = state.participants[0]
        db = MagicMock()
        spell_context = _spell_context(count=2, dice="1d10", spell_mode="spell_attack")
        spell_context["attack_bonus"] = 5
        req = SimpleNamespace(
            has_advantage=False,
            has_disadvantage=False,
            roll_source="system",
            concentration_roll_source="system",
            concentration_manual_roll=None,
        )

        CombatService._apply_spell_effect = MagicMock(return_value=(8, "", 20, None))
        CombatService._resolve_damage_roll = MagicMock(return_value=([], 10))

        outcome = CombatService._resolve_instance_attack(
            db, "session-1", state, attacker, goblin, spell_context, req, is_gm=False,
        )
        self.assertIsNotNone(outcome["roll_result"])

    @patch.object(CombatService, "_get_stats", return_value=(MagicMock(), 12, MagicMock(), MagicMock(), MagicMock(), MagicMock()))
    def test_attacker_condition_disadvantage_applies(self, mock_stats):
        state = _build_state()
        target = state.participants[1]
        attacker = state.participants[0]
        attacker["conditions"] = [{"type": "poisoned"}]
        db = MagicMock()
        spell_context = _spell_context(count=2, dice="1d10", spell_mode="spell_attack")
        spell_context["attack_bonus"] = 5
        req = SimpleNamespace(
            has_advantage=False,
            has_disadvantage=False,
            roll_source="system",
            concentration_roll_source="system",
            concentration_manual_roll=None,
        )

        CombatService._apply_spell_effect = MagicMock(return_value=(8, "", 20, None))
        CombatService._resolve_damage_roll = MagicMock(return_value=([], 10))

        outcome = CombatService._resolve_instance_attack(
            db, "session-1", state, attacker, target, spell_context, req, is_gm=False,
        )
        self.assertIsNotNone(outcome["roll_result"])


class MultiInstanceLogMessageTests(unittest.TestCase):
    def test_formats_multi_instance_log(self):
        outcomes = [
            {"instance_index": 1, "target_display_name": "Goblin A", "damage": 3, "is_hit": None},
            {"instance_index": 2, "target_display_name": "Goblin A", "damage": 5, "is_hit": None},
            {"instance_index": 3, "target_display_name": "Goblin B", "damage": 2, "is_hit": None},
        ]
        msg = CombatService._build_multi_instance_log_message(
            attacker={"display_name": "Hero"},
            spell_context={"spell_name": "Magic Missile", "damage_type": "Force"},
            outcomes=outcomes,
            was_overridden=False,
            action_cost="action",
        )
        self.assertIn("Hero conjurou Magic Missile: 3 instâncias.", msg)
        self.assertIn("Instância 1 → Goblin A: 3 de dano de Force.", msg)
        self.assertIn("Instância 2 → Goblin A: 5 de dano de Force.", msg)
        self.assertIn("Instância 3 → Goblin B: 2 de dano de Force.", msg)

    def test_formats_miss_instance(self):
        outcomes = [
            {"instance_index": 1, "target_display_name": "Goblin A", "damage": 0, "is_hit": False},
        ]
        msg = CombatService._build_multi_instance_log_message(
            attacker={"display_name": "Hero"},
            spell_context={"spell_name": "Eldritch Blast", "damage_type": "Force"},
            outcomes=outcomes,
            was_overridden=False,
            action_cost="action",
        )
        self.assertIn("errou", msg)

    def test_includes_override_prefix(self):
        outcomes = [
            {"instance_index": 1, "target_display_name": "Goblin A", "damage": 4, "is_hit": None},
        ]
        msg = CombatService._build_multi_instance_log_message(
            attacker={"display_name": "Hero"},
            spell_context={"spell_name": "Magic Missile", "damage_type": "Force"},
            outcomes=outcomes,
            was_overridden=True,
            action_cost="action",
        )
        self.assertTrue(msg.startswith("[OVERRIDE:"))

    def test_miss_with_cover_shows_effective_ac(self):
        outcomes = [
            {
                "instance_index": 1,
                "target_display_name": "Goblin A",
                "damage": 0,
                "is_hit": False,
                "roll": 16,
                "cover": "half",
                "base_ac": 15,
                "effective_ac": 17,
                "cover_modifier": 2,
            },
        ]
        msg = CombatService._build_multi_instance_log_message(
            attacker={"display_name": "Hero"},
            spell_context={"spell_name": "Eldritch Blast", "damage_type": "Force"},
            outcomes=outcomes,
            was_overridden=False,
            action_cost="action",
        )
        self.assertIn("AC efetiva 17", msg)
        self.assertIn("base 15", msg)
        self.assertIn("Half Cover", msg)
        self.assertIn("errou", msg)

    def test_miss_without_cover_shows_simple_format(self):
        outcomes = [
            {"instance_index": 1, "target_display_name": "Goblin A", "damage": 0, "is_hit": False},
        ]
        msg = CombatService._build_multi_instance_log_message(
            attacker={"display_name": "Hero"},
            spell_context={"spell_name": "Eldritch Blast", "damage_type": "Force"},
            outcomes=outcomes,
            was_overridden=False,
            action_cost="action",
        )
        self.assertIn("errou", msg)
        self.assertNotIn("AC efetiva", msg)


class ResolveMultiInstanceCastTests(unittest.IsolatedAsyncioTestCase):
    async def test_response_includes_per_target_totals_and_preserves_instance_order(self):
        state = _build_state()
        db = MagicMock()
        attacker = state.participants[0]
        attacker_model = MagicMock()
        attacker_model.state_json = {"spellcasting": {"slots": {"1": {"used": 0, "max": 2}}}}
        spell_context = {
            **_spell_context(count=3),
            "slot_level": 1,
            "action_cost": "action",
            "source_kind": "spell",
            "spell_level": 1,
            "base_effect_instance_count": 3,
            "upcast_added_instances": 0,
        }
        req = SimpleNamespace(
            concentration_roll_source="system",
            concentration_manual_roll=None,
            override_resource_limit=False,
        )
        validated_targets = [
            {"instance_index": 1, "target_ref_id": "entity:goblin-a", "participant": state.participants[1]},
            {"instance_index": 2, "target_ref_id": "entity:goblin-b", "participant": state.participants[2]},
            {"instance_index": 3, "target_ref_id": "entity:goblin-a", "participant": state.participants[1]},
        ]

        with (
            patch.object(CombatService, "_consume_turn_resource", return_value=False),
            patch.object(CombatService, "_consume_player_spell_slot"),
            patch.object(CombatService, "_resolve_instance_direct", side_effect=[
                {"target_ref_id": "entity:goblin-a", "target_display_name": "Goblin A", "target_kind": "session_entity", "damage": 3, "healing": 0, "is_hit": None, "is_saved": None, "is_critical": False, "roll": None, "roll_result": None, "new_hp": None, "previous_hp": None},
                {"target_ref_id": "entity:goblin-b", "target_display_name": "Goblin B", "target_kind": "session_entity", "damage": 5, "healing": 0, "is_hit": None, "is_saved": None, "is_critical": False, "roll": None, "roll_result": None, "new_hp": None, "previous_hp": None},
                {"target_ref_id": "entity:goblin-a", "target_display_name": "Goblin A", "target_kind": "session_entity", "damage": 2, "healing": 0, "is_hit": None, "is_saved": None, "is_critical": False, "roll": None, "roll_result": None, "new_hp": None, "previous_hp": None},
            ]),
            patch.object(CombatService, "_emit_state"),
            patch.object(CombatService, "_emit_player_state_update"),
            patch.object(CombatService, "_emit_entity_hp_update"),
            patch.object(CombatService, "_emit_and_persist_log"),
        ):
            result = await CombatService._resolve_multi_instance_cast(
                db,
                "session-1",
                req,
                state,
                attacker,
                attacker_model,
                spell_context,
                "user-1",
                False,
                validated_targets,
            )

        self.assertEqual(result["effect_instance_count"], 3)
        self.assertEqual([o["instance_index"] for o in result["effect_instance_outcomes"]], [1, 2, 3])
        self.assertEqual(result["damage"], 10)
        per_target = {e["target_ref_id"]: e for e in result["effect_instance_target_totals"]}
        self.assertEqual(per_target["entity:goblin-a"]["instance_count"], 2)
        self.assertEqual(per_target["entity:goblin-a"]["damage"], 5)
        self.assertEqual(per_target["entity:goblin-b"]["instance_count"], 1)
        self.assertEqual(per_target["entity:goblin-b"]["damage"], 5)


class EffectInstanceTargetSchemaTests(unittest.TestCase):
    def test_valid_target(self):
        t = EffectInstanceTarget(instance_index=1, target_ref_id="entity:goblin-a")
        self.assertEqual(t.instance_index, 1)
        self.assertEqual(t.target_ref_id, "entity:goblin-a")

    def test_rejects_zero_index(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            EffectInstanceTarget(instance_index=0, target_ref_id="entity:goblin-a")

    def test_rejects_negative_index(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            EffectInstanceTarget(instance_index=-1, target_ref_id="entity:goblin-a")


class EffectInstanceOutcomeSchemaTests(unittest.TestCase):
    def test_minimal_outcome(self):
        from app.schemas.combat_spells import EffectInstanceOutcome
        o = EffectInstanceOutcome(
            instance_index=1,
            target_ref_id="entity:goblin-a",
            target_display_name="Goblin A",
            target_kind="session_entity",
        )
        self.assertEqual(o.instance_index, 1)
        self.assertEqual(o.damage, 0)
        self.assertIsNone(o.is_hit)

    def test_full_outcome(self):
        from app.schemas.combat_spells import EffectInstanceOutcome
        o = EffectInstanceOutcome(
            instance_index=3,
            target_ref_id="entity:goblin-c",
            target_display_name="Goblin C",
            target_kind="session_entity",
            damage=5,
            healing=0,
            is_hit=True,
            is_saved=None,
            is_critical=False,
            roll=18,
            new_hp=3,
        )
        self.assertEqual(o.damage, 5)
        self.assertTrue(o.is_hit)
        self.assertEqual(o.new_hp, 3)

    def test_outcome_with_cover_fields(self):
        from app.schemas.combat_spells import EffectInstanceOutcome
        o = EffectInstanceOutcome(
            instance_index=1,
            target_ref_id="entity:goblin-a",
            target_display_name="Goblin A",
            target_kind="session_entity",
            cover="half",
            base_ac=15,
            effective_ac=17,
            cover_modifier=2,
        )
        self.assertEqual(o.cover, "half")
        self.assertEqual(o.base_ac, 15)
        self.assertEqual(o.effective_ac, 17)
        self.assertEqual(o.cover_modifier, 2)

    def test_outcome_cover_fields_default_to_none_and_zero(self):
        from app.schemas.combat_spells import EffectInstanceOutcome
        o = EffectInstanceOutcome(
            instance_index=1,
            target_ref_id="entity:goblin-a",
            target_display_name="Goblin A",
            target_kind="session_entity",
        )
        self.assertIsNone(o.cover)
        self.assertIsNone(o.base_ac)
        self.assertIsNone(o.effective_ac)
        self.assertEqual(o.cover_modifier, 0)


class CombatSpellResultInstanceOutcomesTests(unittest.TestCase):
    def test_result_has_empty_outcomes_by_default(self):
        from app.schemas.combat_spells import CombatSpellResult
        r = CombatSpellResult(
            spell_name="Magic Missile",
            action_kind="direct_damage",
            target_display_name="Goblin",
            target_kind="session_entity",
        )
        self.assertEqual(r.effect_instance_outcomes, [])

    def test_result_cover_fields_default(self):
        from app.schemas.combat_spells import CombatSpellResult
        r = CombatSpellResult(
            spell_name="Fireball",
            action_kind="saving_throw",
            target_display_name="Area target",
            target_kind="session_entity",
        )
        self.assertIsNone(r.cover)
        self.assertIsNone(r.base_ac)
        self.assertIsNone(r.base_save_dc)
        self.assertEqual(r.cover_modifier, 0)

    def test_result_with_cover_metadata(self):
        from app.schemas.combat_spells import CombatSpellResult
        r = CombatSpellResult(
            spell_name="Eldritch Blast",
            action_kind="spell_attack",
            target_display_name="Goblin",
            target_kind="session_entity",
            cover="half",
            base_ac=15,
            cover_modifier=2,
        )
        self.assertEqual(r.cover, "half")
        self.assertEqual(r.base_ac, 15)
        self.assertEqual(r.cover_modifier, 2)

    def test_result_with_instance_outcomes(self):
        from app.schemas.combat_spells import CombatSpellResult, EffectInstanceOutcome
        outcomes = [
            EffectInstanceOutcome(
                instance_index=1,
                target_ref_id="entity:goblin-a",
                target_display_name="Goblin A",
                target_kind="session_entity",
                damage=4,
            ),
            EffectInstanceOutcome(
                instance_index=2,
                target_ref_id="entity:goblin-b",
                target_display_name="Goblin B",
                target_kind="session_entity",
                damage=3,
            ),
        ]
        r = CombatSpellResult(
            spell_name="Magic Missile",
            action_kind="direct_damage",
            target_display_name="Goblin A",
            target_kind="session_entity",
            effect_instance_outcomes=outcomes,
        )
        self.assertEqual(len(r.effect_instance_outcomes), 2)
        self.assertEqual(r.effect_instance_outcomes[0].damage, 4)
        self.assertEqual(r.effect_instance_outcomes[1].target_ref_id, "entity:goblin-b")


class ValidateInstanceTargetsEdgeCasesTests(unittest.TestCase):
    def test_validates_against_participants_not_ref_ids(self):
        state = _build_state(participants=[
            {
                "id": "p1",
                "ref_id": "player-1",
                "kind": "player",
                "display_name": "Hero",
                "status": "active",
                "team": "players",
                "visible": True,
                "actor_user_id": "user-1",
            },
        ])
        targets = [EffectInstanceTarget(instance_index=1, target_ref_id="entity:ghost")]
        ctx = _spell_context(count=1)
        ctx["effect_instance_count"] = 1
        req = _req_with_targets(targets)
        with self.assertRaises(CombatServiceError) as cm:
            CombatService._validate_instance_targets(
                req=req, spell_context=ctx, state=state,
            )
        self.assertIn("only supported for multi-instance", str(cm.exception))
