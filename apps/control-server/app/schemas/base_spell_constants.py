import re
import unicodedata

from app.models.base_spell import (
    AreaShape,
    CastingTimeType,
    ResolutionType,
    SpellSource,
    SpellAttackType,
    SpellEffectTiming,
    SpellOriginType,
    SpellRangeKind,
    SpellSelectionType,
    SpellTargetAnchor,
    TargetType,
    UpcastMode,
)

SPELL_CLASS_VALUES = (
    "Bard",
    "Cleric",
    "Druid",
    "Guardian",
    "Paladin",
    "Ranger",
    "Sorcerer",
    "Warlock",
    "Wizard",
)
SPELL_COMPONENT_VALUES = ("V", "S", "M")
SPELL_DAMAGE_TYPE_VALUES = (
    "Acid",
    "Bludgeoning",
    "Cold",
    "Fire",
    "Force",
    "Lightning",
    "Necrotic",
    "Piercing",
    "Poison",
    "Psychic",
    "Radiant",
    "Slashing",
    "Thunder",
)
SPELL_SAVING_THROW_VALUES = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
SPELL_SAVE_SUCCESS_OUTCOME_VALUES = ("none", "half_damage")

SPELL_CLASS_MAP = {value.lower(): value for value in SPELL_CLASS_VALUES}
SPELL_COMPONENT_MAP = {value.lower(): value for value in SPELL_COMPONENT_VALUES}
SPELL_DAMAGE_TYPE_MAP = {value.lower(): value for value in SPELL_DAMAGE_TYPE_VALUES}
SPELL_SAVING_THROW_MAP = {value.lower(): value for value in SPELL_SAVING_THROW_VALUES}
SPELL_SAVE_SUCCESS_OUTCOME_MAP = {
    value.lower(): value for value in SPELL_SAVE_SUCCESS_OUTCOME_VALUES
}

CASTING_TIME_TYPE_MAP = {member.value: member.value for member in CastingTimeType}
TARGET_TYPE_MAP = {member.value: member.value for member in TargetType}
AREA_SHAPE_MAP = {member.value: member.value for member in AreaShape}
SPELL_SELECTION_TYPE_MAP = {member.value: member.value for member in SpellSelectionType}
SPELL_ORIGIN_TYPE_MAP = {member.value: member.value for member in SpellOriginType}
SPELL_TARGET_ANCHOR_MAP = {member.value: member.value for member in SpellTargetAnchor}
SPELL_ATTACK_TYPE_MAP = {member.value: member.value for member in SpellAttackType}
SPELL_RANGE_KIND_MAP = {member.value: member.value for member in SpellRangeKind}
SPELL_EFFECT_TIMING_MAP = {member.value: member.value for member in SpellEffectTiming}
RESOLUTION_TYPE_MAP = {member.value: member.value for member in ResolutionType}
RESOLUTION_TYPE_MAP.update(
    {
        "none": "none",
        "spell_attack": "spell_attack",
        "saving_throw": "saving_throw",
        "automatic": "automatic",
    }
)
UPCAST_MODE_MAP = {member.value: member.value for member in UpcastMode}
UPCAST_MODE_MAP.update(
    {
        "add_dice": "add_dice",
        "add_damage": "add_damage",
        "add_heal": "add_heal",
        "increase_targets": "increase_targets",
        "additional_effect_instances": "additional_effect_instances",
        "increase_duration": "increase_duration",
        "custom": "custom",
    }
)
SPELL_SOURCE_MAP = {member.value: member.value for member in SpellSource}
SPELL_SOURCE_MAP.update(
    {
        "csv": SpellSource.SEED_JSON_BOOTSTRAP.value,
        "csv_import": SpellSource.SEED_JSON_BOOTSTRAP.value,
        "seed": SpellSource.SEED_JSON_BOOTSTRAP.value,
    }
)

DICE_EXPRESSION_RE = re.compile(
    r"^\s*(?:(\d*)d(\d+)|(\d+))\s*(?:([+-])\s*(\d+))?\s*$",
    re.IGNORECASE,
)

_CANONICAL_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9_]*[a-z0-9]$|^[a-z0-9]$")


def _normalize_canonical_key(value: str) -> str:
    text = value.strip()
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_text = nfkd.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_text.lower()).strip("_")
    slug = re.sub(r"_+", "_", slug)
    return slug
