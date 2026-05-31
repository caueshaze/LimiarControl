from __future__ import annotations

from typing import Any

SHATTER_KEY = "shatter"

# Materials that grant disadvantage on Shatter's Constitution save.
INORGANIC_MATERIALS = {"stone", "crystal", "metal"}
# Tag tokens that mark a creature as inorganic for Shatter.
INORGANIC_TAGS = {"inorganic", "stone", "crystal", "metal"}
INORGANIC_SAVE_DISADV_SOURCE = "shatter_inorganic_material"


def _metadata(participant: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(participant, dict):
        return {}
    metadata = participant.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def _material_value(participant: dict[str, Any], metadata: dict[str, Any]) -> str:
    raw = (
        participant.get("material_type")
        or participant.get("material")
        or metadata.get("material_type")
        or metadata.get("material")
    )
    return str(raw or "").strip().lower()


def _tag_tokens(participant: dict[str, Any], metadata: dict[str, Any]) -> set[str]:
    tokens: set[str] = set()
    for source in (
        participant.get("creature_tags"),
        participant.get("tags"),
        metadata.get("creature_tags"),
        metadata.get("tags"),
        metadata.get("material_tags"),
    ):
        if isinstance(source, (list, tuple, set)):
            tokens.update(str(t).strip().lower() for t in source)
    return tokens


def is_inorganic_participant(participant: dict[str, Any] | None) -> bool:
    """True only when a creature carries explicit inorganic material data.

    Reads an explicit `material_type`/`material` (stone/crystal/metal) or a tag in
    {inorganic, stone, crystal, metal}. Deliberately does NOT infer material from
    creature_type (e.g. a construct is not assumed to be stone/crystal/metal).
    """
    if not isinstance(participant, dict):
        return False
    metadata = _metadata(participant)
    if _material_value(participant, metadata) in INORGANIC_MATERIALS:
        return True
    return bool(_tag_tokens(participant, metadata) & INORGANIC_TAGS)
