from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class DiceRoll:
    count: int
    sides: int
    modifier: int


_DICE_RE = re.compile(r"^\s*(\d+)d(\d+)\s*([+-]\s*\d+)?\s*$", re.IGNORECASE)


def parse_dice(expression: str) -> Optional[DiceRoll]:
    """Parse a dice expression like '2d6', '1d20+5', '3d8-2'."""
    match = _DICE_RE.match(expression)
    if not match:
        return None
    count = int(match.group(1))
    sides = int(match.group(2))
    modifier = 0
    if match.group(3):
        modifier = int(match.group(3).replace(" ", ""))
    return DiceRoll(count=count, sides=sides, modifier=modifier)


def roll_dice(expression: str, *, rng: random.Random | None = None) -> Optional[int]:
    """Roll a dice expression and return the total, or None if it cannot be parsed."""
    parsed = parse_dice(expression)
    if parsed is None:
        return None
    roller = rng or random
    total = sum(roller.randint(1, parsed.sides) for _ in range(parsed.count))
    return total + parsed.modifier
