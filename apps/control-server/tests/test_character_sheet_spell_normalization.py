"""Character sheet spell reference normalization tests.

Covers:
  - normalize_character_sheet_spell_references upgrades legacy canonicalKey entries
  - Modern entries (campaignSpellId already set) are left untouched
  - Unresolvable legacy entries are kept as-is
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch


def _make_session(campaign_spell=None):
    """Return a mock DB session that returns campaign_spell on first query."""
    db = MagicMock()
    db.exec.return_value.first.return_value = campaign_spell
    return db


def _make_campaign_spell(id_: str, canonical_key: str) -> MagicMock:
    cs = MagicMock()
    cs.id = id_
    cs.canonical_key = canonical_key
    return cs


class TestNormalizeCharacterSheetSpellReferences(unittest.TestCase):
    """normalize_character_sheet_spell_references() upgrades legacy entries."""

    def _call(self, data: dict, campaign_spell=None, campaign_id: str = "camp-1") -> dict:
        from app.api.routes.character_sheets_common import (
            normalize_character_sheet_spell_references,
        )

        db = _make_session(campaign_spell)
        return normalize_character_sheet_spell_references(
            data,
            campaign_id=campaign_id,
            session=db,
        )

    def test_normalize_upgrades_legacy_canonical_key_to_campaign_spell_id(self):
        """A spell entry with only canonicalKey gets upgraded when a CampaignSpell exists."""
        cs = _make_campaign_spell("cs-abc", "fireball")
        data = {
            "spellcasting": {
                "spells": [
                    {"id": "e1", "name": "Fireball", "canonicalKey": "fireball", "level": 3},
                ],
            },
        }
        result = self._call(data, campaign_spell=cs)
        spells = result["spellcasting"]["spells"]
        self.assertEqual(len(spells), 1)
        self.assertEqual(spells[0]["campaignSpellId"], "cs-abc")
        # Original fields are preserved
        self.assertEqual(spells[0]["canonicalKey"], "fireball")
        self.assertEqual(spells[0]["name"], "Fireball")

    def test_normalize_leaves_modern_entry_untouched(self):
        """An entry that already has campaignSpellId is not re-processed."""
        data = {
            "spellcasting": {
                "spells": [
                    {
                        "id": "e1",
                        "name": "Fireball",
                        "canonicalKey": "fireball",
                        "campaignSpellId": "cs-existing",
                        "level": 3,
                    },
                ],
            },
        }
        result = self._call(data, campaign_spell=None)
        spells = result["spellcasting"]["spells"]
        self.assertEqual(spells[0]["campaignSpellId"], "cs-existing")
        # DB must not have been queried for an already-modern entry
        # (the function returns early, no mutation)
        self.assertEqual(result, data)

    def test_normalize_keeps_unresolvable_legacy_entry_untouched(self):
        """If no CampaignSpell is found for a canonicalKey, entry stays as-is."""
        data = {
            "spellcasting": {
                "spells": [
                    {"id": "e1", "name": "Unknown Spell", "canonicalKey": "unknown_spell", "level": 1},
                ],
            },
        }
        # DB returns None — no matching campaign spell
        result = self._call(data, campaign_spell=None)
        spells = result["spellcasting"]["spells"]
        self.assertIsNone(spells[0].get("campaignSpellId"))
        self.assertEqual(spells[0]["canonicalKey"], "unknown_spell")

    def test_normalize_returns_unchanged_data_when_no_spellcasting(self):
        """Data without spellcasting block is returned unchanged."""
        data = {"name": "Fighter", "class": "fighter"}
        result = self._call(data)
        self.assertEqual(result, data)

    def test_normalize_mixed_modern_and_legacy_entries(self):
        """Modern entries are kept, legacy entries are upgraded if resolvable."""
        cs = _make_campaign_spell("cs-fireball", "fireball")
        data = {
            "spellcasting": {
                "spells": [
                    # Modern entry — unchanged
                    {"id": "e1", "name": "Fireball", "canonicalKey": "fireball", "campaignSpellId": "cs-fireball", "level": 3},
                    # Legacy entry — should be upgraded
                    {"id": "e2", "name": "Fireball", "canonicalKey": "fireball", "level": 3},
                ],
            },
        }

        from app.api.routes.character_sheets_common import (
            normalize_character_sheet_spell_references,
        )

        db = MagicMock()
        # First call: modern entry skips DB. Second call: legacy entry resolves.
        db.exec.return_value.first.side_effect = [cs]
        result = normalize_character_sheet_spell_references(
            data, campaign_id="camp-1", session=db
        )
        spells = result["spellcasting"]["spells"]
        # Modern entry unchanged
        self.assertEqual(spells[0]["campaignSpellId"], "cs-fireball")
        # Legacy entry upgraded
        self.assertEqual(spells[1]["campaignSpellId"], "cs-fireball")


class TestResolverAndNormalizationIntegration(unittest.TestCase):
    """Regression: after normalization, the resolver hits the modern path."""

    def test_resolver_uses_modern_path_after_normalization(self):
        """Self-healed entries must be found via campaignSpellId in the resolver."""
        from app.services.combat import CombatService

        # Simulate a sheet that was just self-healed
        data = {
            "spellcasting": {
                "spells": [
                    {
                        "id": "e1",
                        "name": "Fireball",
                        "canonicalKey": "fireball",
                        "campaignSpellId": "cs-healed",
                        "level": 3,
                        "prepared": True,
                    },
                ],
            },
        }
        result = CombatService._resolve_player_spell_entry(
            data,
            spell_canonical_key="fireball",
            campaign_spell_id="cs-healed",
        )
        self.assertEqual(result.get("campaignSpellId"), "cs-healed")
