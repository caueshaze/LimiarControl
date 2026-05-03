"""Test: Encumbrance disadvantage applied during ability check resolution (Phase 4).

Validates that heavily_encumbered and overloaded tiers apply disadvantage on
STR/DEX/CON checks, composing correctly with spell-based advantage/disadvantage.

Data sync (encumbrance_tier / strength_score + total_weight_kg to CombatState)
is out of scope for this phase — the helper falls back to "normal" when absent.
"""

import unittest

from app.services.combat_service.condition_effects_predicates import (
    explain_check_modifier_sources,
    resolve_check_advantage_mode,
)


def _participant(
    encumbrance_tier: str | None = None,
    strength_score: float | None = None,
    total_weight_kg: float | None = None,
    effects: list | None = None,
) -> dict:
    p: dict = {"id": "p1", "active_effects": effects or []}
    if encumbrance_tier is not None:
        p["encumbrance_tier"] = encumbrance_tier
    if strength_score is not None:
        p["strength_score"] = strength_score
    if total_weight_kg is not None:
        p["total_weight_kg"] = total_weight_kg
    return p


def _spell_advantage_effect(ability: str) -> dict:
    return {
        "kind": "spell_effect",
        "metadata": {
            "declarative_effect": {
                "type": "advantage_on_checks",
                "params": {"ability": ability},
            },
            "source_spell_key": "guidance",
            "source_spell_name": "Guidance",
            "concentration": False,
        },
    }


class TestEncumbranceDisadvantage(unittest.TestCase):

    # ── resolve_check_advantage_mode ──────────────────────────────────────────

    def test_heavily_encumbered_str_gives_disadvantage(self):
        p = _participant(encumbrance_tier="heavily_encumbered")
        self.assertEqual(resolve_check_advantage_mode(p, "strength"), "disadvantage")

    def test_heavily_encumbered_dex_gives_disadvantage(self):
        p = _participant(encumbrance_tier="heavily_encumbered")
        self.assertEqual(resolve_check_advantage_mode(p, "dexterity"), "disadvantage")

    def test_heavily_encumbered_con_gives_disadvantage(self):
        p = _participant(encumbrance_tier="heavily_encumbered")
        self.assertEqual(resolve_check_advantage_mode(p, "constitution"), "disadvantage")

    def test_heavily_encumbered_int_gives_normal(self):
        """Encumbrance does not affect INT checks."""
        p = _participant(encumbrance_tier="heavily_encumbered")
        self.assertEqual(resolve_check_advantage_mode(p, "intelligence"), "normal")

    def test_overloaded_dex_gives_disadvantage(self):
        p = _participant(encumbrance_tier="overloaded")
        self.assertEqual(resolve_check_advantage_mode(p, "dexterity"), "disadvantage")

    def test_encumbered_str_gives_normal(self):
        """encumbered tier does NOT apply disadvantage (only heavily_encumbered/overloaded)."""
        p = _participant(encumbrance_tier="encumbered")
        self.assertEqual(resolve_check_advantage_mode(p, "strength"), "normal")

    def test_no_encumbrance_fields_fallback_normal(self):
        """Participant without encumbrance data falls back safely to normal."""
        p = _participant()
        self.assertEqual(resolve_check_advantage_mode(p, "strength"), "normal")

    def test_spell_advantage_plus_encumbrance_disadvantage_cancel(self):
        """Spell advantage + encumbrance disadvantage → normal (they cancel out)."""
        effect = _spell_advantage_effect("strength")
        p = _participant(encumbrance_tier="heavily_encumbered", effects=[effect])
        self.assertEqual(resolve_check_advantage_mode(p, "strength"), "normal")

    def test_computed_from_strength_score_and_weight(self):
        """Tier computed from strength_score + total_weight_kg when encumbrance_tier absent.

        STR 10 → normal max = 10×5×0.45359237 ≈ 22.7 kg
                 encumbered max = 10×10×0.45359237 ≈ 45.4 kg
                 heavily max = 10×15×0.45359237 ≈ 68.0 kg
        70 kg > 68 kg → overloaded
        """
        p = _participant(strength_score=10, total_weight_kg=70.0)
        self.assertEqual(resolve_check_advantage_mode(p, "strength"), "disadvantage")

    def test_computed_normal_when_under_threshold(self):
        """No disadvantage when computed weight is within normal range."""
        p = _participant(strength_score=10, total_weight_kg=10.0)
        self.assertEqual(resolve_check_advantage_mode(p, "strength"), "normal")

    def test_manual_advantage_overrides_when_no_other_modifiers(self):
        """Manual advantage still works normally when no encumbrance."""
        p = _participant()
        self.assertEqual(
            resolve_check_advantage_mode(p, "strength", manual_mode="advantage"),
            "advantage",
        )

    # ── explain_check_modifier_sources ────────────────────────────────────────

    def test_explain_includes_carga_when_heavily_encumbered_con(self):
        p = _participant(encumbrance_tier="heavily_encumbered")
        sources = explain_check_modifier_sources(p, ability="constitution")
        carga_entries = [e for e in sources if e.get("source_label") == "Carga"]
        self.assertEqual(len(carga_entries), 1)
        entry = carga_entries[0]
        self.assertTrue(entry["applied"])
        self.assertEqual(entry["modifier_type"], "disadvantage")
        self.assertEqual(entry.get("reason"), "encumbrance")

    def test_explain_excludes_carga_when_normal_tier(self):
        p = _participant(encumbrance_tier="normal")
        sources = explain_check_modifier_sources(p, ability="strength")
        carga_entries = [e for e in sources if e.get("source_label") == "Carga"]
        self.assertEqual(len(carga_entries), 0)

    def test_explain_excludes_carga_for_wrong_ability(self):
        p = _participant(encumbrance_tier="overloaded")
        sources = explain_check_modifier_sources(p, ability="wisdom")
        carga_entries = [e for e in sources if e.get("source_label") == "Carga"]
        self.assertEqual(len(carga_entries), 0)

    def test_explain_no_duplicate_carga(self):
        """Only one Carga entry regardless of how many spell effects exist."""
        effects = [_spell_advantage_effect("strength")] * 2
        p = _participant(encumbrance_tier="heavily_encumbered", effects=effects)
        sources = explain_check_modifier_sources(p, ability="strength")
        carga_entries = [e for e in sources if e.get("source_label") == "Carga"]
        self.assertEqual(len(carga_entries), 1)
