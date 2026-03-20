from __future__ import annotations

import re
import unicodedata

ITEM_PROPERTY_ALIASES: dict[str, tuple[str, ...]] = {
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

ITEM_PROPERTY_SLUGS = tuple(ITEM_PROPERTY_ALIASES.keys())


def _normalize_token(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value or "")
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    return re.sub(r"\s+", " ", ascii_value.lower().replace("_", " ").replace("-", " ")).strip()


ITEM_PROPERTY_ALIAS_TO_SLUG: dict[str, str] = {}
for slug, aliases in ITEM_PROPERTY_ALIASES.items():
    ITEM_PROPERTY_ALIAS_TO_SLUG[_normalize_token(slug)] = slug
    for alias in aliases:
        ITEM_PROPERTY_ALIAS_TO_SLUG[_normalize_token(alias)] = slug


def resolve_item_property_slug(value: str) -> str | None:
    normalized = _normalize_token(value)
    if not normalized:
        return None
    return ITEM_PROPERTY_ALIAS_TO_SLUG.get(normalized)


def normalize_item_properties(
    values: list[str] | tuple[str, ...] | None,
) -> tuple[list[str], list[str]]:
    normalized: list[str] = []
    invalid: list[str] = []
    seen: set[str] = set()

    for entry in values or []:
        raw_value = str(entry or "").strip()
        if not raw_value:
            continue

        slug = resolve_item_property_slug(raw_value)
        if slug is None:
            if raw_value not in invalid:
                invalid.append(raw_value)
            continue

        if slug not in seen:
            seen.add(slug)
            normalized.append(slug)

    return normalized, invalid
