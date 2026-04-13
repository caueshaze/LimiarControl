"""Phase F3 — visibility model unit tests."""

import unittest

from app.services.combat_service.visibility import (
    TargetVisibilityContext,
    can_directly_see_target,
    can_target_in_combat,
    resolve_target_visibility,
)
from app.services.combat_service.condition_effects import (
    is_heavily_obscured,
    is_lightly_obscured,
)


def _participant(conditions: list[str] | None = None) -> dict:
    effects: list[dict] = []
    for ctype in conditions or []:
        effects.append({"kind": "condition", "condition_type": ctype})
    return {"id": "p1", "active_effects": effects, "status": "active"}


# ─── resolve_target_visibility ────────────────────────────────────────────────


class TestResolveTargetVisibility(unittest.TestCase):
    """Core visibility resolution tests."""

    def test_no_conditions_no_los_true(self):
        vis = resolve_target_visibility(_participant(), _participant())
        self.assertTrue(vis.has_line_of_sight)
        self.assertTrue(vis.is_directly_visible)
        self.assertEqual(vis.visibility_state, "visible")
        self.assertEqual(vis.visibility_blockers, [])

    def test_no_conditions_explicit_los_true(self):
        vis = resolve_target_visibility(
            _participant(),
            _participant(),
            has_line_of_sight=True,
        )
        self.assertTrue(vis.is_directly_visible)
        self.assertEqual(vis.visibility_state, "visible")

    def test_no_line_of_sight(self):
        vis = resolve_target_visibility(
            _participant(),
            _participant(),
            has_line_of_sight=False,
        )
        self.assertFalse(vis.has_line_of_sight)
        self.assertFalse(vis.is_directly_visible)
        self.assertEqual(vis.visibility_state, "not_visible")
        self.assertIn("no_line_of_sight", vis.visibility_blockers)

    def test_attacker_blinded(self):
        vis = resolve_target_visibility(
            _participant(["blinded"]),
            _participant(),
        )
        self.assertTrue(vis.has_line_of_sight)
        self.assertFalse(vis.is_directly_visible)
        self.assertIn("attacker_cannot_see", vis.visibility_blockers)

    def test_attacker_unconscious(self):
        vis = resolve_target_visibility(
            _participant(["unconscious"]),
            _participant(),
        )
        self.assertFalse(vis.is_directly_visible)
        self.assertIn("attacker_cannot_see", vis.visibility_blockers)

    def test_attacker_petrified(self):
        vis = resolve_target_visibility(
            _participant(["petrified"]),
            _participant(),
        )
        self.assertFalse(vis.is_directly_visible)
        self.assertIn("attacker_cannot_see", vis.visibility_blockers)

    def test_target_invisible(self):
        vis = resolve_target_visibility(
            _participant(),
            _participant(["invisible"]),
        )
        self.assertFalse(vis.is_directly_visible)
        self.assertIn("target_invisible", vis.visibility_blockers)

    def test_target_heavily_obscured(self):
        vis = resolve_target_visibility(
            _participant(),
            _participant(["heavily_obscured"]),
        )
        self.assertFalse(vis.is_directly_visible)
        self.assertIn("target_heavily_obscured", vis.visibility_blockers)

    def test_target_lightly_obscured_still_visible(self):
        vis = resolve_target_visibility(
            _participant(),
            _participant(["lightly_obscured"]),
        )
        self.assertTrue(vis.is_directly_visible)
        self.assertEqual(vis.visibility_blockers, [])

    def test_multiple_blockers(self):
        vis = resolve_target_visibility(
            _participant(["blinded"]),
            _participant(["invisible", "heavily_obscured"]),
            has_line_of_sight=False,
        )
        self.assertFalse(vis.is_directly_visible)
        self.assertEqual(len(vis.visibility_blockers), 4)
        self.assertIn("no_line_of_sight", vis.visibility_blockers)
        self.assertIn("attacker_cannot_see", vis.visibility_blockers)
        self.assertIn("target_invisible", vis.visibility_blockers)
        self.assertIn("target_heavily_obscured", vis.visibility_blockers)

    def test_attacker_blinded_and_target_invisible_single_blocker(self):
        vis = resolve_target_visibility(
            _participant(["blinded"]),
            _participant(["invisible"]),
        )
        self.assertFalse(vis.is_directly_visible)
        self.assertIn("attacker_cannot_see", vis.visibility_blockers)
        self.assertIn("target_invisible", vis.visibility_blockers)

    def test_los_true_but_invisible_not_directly_visible(self):
        vis = resolve_target_visibility(
            _participant(),
            _participant(["invisible"]),
            has_line_of_sight=True,
        )
        self.assertTrue(vis.has_line_of_sight)
        self.assertFalse(vis.is_directly_visible)

    def test_prone_attacker_still_visible(self):
        vis = resolve_target_visibility(
            _participant(["prone"]),
            _participant(),
        )
        self.assertTrue(vis.is_directly_visible)

    def test_restrained_attacker_still_visible(self):
        vis = resolve_target_visibility(
            _participant(["restrained"]),
            _participant(),
        )
        self.assertTrue(vis.is_directly_visible)


# ─── can_directly_see_target ──────────────────────────────────────────────────


class TestCanDirectlySeeTarget(unittest.TestCase):
    def test_visible_returns_true(self):
        self.assertTrue(can_directly_see_target(_participant(), _participant()))

    def test_no_los_returns_false(self):
        self.assertFalse(
            can_directly_see_target(
                _participant(),
                _participant(),
                has_line_of_sight=False,
            )
        )

    def test_target_invisible_returns_false(self):
        self.assertFalse(
            can_directly_see_target(_participant(), _participant(["invisible"]))
        )

    def test_attacker_blinded_returns_false(self):
        self.assertFalse(
            can_directly_see_target(_participant(["blinded"]), _participant())
        )


