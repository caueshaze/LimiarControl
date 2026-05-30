from __future__ import annotations

import random

from app.services.dice import DiceRoll, parse_dice, roll_dice


def test_parse_dice_basic():
    assert parse_dice("2d6") == DiceRoll(count=2, sides=6, modifier=0)
    assert parse_dice("1d20+5") == DiceRoll(count=1, sides=20, modifier=5)
    assert parse_dice("3d8-2") == DiceRoll(count=3, sides=8, modifier=-2)


def test_parse_dice_ignores_whitespace():
    assert parse_dice("  4d10 + 3 ") == DiceRoll(count=4, sides=10, modifier=3)


def test_parse_dice_invalid_returns_none():
    assert parse_dice("not-a-dice") is None
    assert parse_dice("d20") is None
    assert parse_dice("") is None


def test_roll_dice_is_deterministic_with_seeded_rng():
    rng = random.Random(42)
    first = roll_dice("3d6+2", rng=rng)
    rng = random.Random(42)
    second = roll_dice("3d6+2", rng=rng)
    assert first == second


def test_roll_dice_respects_bounds():
    rng = random.Random(0)
    for _ in range(100):
        total = roll_dice("2d6+1", rng=rng)
        assert total is not None
        # 2 dice in [1,6] plus modifier 1 -> range [3, 13]
        assert 3 <= total <= 13


def test_roll_dice_invalid_returns_none():
    assert roll_dice("garbage") is None
