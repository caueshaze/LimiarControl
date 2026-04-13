"""Normalize legacy item property slugs.

Revision ID: 0037_item_property_slugs
Revises: 0036_harden_base_item_mechanics
Create Date: 2026-03-23
"""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0037_item_property_slugs"
down_revision: Union[str, None] = "0036_harden_base_item_mechanics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PROPERTY_ALIAS_GROUPS: dict[str, tuple[str, ...]] = {
    "ammunition": ("ammunition", "ammo", "municao"),
    "finesse": ("finesse", "acuidade"),
    "heavy": ("heavy", "pesada", "pesado"),
    "light": ("light", "leve"),
    "loading": ("loading", "carregamento", "recarga"),
    "range": ("range", "alcance", "ranged", "distancia", "a distancia"),
    "reach": ("reach", "alcance estendido"),
    "special": ("special", "especial"),
    "thrown": ("thrown", "arremesso", "arremessavel"),
    "two_handed": ("two_handed", "two handed", "two-handed", "duas maos"),
    "versatile": ("versatile", "versatil"),
    "stealth_disadvantage": (
        "stealth_disadvantage",
        "stealth disadvantage",
        "disadvantage on stealth",
        "desvantagem em furtividade",
    ),
}


def _normalize_token(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value or "")
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    collapsed = ascii_value.lower().replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", collapsed).strip()


PROPERTY_ALIAS_TO_SLUG: dict[str, str] = {}
for slug, aliases in PROPERTY_ALIAS_GROUPS.items():
    PROPERTY_ALIAS_TO_SLUG[_normalize_token(slug)] = slug
    for alias in aliases:
        PROPERTY_ALIAS_TO_SLUG[_normalize_token(alias)] = slug


def _normalize_properties(values: object) -> list[str]:
    if not isinstance(values, list):
        return []

    normalized: list[str] = []
    seen: set[str] = set()

    for entry in values:
        raw_value = str(entry or "").strip()
        if not raw_value:
            continue
        slug = PROPERTY_ALIAS_TO_SLUG.get(_normalize_token(raw_value))
        if slug is None or slug in seen:
            continue
        seen.add(slug)
        normalized.append(slug)

    return normalized


def upgrade() -> None:
    bind = op.get_bind()

    base_item_rows = bind.execute(
        sa.text(
            """
            SELECT id, weapon_properties_json
            FROM base_item
            WHERE weapon_properties_json IS NOT NULL
            """
        )
    ).fetchall()
    for row in base_item_rows:
        normalized = _normalize_properties(row.weapon_properties_json)
        payload = json.dumps(normalized)
        bind.execute(
            sa.text(
                """
                UPDATE base_item
                SET weapon_properties_json = CAST(:payload AS JSONB)
                WHERE id = :id
                """
            ),
            {"id": row.id, "payload": payload},
        )

    item_rows = bind.execute(
        sa.text(
            """
            SELECT id, properties
            FROM item
            WHERE properties IS NOT NULL
            """
        )
    ).fetchall()
    for row in item_rows:
        normalized = _normalize_properties(list(row.properties or []))
        bind.execute(
            sa.text(
                """
                UPDATE item
                SET properties = :properties
                WHERE id = :id
                """
            ),
            {"id": row.id, "properties": normalized},
        )


def downgrade() -> None:
    # Data normalization is intentionally irreversible.
    return None
