from __future__ import annotations

from pathlib import Path
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
            source_kind="participant",
        )
        self.assertEqual(ctx.result, "advantage")
        self.assertIn("protection_from_evil_and_good", ctx.advantage_sources)


class SourceAwareModifierSemanticsTests(unittest.TestCase):
    # These tests cover the modifier behaviour exercised by npc_action_resolution.py.
    # Integration tests that verify the actual call site are in test_npc_action_resolution.py.

    def _mod(self, creature_type):
        return modify_saving_throw(
            _participant([_protection_effect()]),
            "wisdom",
            source_participant=_source(creature_type),
            source_kind="participant",
        )

    def test_fiend_source_grants_advantage(self):
        self.assertEqual(self._mod("fiend").result, "advantage")

    def test_undead_source_grants_advantage(self):
        self.assertEqual(self._mod("undead").result, "advantage")

    def test_humanoid_source_no_advantage(self):
        self.assertEqual(self._mod("humanoid").result, "normal")

    def test_beast_source_no_advantage(self):
        self.assertEqual(self._mod("beast").result, "normal")

    def test_missing_creature_type_no_advantage(self):
        ctx = modify_saving_throw(
            _participant([_protection_effect()]),
            "wisdom",
            source_participant={"id": "src-1"},  # sem creature_type
            source_kind="participant",
        )
        self.assertEqual(ctx.result, "normal")

    def test_condition_repeat_pattern_no_advantage(self):
        # lifecycle_turns.py passes source_kind="passive_condition"
        ctx = modify_saving_throw(
            _participant([_protection_effect()]),
            "wisdom",
            source_kind="passive_condition",
        )
        self.assertEqual(ctx.result, "normal")

    def test_manual_gm_save_pattern_no_advantage(self):
        # save_resolve.py passes source_kind="manual_gm"
        ctx = modify_saving_throw(
            _participant([_protection_effect()]),
            "constitution",
            source_kind="manual_gm",
        )
        self.assertEqual(ctx.result, "normal")

    def test_preview_pattern_no_advantage_without_source_participant(self):
        ctx = modify_saving_throw(
            _participant([_protection_effect()]),
            "wisdom",
            source_kind="preview",
        )
        self.assertEqual(ctx.result, "normal")


class SourceKindLegacyAuditTests(unittest.TestCase):
    def test_legacy_placeholder_source_kind_not_used_in_app_services(self):
        repo_root = Path(__file__).resolve().parents[1]
        files = [
            str(path.relative_to(repo_root))
            for path in (repo_root / "app/services").rglob("*.py")
        ]
        legacy_kind = "unknown" + "_legacy"
        counts: dict[str, int] = {}
        total = 0
        for rel in files:
            text = (repo_root / rel).read_text(encoding="utf-8")
            count = text.count(f'source_kind="{legacy_kind}"')
            counts[rel] = count
            total += count
        self.assertEqual(
            total,
            0,
            f"Expected 0 legacy placeholder source_kind call sites in app/services, found {total}: {counts}",
        )

    def test_explicit_source_kind_call_site_markers_exist(self):
        repo_root = Path(__file__).resolve().parents[1]
        lifecycle_text = (
            repo_root / "app/services/combat_service/lifecycle_turns.py"
        ).read_text(encoding="utf-8")
        save_resolve_text = (
            repo_root / "app/services/combat_service/save_resolve.py"
        ).read_text(encoding="utf-8")
        npc_action_text = (
            repo_root / "app/services/combat_service/npc_action_resolution.py"
        ).read_text(encoding="utf-8")
        self.assertIn('source_kind="passive_condition"', lifecycle_text)
        self.assertIn('source_kind="manual_gm"', save_resolve_text)
        self.assertIn('source_kind="participant"', npc_action_text)


if __name__ == "__main__":
    unittest.main()
