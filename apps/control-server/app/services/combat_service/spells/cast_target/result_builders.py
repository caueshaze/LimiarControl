from __future__ import annotations

from typing import NotRequired, TypedDict


class SpellCastResultPayload(TypedDict):
    spell_name: str
    spell_canonical_key: str
    action_kind: str
    effect_kind: str | None
    damage: int
    healing: int
    pending_spell_id: NotRequired[str | None]
    pending_save_id: NotRequired[str | None]
