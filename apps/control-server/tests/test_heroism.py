from __future__ import annotations

import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.models.combat import CombatPhase, CombatState
from app.models.session_state import SessionState
from app.schemas.base_spell_effects import ConditionImmunityParams, RecurringTempHpParams, SpellDeclarativeEffect
from app.schemas.combat_spells import CombatResolveSpellContextRequest
from app.services.combat import CombatService
from app.services.combat_service.condition_effects_predicates import has_condition_immunity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_player(pid: str = "p1", user_id: str = "u1") -> dict:
    return {
        "id": pid,
        "ref_id": pid,
        "kind": "player",
        "display_name": "Hero",
        "status": "active",
        "team": "players",
        "visible": True,
        "actor_user_id": user_id,
        "active_effects": [],
        "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False},
    }


def _make_target(pid: str = "t1", ref_id: str = "target-1") -> dict:
    return {
        "id": pid,
        "ref_id": ref_id,
        "kind": "session_entity",
        "display_name": f"Target {pid}",
        "status": "active",
        "team": "players",
        "visible": True,
        "actor_user_id": None,
        "active_effects": [],
        "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False},
    }


def _make_state(participants: list[dict]) -> CombatState:
    return CombatState(
        id="c1",
        session_id="s1",
        phase=CombatPhase.active,
        round=1,
        current_turn_index=0,
        participants=participants,
        use_map=False,
    )


def _make_heroism_catalog_spell(max_targets: int = 1):
    return SimpleNamespace(
        canonical_key="heroism",
        name_en="Heroism",
        name_pt="Heroísmo",
        level=1,
        resolution_type="buff",
        damage_dice=None,
        heal_dice=None,
        damage_type=None,
        saving_throw=None,
        save_success_outcome=None,
        upcast_json={"mode": "additional_targets", "perLevel": 1},
        cantrip_scaling_json=None,
        casting_time_type="action",
        target_type="ranged",
        selection_type="creature",
        origin_type="caster",
        target_anchor="selected_target",
        attack_type="none",
        range_kind="touch",
        effect_timing="persistent",
        area_shape=None,
        range_meters=1.5,
        duration="Concentration, up to 1 minute",
        concentration=True,
        max_targets=max_targets,
        requires_target_sight=True,
        requires_target_effect=True,
        requires_point_sight=False,
        requires_point_effect=False,
        effects_json=[
            {
                "type": "condition_immunity",
                "target": "selected_target",
                "duration": {"type": "manual"},
                "params": {"conditions": ["frightened"]},
                "stacking": "replace",
            }
        ],
    )


def _condition_immunity_effect(concentration_group: str = "grp-1") -> SpellDeclarativeEffect:
    return SpellDeclarativeEffect.model_validate(
        {
            "type": "condition_immunity",
            "target": "selected_target",
            "duration": {"type": "manual"},
            "params": {"conditions": ["frightened"]},
            "stacking": "replace",
        }
    )


def _spell_context(concentration: bool = True) -> dict:
    return {
        "spell_name": "Heroísmo",
        "spell_canonical_key": "heroism",
        "spell_mode": "utility",
        "concentration": concentration,
        "slot_level": 1,
        "action_cost": "action",
        "source_kind": "spell",
        "effect_kind": "none",
        "effect_dice": None,
        "effect_bonus": 0,
        "target_type": "ranged",
        "range_kind": "touch",
        "attack_type": "none",
        "requires_target_sight": True,
        "requires_target_effect": True,
    }


# ---------------------------------------------------------------------------
# Seed tests
# ---------------------------------------------------------------------------

class HeroismSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json"
        )
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        cls.spells = {s["canonicalKey"]: s for s in data.get("spells", [])}

    def test_heroism_present(self):
        self.assertIn("heroism", self.spells)

    def test_heroism_basic_fields(self):
        s = self.spells["heroism"]
        self.assertEqual(s["level"], 1)
        self.assertEqual(s["school"], "enchantment")
        self.assertTrue(s["concentration"])
        self.assertEqual(s["maxTargets"], 1)

    def test_heroism_upcast(self):
        upcast = self.spells["heroism"].get("upcast") or {}
        self.assertEqual(upcast.get("mode"), "additional_targets")
        self.assertEqual(upcast.get("perLevel"), 1)

    def test_heroism_has_condition_immunity_effect(self):
        effects = self.spells["heroism"].get("effects", [])
        types = [e.get("type") for e in effects]
        self.assertIn("condition_immunity", types)

    def test_heroism_condition_immunity_targets_frightened(self):
        effects = self.spells["heroism"].get("effects", [])
        immunity = next(e for e in effects if e.get("type") == "condition_immunity")
        self.assertIn("frightened", immunity["params"]["conditions"])


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

