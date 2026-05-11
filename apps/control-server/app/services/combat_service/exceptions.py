from __future__ import annotations

import random
import re

from fastapi import HTTPException


class CombatServiceError(HTTPException):
    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(status_code=status_code, detail=detail)


def _parse_dice(expression: str) -> tuple[int, int, int, int]:
    if not expression:
        return 1, 0, 0, 0
    static_match = re.fullmatch(r"\s*([+-]?\d+)\s*", expression.lower())
    if static_match:
        return 1, 0, 0, int(static_match.group(1))
    match = re.search(r'([+-])?\s*(\d+)d(\d+)\s*(?:([+-])\s*(\d+))?', expression.lower())
    if not match:
        return 1, 0, 0, 0
    multiplier = -1 if match.group(1) == '-' else 1
    count = int(match.group(2))
    sides = int(match.group(3))
    mod = 0
    if match.group(4) and match.group(5):
        sign = 1 if match.group(4) == '+' else -1
        mod = sign * int(match.group(5))
    return multiplier, count, sides, mod


def _roll_dice_expression(expression: str, critical: bool = False) -> int:
    multiplier, count, sides, mod = _parse_dice(expression)
    if count == 0:
        return mod
    if critical:
        count *= 2
    return (multiplier * sum(random.randint(1, sides) for _ in range(count))) + mod
