from __future__ import annotations

import re
import unicodedata
from enum import Enum

from app.models.base_item import (
    BaseItemDamageType,
    BaseItemDexBonusRule,
    BaseItemProperty,
    BaseItemSource,
)

DAMAGE_EXPRESSION_RE = re.compile(
    r"^\s*(?:(\d*)d(\d+)|(\d+))\s*(?:([+-])\s*(\d+))?\s*$",
    re.IGNORECASE,
)
ITEM_DAMAGE_TYPE_MAP = {
    value.value.lower(): value.value for value in BaseItemDamageType
}
ITEM_DEX_BONUS_RULE_MAP = {
    "full": BaseItemDexBonusRule.FULL.value,
    "unlimited": BaseItemDexBonusRule.FULL.value,
    "0": BaseItemDexBonusRule.NONE.value,
    "max_0": BaseItemDexBonusRule.NONE.value,
    "max 0": BaseItemDexBonusRule.NONE.value,
    "max_2": BaseItemDexBonusRule.MAX_2.value,
    "max 2": BaseItemDexBonusRule.MAX_2.value,
    "none": BaseItemDexBonusRule.NONE.value,
}
ITEM_SOURCE_MAP = {
    value.value: value.value for value in BaseItemSource
}
ITEM_SOURCE_MAP.update(
    {
        "csv": BaseItemSource.SEED_JSON_BOOTSTRAP.value,
        "csv_import": BaseItemSource.SEED_JSON_BOOTSTRAP.value,
        "seed": BaseItemSource.SEED_JSON_BOOTSTRAP.value,
    }
)
WEAPON_PROPERTY_SLUGS = {
    BaseItemProperty.AMMUNITION.value,
    BaseItemProperty.FINESSE.value,
    BaseItemProperty.HEAVY.value,
    BaseItemProperty.LIGHT.value,
    BaseItemProperty.LOADING.value,
    BaseItemProperty.RANGE.value,
    BaseItemProperty.REACH.value,
    BaseItemProperty.SPECIAL.value,
    BaseItemProperty.THROWN.value,
    BaseItemProperty.TWO_HANDED.value,
    BaseItemProperty.VERSATILE.value,
}


def _raw_value(value: object) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def _normalize_slug(value: str) -> str:
    normalized = (
        unicodedata.normalize("NFKD", value or "")
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    collapsed = re.sub(r"[^a-z0-9]+", "_", normalized.lower())
    return re.sub(r"_+", "_", collapsed).strip("_")