class ConditionImmunitySchemaTests(unittest.TestCase):
    def test_valid_condition_immunity_effect(self):
        effect = SpellDeclarativeEffect.model_validate(
            {
                "type": "condition_immunity",
                "target": "selected_target",
                "duration": {"type": "manual"},
                "params": {"conditions": ["frightened", "charmed"]},
            }
        )
        self.assertIsInstance(effect.params, ConditionImmunityParams)
        self.assertEqual(effect.params.conditions, ["frightened", "charmed"])

    def test_invalid_condition_immunity_effect_rejects_unknown_condition(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            SpellDeclarativeEffect.model_validate(
                {
                    "type": "condition_immunity",
                    "target": "selected_target",
                    "duration": {"type": "manual"},
                    "params": {"conditions": ["nonexistent_condition"]},
                }
            )


# ---------------------------------------------------------------------------
# Predicate tests
# ---------------------------------------------------------------------------

class HasConditionImmunityTests(unittest.TestCase):
    def _participant_with_immunity(self, immune_conditions: list[str]) -> dict:
        return {
            "active_effects": [
                {
                    "id": "eff-1",
                    "kind": "spell_effect",
                    "metadata": {
                        "condition_immunity": True,
                        "immune_conditions": immune_conditions,
                    },
                }
            ]
        }

    def test_immune_to_listed_condition(self):
        p = self._participant_with_immunity(["frightened"])
        self.assertTrue(has_condition_immunity(p, "frightened"))

    def test_not_immune_to_unlisted_condition(self):
        p = self._participant_with_immunity(["frightened"])
        self.assertFalse(has_condition_immunity(p, "charmed"))

    def test_no_effects_returns_false(self):
        self.assertFalse(has_condition_immunity({"active_effects": []}, "frightened"))

    def test_non_spell_effect_does_not_count(self):
        p = {
            "active_effects": [
                {
                    "id": "eff-1",
                    "kind": "condition",
                    "metadata": {
                        "condition_immunity": True,
                        "immune_conditions": ["frightened"],
                    },
                }
            ]
        }
        self.assertFalse(has_condition_immunity(p, "frightened"))

    def test_multiple_conditions(self):
        p = self._participant_with_immunity(["frightened", "charmed", "poisoned"])
        self.assertTrue(has_condition_immunity(p, "charmed"))
        self.assertTrue(has_condition_immunity(p, "poisoned"))
        self.assertFalse(has_condition_immunity(p, "blinded"))


# ---------------------------------------------------------------------------
# _apply_single_declarative_effect: condition_immunity
# ---------------------------------------------------------------------------

class ApplyConditionImmunityEffectTests(unittest.TestCase):
    def _apply(self, attacker: dict, target: dict, state: CombatState, effect: SpellDeclarativeEffect | None = None):
        if effect is None:
            effect = _condition_immunity_effect()
        return CombatService._apply_single_declarative_effect(
            state=state,
            attacker=attacker,
            target_participant=target,
            spell_context=_spell_context(concentration=True),
            effect=effect,
            effect_group_id="grp-heroism",
            on_end_effects=[],
        )

    def test_applies_condition_immunity_effect_to_target(self):
        attacker = _make_player()
        target = _make_target()
        state = _make_state([attacker, target])
        created = self._apply(attacker, target, state)
        self.assertEqual(len(created), 1)
        effect = created[0]
        self.assertEqual(effect["kind"], "spell_effect")
        self.assertTrue(effect["metadata"]["condition_immunity"])
        self.assertIn("frightened", effect["metadata"]["immune_conditions"])

    def test_concentration_group_set_when_concentration(self):
        attacker = _make_player()
        target = _make_target()
        state = _make_state([attacker, target])
        created = self._apply(attacker, target, state)
        meta = created[0]["metadata"]
        self.assertEqual(meta["concentration_group"], "grp-heroism")

    def test_target_has_one_active_effect_after_apply(self):
        attacker = _make_player()
        target = _make_target()
        state = _make_state([attacker, target])
        self._apply(attacker, target, state)
        effects = target.get("active_effects") or []
        self.assertEqual(len(effects), 1)

    def test_suppresses_existing_frightened_on_cast(self):
        attacker = _make_player()
        target = _make_target()
        target["active_effects"] = [
            {
                "id": "pre-existing",
                "kind": "condition",
                "condition_type": "frightened",
                "metadata": {},
            }
        ]
        state = _make_state([attacker, target])
        self._apply(attacker, target, state)
        effects = target.get("active_effects") or []
        condition_kinds = [e.get("kind") for e in effects]
        self.assertNotIn("condition", condition_kinds)

    def test_does_not_suppress_unrelated_conditions(self):
        attacker = _make_player()
        target = _make_target()
        target["active_effects"] = [
            {
                "id": "charmed-eff",
                "kind": "condition",
                "condition_type": "charmed",
                "metadata": {},
            }
        ]
        state = _make_state([attacker, target])
        self._apply(attacker, target, state)
        effects = target.get("active_effects") or []
        condition_types = [e.get("condition_type") for e in effects if e.get("kind") == "condition"]
        self.assertIn("charmed", condition_types)


# ---------------------------------------------------------------------------
# Immunity gate: apply_condition blocked when immune
# ---------------------------------------------------------------------------

class ConditionImmunityGateTests(unittest.TestCase):
    def _immunity_effect_dict(self, conditions: list[str]) -> dict:
        return {
            "id": "immunity-eff",
            "kind": "spell_effect",
            "metadata": {
                "condition_immunity": True,
                "immune_conditions": conditions,
            },
        }

    def _apply_condition(self, target: dict, state: CombatState, condition: str = "frightened") -> list[dict]:
        attacker = next(p for p in state.participants if p["id"] == "p1")
        effect = SpellDeclarativeEffect.model_validate(
            {
                "type": "apply_condition",
                "target": "selected_target",
                "duration": {"type": "manual"},
                "params": {"condition": condition},
            }
        )
        return CombatService._apply_single_declarative_effect(
            state=state,
            attacker=attacker,
            target_participant=target,
            spell_context={"spell_name": "Fear", "spell_canonical_key": "fear", "concentration": False},
            effect=effect,
            effect_group_id="grp-fear",
            on_end_effects=[],
        )

    def test_frightened_blocked_by_heroism_immunity(self):
        attacker = _make_player()
        target = _make_target()
        target["active_effects"] = [self._immunity_effect_dict(["frightened"])]
        state = _make_state([attacker, target])

        pre_count = len(target["active_effects"])
        created = self._apply_condition(target, state, "frightened")
        self.assertEqual(created, [])
        self.assertEqual(len(target["active_effects"]), pre_count)

    def test_non_immune_condition_not_blocked(self):
        attacker = _make_player()
        target = _make_target()
        target["active_effects"] = [self._immunity_effect_dict(["frightened"])]
        state = _make_state([attacker, target])

        created = self._apply_condition(target, state, "charmed")
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0]["kind"], "condition")