# ─── can_target_in_combat ─────────────────────────────────────────────────────


class TestCanTargetInCombat(unittest.TestCase):
    def test_no_sight_requirement_always_targetable(self):
        can, reason = can_target_in_combat(
            _participant(),
            _participant(["invisible"]),
            requires_sight=False,
        )
        self.assertTrue(can)
        self.assertIsNone(reason)

    def test_no_sight_requirement_blinded_can_still_target(self):
        can, reason = can_target_in_combat(
            _participant(["blinded"]),
            _participant(),
            requires_sight=False,
        )
        self.assertTrue(can)
        self.assertIsNone(reason)

    def test_sight_requirement_visible_target(self):
        can, reason = can_target_in_combat(
            _participant(),
            _participant(),
            requires_sight=True,
        )
        self.assertTrue(can)
        self.assertIsNone(reason)

    def test_sight_requirement_invisible_target_rejected(self):
        can, reason = can_target_in_combat(
            _participant(),
            _participant(["invisible"]),
            requires_sight=True,
        )
        self.assertFalse(can)
        self.assertEqual(reason, "target_not_visible")

    def test_sight_requirement_blinded_rejected(self):
        can, reason = can_target_in_combat(
            _participant(["blinded"]),
            _participant(),
            requires_sight=True,
        )
        self.assertFalse(can)
        self.assertEqual(reason, "target_not_visible")

    def test_sight_requirement_heavily_obscured_rejected(self):
        can, reason = can_target_in_combat(
            _participant(),
            _participant(["heavily_obscured"]),
            requires_sight=True,
        )
        self.assertFalse(can)
        self.assertEqual(reason, "target_not_visible")

    def test_sight_requirement_lightly_obscured_allowed(self):
        can, reason = can_target_in_combat(
            _participant(),
            _participant(["lightly_obscured"]),
            requires_sight=True,
        )
        self.assertTrue(can)
        self.assertIsNone(reason)

    def test_no_los_rejected_even_without_conditions(self):
        can, reason = can_target_in_combat(
            _participant(),
            _participant(),
            has_line_of_sight=False,
            requires_sight=True,
        )
        self.assertFalse(can)
        self.assertEqual(reason, "no_line_of_sight")

    def test_no_los_without_sight_requirement(self):
        can, reason = can_target_in_combat(
            _participant(),
            _participant(),
            has_line_of_sight=False,
            requires_sight=False,
        )
        self.assertTrue(can)
        self.assertIsNone(reason)


# ─── TargetVisibilityContext.describe ─────────────────────────────────────────


class TestTargetVisibilityContextDescribe(unittest.TestCase):
    def test_visible(self):
        ctx = TargetVisibilityContext(
            has_line_of_sight=True,
            is_directly_visible=True,
            visibility_state="visible",
            visibility_blockers=[],
        )
        self.assertEqual(ctx.describe(), "visible")

    def test_not_visible_single_blocker(self):
        ctx = TargetVisibilityContext(
            has_line_of_sight=True,
            is_directly_visible=False,
            visibility_state="not_visible",
            visibility_blockers=["target_invisible"],
        )
        self.assertEqual(ctx.describe(), "not_visible (target_invisible)")

    def test_not_visible_multiple_blockers(self):
        ctx = TargetVisibilityContext(
            has_line_of_sight=False,
            is_directly_visible=False,
            visibility_state="not_visible",
            visibility_blockers=["no_line_of_sight", "attacker_cannot_see"],
        )
        desc = ctx.describe()
        self.assertIn("no_line_of_sight", desc)
        self.assertIn("attacker_cannot_see", desc)


# ─── obscurement predicates ───────────────────────────────────────────────────


class TestObscurementPredicates(unittest.TestCase):
    def test_heavily_obscured(self):
        self.assertTrue(is_heavily_obscured(_participant(["heavily_obscured"])))

    def test_not_heavily_obscured(self):
        self.assertFalse(is_heavily_obscured(_participant()))
        self.assertFalse(is_heavily_obscured(_participant(["lightly_obscured"])))

    def test_lightly_obscured(self):
        self.assertTrue(is_lightly_obscured(_participant(["lightly_obscured"])))

    def test_not_lightly_obscured(self):
        self.assertFalse(is_lightly_obscured(_participant()))
        self.assertFalse(is_lightly_obscured(_participant(["heavily_obscured"])))


# ─── player/NPC parity ────────────────────────────────────────────────────────


class TestPlayerNpcParity(unittest.TestCase):
    """Visibility rules must be identical regardless of participant kind."""

    def test_invisible_player(self):
        player = _participant(["invisible"])
        player["kind"] = "player"
        vis = resolve_target_visibility(_participant(), player)
        self.assertFalse(vis.is_directly_visible)
        self.assertIn("target_invisible", vis.visibility_blockers)

    def test_invisible_entity(self):
        entity = _participant(["invisible"])
        entity["kind"] = "session_entity"
        vis = resolve_target_visibility(_participant(), entity)
        self.assertFalse(vis.is_directly_visible)
        self.assertIn("target_invisible", vis.visibility_blockers)

    def test_blinded_attacker_player(self):
        player = _participant(["blinded"])
        player["kind"] = "player"
        vis = resolve_target_visibility(player, _participant())
        self.assertFalse(vis.is_directly_visible)

    def test_blinded_attacker_entity(self):
        entity = _participant(["blinded"])
        entity["kind"] = "session_entity"
        vis = resolve_target_visibility(entity, _participant())
        self.assertFalse(vis.is_directly_visible)


if __name__ == "__main__":
    unittest.main()
