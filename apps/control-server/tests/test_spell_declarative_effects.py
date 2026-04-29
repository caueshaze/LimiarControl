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