# ---------------------------------------------------------------------------
# Upcast max_targets via resolve_spell_context
# ---------------------------------------------------------------------------

class HeroismUpcastContextTests(unittest.TestCase):
    def _resolve_context(self, slot_level: int) -> dict:
        state = _make_state([_make_player()])
        attacker_state = SessionState(
            id="ss-1",
            session_id="s1",
            player_user_id="u1",
            state_json={
                "spellcasting": {
                    "spells": [{"canonicalKey": "heroism", "level": 1, "prepared": True}],
                    "slots": {str(slot_level): {"used": 0, "max": 3}},
                }
            },
        )
        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch("app.services.combat.CombatService._get_spell_catalog_entry_for_session", return_value=_make_heroism_catalog_spell(1)),
            patch("app.services.combat.CombatService._get_stats", return_value=(attacker_state, 12, 10, 10, 3, 4)),
        ):
            return CombatService.resolve_spell_context(
                None,
                "s1",
                CombatResolveSpellContextRequest(
                    actor_participant_id="p1",
                    spell_canonical_key="heroism",
                    spell_mode="utility",
                    slot_level=slot_level,
                ),
                "u1",
                False,
            )

    def test_upcast_max_targets_progression(self):
        self.assertEqual(self._resolve_context(1)["max_targets"], 1)
        self.assertEqual(self._resolve_context(2)["max_targets"], 2)
        self.assertEqual(self._resolve_context(3)["max_targets"], 3)


