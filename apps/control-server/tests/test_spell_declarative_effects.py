from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.schemas.base_spell import BaseSpellCreate
from app.schemas.roll import RollActorStats
from app.services.combat import CombatService


class TestSpellDeclarativeEffectSchemas(unittest.TestCase):
    def test_accepts_effects_and_on_end_effects(self):
        spell = BaseSpellCreate(
            canonicalKey="friends",
            nameEn="Friends",
            descriptionEn="Charm-like social cantrip.",
            level=0,
            school="enchantment",
            resolutionType="utility",
            effects=[
                {
                    "type": "advantage_on_checks",
                    "target": "caster",
                    "duration": {"type": "rounds", "rounds": 10, "anchor": "caster"},
                    "params": {"ability": "charisma"},
                    "stacking": "replace",
                }
            ],
            onEndEffects=[
                {
                    "type": "apply_condition",
                    "target": "selected_target",
                    "duration": {"type": "manual"},
                    "params": {"condition": "hostile_to_caster"},
                }
            ],
        )
        self.assertEqual(spell.effects[0].type, "advantage_on_checks")
        self.assertEqual(spell.onEndEffects[0].params.condition, "hostile_to_caster")

    def test_rejects_on_end_effects_without_effects(self):
        with self.assertRaises(ValueError):
            BaseSpellCreate(
                canonicalKey="friends",
                nameEn="Friends",
                descriptionEn="Charm-like social cantrip.",
                level=0,
                school="enchantment",
                resolutionType="utility",
                onEndEffects=[
                    {
                        "type": "apply_condition",
                        "target": "selected_target",
                        "duration": {"type": "manual"},
                        "params": {"condition": "hostile_to_caster"},
                    }
                ],
            )

    def test_accepts_spell_variants(self):
        spell = BaseSpellCreate(
            canonicalKey="enhance_ability",
            nameEn="Enhance Ability",
            descriptionEn="Choose one ability enhancement.",
            level=2,
            school="transmutation",
            resolutionType="buff",
            variants=[
                {
                    "key": "bears_endurance",
                    "labelPt": "Resistência do Urso",
                    "effects": [
                        {
                            "type": "advantage_on_checks",
                            "target": "selected_target",
                            "params": {"ability": "constitution"},
                            "stacking": "replace",
                        },
                        {
                            "type": "grant_temp_hp",
                            "target": "selected_target",
                            "duration": {"type": "manual"},
                            "params": {"dice": "2d6"},
                        },
                    ],
                }
            ],
        )
        self.assertEqual(spell.variants[0].key, "bears_endurance")
        self.assertEqual(spell.variants[0].effects[1].type, "grant_temp_hp")
        self.assertEqual(spell.variants[0].effects[1].params.dice, "2d6")

    def test_accepts_enhance_ability_all_variants_declarative(self):
        spell = BaseSpellCreate(
            canonicalKey="enhance_ability",
            nameEn="Enhance Ability",
            descriptionEn="Choose one ability enhancement.",
            level=2,
            school="transmutation",
            resolutionType="buff",
            variants=[
                {
                    "key": "owls_wisdom",
                    "labelPt": "Sabedoria da Coruja",
                    "effects": [
                        {
                            "type": "advantage_on_checks",
                            "target": "selected_target",
                            "params": {"ability": "wisdom"},
                            "stacking": "replace",
                        },
                        {
                            "type": "passive_skill_bonus",
                            "target": "selected_target",
                            "duration": {"type": "manual"},
                            "params": {"skill": "perception", "bonus": 5},
                        },
                    ],
                },
                {
                    "key": "bulls_strength",
                    "labelPt": "Força do Touro",
                    "effects": [
                        {
                            "type": "advantage_on_checks",
                            "target": "selected_target",
                            "params": {"ability": "strength"},
                            "stacking": "replace",
                        },
                        {
                            "type": "carrying_capacity_multiplier",
                            "target": "selected_target",
                            "duration": {"type": "manual"},
                            "params": {"multiplier": 2.0},
                        },
                    ],
                },
                {
                    "key": "cats_grace",
                    "labelPt": "Graça do Gato",
                    "effects": [
                        {
                            "type": "advantage_on_checks",
                            "target": "selected_target",
                            "params": {"ability": "dexterity"},
                            "stacking": "replace",
                        },
                        {
                            "type": "fall_damage_immunity_threshold",
                            "target": "selected_target",
                            "duration": {"type": "manual"},
                            "params": {"max_distance_meters": 6.0},
                        },
                    ],
                },
            ],
        )
        owls = spell.variants[0]
        self.assertEqual(owls.effects[1].type, "passive_skill_bonus")
        self.assertEqual(owls.effects[1].params.skill, "perception")
        self.assertEqual(owls.effects[1].params.bonus, 5)

        bulls = spell.variants[1]
        self.assertEqual(bulls.effects[1].type, "carrying_capacity_multiplier")
        self.assertEqual(bulls.effects[1].params.multiplier, 2.0)

        cats = spell.variants[2]
        self.assertEqual(cats.effects[1].type, "fall_damage_immunity_threshold")
        self.assertEqual(cats.effects[1].params.max_distance_meters, 6.0)

    def test_rejects_duplicate_variant_keys(self):
        with self.assertRaises(ValueError):
            BaseSpellCreate(
                canonicalKey="enhance_ability",
                nameEn="Enhance Ability",
                descriptionEn="Choose one ability enhancement.",
                level=2,
                school="transmutation",
                resolutionType="buff",
                variants=[
                    {"key": "fox", "labelPt": "Raposa"},
                    {"key": "fox", "labelPt": "Outra Raposa"},
                ],
            )

    def test_accepts_persistent_area_payload(self):
        spell = BaseSpellCreate(
            canonicalKey="fog_cloud",
            nameEn="Fog Cloud",
            descriptionEn="Create a cloud of fog.",
            level=1,
            school="conjuration",
            resolutionType="utility",
            effectTiming="persistent",
            persistentArea={
                "kind": "obscurement",
                "params": {"obscurement": "heavily_obscured"},
            },
        )
        self.assertEqual(spell.persistentArea.kind, "obscurement")

    def test_rejects_hazard_persistent_area_without_semantics(self):
        with self.assertRaises(ValueError):
            BaseSpellCreate(
                canonicalKey="bad_hazard",
                nameEn="Bad Hazard",
                descriptionEn="Broken area.",
                level=1,
                school="conjuration",
                resolutionType="utility",
                effectTiming="persistent",
                persistentArea={
                    "kind": "hazard",
                    "params": {},
                },
            )

    def test_rejects_movement_damage_without_distance_interval(self):
        with self.assertRaises(ValueError):
            BaseSpellCreate(
                canonicalKey="bad_spike_growth",
                nameEn="Bad Spike Growth",
                descriptionEn="Broken hazard area.",
                level=2,
                school="transmutation",
                resolutionType="damage",
                effectTiming="persistent",
                persistentArea={
                    "kind": "hazard",
                    "params": {
                        "movementDamageDice": "2d4",
                        "damageType": "Piercing",
                    },
                },
            )


