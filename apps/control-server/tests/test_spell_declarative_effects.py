from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.schemas.base_spell import BaseSpellCreate
from app.schemas.roll import RollActorStats
from app.services.combat import CombatService
from app.services.combat_service.condition_effects_predicates import (
    _declarative_effect_group_key,
    explain_check_modifier_sources,
    get_carrying_capacity_multiplier,
    get_passive_skill_bonus,
    resolve_check_advantage_mode,
)


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

    def _make_player_target_state(self) -> CombatState:
        state = self._make_state()
        state.participants[1] = {
            "id": "target-1",
            "ref_id": "player-2",
            "kind": "player",
            "display_name": "Target Player",
            "active_effects": [],
            "status": "active",
        }
        return state

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

    def test_cats_grace_creates_fall_immunity_with_variant_label(self):
        state = self._make_state()
        attacker = state.participants[0]
        target = state.participants[1]
        spell_context = {
            "spell_name": "Melhorar Habilidade",
            "spell_canonical_key": "enhance_ability",
            "concentration": True,
            "selected_variant_key": "cats_grace",
            "selected_variant_label": "Graça do Gato",
            "effects": [
                {
                    "type": "advantage_on_checks",
                    "target": "selected_target",
                    "duration": {"type": "manual"},
                    "params": {"ability": "dexterity", "against": "any"},
                    "stacking": "replace",
                },
                {
                    "type": "fall_damage_immunity_threshold",
                    "target": "selected_target",
                    "duration": {"type": "manual"},
                    "params": {"max_distance_meters": 6.0},
                },
            ],
            "on_end_effects": [],
        }

        CombatService._apply_declarative_spell_effects(
            state=state,
            attacker=attacker,
            target_participant=target,
            spell_context=spell_context,
        )

        fall_effect = next(
            e for e in target["active_effects"]
            if e["metadata"]["declarative_effect"]["type"] == "fall_damage_immunity_threshold"
        )
        self.assertEqual(fall_effect["metadata"]["selected_variant_label"], "Graça do Gato")
        self.assertEqual(
            fall_effect["metadata"]["declarative_effect"]["params"]["max_distance_meters"], 6.0,
        )

    def test_cats_grace_creates_dexterity_advantage(self):
        state = self._make_state()
        attacker = state.participants[0]
        target = state.participants[1]
        spell_context = {
            "spell_name": "Melhorar Habilidade",
            "spell_canonical_key": "enhance_ability",
            "concentration": True,
            "selected_variant_key": "cats_grace",
            "selected_variant_label": "Graça do Gato",
            "effects": [
                {
                    "type": "advantage_on_checks",
                    "target": "selected_target",
                    "duration": {"type": "manual"},
                    "params": {"ability": "dexterity", "against": "any"},
                    "stacking": "replace",
                },
                {
                    "type": "fall_damage_immunity_threshold",
                    "target": "selected_target",
                    "duration": {"type": "manual"},
                    "params": {"max_distance_meters": 6.0},
                },
            ],
            "on_end_effects": [],
        }

        CombatService._apply_declarative_spell_effects(
            state=state,
            attacker=attacker,
            target_participant=target,
            spell_context=spell_context,
        )

        dex_effect = next(
            e for e in target["active_effects"]
            if e["metadata"]["declarative_effect"]["type"] == "advantage_on_checks"
        )
        self.assertEqual(dex_effect["metadata"]["declarative_effect"]["params"]["ability"], "dexterity")

    def test_other_variant_no_fall_immunity(self):
        state = self._make_state()
        attacker = state.participants[0]
        target = state.participants[1]
        spell_context = {
            "spell_name": "Melhorar Habilidade",
            "spell_canonical_key": "enhance_ability",
            "concentration": True,
            "selected_variant_key": "bulls_strength",
            "selected_variant_label": "Força do Touro",
            "effects": [
                {
                    "type": "advantage_on_checks",
                    "target": "selected_target",
                    "duration": {"type": "manual"},
                    "params": {"ability": "strength", "against": "any"},
                    "stacking": "replace",
                },
                {
                    "type": "carrying_capacity_multiplier",
                    "target": "selected_target",
                    "duration": {"type": "manual"},
                    "params": {"multiplier": 2.0},
                },
            ],
            "on_end_effects": [],
        }

        CombatService._apply_declarative_spell_effects(
            state=state,
            attacker=attacker,
            target_participant=target,
            spell_context=spell_context,
        )

        fall_effects = [
            e for e in target["active_effects"]
            if e["metadata"]["declarative_effect"]["type"] == "fall_damage_immunity_threshold"
        ]
        self.assertEqual(fall_effects, [])

    def test_all_enhance_ability_variants_apply_correct_effects(self):
        variants = [
            {
                "key": "bears_endurance",
                "label": "Resistência do Urso",
                "effects": [
                    {"type": "advantage_on_checks", "target": "selected_target",
                     "duration": {"type": "manual"}, "params": {"ability": "constitution", "against": "any"},
                     "stacking": "replace"},
                    {"type": "grant_temp_hp", "target": "selected_target",
                     "duration": {"type": "manual"}, "params": {"dice": "2d6"}},
                ],
                "expected_types": {"spell_effect", "temp_hp_granted"},
            },
            {
                "key": "bulls_strength",
                "label": "Força do Touro",
                "effects": [
                    {"type": "advantage_on_checks", "target": "selected_target",
                     "duration": {"type": "manual"}, "params": {"ability": "strength", "against": "any"},
                     "stacking": "replace"},
                    {"type": "carrying_capacity_multiplier", "target": "selected_target",
                     "duration": {"type": "manual"}, "params": {"multiplier": 2}},
                ],
                "expected_types": {"spell_effect"},
            },
            {
                "key": "cats_grace",
                "label": "Graça do Gato",
                "effects": [
                    {"type": "advantage_on_checks", "target": "selected_target",
                     "duration": {"type": "manual"}, "params": {"ability": "dexterity", "against": "any"},
                     "stacking": "replace"},
                    {"type": "fall_damage_immunity_threshold", "target": "selected_target",
                     "duration": {"type": "manual"}, "params": {"max_distance_meters": 6}},
                ],
                "expected_types": {"spell_effect"},
            },
            {
                "key": "eagles_splendor",
                "label": "Esplendor da Águia",
                "effects": [
                    {"type": "advantage_on_checks", "target": "selected_target",
                     "duration": {"type": "manual"}, "params": {"ability": "charisma", "against": "any"},
                     "stacking": "replace"},
                ],
                "expected_types": {"spell_effect"},
            },
            {
                "key": "foxs_cunning",
                "label": "Astúcia da Raposa",
                "effects": [
                    {"type": "advantage_on_checks", "target": "selected_target",
                     "duration": {"type": "manual"}, "params": {"ability": "intelligence", "against": "any"},
                     "stacking": "replace"},
                ],
                "expected_types": {"spell_effect"},
            },
            {
                "key": "owls_wisdom",
                "label": "Sabedoria da Coruja",
                "effects": [
                    {"type": "advantage_on_checks", "target": "selected_target",
                     "duration": {"type": "manual"}, "params": {"ability": "wisdom", "against": "any"},
                     "stacking": "replace"},
                    {"type": "passive_skill_bonus", "target": "selected_target",
                     "duration": {"type": "manual"}, "stacking": "replace",
                     "params": {"skill": "perception", "bonus": 5}},
                ],
                "expected_types": {"spell_effect"},
            },
        ]

        for variant in variants:
            with self.subTest(variant=variant["key"]):
                state = self._make_state()
                attacker = state.participants[0]
                target = state.participants[1]
                spell_context = {
                    "spell_name": "Melhorar Habilidade",
                    "spell_canonical_key": "enhance_ability",
                    "concentration": True,
                    "selected_variant_key": variant["key"],
                    "selected_variant_label": variant["label"],
                    "effects": variant["effects"],
                    "on_end_effects": [],
                }

                CombatService._apply_declarative_spell_effects(
                    state=state,
                    attacker=attacker,
                    target_participant=target,
                    spell_context=spell_context,
                )

                actual_types = {e["kind"] for e in target["active_effects"]}
                self.assertEqual(actual_types, variant["expected_types"])
                for effect in target["active_effects"]:
                    self.assertEqual(effect["metadata"]["selected_variant_key"], variant["key"])
                    self.assertEqual(effect["metadata"]["selected_variant_label"], variant["label"])

    def test_builds_applied_declarative_effects_summary_by_target(self):
        state = self._make_state()
        attacker = state.participants[0]
        target = state.participants[1]
        spell_context = {
            "spell_name": "Enhance Ability",
            "spell_canonical_key": "enhance_ability",
            "concentration": True,
            "selected_variant_key": "bulls_strength",
            "selected_variant_label": "Força do Touro",
            "effects": [
                {
                    "type": "advantage_on_checks",
                    "target": "selected_target",
                    "duration": {"type": "manual"},
                    "params": {"ability": "strength"},
                },
                {
                    "type": "carrying_capacity_multiplier",
                    "target": "selected_target",
                    "duration": {"type": "manual"},
                    "params": {"multiplier": 2.0},
                },
            ],
            "on_end_effects": [],
        }

        application = CombatService._apply_declarative_spell_effects(
            state=state,
            attacker=attacker,
            target_participant=target,
            spell_context=spell_context,
        )

        summary = CombatService._build_applied_declarative_effects_by_target(
            application["applied_effects"]
        )

        self.assertEqual(
            summary,
            [
                {
                    "target_display_name": "Target",
                    "target_participant_id": "target-1",
                    "target_ref_id": "entity-1",
                    "variant_key": "bulls_strength",
                    "variant_label": "Força do Touro",
                    "effects": [
                        {
                            "type": "advantage_on_checks",
                            "params": {"ability": "strength"},
                        },
                        {
                            "type": "carrying_capacity_multiplier",
                            "params": {"multiplier": 2.0},
                        },
                    ],
                }
            ],
        )

    def test_builds_grant_temp_hp_summary_for_applied_and_replaced_cases(self):
        state = self._make_player_target_state()
        attacker = state.participants[0]
        target = state.participants[1]
        spell_context = {
            "spell_name": "Enhance Ability",
            "spell_canonical_key": "enhance_ability",
            "concentration": True,
            "selected_variant_key": "bears_endurance",
            "selected_variant_label": "Resistência do Urso",
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
        target_model = MagicMock()
        target_model.state_json = {"tempHP": 3}

        with patch(
            "app.services.combat_service.spell_declarative_effects._roll_dice_expression",
            return_value=7,
        ), patch.object(
            CombatService,
            "_get_stats",
            return_value=(target_model, None, None, None, None, None),
        ):
            application = CombatService._apply_declarative_spell_effects(
                state=state,
                attacker=attacker,
                target_participant=target,
                spell_context=spell_context,
            )
            CombatService._apply_temp_hp_from_granted_effects(
                MagicMock(),
                state,
                application["applied_effects"],
            )

        summary = CombatService._build_applied_declarative_effects_by_target(
            application["applied_effects"]
        )
        self.assertEqual(
            summary[0]["effects"][0]["observability"],
            {
                "rolled_temp_hp": 7,
                "applied_temp_hp": True,
                "previous_temp_hp": 3,
                "final_temp_hp": 7,
                "does_not_expire_temp_hp": True,
            },
        )

    def test_builds_grant_temp_hp_summary_when_existing_value_is_kept(self):
        state = self._make_player_target_state()
        attacker = state.participants[0]
        target = state.participants[1]
        spell_context = {
            "spell_name": "Enhance Ability",
            "spell_canonical_key": "enhance_ability",
            "concentration": True,
            "selected_variant_key": "bears_endurance",
            "selected_variant_label": "Resistência do Urso",
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
        target_model = MagicMock()
        target_model.state_json = {"tempHP": 8}

        with patch(
            "app.services.combat_service.spell_declarative_effects._roll_dice_expression",
            return_value=5,
        ), patch.object(
            CombatService,
            "_get_stats",
            return_value=(target_model, None, None, None, None, None),
        ):
            application = CombatService._apply_declarative_spell_effects(
                state=state,
                attacker=attacker,
                target_participant=target,
                spell_context=spell_context,
            )
            CombatService._apply_temp_hp_from_granted_effects(
                MagicMock(),
                state,
                application["applied_effects"],
            )

        summary = CombatService._build_applied_declarative_effects_by_target(
            application["applied_effects"]
        )
        self.assertEqual(
            summary[0]["effects"][0]["observability"],
            {
                "rolled_temp_hp": 5,
                "applied_temp_hp": True,
                "previous_temp_hp": 8,
                "final_temp_hp": 8,
                "does_not_expire_temp_hp": True,
            },
        )

    def test_clearing_concentration_removes_tracking_effect_but_keeps_temp_hp(self):
        state = self._make_player_target_state()
        attacker = state.participants[0]
        target = state.participants[1]
        spell_context = {
            "spell_name": "Enhance Ability",
            "spell_canonical_key": "enhance_ability",
            "concentration": True,
            "selected_variant_key": "bears_endurance",
            "selected_variant_label": "Resistência do Urso",
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
        target_model = MagicMock()
        target_model.state_json = {"tempHP": 0}

        with patch(
            "app.services.combat_service.spell_declarative_effects._roll_dice_expression",
            return_value=9,
        ), patch.object(
            CombatService,
            "_get_stats",
            return_value=(target_model, None, None, None, None, None),
        ):
            application = CombatService._apply_declarative_spell_effects(
                state=state,
                attacker=attacker,
                target_participant=target,
                spell_context=spell_context,
            )
            CombatService._apply_temp_hp_from_granted_effects(
                MagicMock(),
                state,
                application["applied_effects"],
            )

        self.assertEqual(target_model.state_json["tempHP"], 9)
        result = CombatService._clear_concentration_for_source(
            state,
            source_participant_id=attacker["id"],
        )
        self.assertEqual(len(result["removed_effects"]), 1)
        self.assertEqual(result["removed_effects"][0]["kind"], "temp_hp_granted")
        self.assertEqual(target["active_effects"], [])
        self.assertEqual(target_model.state_json["tempHP"], 9)

    def test_declarative_cast_log_includes_temp_hp_summary(self):
        state = self._make_player_target_state()
        attacker = state.participants[0]
        target = state.participants[1]
        target_model = MagicMock()
        target_model.state_json = {"tempHP": 8}
        spell_context = {
            "spell_name": "Enhance Ability",
            "spell_canonical_key": "enhance_ability",
            "spell_mode": "utility",
            "concentration": True,
            "selected_variant_key": "bears_endurance",
            "selected_variant_label": "Resistência do Urso",
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
            return_value=5,
        ), patch.object(
            CombatService,
            "_get_stats",
            return_value=(target_model, None, None, None, None, None),
        ):
            result = asyncio.run(
                CombatService._cast_spell_via_declarative_effects(
                    MagicMock(),
                    "session-1",
                    attacker=attacker,
                    attacker_model=MagicMock(),
                    actor_user_id="user-1",
                    is_gm=False,
                    req=MagicMock(),
                    state=state,
                    spell_context=spell_context,
                    target_participant=target,
                )
            )

        self.assertIn("Target Player: PV temporários: 5 rolados, mantidos 8 existentes.", result["__log_message"])

    def test_commit_cast_result_marks_participants_dirty_for_nested_effect_updates(self):
        state = self._make_player_target_state()
        attacker = state.participants[0]
        target = state.participants[1]
        target["active_effects"] = [
            {
                "id": "effect-1",
                "kind": "spell_effect",
                "duration_type": "manual",
                "created_at": "2026-05-02T00:00:00+00:00",
                "metadata": {
                    "source_spell_name": "Sabedoria da Coruja",
                    "declarative_effect": {
                        "type": "advantage_on_checks",
                        "params": {"ability": "wisdom", "against": "any"},
                    },
                },
            }
        ]
        resolution = {
            "result": MagicMock(damage=0, healing=0, previous_hp=None, new_hp=None),
            "spell_mode": "utility",
            "effect_kind": None,
            "effect_bonus": 0,
            "save_success_outcome": None,
            "slot_spent": False,
            "inventory_refresh_required": False,
            "summary_text": None,
            "custom_log_message": None,
            "automation_player_state_ids": set(),
            "was_overridden": False,
            "action_cost": "action",
            "target_p": target,
            "automation_result": None,
        }

        with patch(
            "app.services.combat_service.spells.cast_target_commit.flag_modified"
        ) as mock_flag_modified, patch.object(
            CombatService,
            "_emit_player_state_update",
            new=AsyncMock(),
        ), patch.object(
            CombatService,
            "_emit_entity_hp_update",
            new=AsyncMock(),
        ), patch.object(
            CombatService,
            "_emit_state",
            new=AsyncMock(),
        ), patch.object(
            CombatService,
            "_emit_and_persist_log",
            new=AsyncMock(),
        ), patch.object(
            CombatService,
            "_build_cast_log_message",
            return_value="log",
        ), patch.object(
            CombatService,
            "_build_cast_response",
            return_value={"ok": True},
        ):
            result = asyncio.run(
                CombatService._commit_cast_result(
                    MagicMock(),
                    "session-1",
                    state,
                    attacker,
                    {
                        "spell_name": "Enhance Ability",
                        "spell_canonical_key": "enhance_ability",
                    },
                    resolution,
                    "user-1",
                    False,
                )
            )

        mock_flag_modified.assert_called_once_with(state, "participants")
        self.assertEqual(result, {"ok": True})


class TestCarryingCapacityMultiplier(unittest.TestCase):
    def _make_participant(self, effects=None):
        return {
            "id": "p-1",
            "ref_id": "ref-1",
            "kind": "player",
            "display_name": "Test",
            "active_effects": effects or [],
        }

    def _carry_effect(self, multiplier, group_id=None, source_name=None):
        metadata = {
            "source_spell_name": source_name or "Enhance Ability",
            "declarative_effect": {
                "type": "carrying_capacity_multiplier",
                "params": {"multiplier": multiplier},
            },
        }
        if group_id:
            metadata["declarative_effect_group_id"] = group_id
        return {
            "id": f"eff-{multiplier}-{group_id or source_name or 'default'}",
            "kind": "spell_effect",
            "metadata": metadata,
        }

    def test_no_effects_returns_one(self):
        participant = self._make_participant([])
        self.assertEqual(get_carrying_capacity_multiplier(participant), 1.0)

    def test_single_x2_multiplier(self):
        participant = self._make_participant([self._carry_effect(2.0)])
        self.assertEqual(get_carrying_capacity_multiplier(participant), 2.0)

    def test_two_same_group_x2_does_not_double(self):
        effects = [
            self._carry_effect(2.0, group_id="g1"),
            self._carry_effect(2.0, group_id="g1"),
        ]
        participant = self._make_participant(effects)
        self.assertEqual(get_carrying_capacity_multiplier(participant), 2.0)

    def test_different_groups_x2_and_x3_uses_max(self):
        effects = [
            self._carry_effect(2.0, group_id="g1"),
            self._carry_effect(3.0, group_id="g2"),
        ]
        participant = self._make_participant(effects)
        self.assertEqual(get_carrying_capacity_multiplier(participant), 3.0)

    def test_same_group_x2_and_x3_uses_max(self):
        effects = [
            self._carry_effect(2.0, group_id="g1"),
            self._carry_effect(3.0, group_id="g1"),
        ]
        participant = self._make_participant(effects)
        self.assertEqual(get_carrying_capacity_multiplier(participant), 3.0)

    def test_ignores_non_spell_effects(self):
        effects = [
            {
                "id": "condition-eff",
                "kind": "condition",
                "condition_type": "prone",
            }
        ]
        participant = self._make_participant(effects)
        self.assertEqual(get_carrying_capacity_multiplier(participant), 1.0)

    def test_ignores_null_metadata(self):
        effects = [{"id": "no-meta", "kind": "spell_effect", "metadata": None}]
        participant = self._make_participant(effects)
        self.assertEqual(get_carrying_capacity_multiplier(participant), 1.0)


class TestDeclarativeEffectGroupKey(unittest.TestCase):
    def _effect(self, effect_id="eff-1"):
        return {"id": effect_id}

    def test_prefers_declarative_effect_group_id(self):
        metadata = {"declarative_effect_group_id": "group-abc"}
        key = _declarative_effect_group_key(metadata, self._effect(), "passive_skill_bonus", "perception|5")
        self.assertEqual(key, "group-abc")

    def test_composite_key_from_source_spell_key(self):
        metadata = {"source_spell_key": "owls_wisdom", "selected_variant_key": "owls_wisdom"}
        key = _declarative_effect_group_key(metadata, self._effect(), "passive_skill_bonus", "perception|5")
        self.assertEqual(key, "owls_wisdom|owls_wisdom|passive_skill_bonus|perception|5")

    def test_composite_key_from_source_spell_name_fallback(self):
        metadata = {"source_spell_name": "Owl's Wisdom"}
        key = _declarative_effect_group_key(metadata, self._effect(), "passive_skill_bonus", "perception|5")
        self.assertEqual(key, "Owl's Wisdom||passive_skill_bonus|perception|5")

    def test_composite_key_includes_effect_type_and_params_key(self):
        metadata = {"source_spell_key": "enhance_ability", "selected_variant_key": "bulls_strength"}
        key = _declarative_effect_group_key(metadata, self._effect(), "carrying_capacity_multiplier", "2")
        self.assertEqual(key, "enhance_ability|bulls_strength|carrying_capacity_multiplier|2")

    def test_falls_back_to_effect_id(self):
        metadata = {}
        key = _declarative_effect_group_key(metadata, self._effect("my-id"), "advantage_on_checks", "wisdom")
        self.assertEqual(key, "my-id")

    def test_falls_back_to_unknown_with_python_id(self):
        metadata = {}
        effect = {}
        key = _declarative_effect_group_key(metadata, effect, "advantage_on_checks", "wisdom")
        self.assertTrue(key.startswith("__unknown_"))

    def test_empty_group_id_treated_as_absent(self):
        metadata = {"declarative_effect_group_id": ""}
        key = _declarative_effect_group_key(metadata, self._effect(), "passive_skill_bonus", "perception|5")
        self.assertNotEqual(key, "")

    def test_different_params_keys_produce_different_groups(self):
        metadata = {"source_spell_key": "owls_wisdom"}
        key1 = _declarative_effect_group_key(metadata, self._effect(), "passive_skill_bonus", "perception|5")
        key2 = _declarative_effect_group_key(metadata, self._effect(), "passive_skill_bonus", "perception|3")
        self.assertNotEqual(key1, key2)


class TestAdvantageOnChecksDedup(unittest.TestCase):
    def _make_participant(self, effects):
        return {"id": "p-1", "active_effects": effects, "status": "active"}

    def _advantage_effect(self, ability="wisdom", group_id=None, source_spell_key=None, effect_id="eff-1"):
        metadata = {
            "declarative_effect": {
                "type": "advantage_on_checks",
                "params": {"ability": ability, "against": "any"},
            },
            "source_spell_name": "Test Spell",
        }
        if group_id:
            metadata["declarative_effect_group_id"] = group_id
        if source_spell_key:
            metadata["source_spell_key"] = source_spell_key
        return {
            "id": effect_id,
            "kind": "spell_effect",
            "metadata": metadata,
        }

    def test_two_identical_advantages_same_group_resolve_to_advantage(self):
        effects = [
            self._advantage_effect(group_id="group-1", effect_id="eff-1"),
            self._advantage_effect(group_id="group-1", effect_id="eff-2"),
        ]
        participant = self._make_participant(effects)
        mode = resolve_check_advantage_mode(participant, "wisdom")
        self.assertEqual(mode, "advantage")

    def test_two_identical_advantages_same_source_key_resolve_to_advantage(self):
        effects = [
            self._advantage_effect(source_spell_key="owls_wisdom", effect_id="eff-1"),
            self._advantage_effect(source_spell_key="owls_wisdom", effect_id="eff-2"),
        ]
        participant = self._make_participant(effects)
        mode = resolve_check_advantage_mode(participant, "wisdom")
        self.assertEqual(mode, "advantage")

    def test_different_groups_both_contribute(self):
        effects = [
            self._advantage_effect(group_id="group-a", effect_id="eff-1"),
            self._advantage_effect(group_id="group-b", effect_id="eff-2"),
        ]
        participant = self._make_participant(effects)
        mode = resolve_check_advantage_mode(participant, "wisdom")
        self.assertEqual(mode, "advantage")

    def test_advantage_plus_disadvantage_same_group_cancels(self):
        adv = self._advantage_effect(group_id="group-1", effect_id="eff-1")
        dis = self._advantage_effect(group_id="group-1", effect_id="eff-2")
        dis["metadata"]["declarative_effect"]["type"] = "disadvantage_on_checks"
        participant = self._make_participant([adv, dis])
        mode = resolve_check_advantage_mode(participant, "wisdom")
        self.assertEqual(mode, "normal")

    def test_effects_without_metadata_are_skipped(self):
        effects = [
            {"id": "no-meta", "kind": "spell_effect", "metadata": None},
            self._advantage_effect(effect_id="eff-2"),
        ]
        participant = self._make_participant(effects)
        mode = resolve_check_advantage_mode(participant, "wisdom")
        self.assertEqual(mode, "advantage")


class TestExplainCheckModifierSourcesDedup(unittest.TestCase):
    def _make_participant(self, effects):
        return {"id": "p-1", "active_effects": effects, "status": "active"}

    def _advantage_effect(self, ability="wisdom", group_id=None, source_spell_key=None, effect_id="eff-1"):
        metadata = {
            "declarative_effect": {
                "type": "advantage_on_checks",
                "params": {"ability": ability, "against": "any"},
            },
            "source_spell_name": "Test Spell",
        }
        if group_id:
            metadata["declarative_effect_group_id"] = group_id
        if source_spell_key:
            metadata["source_spell_key"] = source_spell_key
        return {
            "id": effect_id,
            "kind": "spell_effect",
            "metadata": metadata,
        }

    def test_two_identical_effects_same_group_returns_one_entry(self):
        effects = [
            self._advantage_effect(group_id="group-1", effect_id="eff-1"),
            self._advantage_effect(group_id="group-1", effect_id="eff-2"),
        ]
        participant = self._make_participant(effects)
        explanations = explain_check_modifier_sources(participant, ability="wisdom", roll_type="ability")
        self.assertEqual(len(explanations), 1)
        self.assertTrue(explanations[0]["applied"])

    def test_two_identical_effects_same_source_key_returns_one_entry(self):
        effects = [
            self._advantage_effect(source_spell_key="owls_wisdom", effect_id="eff-1"),
            self._advantage_effect(source_spell_key="owls_wisdom", effect_id="eff-2"),
        ]
        participant = self._make_participant(effects)
        explanations = explain_check_modifier_sources(participant, ability="wisdom", roll_type="ability")
        self.assertEqual(len(explanations), 1)

    def test_different_groups_returns_both(self):
        effects = [
            self._advantage_effect(group_id="group-a", effect_id="eff-1"),
            self._advantage_effect(group_id="group-b", effect_id="eff-2"),
        ]
        participant = self._make_participant(effects)
        explanations = explain_check_modifier_sources(participant, ability="wisdom", roll_type="ability")
        self.assertEqual(len(explanations), 2)

    def test_no_metadata_effects_are_skipped(self):
        effects = [
            {"id": "no-meta", "kind": "spell_effect", "metadata": None},
            self._advantage_effect(effect_id="eff-2"),
        ]
        participant = self._make_participant(effects)
        explanations = explain_check_modifier_sources(participant, ability="wisdom", roll_type="ability")
        self.assertEqual(len(explanations), 1)


class TestPassiveSkillBonusDedup(unittest.TestCase):
    def _make_participant(self, effects):
        return {"id": "p-1", "active_effects": effects, "status": "active"}

    def _bonus_effect(self, skill="perception", bonus=5, group_id=None, source_spell_key=None, effect_id="eff-1"):
        metadata = {
            "declarative_effect": {
                "type": "passive_skill_bonus",
                "params": {"skill": skill, "bonus": bonus},
            },
            "source_spell_name": "Test Spell",
        }
        if group_id:
            metadata["declarative_effect_group_id"] = group_id
        if source_spell_key:
            metadata["source_spell_key"] = source_spell_key
        return {
            "id": effect_id,
            "kind": "spell_effect",
            "metadata": metadata,
        }

    def test_two_same_group_bonuses_uses_max(self):
        effects = [
            self._bonus_effect(bonus=5, group_id="group-1", effect_id="eff-1"),
            self._bonus_effect(bonus=3, group_id="group-1", effect_id="eff-2"),
        ]
        participant = self._make_participant(effects)
        self.assertEqual(get_passive_skill_bonus(participant, "perception"), 5)

    def test_two_same_source_key_bonuses_uses_max(self):
        effects = [
            self._bonus_effect(bonus=5, source_spell_key="owls_wisdom", effect_id="eff-1"),
            self._bonus_effect(bonus=5, source_spell_key="owls_wisdom", effect_id="eff-2"),
        ]
        participant = self._make_participant(effects)
        self.assertEqual(get_passive_skill_bonus(participant, "perception"), 5)

    def test_different_groups_sum(self):
        effects = [
            self._bonus_effect(bonus=5, group_id="group-a", effect_id="eff-1"),
            self._bonus_effect(bonus=3, group_id="group-b", effect_id="eff-2"),
        ]
        participant = self._make_participant(effects)
        self.assertEqual(get_passive_skill_bonus(participant, "perception"), 8)


class TestSaveDeclarativeEffectSchema(unittest.TestCase):
    def test_advantage_on_saves_accepts_valid_params(self):
        spell = BaseSpellCreate(
            canonicalKey="enlarge_reduce",
            nameEn="Enlarge/Reduce",
            descriptionEn="Test spell.",
            level=2,
            school="transmutation",
            resolutionType="buff",
            effects=[
                {
                    "type": "advantage_on_saves",
                    "target": "selected_target",
                    "duration": {"type": "rounds", "rounds": 10, "anchor": "target"},
                    "params": {"abilities": ["strength"]},
                    "stacking": "replace",
                }
            ],
        )
        self.assertEqual(spell.effects[0].type, "advantage_on_saves")
        self.assertEqual(spell.effects[0].params.abilities, ["strength"])

    def test_disadvantage_on_saves_accepts_valid_params(self):
        spell = BaseSpellCreate(
            canonicalKey="enlarge_reduce",
            nameEn="Enlarge/Reduce",
            descriptionEn="Test spell.",
            level=2,
            school="transmutation",
            resolutionType="buff",
            effects=[
                {
                    "type": "disadvantage_on_saves",
                    "target": "selected_target",
                    "duration": {"type": "rounds", "rounds": 10, "anchor": "target"},
                    "params": {"abilities": ["strength"]},
                    "stacking": "replace",
                }
            ],
        )
        self.assertEqual(spell.effects[0].type, "disadvantage_on_saves")
        self.assertEqual(spell.effects[0].params.abilities, ["strength"])

    def test_save_modifier_rejects_missing_abilities(self):
        with self.assertRaises(ValueError):
            BaseSpellCreate(
                canonicalKey="enlarge_reduce",
                nameEn="Enlarge/Reduce",
                descriptionEn="Test spell.",
                level=2,
                school="transmutation",
                resolutionType="buff",
                effects=[
                    {
                        "type": "advantage_on_saves",
                        "target": "selected_target",
                        "params": {},
                    }
                ],
            )

    def test_save_modifier_rejects_invalid_ability(self):
        with self.assertRaises(ValueError):
            BaseSpellCreate(
                canonicalKey="enlarge_reduce",
                nameEn="Enlarge/Reduce",
                descriptionEn="Test spell.",
                level=2,
                school="transmutation",
                resolutionType="buff",
                effects=[
                    {
                        "type": "advantage_on_saves",
                        "target": "selected_target",
                        "params": {"abilities": ["luck"]},
                    }
                ],
            )