# ---------------------------------------------------------------------------
# Concentration cleanup removes condition_immunity
# ---------------------------------------------------------------------------

class HeroismConcentrationCleanupTests(unittest.TestCase):
    def test_clearing_concentration_removes_immunity_effect(self):
        attacker = _make_player()
        target = _make_target()
        target["active_effects"] = [
            {
                "id": "heroism-immunity",
                "kind": "spell_effect",
                "source_participant_id": "p1",
                "metadata": {
                    "condition_immunity": True,
                    "immune_conditions": ["frightened"],
                    "concentration": True,
                    "concentration_group": "grp-heroism-1",
                },
            }
        ]
        attacker["active_effects"] = [
            {
                "id": "heroism-concentration-marker",
                "kind": "spell_effect",
                "source_participant_id": "p1",
                "metadata": {
                    "concentration": True,
                    "concentration_group": "grp-heroism-1",
                },
            }
        ]
        state = _make_state([attacker, target])

        CombatService._clear_concentration_for_source(state, source_participant_id="p1")

        remaining = target.get("active_effects") or []
        immunity_effects = [
            e for e in remaining
            if (e.get("metadata") or {}).get("condition_immunity")
        ]
        self.assertEqual(immunity_effects, [])

    def test_clearing_one_concentration_does_not_affect_other_groups(self):
        attacker = _make_player()
        target = _make_target()
        target["active_effects"] = [
            {
                "id": "heroism-immunity",
                "kind": "spell_effect",
                "source_participant_id": "p1",
                "metadata": {
                    "condition_immunity": True,
                    "immune_conditions": ["frightened"],
                    "concentration": True,
                    "concentration_group": "grp-heroism-1",
                },
            },
            {
                "id": "other-effect",
                "kind": "spell_effect",
                "source_participant_id": "p2",
                "metadata": {
                    "concentration": True,
                    "concentration_group": "grp-other",
                },
            },
        ]
        attacker["active_effects"] = [
            {
                "id": "heroism-marker",
                "kind": "spell_effect",
                "source_participant_id": "p1",
                "metadata": {
                    "concentration": True,
                    "concentration_group": "grp-heroism-1",
                },
            }
        ]
        state = _make_state([attacker, target])

        CombatService._clear_concentration_for_source(state, source_participant_id="p1")

        remaining = target.get("active_effects") or []
        remaining_ids = [e["id"] for e in remaining]
        self.assertNotIn("heroism-immunity", remaining_ids)
        self.assertIn("other-effect", remaining_ids)


# ---------------------------------------------------------------------------
# RecurringTempHp schema tests
# ---------------------------------------------------------------------------

