from __future__ import annotations

import random
import re

from fastapi import HTTPException


class CombatServiceError(HTTPException):
    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(status_code=status_code, detail=detail)


def _parse_dice(expression: str) -> tuple[int, int, int]:
    if not expression:
        return 0, 0, 0
    static_match = re.fullmatch(r"\s*(\d+)\s*", expression.lower())
    if static_match:
        return 0, 0, int(static_match.group(1))
    match = re.search(r'(\d+)d(\d+)\s*(?:([+-])\s*(\d+))?', expression.lower())
    if not match:
        return 0, 0, 0
    count = int(match.group(1))
    sides = int(match.group(2))
    mod = 0
    if match.group(3) and match.group(4):
        sign = 1 if match.group(3) == '+' else -1
        mod = sign * int(match.group(4))
    return count, sides, mod


def _roll_dice_expression(expression: str, critical: bool = False) -> int:
    count, sides, mod = _parse_dice(expression)
    if count == 0:
        return 0
    if critical:
        count *= 2
    return sum(random.randint(1, sides) for _ in range(count)) + mod