class TestSpellDeclarativeEffectRuntime(unittest.TestCase):
    def _make_state(self) -> CombatState:
        return CombatState(
            id="combat-1",
            session_id="session-1",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[
                {
                    "id": "caster-1",
                    "ref_id": "player-1",
                    "kind": "player",
                    "display_name": "Caster",
                    "active_effects": [],
                    "status": "active",
                },
                {
                    "id": "target-1",
                    "ref_id": "entity-1",
                    "kind": "session_entity",
                    "display_name": "Target",
                    "active_effects": [],
                    "status": "active",
                },
            ],
            active_area_effects=[],
            map_selection={"kind": "demo_map", "mapId": "demo"},
        )

    def test_applies_friends_effect_and_on_end_hostility(self):
        state = self._make_state()
        attacker = state.participants[0]
        target = state.participants[1]
        spell_context = {
            "spell_name": "Friends",
            "spell_canonical_key": "friends",
            "concentration": False,
            "effects": [
                {
                    "type": "advantage_on_checks",
                    "target": "caster",
                    "duration": {"type": "rounds", "rounds": 10, "anchor": "caster"},
                    "params": {"ability": "charisma"},
                    "stacking": "replace",
                }
            ],
            "on_end_effects": [
                {
                    "type": "apply_condition",
                    "target": "selected_target",
                    "duration": {"type": "manual"},
                    "params": {"condition": "hostile_to_caster"},
                }
            ],
        }

        CombatService._apply_declarative_spell_effects(
            state=state,
            attacker=attacker,
            target_participant=target,
            spell_context=spell_context,
        )

        self.assertEqual(len(attacker["active_effects"]), 1)
        removed = list(attacker["active_effects"])
        attacker["active_effects"] = []

        CombatService._execute_on_end_effects_for_removed(
            state=state,
            removed_effects=removed,
        )

        self.assertEqual(len(target["active_effects"]), 1)
        self.assertEqual(target["active_effects"][0]["condition_type"], "hostile_to_caster")

    def test_skill_advantage_mode_comes_from_active_effects(self):
        state = self._make_state()
        state.participants[0]["active_effects"] = [
            {
                "id": "effect-1",
                "kind": "spell_effect",
                "source_participant_id": "caster-1",
                "duration_type": "manual",
                "remaining_rounds": None,
                "expires_on": None,
                "expires_at_participant_id": None,
                "created_at": "2026-04-29T00:00:00+00:00",
                "metadata": {
                    "declarative_effect": {
                        "type": "advantage_on_checks",
                        "params": {"ability": "charisma"},
                    }
                },
            }
        ]

        with patch.object(CombatService, "get_state", return_value=state):
            mode = CombatService._resolve_skill_check_advantage_mode_for_actor(
                MagicMock(),
                "session-1",
                actor_kind="player",
                actor_ref_id="player-1",
                skill="persuasion",
            )

        self.assertEqual(mode, "advantage")

    def test_shared_declarative_effect_group_can_be_reused_across_targets(self):
        state = self._make_state()
        attacker = state.participants[0]
        first_target = state.participants[1]
        second_target = {
            "id": "target-2",
            "ref_id": "entity-2",
            "kind": "session_entity",
            "display_name": "Target B",
            "active_effects": [],
            "status": "active",
        }
        state.participants.append(second_target)
        spell_context = {
            "spell_name": "Enhance Ability",
            "spell_canonical_key": "enhance_ability",
            "concentration": True,
            "effects": [
                {
                    "type": "advantage_on_checks",
                    "target": "selected_target",
                    "params": {"ability": "wisdom"},
                    "stacking": "replace",
                }
            ],
            "on_end_effects": [],
        }

        CombatService._apply_declarative_spell_effects(
            state=state,
            attacker=attacker,
            target_participant=first_target,
            spell_context=spell_context,
            effect_group_id="shared-group",
        )
        CombatService._apply_declarative_spell_effects(
            state=state,
            attacker=attacker,
            target_participant=second_target,
            spell_context=spell_context,
            effect_group_id="shared-group",
        )

        first_metadata = first_target["active_effects"][0]["metadata"]
        second_metadata = second_target["active_effects"][0]["metadata"]
        self.assertEqual(first_metadata["declarative_effect_group_id"], "shared-group")
        self.assertEqual(second_metadata["declarative_effect_group_id"], "shared-group")
        self.assertEqual(first_metadata["concentration_group"], "shared-group")
        self.assertEqual(second_metadata["concentration_group"], "shared-group")

    def test_active_effect_metadata_exposes_modal_and_contextual_debug_fields(self):
        state = self._make_state()
        attacker = state.participants[0]
        target = state.participants[1]
        spell_context = {
            "spell_name": "Friends",
            "spell_canonical_key": "friends",
            "selected_variant_key": "eagles_splendor",
            "selected_variant_label": "Esplendor da Aguia",
            "variant_scope": "single_target",
            "context_origin": "initial_cast",
            "concentration": True,
            "effects": [
                {
                    "type": "advantage_on_checks",
                    "target": "caster",
                    "params": {"ability": "charisma", "against": "selected_target"},
                    "stacking": "replace",
                }
            ],
            "on_end_effects": [],
        }

        CombatService._apply_declarative_spell_effects(
            state=state,
            attacker=attacker,
            target_participant=target,
            spell_context=spell_context,
            effect_group_id="group-ctx",
        )

        metadata = attacker["active_effects"][0]["metadata"]
        self.assertEqual(metadata["source_spell_name"], "Friends")
        self.assertEqual(metadata["selected_variant_key"], "eagles_splendor")
        self.assertEqual(metadata["selected_variant_label"], "Esplendor da Aguia")
        self.assertEqual(metadata["target_assignment_source"], "single_target")
        self.assertEqual(metadata["context_origin"], "initial_cast")
        self.assertEqual(metadata["selected_target_participant_id"], "target-1")
        self.assertEqual(metadata["selected_target_ref_id"], "entity-1")
        self.assertEqual(metadata["selected_target_display_name"], "Target")
        self.assertEqual(metadata["effect_target_participant_id"], "caster-1")
        self.assertEqual(metadata["effect_target_ref_id"], "player-1")
        self.assertEqual(metadata["effect_target_display_name"], "Caster")
        self.assertEqual(metadata["against"], "selected_target")
        self.assertEqual(metadata["concentration_group"], "group-ctx")

    def test_grant_temp_hp_creates_observability_effect_with_rolled_value(self):
        state = self._make_state()
        attacker = state.participants[0]
        target = state.participants[1]
        spell_context = {
            "spell_name": "Enhance Ability",
            "spell_canonical_key": "enhance_ability",
            "concentration": True,
            "effects": [
                {
                    "type": "grant_temp_hp",
                    "target": "selected_target",
                    "duration": {"type": "manual"},
                    "params": {"dice": "2d6"},
                }
            ],
            "on_end_effects": [],
        }

        with patch(
            "app.services.combat_service.spell_declarative_effects._roll_dice_expression",
            return_value=9,
        ):
            CombatService._apply_declarative_spell_effects(
                state=state,
                attacker=attacker,
                target_participant=target,
                spell_context=spell_context,
            )

        self.assertEqual(len(target["active_effects"]), 1)
        effect = target["active_effects"][0]
        self.assertEqual(effect["kind"], "temp_hp_granted")
        self.assertEqual(effect["numeric_value"], 9)
        metadata = effect["metadata"]
        self.assertEqual(metadata["rolled_temp_hp"], 9)
        self.assertTrue(metadata["does_not_expire_temp_hp"])
        self.assertFalse(metadata["applied_temp_hp"])

    def test_passive_skill_bonus_creates_spell_effect_and_predicate_sums_correctly(self):
        from app.services.combat_service.condition_effects_predicates import get_passive_skill_bonus

        state = self._make_state()
        attacker = state.participants[0]
        target = state.participants[1]
        spell_context = {
            "spell_name": "Enhance Ability",
            "spell_canonical_key": "enhance_ability",
            "concentration": True,
            "effects": [
                {
                    "type": "passive_skill_bonus",
                    "target": "selected_target",
                    "duration": {"type": "manual"},
                    "params": {"skill": "perception", "bonus": 5},
                }
            ],
            "on_end_effects": [],
        }

        CombatService._apply_declarative_spell_effects(
            state=state,
            attacker=attacker,
            target_participant=target,
            spell_context=spell_context,
        )

        self.assertEqual(len(target["active_effects"]), 1)
        effect = target["active_effects"][0]
        self.assertEqual(effect["kind"], "spell_effect")
        declarative = effect["metadata"]["declarative_effect"]
        self.assertEqual(declarative["type"], "passive_skill_bonus")
        self.assertEqual(declarative["params"]["skill"], "perception")
        self.assertEqual(declarative["params"]["bonus"], 5)

        self.assertEqual(get_passive_skill_bonus(target, "perception"), 5)
        self.assertEqual(get_passive_skill_bonus(target, "stealth"), 0)

    def test_carrying_capacity_multiplier_stores_params_in_metadata(self):
        state = self._make_state()
        attacker = state.participants[0]
        target = state.participants[1]
        spell_context = {
            "spell_name": "Enhance Ability",
            "spell_canonical_key": "enhance_ability",
            "concentration": True,
            "effects": [
                {
                    "type": "carrying_capacity_multiplier",
                    "target": "selected_target",
                    "duration": {"type": "manual"},
                    "params": {"multiplier": 2.0},
                }
            ],
            "on_end_effects": [],
        }

        CombatService._apply_declarative_spell_effects(
            state=state,
            attacker=attacker,
            target_participant=target,
            spell_context=spell_context,
        )

        effect = target["active_effects"][0]
        self.assertEqual(effect["kind"], "spell_effect")
        declarative = effect["metadata"]["declarative_effect"]
        self.assertEqual(declarative["type"], "carrying_capacity_multiplier")
        self.assertEqual(declarative["params"]["multiplier"], 2.0)

    def test_fall_damage_immunity_threshold_stores_params_in_metadata(self):
        state = self._make_state()
        attacker = state.participants[0]
        target = state.participants[1]
        spell_context = {
            "spell_name": "Enhance Ability",
            "spell_canonical_key": "enhance_ability",
            "concentration": True,
            "effects": [
                {
                    "type": "fall_damage_immunity_threshold",
                    "target": "selected_target",
                    "duration": {"type": "manual"},
                    "params": {"max_distance_meters": 6.0},
                }
            ],
            "on_end_effects": [],
        }

        CombatService._apply_declarative_spell_effects(
            state=state,
            attacker=attacker,
            target_participant=target,
            spell_context=spell_context,
        )

        effect = target["active_effects"][0]
        self.assertEqual(effect["kind"], "spell_effect")
        declarative = effect["metadata"]["declarative_effect"]
        self.assertEqual(declarative["type"], "fall_damage_immunity_threshold")
        self.assertEqual(declarative["params"]["max_distance_meters"], 6.0)
