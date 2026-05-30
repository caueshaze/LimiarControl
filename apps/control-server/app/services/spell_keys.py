from __future__ import annotations

from app.services.canonical_keys import canonical_keys_equal, normalize_canonical_key


def normalize_spell_key(value: object) -> str:
    """Normalize spell canonical keys to snake_case."""
    return normalize_canonical_key(value)


def spell_keys_equal(a: object, b: object) -> bool:
    return canonical_keys_equal(a, b)
