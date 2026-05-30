from __future__ import annotations

import unittest

from app.models.combat import CombatPhase, CombatState
from app.schemas.base_spell_effects import SpellDeclarativeEffect
from app.schemas.combat import CombatApplyEffectRequest
from app.services.combat import CombatService
from app.services.combat_service.condition_effects_predicates import (
    has_condition_immunity_from_source,
)


def _protection_effect() -> dict:
    protected = ["aberration", "celestial", "elemental", "fey", "fiend", "undead"]
    return {
        "id": "eff-protection",
        "kind": "spell_effect",
        "metadata": {
            "source_spell_key": "protection_from_evil_and_good",
            "condition_immunity": True,
            "immune_conditions": ["charmed", "frightened", "possessed"],
            "immune_conditions_from_creature_types": protected,
        },
    }


class PossessedConditionSchemaTests(unittest.TestCase):
    def test_combat_apply_effect_request_accepts_possessed(self):
        req = CombatApplyEffectRequest(
            target_participant_id="p1",
            kind="condition",
            condition_type="possessed",
            duration_type="manual",
        )
        self.assertEqual(req.condition_type, "possessed")

    def test_spell_declarative_effect_accepts_possessed(self):
        effect = SpellDeclarativeEffect.model_validate(
            {
                "type": "apply_condition",
                "target": "selected_target",
                "duration": {"type": "manual"},
                "params": {"condition": "possessed"},
            }
        )
        self.assertEqual(effect.params.condition, "possessed")


class PossessedSourceAwareImmunityTests(unittest.TestCase):
    def _protected_target(self) -> dict:
        return {
            "id": "target-1",
            "kind": "player",
            "ref_id": "user-2",
            "display_name": "Target",
            "active_effects": [_protection_effect()],
        }

    def test_source_protected_type_blocks_possessed(self):
        target = self._protected_target()
        source = {"id": "src-1", "creature_type": "fiend"}
        self.assertTrue(has_condition_immunity_from_source(target, "possessed", source))

    def test_source_humanoid_does_not_block_possessed(self):
        target = self._protected_target()
        source = {"id": "src-1", "creature_type": "humanoid"}
        self.assertFalse(has_condition_immunity_from_source(target, "possessed", source))

    def test_missing_source_does_not_block_possessed(self):
        target = self._protected_target()
        self.assertFalse(has_condition_immunity_from_source(target, "possessed", None))


class PossessedDeclarativeBlockTests(unittest.TestCase):
    def _state(self, attacker_creature_type: str | None) -> tuple[CombatState, dict, dict]:
        attacker = {
            "id": "caster-1",
            "ref_id": "entity-1",
            "kind": "session_entity",
            "display_name": "Caster",
            "active_effects": [],
            "status": "active",
        }
        if attacker_creature_type is not None:
            attacker["creature_type"] = attacker_creature_type
        target = {
            "id": "target-1",
            "ref_id": "entity-2",
            "kind": "session_entity",
            "display_name": "Target",
            "active_effects": [_protection_effect()],
            "status": "active",
        }
        state = CombatState(
            id="state-1",
            session_id="session-1",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[attacker, target],
            active_area_effects=[],
            map_selection={"kind": "demo_map", "mapId": "demo"},
        )
        return state, attacker, target

    def _apply_possessed(self, attacker_creature_type: str | None) -> dict:
        state, attacker, target = self._state(attacker_creature_type)
        spell_context = {
            "spell_name": "Possession Test",
            "spell_canonical_key": "possession_test",
            "effects": [
                {
                    "type": "apply_condition",
                    "target": "selected_target",
                    "duration": {"type": "manual"},
                    "params": {"condition": "possessed"},
                }
            ],
        }
        return CombatService._apply_declarative_spell_effects(
            state=state,
            attacker=attacker,
            target_participant=target,
            spell_context=spell_context,
        )

    def test_apply_condition_possessed_blocked_for_fiend_source(self):
        result = self._apply_possessed("fiend")
        self.assertEqual(result["applied_effects"], [])

    def test_apply_condition_possessed_not_blocked_for_humanoid_source(self):
        result = self._apply_possessed("humanoid")
        self.assertEqual(len(result["applied_effects"]), 1)
        self.assertEqual(result["applied_effects"][0].get("condition_type"), "possessed")

    def test_apply_condition_possessed_not_blocked_without_source_type(self):
        result = self._apply_possessed(None)
        self.assertEqual(len(result["applied_effects"]), 1)
        self.assertEqual(result["applied_effects"][0].get("condition_type"), "possessed")


if __name__ == "__main__":
    unittest.main()