class RecurringTempHpSchemaTests(unittest.TestCase):
    def test_valid_recurring_temp_hp_effect(self):
        effect = SpellDeclarativeEffect.model_validate(
            {
                "type": "recurring_temp_hp",
                "target": "selected_target",
                "duration": {"type": "manual"},
                "params": {
                    "amount_source": "caster_spellcasting_modifier",
                    "timing": "start_of_target_turn",
                    "remove_granted_temp_hp_on_end": True,
                },
            }
        )
        self.assertIsInstance(effect.params, RecurringTempHpParams)
        self.assertEqual(effect.params.amount_source, "caster_spellcasting_modifier")
        self.assertTrue(effect.params.remove_granted_temp_hp_on_end)

    def test_invalid_amount_source_rejected(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            SpellDeclarativeEffect.model_validate(
                {
                    "type": "recurring_temp_hp",
                    "target": "selected_target",
                    "duration": {"type": "manual"},
                    "params": {
                        "amount_source": "fixed_value",
                        "timing": "start_of_target_turn",
                    },
                }
            )

    def test_heroism_seed_has_recurring_temp_hp_effect(self):
        path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json"
        )
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        spells = {s["canonicalKey"]: s for s in data.get("spells", [])}
        effects = spells["heroism"].get("effects", [])
        types = [e.get("type") for e in effects]
        self.assertIn("recurring_temp_hp", types)

    def test_heroism_recurring_temp_hp_params(self):
        path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json"
        )
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        spells = {s["canonicalKey"]: s for s in data.get("spells", [])}
        effects = spells["heroism"].get("effects", [])
        recur = next(e for e in effects if e.get("type") == "recurring_temp_hp")
        self.assertEqual(recur["params"]["amount_source"], "caster_spellcasting_modifier")
        self.assertEqual(recur["params"]["timing"], "start_of_target_turn")
        self.assertTrue(recur["params"]["remove_granted_temp_hp_on_end"])


# ---------------------------------------------------------------------------
# Apply recurring_temp_hp effect via _apply_single_declarative_effect
# ---------------------------------------------------------------------------

class ApplyRecurringTempHpEffectTests(unittest.TestCase):
    def _apply(self, attacker: dict, target: dict, state: CombatState, caster_spell_mod: int = 3):
        effect = SpellDeclarativeEffect.model_validate(
            {
                "type": "recurring_temp_hp",
                "target": "selected_target",
                "duration": {"type": "manual"},
                "params": {
                    "amount_source": "caster_spellcasting_modifier",
                    "timing": "start_of_target_turn",
                    "remove_granted_temp_hp_on_end": True,
                },
                "stacking": "replace",
            }
        )
        ctx = _spell_context(concentration=True)
        ctx["caster_spell_mod"] = caster_spell_mod
        return CombatService._apply_single_declarative_effect(
            state=state,
            attacker=attacker,
            target_participant=target,
            spell_context=ctx,
            effect=effect,
            effect_group_id="grp-heroism",
            on_end_effects=[],
        )

    def test_creates_spell_effect_with_recurring_temp_hp_metadata(self):
        attacker = _make_player()
        target = _make_target()
        state = _make_state([attacker, target])
        created = self._apply(attacker, target, state, caster_spell_mod=3)
        self.assertEqual(len(created), 1)
        meta = created[0]["metadata"]
        self.assertTrue(meta["recurring_temp_hp"])
        self.assertEqual(meta["temp_hp_per_turn"], 3)
        self.assertEqual(meta["last_granted_temp_hp"], 0)
        self.assertTrue(meta["remove_granted_temp_hp_on_end"])

    def test_temp_hp_per_turn_reflects_caster_spell_mod(self):
        attacker = _make_player()
        target = _make_target()
        state = _make_state([attacker, target])
        created = self._apply(attacker, target, state, caster_spell_mod=5)
        self.assertEqual(created[0]["metadata"]["temp_hp_per_turn"], 5)

    def test_zero_spell_mod_yields_zero_temp_hp_per_turn(self):
        attacker = _make_player()
        target = _make_target()
        state = _make_state([attacker, target])
        created = self._apply(attacker, target, state, caster_spell_mod=0)
        self.assertEqual(created[0]["metadata"]["temp_hp_per_turn"], 0)

    def test_concentration_group_set_on_recurring_effect(self):
        attacker = _make_player()
        target = _make_target()
        state = _make_state([attacker, target])
        created = self._apply(attacker, target, state)
        self.assertEqual(created[0]["metadata"]["concentration_group"], "grp-heroism")


# ---------------------------------------------------------------------------
# _process_recurring_temp_hp: applies temp HP at turn start
# ---------------------------------------------------------------------------

