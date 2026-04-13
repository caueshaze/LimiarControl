"""D&D 5e XP thresholds (PHB p.15)."""

XP_THRESHOLDS: dict[int, int] = {
    1: 0,
    2: 300,
    3: 900,
    4: 2700,
    5: 6500,
    6: 14000,
    7: 23000,
    8: 34000,
    9: 48000,
    10: 64000,
    11: 85000,
    12: 100000,
    13: 120000,
    14: 140000,
    15: 165000,
    16: 195000,
    17: 225000,
    18: 265000,
    19: 305000,
    20: 355000,
}

MAX_LEVEL = 20


def get_xp_for_next_level(current_level: int) -> int | None:
    if current_level >= MAX_LEVEL:
        return None
    return XP_THRESHOLDS.get(current_level + 1)


def can_level_up(current_level: int, xp: int) -> bool:
    threshold = get_xp_for_next_level(current_level)
    return threshold is not None and xp >= threshold
