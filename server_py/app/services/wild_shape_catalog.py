"""Wild Shape beast catalog — PHB 5e stat blocks for Druid transformation.

Each WildFormStats entry is keyed by canonical_key and referenced by
wild_shape_service.py when the player transforms. All values follow
PHB 2014 appendix A Monster statistics.

Druid CR restriction by level:
  Level 2–3  → max CR 1/4
  Level 4–7  → max CR 1/2
  Level 8–11 → max CR 1
  Level 12+  → max CR (level // 4)  [simplified; PHB caps are higher]

This catalog deliberately includes only the most-used PHB forms; more
can be added without touching the service layer.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class NaturalAttackDef:
    name: str
    name_pt: str
    attack_bonus: int
    damage_dice: str
    damage_bonus: int
    damage_type: str


@dataclass(frozen=True)
class WildFormStats:
    canonical_key: str
    display_name: str
    display_name_pt: str
    cr: str          # "0", "1/4", "1/2", "1"
    cr_numeric: float
    min_druid_level: int
    size: str        # "tiny", "small", "medium", "large"
    max_hp: int
    armor_class: int
    speed_meters: int
    str_score: int
    dex_score: int
    con_score: int
    int_score: int
    wis_score: int
    cha_score: int
    natural_attacks: list[NaturalAttackDef] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Beast catalog
# ---------------------------------------------------------------------------

_CATALOG: dict[str, WildFormStats] = {}


def _reg(form: WildFormStats) -> WildFormStats:
    _CATALOG[form.canonical_key] = form
    return form


# CR 0 ── Level 2+
CAT = _reg(WildFormStats(
    canonical_key="cat",
    display_name="Cat",
    display_name_pt="Gato",
    cr="0",
    cr_numeric=0.0,
    min_druid_level=2,
    size="tiny",
    max_hp=2,
    armor_class=12,
    speed_meters=12,
    str_score=3,
    dex_score=15,
    con_score=10,
    int_score=3,
    wis_score=12,
    cha_score=7,
    natural_attacks=[
        NaturalAttackDef(
            name="Claws",
            name_pt="Garras",
            attack_bonus=0,
            damage_dice="1",
            damage_bonus=0,
            damage_type="slashing",
        )
    ],
    tags=["beast", "cr0"],
))

# CR 1/4 ── Level 2+
WOLF = _reg(WildFormStats(
    canonical_key="wolf",
    display_name="Wolf",
    display_name_pt="Lobo",
    cr="1/4",
    cr_numeric=0.25,
    min_druid_level=2,
    size="medium",
    max_hp=11,
    armor_class=13,
    speed_meters=12,
    str_score=12,
    dex_score=15,
    con_score=12,
    int_score=3,
    wis_score=12,
    cha_score=6,
    natural_attacks=[
        NaturalAttackDef(
            name="Bite",
            name_pt="Mordida",
            attack_bonus=4,
            damage_dice="2d4",
            damage_bonus=2,
            damage_type="piercing",
        )
    ],
    tags=["beast", "cr1/4"],
))

# CR 1/2 ── Level 4+
BLACK_BEAR = _reg(WildFormStats(
    canonical_key="black_bear",
    display_name="Black Bear",
    display_name_pt="Urso Negro",
    cr="1/2",
    cr_numeric=0.5,
    min_druid_level=4,
    size="medium",
    max_hp=19,
    armor_class=11,
    speed_meters=12,
    str_score=15,
    dex_score=10,
    con_score=14,
    int_score=2,
    wis_score=12,
    cha_score=7,
    natural_attacks=[
        NaturalAttackDef(
            name="Bite",
            name_pt="Mordida",
            attack_bonus=3,
            damage_dice="1d6",
            damage_bonus=2,
            damage_type="piercing",
        ),
        NaturalAttackDef(
            name="Claws",
            name_pt="Garras",
            attack_bonus=3,
            damage_dice="2d6",
            damage_bonus=2,
            damage_type="slashing",
        ),
    ],
    tags=["beast", "cr1/2"],
))

CROCODILE = _reg(WildFormStats(
    canonical_key="crocodile",
    display_name="Crocodile",
    display_name_pt="Crocodilo",
    cr="1/2",
    cr_numeric=0.5,
    min_druid_level=4,
    size="large",
    max_hp=19,
    armor_class=12,
    speed_meters=9,
    str_score=15,
    dex_score=10,
    con_score=13,
    int_score=2,
    wis_score=10,
    cha_score=5,
    natural_attacks=[
        NaturalAttackDef(
            name="Bite",
            name_pt="Mordida",
            attack_bonus=4,
            damage_dice="1d10",
            damage_bonus=2,
            damage_type="piercing",
        )
    ],
    tags=["beast", "cr1/2"],
))

# CR 1 ── Level 8+
GIANT_SPIDER = _reg(WildFormStats(
    canonical_key="giant_spider",
    display_name="Giant Spider",
    display_name_pt="Aranha Gigante",
    cr="1",
    cr_numeric=1.0,
    min_druid_level=8,
    size="large",
    max_hp=26,
    armor_class=14,
    speed_meters=9,
    str_score=14,
    dex_score=16,
    con_score=12,
    int_score=2,
    wis_score=11,
    cha_score=4,
    natural_attacks=[
        NaturalAttackDef(
            name="Bite",
            name_pt="Mordida",
            attack_bonus=5,
            damage_dice="1d8",
            damage_bonus=3,
            damage_type="piercing",
        )
    ],
    tags=["beast", "cr1"],
))

BROWN_BEAR = _reg(WildFormStats(
    canonical_key="brown_bear",
    display_name="Brown Bear",
    display_name_pt="Urso Pardo",
    cr="1",
    cr_numeric=1.0,
    min_druid_level=8,
    size="large",
    max_hp=34,
    armor_class=11,
    speed_meters=12,
    str_score=19,
    dex_score=10,
    con_score=16,
    int_score=2,
    wis_score=13,
    cha_score=7,
    natural_attacks=[
        NaturalAttackDef(
            name="Bite",
            name_pt="Mordida",
            attack_bonus=5,
            damage_dice="1d8",
            damage_bonus=4,
            damage_type="piercing",
        ),
        NaturalAttackDef(
            name="Claws",
            name_pt="Garras",
            attack_bonus=5,
            damage_dice="2d6",
            damage_bonus=4,
            damage_type="slashing",
        ),
    ],
    tags=["beast", "cr1"],
))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_all_forms() -> list[WildFormStats]:
    """Return all registered forms sorted by CR then name."""
    return sorted(_CATALOG.values(), key=lambda f: (f.cr_numeric, f.canonical_key))


def get_form(canonical_key: str) -> WildFormStats | None:
    return _CATALOG.get(canonical_key)


def get_forms_for_level(druid_level: int) -> list[WildFormStats]:
    """Return forms available to a druid of the given level."""
    return [f for f in get_all_forms() if f.min_druid_level <= druid_level]