class ProcessRecurringTempHpTests(unittest.IsolatedAsyncioTestCase):
    def _participant_with_recurring_effect(
        self,
        ref_id: str = "p1",
        temp_hp_per_turn: int = 3,
        last_granted: int = 0,
    ) -> dict:
        return {
            "id": "pid-1",
            "ref_id": ref_id,
            "kind": "player",
            "display_name": "Hero",
            "status": "active",
            "team": "players",
            "actor_user_id": "u1",
            "active_effects": [
                {
                    "id": "recurring-eff",
                    "kind": "spell_effect",
                    "metadata": {
                        "recurring_temp_hp": True,
                        "temp_hp_per_turn": temp_hp_per_turn,
                        "last_granted_temp_hp": last_granted,
                        "remove_granted_temp_hp_on_end": True,
                        "effect_target_participant_id": "pid-1",
                        "effect_target_ref_id": ref_id,
                        "source_spell_name": "Heroísmo",
                    },
                }
            ],
        }

    def _mock_player_model(self, current_temp_hp: int = 0):
        model = SimpleNamespace()
        model.state_json = {"tempHP": current_temp_hp, "level": 5}
        return model

    async def test_applies_temp_hp_when_zero_current(self):
        participant = self._participant_with_recurring_effect(temp_hp_per_turn=3)
        state = _make_state([participant])
        player_model = self._mock_player_model(current_temp_hp=0)

        with (
            patch.object(CombatService, "_get_stats", return_value=(player_model, 20, 20, 15, 3, 3)),
            patch.object(CombatService, "_emit_log"),
            patch("app.services.session_state_finalize.finalize_session_state_data", side_effect=lambda d: d),
        ):
            await CombatService._process_recurring_temp_hp(None, "s1", state, participant)

        self.assertEqual(player_model.state_json["tempHP"], 3)

    async def test_keep_higher_does_not_overwrite_existing_higher_temp_hp(self):
        participant = self._participant_with_recurring_effect(temp_hp_per_turn=3)
        state = _make_state([participant])
        player_model = self._mock_player_model(current_temp_hp=10)

        with (
            patch.object(CombatService, "_get_stats", return_value=(player_model, 20, 20, 15, 3, 3)),
            patch.object(CombatService, "_emit_log"),
            patch("app.services.session_state_finalize.finalize_session_state_data", side_effect=lambda d: d),
        ):
            await CombatService._process_recurring_temp_hp(None, "s1", state, participant)

        self.assertEqual(player_model.state_json["tempHP"], 10)

    async def test_last_granted_temp_hp_updated_in_metadata(self):
        participant = self._participant_with_recurring_effect(temp_hp_per_turn=3)
        state = _make_state([participant])
        player_model = self._mock_player_model(current_temp_hp=0)

        with (
            patch.object(CombatService, "_get_stats", return_value=(player_model, 20, 20, 15, 3, 3)),
            patch.object(CombatService, "_emit_log"),
            patch("app.services.session_state_finalize.finalize_session_state_data", side_effect=lambda d: d),
        ):
            await CombatService._process_recurring_temp_hp(None, "s1", state, participant)

        meta = participant["active_effects"][0]["metadata"]
        self.assertEqual(meta["last_granted_temp_hp"], 3)

    async def test_zero_temp_hp_per_turn_skipped(self):
        participant = self._participant_with_recurring_effect(temp_hp_per_turn=0)
        state = _make_state([participant])
        player_model = self._mock_player_model(current_temp_hp=0)

        with (
            patch.object(CombatService, "_get_stats", return_value=(player_model, 20, 20, 15, 3, 3)),
            patch.object(CombatService, "_emit_log"),
            patch("app.services.session_state_finalize.finalize_session_state_data", side_effect=lambda d: d),
        ):
            await CombatService._process_recurring_temp_hp(None, "s1", state, participant)

        # tempHP unchanged because temp_hp_per_turn is 0
        self.assertEqual(player_model.state_json["tempHP"], 0)

    async def test_non_player_participant_skipped(self):
        participant = {
            "id": "npc-1",
            "ref_id": "npc-ref",
            "kind": "session_entity",
            "display_name": "NPC",
            "status": "active",
            "team": "enemies",
            "actor_user_id": None,
            "active_effects": [
                {
                    "id": "recurring-eff",
                    "kind": "spell_effect",
                    "metadata": {
                        "recurring_temp_hp": True,
                        "temp_hp_per_turn": 3,
                        "last_granted_temp_hp": 0,
                        "effect_target_participant_id": "npc-1",
                        "effect_target_ref_id": "npc-ref",
                        "source_spell_name": "Heroísmo",
                    },
                }
            ],
        }
        state = _make_state([participant])
        get_stats_mock = patch.object(CombatService, "_get_stats")
        with get_stats_mock as mock_stats:
            await CombatService._process_recurring_temp_hp(None, "s1", state, participant)
            mock_stats.assert_not_called()


