from __future__ import annotations

import unittest

from app.services.combat_service.condition_effects_predicates import (
    _get_save_declarative_context,
    resolve_saving_throw_advantage_from_effects,
)
from app.services.combat_service.condition_effects_saves import modify_saving_throw


def _source(creature_type: str | None) -> dict | None:
    if creature_type is None:
        return None
    return {"id": "src-1", "creature_type": creature_type}


def _protection_effect() -> dict:
    protected = ["aberration", "celestial", "elemental", "fey", "fiend", "undead"]
    return {
        "id": "eff-protection",
        "kind": "spell_effect",
        "metadata": {
            "source_spell_key": "protection_from_evil_and_good",
            "declarative_save_effect": {
                "type": "saving_throw_advantage_against_creature_types",
                "params": {
                    "mode": "advantage",
                    "source": "protection_from_evil_and_good",
                    "source_creature_types": protected,
                    "roll_types": ["saving_throw"],
                    "consume_on_apply": False,
                },
            },
        },
    }


def _participant(effects: list[dict]) -> dict:
    return {"id": "tgt-1", "kind": "session_entity", "ref_id": "tgt", "active_effects": effects}


class SourceAwareSaveHelperTests(unittest.TestCase):
    def test_no_effects_no_advantage(self):
        ctx = resolve_saving_throw_advantage_from_effects(_participant([]), source_participant=_source("fiend"))
        self.assertEqual(ctx["advantage_sources"], [])

    def test_protection_against_fiend_grants_advantage(self):
        ctx = resolve_saving_throw_advantage_from_effects(
            _participant([_protection_effect()]),
            source_participant=_source("fiend"),
        )
        self.assertEqual(ctx["advantage_sources"], ["protection_from_evil_and_good"])

    def test_protection_against_undead_grants_advantage(self):
        ctx = resolve_saving_throw_advantage_from_effects(
            _participant([_protection_effect()]),
            source_participant=_source("undead"),
        )
        self.assertEqual(ctx["advantage_sources"], ["protection_from_evil_and_good"])

    def test_humanoid_source_does_not_grant_advantage(self):
        ctx = resolve_saving_throw_advantage_from_effects(
            _participant([_protection_effect()]),
            source_participant=_source("humanoid"),
        )
        self.assertEqual(ctx["advantage_sources"], [])

    def test_none_source_does_not_grant_advantage(self):
        ctx = resolve_saving_throw_advantage_from_effects(
            _participant([_protection_effect()]),
            source_participant=None,
        )
        self.assertEqual(ctx["advantage_sources"], [])

    def test_malformed_metadata_does_not_crash(self):
        participant = _participant([
            {"id": "bad-1", "kind": "spell_effect", "metadata": {"declarative_save_effect": "bad"}},
            {"id": "bad-2", "kind": "spell_effect", "metadata": {"declarative_save_effect": {"type": "x"}}},
        ])
        ctx = resolve_saving_throw_advantage_from_effects(participant, source_participant=_source("fiend"))
        self.assertEqual(ctx["advantage_sources"], [])

    def test_duplicate_effects_are_deduped(self):
        p = _participant([_protection_effect(), _protection_effect()])
        ctx = resolve_saving_throw_advantage_from_effects(p, source_participant=_source("fiend"))
        self.assertEqual(ctx["advantage_sources"], ["protection_from_evil_and_good"])

    def test_consume_on_apply_false_does_not_consume(self):
        p = _participant([_protection_effect()])
        ctx = resolve_saving_throw_advantage_from_effects(p, source_participant=_source("fiend"))
        self.assertEqual(ctx["consume_effect_ids"], [])


class SourceAwareSaveContextTests(unittest.TestCase):
    def test_get_save_context_includes_source_aware_advantage(self):
        mode, adv, dis, _ = _get_save_declarative_context(
            _participant([_protection_effect()]),
            "wisdom",
            source_participant=_source("fiend"),
        )
        self.assertEqual(mode, "advantage")
        self.assertIn("protection_from_evil_and_good", adv)
        self.assertEqual(dis, [])

    def test_source_none_keeps_normal_behavior(self):
        mode, adv, dis, _ = _get_save_declarative_context(
            _participant([_protection_effect()]),
            "wisdom",
            source_participant=None,
        )
        self.assertEqual(mode, "normal")
        self.assertEqual(adv, [])
        self.assertEqual(dis, [])

    def test_modify_saving_throw_wires_source_aware_advantage(self):
        ctx = modify_saving_throw(
            _participant([_protection_effect()]),
            "wisdom",
            source_participant=_source("fiend"),
        )
        self.assertEqual(ctx.result, "advantage")
        self.assertIn("protection_from_evil_and_good", ctx.advantage_sources)


if __name__ == "__main__":
    unittest.main()
