from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from app.services.combat import CombatService


class SpellAutomationEffectApplyHelperTests(unittest.TestCase):
    def _effect(self, spell_key: str, effect_id: str) -> dict:
        return {
            "id": effect_id,
            "kind": "spell_effect",
            "metadata": {"source_spell_key": spell_key},
        }

    def test_replaces_same_spell_and_preserves_other_spells(self):
        target = {
            "id": "target-1",
            "active_effects": [
                self._effect("jump", "old-jump"),
                self._effect("blur", "old-blur"),
            ],
        }
        new_effect = self._effect("jump", "new-jump")

        CombatService._apply_factory_spell_effect_to_target(
            state=MagicMock(),
            target_participant=target,
            effect=new_effect,
            source_spell_key="jump",
        )

        ids = [e.get("id") for e in target["active_effects"]]
        self.assertNotIn("old-jump", ids)
        self.assertIn("old-blur", ids)
        self.assertIn("new-jump", ids)

    def test_normalizes_spell_key_for_replacement(self):
        target = {
            "id": "target-1",
            "active_effects": [self._effect("Spider Climb", "old-spider")],
        }
        new_effect = self._effect("spider_climb", "new-spider")

        CombatService._apply_factory_spell_effect_to_target(
            state=MagicMock(),
            target_participant=target,
            effect=new_effect,
            source_spell_key="spider_climb",
        )

        ids = [e.get("id") for e in target["active_effects"]]
        self.assertNotIn("old-spider", ids)
        self.assertIn("new-spider", ids)

    def test_handles_missing_active_effects_list(self):
        target = {"id": "target-1"}
        new_effect = self._effect("barkskin", "new-barkskin")

        CombatService._apply_factory_spell_effect_to_target(
            state=MagicMock(),
            target_participant=target,
            effect=new_effect,
            source_spell_key="barkskin",
        )

        self.assertIsInstance(target.get("active_effects"), list)
        self.assertEqual(len(target["active_effects"]), 1)
        self.assertEqual(target["active_effects"][0]["id"], "new-barkskin")

    def test_replace_existing_false_preserves_previous(self):
        target = {
            "id": "target-1",
            "active_effects": [self._effect("jump", "old-jump")],
        }
        new_effect = self._effect("jump", "new-jump")

        CombatService._apply_factory_spell_effect_to_target(
            state=MagicMock(),
            target_participant=target,
            effect=new_effect,
            source_spell_key="jump",
            replace_existing=False,
        )

        ids = [e.get("id") for e in target["active_effects"]]
        self.assertIn("old-jump", ids)
        self.assertIn("new-jump", ids)


if __name__ == "__main__":
    unittest.main()