# ---------------------------------------------------------------------------
# _cleanup_recurring_temp_hp_effects: zeros temp HP on concentration end
# ---------------------------------------------------------------------------

class CleanupRecurringTempHpTests(unittest.TestCase):
    def _removed_effect(
        self,
        ref_id: str = "p1",
        last_granted: int = 3,
        remove_on_end: bool = True,
    ) -> dict:
        return {
            "id": "recurring-eff",
            "kind": "spell_effect",
            "metadata": {
                "recurring_temp_hp": True,
                "temp_hp_per_turn": 3,
                "last_granted_temp_hp": last_granted,
                "remove_granted_temp_hp_on_end": remove_on_end,
                "effect_target_participant_id": "pid-1",
                "effect_target_ref_id": ref_id,
            },
        }

    def _mock_player_model(self, current_temp_hp: int):
        m = SimpleNamespace()
        m.state_json = {"tempHP": current_temp_hp}
        return m

    def _state_with_player(self, ref_id: str = "p1") -> CombatState:
        p = {"id": "pid-1", "ref_id": ref_id, "kind": "player", "display_name": "Hero", "active_effects": []}
        return _make_state([p])

    def test_zeros_temp_hp_when_at_or_below_last_granted(self):
        state = self._state_with_player()
        player_model = self._mock_player_model(current_temp_hp=3)
        removed = [self._removed_effect(last_granted=3)]

        with (
            patch.object(CombatService, "_get_stats", return_value=(player_model, 20, 20, 15, 3, 3)),
            patch("app.services.session_state_finalize.finalize_session_state_data", side_effect=lambda d: d),
        ):
            db_mock = SimpleNamespace(add=lambda x: None)
            CombatService._cleanup_recurring_temp_hp_effects(db_mock, state, removed)

        self.assertEqual(player_model.state_json["tempHP"], 0)

    def test_does_not_zero_when_higher_source_replaced_it(self):
        state = self._state_with_player()
        player_model = self._mock_player_model(current_temp_hp=10)
        removed = [self._removed_effect(last_granted=3)]

        with (
            patch.object(CombatService, "_get_stats", return_value=(player_model, 20, 20, 15, 3, 3)),
            patch("app.services.session_state_finalize.finalize_session_state_data", side_effect=lambda d: d),
        ):
            db_mock = SimpleNamespace(add=lambda x: None)
            CombatService._cleanup_recurring_temp_hp_effects(db_mock, state, removed)

        self.assertEqual(player_model.state_json["tempHP"], 10)

    def test_skipped_when_remove_on_end_false(self):
        state = self._state_with_player()
        player_model = self._mock_player_model(current_temp_hp=3)
        removed = [self._removed_effect(last_granted=3, remove_on_end=False)]

        with patch.object(CombatService, "_get_stats", return_value=(player_model, 20, 20, 15, 3, 3)) as mock_stats:
            db_mock = SimpleNamespace(add=lambda x: None)
            CombatService._cleanup_recurring_temp_hp_effects(db_mock, state, removed)
            mock_stats.assert_not_called()

        self.assertEqual(player_model.state_json["tempHP"], 3)

    def test_skipped_when_last_granted_is_zero(self):
        state = self._state_with_player()
        player_model = self._mock_player_model(current_temp_hp=0)
        removed = [self._removed_effect(last_granted=0)]

        with patch.object(CombatService, "_get_stats", return_value=(player_model, 20, 20, 15, 3, 3)) as mock_stats:
            db_mock = SimpleNamespace(add=lambda x: None)
            CombatService._cleanup_recurring_temp_hp_effects(db_mock, state, removed)
            mock_stats.assert_not_called()

    def test_skipped_for_non_recurring_effects(self):
        state = self._state_with_player()
        player_model = self._mock_player_model(current_temp_hp=5)
        removed = [
            {
                "id": "other-eff",
                "kind": "spell_effect",
                "metadata": {"condition_immunity": True, "immune_conditions": ["frightened"]},
            }
        ]

        with patch.object(CombatService, "_get_stats", return_value=(player_model, 20, 20, 15, 3, 3)) as mock_stats:
            db_mock = SimpleNamespace(add=lambda x: None)
            CombatService._cleanup_recurring_temp_hp_effects(db_mock, state, removed)
            mock_stats.assert_not_called()

        self.assertEqual(player_model.state_json["tempHP"], 5)


