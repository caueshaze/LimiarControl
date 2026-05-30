from __future__ import annotations

LESSER_RESTORATION_CONDITIONS: frozenset[str] = frozenset({"blinded", "deafened", "paralyzed", "poisoned"})

PROTECTION_FROM_EVIL_AND_GOOD_CREATURE_TYPES: frozenset[str] = frozenset({
    "aberration", "celestial", "elemental", "fey", "fiend", "undead",
})

PROTECTION_FROM_EVIL_AND_GOOD_CONDITIONS: frozenset[str] = frozenset({
    "charmed", "frightened", "possessed",
})

COMMAND_VARIANTS: frozenset[str] = frozenset({"approach", "drop", "flee", "grovel", "halt"})
COMMAND_VARIANT_LABELS: dict[str, str] = {
    "approach": "Aproxime-se",
    "drop": "Largue",
    "flee": "Fuja",
    "grovel": "Prostre-se",
    "halt": "Pare",
}
