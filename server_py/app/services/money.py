from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

CP_PER_UNIT = {
    "cp": 1,
    "sp": 10,
    "ep": 50,
    "gp": 100,
    "pp": 1000,
}


def to_copper(value: int | float, unit: str) -> int:
    multiplier = CP_PER_UNIT.get(str(unit).lower(), 1)
    amount = Decimal(str(value or 0)) * Decimal(multiplier)
    return max(0, int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)))


def from_copper(copper_value: int) -> dict[str, int]:
    remaining = max(0, int(copper_value or 0))
    pp, remaining = divmod(remaining, CP_PER_UNIT["pp"])
    gp, remaining = divmod(remaining, CP_PER_UNIT["gp"])
    ep, remaining = divmod(remaining, CP_PER_UNIT["ep"])
    sp, cp = divmod(remaining, CP_PER_UNIT["sp"])
    return {
        "pp": pp,
        "gp": gp,
        "ep": ep,
        "sp": sp,
        "cp": cp,
    }


def normalize_money(value: object | None) -> dict[str, int]:
    if not isinstance(value, dict):
        return {"copperValue": 0}

    if "copperValue" in value:
        return {"copperValue": max(0, int(value.get("copperValue", 0) or 0))}

    return {
        "copperValue": (
            max(0, int(value.get("cp", 0) or 0))
            + max(0, int(value.get("sp", 0) or 0)) * CP_PER_UNIT["sp"]
            + max(0, int(value.get("ep", 0) or 0)) * CP_PER_UNIT["ep"]
            + max(0, int(value.get("gp", 0) or 0)) * CP_PER_UNIT["gp"]
            + max(0, int(value.get("pp", 0) or 0)) * CP_PER_UNIT["pp"]
        )
    }


def format_money(copper_value: int) -> str:
    coins = from_copper(copper_value)
    parts: list[str] = []
    if coins["pp"] > 0:
        parts.append(f"{coins['pp']} pp")
    if coins["gp"] > 0:
        parts.append(f"{coins['gp']} gp")
    if coins["sp"] > 0:
        parts.append(f"{coins['sp']} sp")
    if coins["cp"] > 0 or not parts:
        parts.append(f"{coins['cp']} cp")
    return " ".join(parts)