# ---------------------------------------------------------------------------
# _clear_concentration_for_source triggers cleanup when db is passed
# ---------------------------------------------------------------------------

class ConcentrationEndCleanupIntegrationTests(unittest.TestCase):
    def _participant_with_heroism_effects(self, caster_id: str = "p1", target_id: str = "t1") -> tuple[dict, dict]:
        caster = _make_player(caster_id, "u1")
        target = _make_player(target_id, "u2")
        conc_group = "grp-heroism-test"
        shared_meta = {
            "concentration": True,
            "concentration_group": conc_group,
            "source_spell_key": "heroism",
        }
        caster["active_effects"] = [
            {
                "id": "immunity-eff",
                "kind": "spell_effect",
                "source_participant_id": caster_id,
                "metadata": {
                    **shared_meta,
                    "condition_immunity": True,
                    "immune_conditions": ["frightened"],
                    "effect_target_participant_id": target_id,
                    "effect_target_ref_id": target_id,
                },
            }
        ]
        target["active_effects"] = [
            {
                "id": "recurring-eff",
                "kind": "spell_effect",
                "source_participant_id": caster_id,
                "metadata": {
                    **shared_meta,
                    "recurring_temp_hp": True,
                    "temp_hp_per_turn": 3,
                    "last_granted_temp_hp": 3,
                    "remove_granted_temp_hp_on_end": True,
                    "effect_target_participant_id": target_id,
                    "effect_target_ref_id": target_id,
                },
            }
        ]
        return caster, target

    def test_cleanup_runs_when_db_passed(self):
        caster, target = self._participant_with_heroism_effects()
        state = _make_state([caster, target])
        player_model = SimpleNamespace()
        player_model.state_json = {"tempHP": 3}

        with (
            patch.object(CombatService, "_get_stats", return_value=(player_model, 20, 20, 15, 3, 3)),
            patch.object(CombatService, "_execute_on_end_effects_for_removed"),
            patch("app.services.session_state_finalize.finalize_session_state_data", side_effect=lambda d: d),
        ):
            db_mock = SimpleNamespace(add=lambda x: None)
            CombatService._clear_concentration_for_source(
                state,
                source_participant_id="p1",
                db=db_mock,
            )

        self.assertEqual(player_model.state_json["tempHP"], 0)

    def test_cleanup_skipped_when_no_db(self):
        caster, target = self._participant_with_heroism_effects()
        state = _make_state([caster, target])
        player_model = SimpleNamespace()
        player_model.state_json = {"tempHP": 3}

        with (
            patch.object(CombatService, "_get_stats", return_value=(player_model, 20, 20, 15, 3, 3)) as mock_stats,
            patch.object(CombatService, "_execute_on_end_effects_for_removed"),
        ):
            CombatService._clear_concentration_for_source(
                state,
                source_participant_id="p1",
            )
            mock_stats.assert_not_called()

        self.assertEqual(player_model.state_json["tempHP"], 3)

    def test_all_effects_removed_from_participants_on_concentration_end(self):
        caster, target = self._participant_with_heroism_effects()
        state = _make_state([caster, target])

        with (
            patch.object(CombatService, "_execute_on_end_effects_for_removed"),
            patch.object(CombatService, "_cleanup_recurring_temp_hp_effects"),
        ):
            CombatService._clear_concentration_for_source(
                state,
                source_participant_id="p1",
                db=SimpleNamespace(add=lambda x: None),
            )

        self.assertEqual(caster.get("active_effects") or [], [])
        self.assertEqual(target.get("active_effects") or [], [])


if __name__ == "__main__":
    unittest.main()
