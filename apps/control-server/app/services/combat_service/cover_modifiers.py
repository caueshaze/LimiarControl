"""
Single source of truth for cover modifier logic.

Attack-roll cover (Phase 4):
  - cover adds to the defender's effective AC
  - half → +2 AC | threeQuarters → +5 AC

Saving throw cover (Phase 5):
  - cover reduces the effective DC seen by the defender
  - same numeric values as attack cover (half → -2 DC | threeQuarters → -5 DC)
  - only applies when the spell/action explicitly allows it via metadata

Cover levels:
  none          → +0 (no modifier in any path)
  half          → +2 / -2
  threeQuarters → +5 / -5
  full          → blocked before resolution; modifier is irrelevant here

Metadata-driven save cover (coverAppliesToSave field on BaseSpell):
  "physical" → cover applies  (spatial, projectile, blast, or wave effects)
  "none"     → cover does not apply (mental, control, self-emanation, etc.)
  None/unset → use fallback heuristic (see should_cover_apply_to_save)

The fallback heuristic is intentionally conservative and temporary.
It should be removed once all spell catalog entries carry explicit metadata.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Attack-roll cover (Phase 4)
# ---------------------------------------------------------------------------

COVER_AC_MODIFIERS: dict[str, int] = {
    "none": 0,
    "half": 2,
    "threeQuarters": 5,
    "full": 0,  # Full cover is rejected at targeting phase; never applied.
}

_COVER_LABELS: dict[str, str] = {
    "half": "Half Cover",
    "threeQuarters": "Three-Quarters Cover",
}


def resolve_cover_modifier(cover: str | None) -> int:
    """Return the AC bonus for attack rolls granted by the given cover level."""
    return COVER_AC_MODIFIERS.get(cover or "none", 0)


def cover_label(cover: str | None) -> str | None:
    """Return a human-readable label for a cover level, or None for no cover."""
    return _COVER_LABELS.get(cover or "none")


# ---------------------------------------------------------------------------
# Saving throw cover (Phase 5)
# ---------------------------------------------------------------------------

# The save bonus is the same numeric value as the AC bonus: cover consistently
# makes the defender harder to affect, whether via attack or via save.
COVER_SAVE_MODIFIERS: dict[str, int] = {
    "none": 0,
    "half": 2,
    "threeQuarters": 5,
    "full": 0,  # Full cover is blocked upstream; modifier is irrelevant here.
}

# Canonical values for the coverAppliesToSave metadata field on BaseSpell.
COVER_SAVE_RULE_PHYSICAL = "physical"
COVER_SAVE_RULE_NONE = "none"

# All valid cover-applies-to-save rule values for schema validation.
COVER_SAVE_RULE_VALUES: tuple[str, ...] = (
    COVER_SAVE_RULE_PHYSICAL,
    COVER_SAVE_RULE_NONE,
)


def resolve_cover_save_modifier(cover: str | None) -> int:
    """Return the save bonus granted by cover (reduces effective DC by this amount).

    Numeric values are identical to attack-roll cover modifiers. Cover
    consistently makes the defender harder to affect in all combat paths.
    """
    return COVER_SAVE_MODIFIERS.get(cover or "none", 0)


def should_cover_apply_to_save(
    cover_applies_to_save: str | None,
    save_ability: str | None = None,
) -> bool:
    """Return True if cover should modify the saving throw DC for this effect.

    Explicit metadata (coverAppliesToSave on the spell/action) is authoritative.
    When metadata is absent the fallback heuristic applies.

    Args:
        cover_applies_to_save: Value from BaseSpell.cover_applies_to_save.
            "physical" → cover applies.
            "none"     → cover does not apply.
            None       → fall back to heuristic.
        save_ability: Normalized ability name ("dexterity", "strength", etc.).
            Used only by the fallback when metadata is absent.

    Returns:
        True if cover should be applied; False otherwise.
    """
    # Explicit metadata is authoritative — check first.
    if cover_applies_to_save == COVER_SAVE_RULE_PHYSICAL:
        return True
    if cover_applies_to_save == COVER_SAVE_RULE_NONE:
        return False

    # --- Fallback heuristic (legacy safety net) ----------------------------
    # All base spells and newly created campaign spells carry explicit metadata
    # after migration 0052/0053.  This path is reached only for campaign spells
    # that were created before those migrations and have not been updated.
    # It must not be extended; remove once such records are no longer reachable.
    return (save_ability or "").lower() in ("dex", "dexterity")
