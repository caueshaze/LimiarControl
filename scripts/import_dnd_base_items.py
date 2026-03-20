#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = REPO_ROOT / "server_py"
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from sqlmodel import Session, select

from app.db.session import engine
from app.models.base_item import (
    BaseItem,
    BaseItemAlias,
    BaseItemArmorCategory,
    BaseItemCostUnit,
    BaseItemKind,
    BaseItemWeaponCategory,
    BaseItemWeaponRangeType,
)
from app.models.campaign import SystemType

LOGGER = logging.getLogger("import_dnd_base_items")

WEAPONS_CSV_PATH = REPO_ROOT / "Base" / "DND5e_Armas_Database_Programador.csv"
ARMORS_CSV_PATH = REPO_ROOT / "Base" / "DND5e_Armaduras_Database.csv"
GEAR_JSON_PATH = REPO_ROOT / "Base" / "DND5e_Equipamentos.json"
SYSTEM = SystemType.DND5E

NAME_EN_BY_PT: dict[str, str] = {
    "Adaga": "Dagger",
    "Cajado": "Quarterstaff",
    "Clava": "Club",
    "Clava Grande": "Greatclub",
    "Foice": "Sickle",
    "Lança": "Spear",
    "Lança Curta (Dardo/Javelin)": "Javelin",
    "Maça": "Mace",
    "Machado de Mão": "Handaxe",
    "Martelo Leve": "Light Hammer",
    "Arco Curto": "Shortbow",
    "Atiradeira (Funda)": "Sling",
    "Besta Leve": "Light Crossbow",
    "Dardo": "Dart",
    "Alabarda": "Halberd",
    "Chicote": "Whip",
    "Cimitarra": "Scimitar",
    "Espada Curta": "Shortsword",
    "Espada Grande": "Greatsword",
    "Espada Longa": "Longsword",
    "Glaive": "Glaive",
    "Lança de Montaria": "Lance",
    "Machado de Batalha": "Battleaxe",
    "Machado Grande": "Greataxe",
    "Malho": "Maul",
    "Mangual": "Flail",
    "Manhã-Estrela": "Morningstar",
    "Martelo de Guerra": "Warhammer",
    "Picareta de Guerra": "War Pick",
    "Pique": "Pike",
    "Rapieira": "Rapier",
    "Tridente": "Trident",
    "Arco Longo": "Longbow",
    "Besta de Mão": "Hand Crossbow",
    "Besta Pesada": "Heavy Crossbow",
    "Rede": "Net",
    "Zarabatana": "Blowgun",
    "Pistola": "Pistol",
    "Mosquete": "Musket",
    "Acolchoada": "Padded",
    "Couro": "Leather",
    "Couro Batido": "Studded Leather",
    "Gibão de Peles": "Hide",
    "Camisão de Malha": "Chain Shirt",
    "Brunea": "Scale Mail",
    "Peitoral": "Breastplate",
    "Meia-Armadura": "Half Plate",
    "Cota de Anéis": "Ring Mail",
    "Cota de Malha": "Chain Mail",
    "Cota de Talas": "Splint",
    "Placas": "Plate",
    "Escudo": "Shield",
}

CANONICAL_KEY_OVERRIDES: dict[str, str] = {
    "Adaga": "dagger",
    "Cajado": "quarterstaff",
    "Clava": "club",
    "Clava Grande": "greatclub",
    "Foice": "sickle",
    "Lança": "spear",
    "Lança Curta (Dardo/Javelin)": "javelin",
    "Maça": "mace",
    "Machado de Mão": "handaxe",
    "Martelo Leve": "light_hammer",
    "Arco Curto": "shortbow",
    "Atiradeira (Funda)": "sling",
    "Besta Leve": "light_crossbow",
    "Dardo": "dart",
    "Alabarda": "halberd",
    "Chicote": "whip",
    "Cimitarra": "scimitar",
    "Espada Curta": "shortsword",
    "Espada Grande": "greatsword",
    "Espada Longa": "longsword",
    "Glaive": "glaive",
    "Lança de Montaria": "lance",
    "Machado de Batalha": "battleaxe",
    "Machado Grande": "greataxe",
    "Malho": "maul",
    "Mangual": "flail",
    "Manhã-Estrela": "morningstar",
    "Martelo de Guerra": "warhammer",
    "Picareta de Guerra": "war_pick",
    "Pique": "pike",
    "Rapieira": "rapier",
    "Tridente": "trident",
    "Arco Longo": "longbow",
    "Besta de Mão": "hand_crossbow",
    "Besta Pesada": "heavy_crossbow",
    "Rede": "net",
    "Zarabatana": "blowgun",
    "Pistola": "pistol",
    "Mosquete": "musket",
    "Acolchoada": "padded",
    "Couro": "leather",
    "Couro Batido": "studded_leather",
    "Gibão de Peles": "hide",
    "Camisão de Malha": "chain_shirt",
    "Brunea": "scale_mail",
    "Peitoral": "breastplate",
    "Meia-Armadura": "half_plate",
    "Cota de Anéis": "ring_mail",
    "Cota de Malha": "chain_mail",
    "Cota de Talas": "splint",
    "Placas": "plate",
    "Escudo": "shield",
}

DAMAGE_TYPE_BY_PT: dict[str, str] = {
    "contundente": "bludgeoning",
    "cortante": "slashing",
    "perfurante": "piercing",
}

PROPERTY_BY_PT: dict[str, str] = {
    "alcance": "reach",
    "arremesso": "thrown",
    "carregamento": "loading",
    "duas maos": "two-handed",
    "especial": "special",
    "fineza": "finesse",
    "lancavel": "thrown",
    "leve": "light",
    "municao": "ammunition",
    "pesada": "heavy",
    "versatil": "versatile",
}

WEAPON_CATEGORY_BY_PT: dict[str, BaseItemWeaponCategory] = {
    "simples": BaseItemWeaponCategory.SIMPLE,
    "marcial": BaseItemWeaponCategory.MARTIAL,
}

WEAPON_RANGE_TYPE_BY_PT: dict[str, BaseItemWeaponRangeType] = {
    "corpo a corpo": BaseItemWeaponRangeType.MELEE,
    "a distancia": BaseItemWeaponRangeType.RANGED,
}

ARMOR_CATEGORY_BY_PT: dict[str, BaseItemArmorCategory] = {
    "leve": BaseItemArmorCategory.LIGHT,
    "media": BaseItemArmorCategory.MEDIUM,
    "pesada": BaseItemArmorCategory.HEAVY,
    "escudo": BaseItemArmorCategory.SHIELD,
}

EXTRA_ALIASES_BY_CANONICAL_KEY: dict[str, list[tuple[str, str | None, str | None]]] = {
    "shield": [
        ("Wooden Shield", "en", "legacy"),
    ],
    "light_crossbow": [
        ("Crossbow, light", "en", "legacy"),
    ],
    "hand_crossbow": [
        ("Crossbow, hand", "en", "legacy"),
    ],
    "heavy_crossbow": [
        ("Crossbow, heavy", "en", "legacy"),
    ],
    "javelin": [
        ("Lança Curta", "pt-BR", "legacy"),
        ("Javelin", "en", "legacy"),
    ],
    "quarterstaff": [
        ("Staff", "en", "legacy"),
    ],
    "arcane_focus": [
        ("Foco Arcano", "pt-BR", "localized_name"),
    ],
    "druidic_focus": [
        ("Foco Druidico", "pt-BR", "localized_name"),
        ("Foco Druídico", "pt-BR", "localized_name"),
    ],
    "holy_symbol": [
        ("Holy symbol", "en", "legacy"),
        ("Holy Symbols", "en", "legacy"),
        ("Amulet", "en", "legacy"),
        ("Emblem", "en", "legacy"),
        ("Reliquary", "en", "legacy"),
        ("Simbolo Sagrado", "pt-BR", "localized_name"),
        ("Símbolo Sagrado", "pt-BR", "localized_name"),
    ],
    "component_pouch": [
        ("Bolsa de Componentes", "pt-BR", "localized_name"),
    ],
    "spellbook": [
        ("Grimorio", "pt-BR", "localized_name"),
        ("Grimório", "pt-BR", "localized_name"),
    ],
    "thieves_tools": [
        ("Thieves' tools", "en", "legacy"),
        ("Ferramentas de Ladrao", "pt-BR", "localized_name"),
        ("Ferramentas de Ladrão", "pt-BR", "localized_name"),
    ],
    "forgery_kit": [
        ("Forgery kit", "en", "legacy"),
        ("Kit de Falsificacao", "pt-BR", "localized_name"),
        ("Kit de Falsificação", "pt-BR", "localized_name"),
    ],
    "disguise_kit": [
        ("Kit de Disfarce", "pt-BR", "localized_name"),
    ],
    "artisans_tools": [
        ("Ferramentas de Artesao", "pt-BR", "localized_name"),
        ("Ferramentas de Artesão", "pt-BR", "localized_name"),
    ],
    "herbalism_kit": [
        ("Kit de Herbalismo", "pt-BR", "localized_name"),
    ],
    "gaming_set": [
        ("Jogo de Mesa", "pt-BR", "localized_name"),
    ],
    "musical_instrument": [
        ("Instrumento Musical", "pt-BR", "localized_name"),
    ],
    "arrow": [
        ("Arrows", "en", "legacy"),
        ("Flecha", "pt-BR", "localized_name"),
        ("Flechas", "pt-BR", "localized_name"),
    ],
    "crossbow_bolt": [
        ("Crossbow bolts", "en", "legacy"),
        ("Bolt", "en", "legacy"),
        ("Bolts", "en", "legacy"),
        ("Virote", "pt-BR", "localized_name"),
        ("Virotes", "pt-BR", "localized_name"),
    ],
    "case_crossbow_bolt": [
        ("Crossbow bolt case", "en", "legacy"),
        ("Estojo de Virotes", "pt-BR", "localized_name"),
    ],
    "quiver": [
        ("Aljava", "pt-BR", "localized_name"),
    ],
    "explorers_pack": [
        ("Mochila do Explorador", "pt-BR", "localized_name"),
    ],
    "dungeoneers_pack": [
        ("Mochila do Masmorrador", "pt-BR", "localized_name"),
    ],
    "burglars_pack": [
        ("Mochila do Ladrao", "pt-BR", "localized_name"),
        ("Mochila do Ladrão", "pt-BR", "localized_name"),
    ],
    "scholars_pack": [
        ("Mochila do Estudioso", "pt-BR", "localized_name"),
    ],
    "priests_pack": [
        ("Mochila do Sacerdote", "pt-BR", "localized_name"),
    ],
    "diplomats_pack": [
        ("Mochila do Diplomata", "pt-BR", "localized_name"),
    ],
    "entertainers_pack": [
        ("Mochila do Artista", "pt-BR", "localized_name"),
    ],
    "lute": [
        ("Alaude", "pt-BR", "localized_name"),
        ("Alaúde", "pt-BR", "localized_name"),
    ],
    "flute": [
        ("Flauta", "pt-BR", "localized_name"),
    ],
    "lyre": [
        ("Lira", "pt-BR", "localized_name"),
    ],
    "drum": [
        ("Tambor", "pt-BR", "localized_name"),
    ],
    "viol": [
        ("Viola", "pt-BR", "localized_name"),
    ],
    "pan_flute": [
        ("Flauta de Pa", "pt-BR", "localized_name"),
        ("Flauta de Pã", "pt-BR", "localized_name"),
    ],
    "fine_clothes": [
        ("Roupas Finas", "pt-BR", "localized_name"),
    ],
    "common_clothes": [
        ("Roupas Comuns", "pt-BR", "localized_name"),
    ],
    "travelers_clothes": [
        ("Roupas de Viagem", "pt-BR", "localized_name"),
    ],
    "scroll_case": [
        ("Estojo de Pergaminho", "pt-BR", "localized_name"),
    ],
    "winter_blanket": [
        ("Cobertor de Inverno", "pt-BR", "localized_name"),
    ],
    "shovel": [
        ("Pa", "pt-BR", "localized_name"),
        ("Pá", "pt-BR", "localized_name"),
    ],
    "iron_pot": [
        ("Panela de Ferro", "pt-BR", "localized_name"),
    ],
    "letter_of_introduction": [
        ("Carta de Introducao", "pt-BR", "localized_name"),
        ("Carta de Introdução", "pt-BR", "localized_name"),
    ],
    "crowbar": [
        ("Pe de Cabra", "pt-BR", "localized_name"),
        ("Pé de Cabra", "pt-BR", "localized_name"),
    ],
    "costume": [
        ("Fantasia", "pt-BR", "localized_name"),
    ],
    "prayer_book": [
        ("Livro de Orações", "pt-BR", "localized_name"),
        ("Livro de Oracoes", "pt-BR", "localized_name"),
    ],
}


@dataclass(frozen=True)
class AliasSeed:
    alias: str
    locale: str | None
    alias_type: str | None


@dataclass
class BaseItemSeed:
    canonical_key: str
    name_en: str
    name_pt: str
    description_pt: str | None
    item_kind: BaseItemKind
    source: str
    source_ref: str
    description_en: str | None = None
    aliases: list[AliasSeed] = field(default_factory=list)
    equipment_category: str | None = None
    cost_quantity: float | None = None
    cost_unit: BaseItemCostUnit | None = None
    weight: float | None = None
    weapon_category: BaseItemWeaponCategory | None = None
    weapon_range_type: BaseItemWeaponRangeType | None = None
    damage_dice: str | None = None
    damage_type: str | None = None
    range_normal: int | None = None
    range_long: int | None = None
    versatile_damage: str | None = None
    weapon_properties_json: list[str] | None = None
    armor_category: BaseItemArmorCategory | None = None
    armor_class_base: int | None = None
    dex_bonus_rule: str | None = None
    strength_requirement: int | None = None
    stealth_disadvantage: bool | None = None
    is_shield: bool = False


@dataclass(frozen=True)
class EssentialGearSpec:
    name_en: str
    name_pt: str
    item_kind: BaseItemKind
    equipment_category: str | None
    cost: str | None = None
    weight: float | None = None
    description_en: str | None = None
    description_pt: str | None = None
    aliases_en: tuple[str, ...] = ()
    aliases_pt: tuple[str, ...] = ()
    json_names: tuple[str, ...] = ()


GEAR_CANONICAL_KEY_OVERRIDES: dict[str, str] = {
    "Arcane Focus": "arcane_focus",
    "Druidic Focus": "druidic_focus",
    "Holy Symbol": "holy_symbol",
    "Component Pouch": "component_pouch",
    "Spellbook": "spellbook",
    "Thieves' Tools": "thieves_tools",
    "Forgery Kit": "forgery_kit",
    "Disguise Kit": "disguise_kit",
    "Artisan's Tools": "artisans_tools",
    "Herbalism Kit": "herbalism_kit",
    "Gaming Set": "gaming_set",
    "Musical Instrument": "musical_instrument",
    "Arrow": "arrow",
    "Crossbow bolt": "crossbow_bolt",
    "Case, crossbow bolt": "case_crossbow_bolt",
    "Quiver": "quiver",
    "Explorer's Pack": "explorers_pack",
    "Dungeoneer's Pack": "dungeoneers_pack",
    "Burglar's Pack": "burglars_pack",
    "Scholar's Pack": "scholars_pack",
    "Priest's Pack": "priests_pack",
    "Diplomat's Pack": "diplomats_pack",
    "Entertainer's Pack": "entertainers_pack",
    "Lute": "lute",
    "Flute": "flute",
    "Lyre": "lyre",
    "Drum": "drum",
    "Viol": "viol",
    "Pan Flute": "pan_flute",
    "Fine clothes": "fine_clothes",
    "Common clothes": "common_clothes",
    "Traveler's clothes": "travelers_clothes",
    "Scroll case": "scroll_case",
    "Winter blanket": "winter_blanket",
    "Shovel": "shovel",
    "Iron pot": "iron_pot",
    "Letter of introduction": "letter_of_introduction",
    "Crowbar": "crowbar",
    "Costume": "costume",
    "Prayer book": "prayer_book",
    "Incense": "incense",
    "Vestments": "vestments",
    "Dark common clothes with hood": "dark_common_clothes_with_hood",
    "Favor of an admirer": "favor_of_an_admirer",
    "Signet ring": "signet_ring",
    "Scroll of pedigree": "scroll_of_pedigree",
    "Hunting trap": "hunting_trap",
    "Animal trophy": "animal_trophy",
    "Bottle of black ink": "bottle_of_black_ink",
    "Quill": "quill",
    "Small knife": "small_knife",
    "Letter with unanswered question": "letter_with_unanswered_question",
    "Belaying pin": "belaying_pin",
    "Silk Rope": "silk_rope",
    "Lucky charm": "lucky_charm",
    "Insignia of rank": "insignia_of_rank",
    "Trophy from fallen enemy": "trophy_from_fallen_enemy",
    "Map of home city": "map_of_home_city",
    "Pet mouse": "pet_mouse",
    "Token from parent": "token_from_parent",
}


ESSENTIAL_GEAR_SPECS: tuple[EssentialGearSpec, ...] = (
    EssentialGearSpec(
        name_en="Arcane Focus",
        name_pt="Foco Arcano",
        item_kind=BaseItemKind.FOCUS,
        equipment_category="spellcasting_focus",
        cost="10 gp",
        description_en="Spellcasting focus used by arcane casters.",
        aliases_pt=("Foco Arcano",),
    ),
    EssentialGearSpec(
        name_en="Druidic Focus",
        name_pt="Foco Druídico",
        item_kind=BaseItemKind.FOCUS,
        equipment_category="spellcasting_focus",
        cost="1 gp",
        description_en="Spellcasting focus used by druids.",
        aliases_pt=("Foco Druídico", "Foco Druidico"),
    ),
    EssentialGearSpec(
        name_en="Holy Symbol",
        name_pt="Símbolo Sagrado",
        item_kind=BaseItemKind.FOCUS,
        equipment_category="spellcasting_focus",
        cost="5 gp",
        weight=1,
        description_en="Divine focus used by clerics and paladins.",
        aliases_en=("Holy symbol", "Holy Symbols", "Amulet", "Emblem", "Reliquary"),
        aliases_pt=("Símbolo Sagrado", "Simbolo Sagrado"),
        json_names=("Holy symbol",),
    ),
    EssentialGearSpec(
        name_en="Component Pouch",
        name_pt="Bolsa de Componentes",
        item_kind=BaseItemKind.GEAR,
        equipment_category="spellcasting_gear",
        cost="25 gp",
        weight=2,
        description_en="Small pouch filled with spellcasting material components.",
        aliases_pt=("Bolsa de Componentes",),
    ),
    EssentialGearSpec(
        name_en="Spellbook",
        name_pt="Grimório",
        item_kind=BaseItemKind.GEAR,
        equipment_category="book",
        cost="50 gp",
        weight=3,
        description_en="Wizard spellbook used to record arcane formulas.",
        aliases_pt=("Grimório", "Grimorio"),
    ),
    EssentialGearSpec(
        name_en="Thieves' Tools",
        name_pt="Ferramentas de Ladrão",
        item_kind=BaseItemKind.TOOL,
        equipment_category="tools",
        cost="25 gp",
        weight=1,
        description_en="Lockpicks and precision tools used by rogues.",
        aliases_en=("Thieves' tools",),
        aliases_pt=("Ferramentas de Ladrão", "Ferramentas de Ladrao"),
    ),
    EssentialGearSpec(
        name_en="Forgery Kit",
        name_pt="Kit de Falsificação",
        item_kind=BaseItemKind.TOOL,
        equipment_category="tools",
        cost="15 gp",
        weight=5,
        description_en="Tools and materials used to create false documents.",
        aliases_en=("Forgery kit", "Con tools"),
        aliases_pt=("Kit de Falsificação", "Kit de Falsificacao"),
    ),
    EssentialGearSpec(
        name_en="Disguise Kit",
        name_pt="Kit de Disfarce",
        item_kind=BaseItemKind.TOOL,
        equipment_category="tools",
        cost="25 gp",
        weight=3,
        description_en="Makeup, costumes, and props for disguises.",
        aliases_pt=("Kit de Disfarce",),
    ),
    EssentialGearSpec(
        name_en="Artisan's Tools",
        name_pt="Ferramentas de Artesão",
        item_kind=BaseItemKind.TOOL,
        equipment_category="tools",
        cost="5 gp",
        weight=5,
        description_en="General trade tools for a chosen craft.",
        aliases_pt=("Ferramentas de Artesão", "Ferramentas de Artesao"),
    ),
    EssentialGearSpec(
        name_en="Herbalism Kit",
        name_pt="Kit de Herbalismo",
        item_kind=BaseItemKind.TOOL,
        equipment_category="tools",
        cost="5 gp",
        weight=3,
        description_en="Pouches and clippers used to gather and prepare herbs.",
        aliases_pt=("Kit de Herbalismo",),
    ),
    EssentialGearSpec(
        name_en="Gaming Set",
        name_pt="Jogo de Mesa",
        item_kind=BaseItemKind.TOOL,
        equipment_category="gaming_set",
        description_en="Generic gaming set used in character starting equipment.",
        aliases_pt=("Jogo de Mesa",),
    ),
    EssentialGearSpec(
        name_en="Musical Instrument",
        name_pt="Instrumento Musical",
        item_kind=BaseItemKind.TOOL,
        equipment_category="musical_instrument",
        description_en="Generic musical instrument used in character starting equipment.",
        aliases_pt=("Instrumento Musical",),
    ),
    EssentialGearSpec(
        name_en="Lute",
        name_pt="Alaúde",
        item_kind=BaseItemKind.TOOL,
        equipment_category="musical_instrument",
        cost="35 gp",
        weight=2,
        description_en="String instrument commonly carried by bards.",
        aliases_pt=("Alaúde", "Alaude"),
    ),
    EssentialGearSpec(
        name_en="Flute",
        name_pt="Flauta",
        item_kind=BaseItemKind.TOOL,
        equipment_category="musical_instrument",
        cost="2 gp",
        weight=1,
        description_en="Woodwind instrument used as a simple musical focus.",
        aliases_pt=("Flauta",),
    ),
    EssentialGearSpec(
        name_en="Lyre",
        name_pt="Lira",
        item_kind=BaseItemKind.TOOL,
        equipment_category="musical_instrument",
        cost="30 gp",
        weight=2,
        description_en="String instrument used by wandering performers.",
        aliases_pt=("Lira",),
    ),
    EssentialGearSpec(
        name_en="Drum",
        name_pt="Tambor",
        item_kind=BaseItemKind.TOOL,
        equipment_category="musical_instrument",
        cost="6 gp",
        weight=3,
        description_en="Percussion instrument carried by traveling performers.",
        aliases_pt=("Tambor",),
    ),
    EssentialGearSpec(
        name_en="Viol",
        name_pt="Viola",
        item_kind=BaseItemKind.TOOL,
        equipment_category="musical_instrument",
        cost="30 gp",
        weight=1,
        description_en="Bowed string instrument suited for formal performances.",
        aliases_pt=("Viola",),
    ),
    EssentialGearSpec(
        name_en="Pan Flute",
        name_pt="Flauta de Pã",
        item_kind=BaseItemKind.TOOL,
        equipment_category="musical_instrument",
        cost="12 gp",
        weight=2,
        description_en="Set of tuned reeds bound together as a wind instrument.",
        aliases_pt=("Flauta de Pã", "Flauta de Pa"),
    ),
    EssentialGearSpec(
        name_en="Arrow",
        name_pt="Flecha",
        item_kind=BaseItemKind.AMMO,
        equipment_category="ammunition",
        cost="0.05 gp",
        weight=0.05,
        description_en="Standard ammunition for bows.",
        aliases_en=("Arrows",),
        aliases_pt=("Flecha", "Flechas"),
    ),
    EssentialGearSpec(
        name_en="Crossbow bolt",
        name_pt="Virote",
        item_kind=BaseItemKind.AMMO,
        equipment_category="ammunition",
        cost="0.05 gp",
        weight=0.075,
        description_en="Ammunition for hand, light, and heavy crossbows.",
        aliases_en=("Crossbow bolts", "Bolt", "Bolts"),
        aliases_pt=("Virote", "Virotes"),
    ),
    EssentialGearSpec(
        name_en="Case, crossbow bolt",
        name_pt="Estojo de Virotes",
        item_kind=BaseItemKind.GEAR,
        equipment_category="container",
        cost="1 gp",
        weight=1,
        description_en="Case used to hold crossbow bolts.",
        aliases_en=("Crossbow bolt case",),
        aliases_pt=("Estojo de Virotes",),
    ),
    EssentialGearSpec(
        name_en="Quiver",
        name_pt="Aljava",
        item_kind=BaseItemKind.GEAR,
        equipment_category="container",
        cost="1 gp",
        weight=1,
        description_en="Case used to carry arrows or bolts.",
        aliases_pt=("Aljava",),
    ),
    EssentialGearSpec(
        name_en="Explorer's Pack",
        name_pt="Mochila do Explorador",
        item_kind=BaseItemKind.PACK,
        equipment_category="adventuring_pack",
        cost="10 gp",
        weight=59,
        description_en="General-purpose pack for outdoor travel and dungeon delving.",
        aliases_pt=("Mochila do Explorador",),
    ),
    EssentialGearSpec(
        name_en="Dungeoneer's Pack",
        name_pt="Mochila do Masmorrador",
        item_kind=BaseItemKind.PACK,
        equipment_category="adventuring_pack",
        cost="12 gp",
        weight=61.5,
        description_en="Utility pack suited for exploration in enclosed spaces.",
        aliases_pt=("Mochila do Masmorrador",),
    ),
    EssentialGearSpec(
        name_en="Burglar's Pack",
        name_pt="Mochila do Ladrão",
        item_kind=BaseItemKind.PACK,
        equipment_category="adventuring_pack",
        cost="16 gp",
        weight=46.5,
        description_en="Pack with stealth and infiltration essentials.",
        aliases_pt=("Mochila do Ladrão", "Mochila do Ladrao"),
    ),
    EssentialGearSpec(
        name_en="Scholar's Pack",
        name_pt="Mochila do Estudioso",
        item_kind=BaseItemKind.PACK,
        equipment_category="adventuring_pack",
        cost="40 gp",
        weight=10,
        description_en="Study pack with writing, reference, and research essentials.",
        aliases_pt=("Mochila do Estudioso",),
    ),
    EssentialGearSpec(
        name_en="Priest's Pack",
        name_pt="Mochila do Sacerdote",
        item_kind=BaseItemKind.PACK,
        equipment_category="adventuring_pack",
        cost="19 gp",
        weight=24,
        description_en="Pack carrying basic devotional and travel supplies.",
        aliases_pt=("Mochila do Sacerdote",),
    ),
    EssentialGearSpec(
        name_en="Diplomat's Pack",
        name_pt="Mochila do Diplomata",
        item_kind=BaseItemKind.PACK,
        equipment_category="adventuring_pack",
        cost="39 gp",
        weight=39,
        description_en="Formal pack with supplies suited for noble travel.",
        aliases_pt=("Mochila do Diplomata",),
    ),
    EssentialGearSpec(
        name_en="Entertainer's Pack",
        name_pt="Mochila do Artista",
        item_kind=BaseItemKind.PACK,
        equipment_category="adventuring_pack",
        cost="40 gp",
        weight=38,
        description_en="Pack with practical supplies for performers on the road.",
        aliases_pt=("Mochila do Artista",),
    ),
    EssentialGearSpec(
        name_en="Fine clothes",
        name_pt="Roupas Finas",
        item_kind=BaseItemKind.GEAR,
        equipment_category="clothing",
        cost="15 gp",
        weight=6,
        description_en="Formal clothing meant for social occasions.",
        aliases_pt=("Roupas Finas",),
    ),
    EssentialGearSpec(
        name_en="Common clothes",
        name_pt="Roupas Comuns",
        item_kind=BaseItemKind.GEAR,
        equipment_category="clothing",
        cost="0.5 gp",
        weight=3,
        description_en="Simple everyday clothing.",
        aliases_pt=("Roupas Comuns",),
    ),
    EssentialGearSpec(
        name_en="Traveler's clothes",
        name_pt="Roupas de Viagem",
        item_kind=BaseItemKind.GEAR,
        equipment_category="clothing",
        cost="2 gp",
        weight=4,
        description_en="Sturdy clothes suited for long journeys.",
        aliases_pt=("Roupas de Viagem",),
    ),
    EssentialGearSpec(
        name_en="Scroll case",
        name_pt="Estojo de Pergaminho",
        item_kind=BaseItemKind.GEAR,
        equipment_category="container",
        cost="1 gp",
        weight=0.5,
        description_en="Protective case for maps, scrolls, or documents.",
        aliases_pt=("Estojo de Pergaminho",),
    ),
    EssentialGearSpec(
        name_en="Winter blanket",
        name_pt="Cobertor de Inverno",
        item_kind=BaseItemKind.GEAR,
        equipment_category="supplies",
        cost="0.5 gp",
        weight=3,
        description_en="Thick blanket for cold weather travel.",
        aliases_pt=("Cobertor de Inverno",),
    ),
    EssentialGearSpec(
        name_en="Shovel",
        name_pt="Pá",
        item_kind=BaseItemKind.GEAR,
        equipment_category="tools",
        cost="2 gp",
        weight=5,
        description_en="Simple digging tool.",
        aliases_pt=("Pá", "Pa"),
    ),
    EssentialGearSpec(
        name_en="Iron pot",
        name_pt="Panela de Ferro",
        item_kind=BaseItemKind.GEAR,
        equipment_category="supplies",
        cost="2 gp",
        weight=10,
        description_en="Heavy cooking pot for camp meals.",
        aliases_pt=("Panela de Ferro",),
    ),
    EssentialGearSpec(
        name_en="Letter of introduction",
        name_pt="Carta de Introdução",
        item_kind=BaseItemKind.GEAR,
        equipment_category="document",
        description_en="Letter used to establish identity or recommendation.",
        aliases_pt=("Carta de Introdução", "Carta de Introducao"),
    ),
    EssentialGearSpec(
        name_en="Crowbar",
        name_pt="Pé de Cabra",
        item_kind=BaseItemKind.GEAR,
        equipment_category="tools",
        cost="2 gp",
        weight=5,
        description_en="Leverage bar commonly used to pry open doors and crates.",
        aliases_pt=("Pé de Cabra", "Pe de Cabra"),
    ),
    EssentialGearSpec(
        name_en="Costume",
        name_pt="Fantasia",
        item_kind=BaseItemKind.GEAR,
        equipment_category="clothing",
        cost="5 gp",
        weight=4,
        description_en="Stage costume or disguise apparel used by performers.",
        aliases_pt=("Fantasia",),
    ),
    EssentialGearSpec(
        name_en="Prayer book",
        name_pt="Livro de Orações",
        item_kind=BaseItemKind.GEAR,
        equipment_category="book",
        description_en="Devotional book used in religious practice.",
        aliases_pt=("Livro de Orações", "Livro de Oracoes"),
    ),
    EssentialGearSpec(
        name_en="Incense",
        name_pt="Incenso",
        item_kind=BaseItemKind.GEAR,
        equipment_category="consumable_supply",
        description_en="Small incense sticks used in rituals and offerings.",
        aliases_en=("5 sticks of incense",),
        aliases_pt=("Incenso",),
    ),
    EssentialGearSpec(
        name_en="Vestments",
        name_pt="Vestes Litúrgicas",
        item_kind=BaseItemKind.GEAR,
        equipment_category="clothing",
        description_en="Ceremonial religious clothing.",
        aliases_pt=("Vestes Litúrgicas", "Vestes Liturgicas"),
    ),
    EssentialGearSpec(
        name_en="Dark common clothes with hood",
        name_pt="Roupas Comuns Escuras com Capuz",
        item_kind=BaseItemKind.GEAR,
        equipment_category="clothing",
        description_en="Dark common clothes tailored for keeping a low profile.",
        aliases_pt=("Roupas Comuns Escuras com Capuz",),
    ),
    EssentialGearSpec(
        name_en="Favor of an admirer",
        name_pt="Lembrança de um Admirador",
        item_kind=BaseItemKind.GEAR,
        equipment_category="memento",
        description_en="A token of affection kept as a sentimental keepsake.",
        aliases_pt=("Lembrança de um Admirador", "Lembranca de um Admirador"),
    ),
    EssentialGearSpec(
        name_en="Signet ring",
        name_pt="Anel de Sinete",
        item_kind=BaseItemKind.GEAR,
        equipment_category="jewelry",
        description_en="Ring bearing a family or institutional seal.",
        aliases_pt=("Anel de Sinete",),
    ),
    EssentialGearSpec(
        name_en="Scroll of pedigree",
        name_pt="Pergaminho de Linhagem",
        item_kind=BaseItemKind.GEAR,
        equipment_category="document",
        description_en="Official record attesting to lineage or noble standing.",
        aliases_pt=("Pergaminho de Linhagem",),
    ),
    EssentialGearSpec(
        name_en="Hunting trap",
        name_pt="Armadilha de Caça",
        item_kind=BaseItemKind.GEAR,
        equipment_category="tools",
        description_en="Steel trap used to catch or restrain prey.",
        aliases_pt=("Armadilha de Caça", "Armadilha de Caca"),
    ),
    EssentialGearSpec(
        name_en="Animal trophy",
        name_pt="Troféu Animal",
        item_kind=BaseItemKind.GEAR,
        equipment_category="trophy",
        description_en="Keepsake crafted from an animal or monster.",
        aliases_pt=("Troféu Animal", "Trofeu Animal"),
    ),
    EssentialGearSpec(
        name_en="Bottle of black ink",
        name_pt="Frasco de Tinta Preta",
        item_kind=BaseItemKind.GEAR,
        equipment_category="writing_supply",
        description_en="Bottle of dark ink used for correspondence and study.",
        aliases_pt=("Frasco de Tinta Preta",),
    ),
    EssentialGearSpec(
        name_en="Quill",
        name_pt="Pena de Escrita",
        item_kind=BaseItemKind.GEAR,
        equipment_category="writing_supply",
        description_en="Writing quill for use with ink and parchment.",
        aliases_pt=("Pena de Escrita",),
    ),
    EssentialGearSpec(
        name_en="Small knife",
        name_pt="Faca Pequena",
        item_kind=BaseItemKind.GEAR,
        equipment_category="utility_tool",
        description_en="Utility knife meant for small, non-martial tasks.",
        aliases_pt=("Faca Pequena",),
    ),
    EssentialGearSpec(
        name_en="Letter with unanswered question",
        name_pt="Carta com Pergunta sem Resposta",
        item_kind=BaseItemKind.GEAR,
        equipment_category="document",
        description_en="A letter whose unanswered question still lingers.",
        aliases_pt=("Carta com Pergunta sem Resposta",),
    ),
    EssentialGearSpec(
        name_en="Belaying pin",
        name_pt="Pino de Amarração",
        item_kind=BaseItemKind.GEAR,
        equipment_category="sailing_gear",
        description_en="Wooden pin used aboard ships to secure rigging.",
        aliases_pt=("Pino de Amarração", "Pino de Amarracao"),
    ),
    EssentialGearSpec(
        name_en="Silk Rope",
        name_pt="Corda de Seda",
        item_kind=BaseItemKind.GEAR,
        equipment_category="rope",
        cost="10 gp",
        weight=5,
        description_en="Fine but sturdy silk rope used for climbing and travel.",
        aliases_en=("50 feet of silk rope",),
        aliases_pt=("Corda de Seda",),
    ),
    EssentialGearSpec(
        name_en="Lucky charm",
        name_pt="Amuleto da Sorte",
        item_kind=BaseItemKind.GEAR,
        equipment_category="memento",
        description_en="Simple token carried for luck or protection.",
        aliases_pt=("Amuleto da Sorte",),
    ),
    EssentialGearSpec(
        name_en="Insignia of rank",
        name_pt="Insígnia de Patente",
        item_kind=BaseItemKind.GEAR,
        equipment_category="insignia",
        description_en="Marker of military status and service.",
        aliases_pt=("Insígnia de Patente", "Insignia de Patente"),
    ),
    EssentialGearSpec(
        name_en="Trophy from fallen enemy",
        name_pt="Troféu de Inimigo Derrotado",
        item_kind=BaseItemKind.GEAR,
        equipment_category="trophy",
        description_en="Keepsake taken from a defeated foe.",
        aliases_pt=("Troféu de Inimigo Derrotado", "Trofeu de Inimigo Derrotado"),
    ),
    EssentialGearSpec(
        name_en="Map of home city",
        name_pt="Mapa da Cidade Natal",
        item_kind=BaseItemKind.GEAR,
        equipment_category="document",
        description_en="Map marking familiar streets, hideouts, and shortcuts.",
        aliases_pt=("Mapa da Cidade Natal",),
    ),
    EssentialGearSpec(
        name_en="Pet mouse",
        name_pt="Rato de Estimação",
        item_kind=BaseItemKind.GEAR,
        equipment_category="pet",
        description_en="Tiny companion kept close for comfort and luck.",
        aliases_pt=("Rato de Estimação", "Rato de Estimacao"),
    ),
    EssentialGearSpec(
        name_en="Token from parent",
        name_pt="Lembrança dos Pais",
        item_kind=BaseItemKind.GEAR,
        equipment_category="memento",
        description_en="Sentimental token carried from one's parents.",
        aliases_pt=("Lembrança dos Pais", "Lembranca dos Pais"),
    ),
)


def normalize_lookup(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", ascii_only.lower()).strip()


def snake_case(value: str) -> str:
    return normalize_lookup(value).replace(" ", "_")


def load_weapons_csv() -> list[dict[str, str]]:
    return load_csv(WEAPONS_CSV_PATH)


def load_armors_csv() -> list[dict[str, str]]:
    return load_csv(ARMORS_CSV_PATH)


def load_gear_json() -> dict[str, dict[str, object]]:
    if not GEAR_JSON_PATH.exists():
        LOGGER.warning(
            "Gear JSON not found at %s. Falling back to synthetic essential gear seeds.",
            GEAR_JSON_PATH,
        )
        return {}

    data = json.loads(GEAR_JSON_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        LOGGER.warning("Unexpected gear JSON payload, expected a list: %s", GEAR_JSON_PATH)
        return {}

    entries_by_key: dict[str, dict[str, object]] = {}
    for raw_entry in data:
        if not isinstance(raw_entry, dict):
            continue
        name = str(raw_entry.get("name", "")).strip()
        if not name:
            continue
        entries_by_key.setdefault(normalize_lookup(name), raw_entry)
    return entries_by_key


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def parse_cost(raw_value: str) -> tuple[float | None, BaseItemCostUnit | None]:
    raw = raw_value.strip()
    if not raw or raw == "-":
        return None, None
    match = re.match(r"^\s*([\d.]+)\s*(cp|sp|ep|gp|pp)\s*$", raw, flags=re.IGNORECASE)
    if not match:
        LOGGER.warning("Unrecognized cost format: %s", raw_value)
        return None, None
    quantity = float(match.group(1))
    unit = BaseItemCostUnit(match.group(2).lower())
    return quantity, unit


def parse_weight(raw_value: str) -> float | None:
    raw = raw_value.strip()
    if not raw or raw == "-":
        return None
    match = re.search(r"[\d.]+", raw)
    if not match:
        LOGGER.warning("Unrecognized weight format: %s", raw_value)
        return None
    return float(match.group(0))


def parse_json_cost(raw_value: object) -> tuple[float | None, BaseItemCostUnit | None]:
    if not isinstance(raw_value, dict):
        return None, None

    quantity = raw_value.get("quantity")
    unit = raw_value.get("unit")
    if not isinstance(quantity, (int, float)) or not isinstance(unit, str):
        return None, None

    normalized_unit = unit.strip().lower()
    if normalized_unit not in {"cp", "sp", "ep", "gp", "pp"}:
        LOGGER.warning("Unrecognized JSON cost unit: %s", unit)
        return None, None

    return float(quantity), BaseItemCostUnit(normalized_unit)


def parse_json_weight(raw_value: object) -> float | None:
    if isinstance(raw_value, (int, float)):
        return float(raw_value)
    return None


def normalize_json_description(raw_value: object) -> str | None:
    if isinstance(raw_value, list):
        parts = [str(part).strip() for part in raw_value if str(part).strip()]
        return " ".join(parts) or None
    if isinstance(raw_value, str):
        return raw_value.strip() or None
    return None


def parse_int_value(raw_value: str) -> int | None:
    raw = raw_value.strip()
    if not raw or raw in {"-", "N/A"}:
        return None
    try:
        return int(float(raw))
    except ValueError:
        LOGGER.warning("Unrecognized integer format: %s", raw_value)
        return None


def parse_damage_type(raw_value: str) -> str | None:
    raw = raw_value.strip()
    if not raw or raw == "-":
        return None
    mapped = DAMAGE_TYPE_BY_PT.get(normalize_lookup(raw))
    if mapped:
        return mapped
    LOGGER.warning("Unknown damage type, using fallback token: %s", raw_value)
    return snake_case(raw)


def parse_properties(raw_value: str) -> list[str]:
    raw = raw_value.strip()
    if not raw or raw == "-":
        return []
    normalized_properties: list[str] = []
    seen: set[str] = set()
    for part in raw.split(","):
        candidate = part.strip()
        if not candidate:
            continue
        property_key = PROPERTY_BY_PT.get(normalize_lookup(candidate))
        if not property_key:
            property_key = snake_case(candidate)
            LOGGER.warning("Unknown weapon property, using fallback token: %s", candidate)
        if property_key in seen:
            continue
        seen.add(property_key)
        normalized_properties.append(property_key)
    return normalized_properties


def parse_dex_bonus_rule(raw_value: str) -> str | None:
    raw = raw_value.strip()
    normalized = normalize_lookup(raw)
    if not raw or normalized in {"ilimitado"}:
        return "full"
    if normalized in {"n a", "na", "0"}:
        return "none"
    if normalized == "2":
        return "max_2"
    LOGGER.warning("Unknown dex bonus rule value: %s", raw_value)
    return None


def resolve_name_en(name_pt: str) -> str | None:
    translated = NAME_EN_BY_PT.get(name_pt)
    if translated:
        return translated
    LOGGER.warning("Missing English translation for: %s", name_pt)
    return None


def resolve_canonical_key(name_pt: str, name_en: str) -> str:
    if name_pt in CANONICAL_KEY_OVERRIDES:
        return CANONICAL_KEY_OVERRIDES[name_pt]
    return snake_case(name_en)


def resolve_gear_name_en(
    spec: EssentialGearSpec,
    raw_entry: dict[str, object] | None,
) -> str | None:
    raw_name = str(raw_entry.get("name", "")).strip() if raw_entry else ""
    if spec.name_en:
        return spec.name_en
    if raw_name:
        return raw_name
    LOGGER.warning("Missing English name for gear seed: %s", spec)
    return None


def resolve_gear_name_pt(spec: EssentialGearSpec) -> str:
    return spec.name_pt or spec.name_en


def resolve_gear_canonical_key(name_en: str) -> str:
    return GEAR_CANONICAL_KEY_OVERRIDES.get(name_en, snake_case(name_en))


def build_aliases(
    *,
    canonical_key: str,
    name_en: str,
    name_pt: str,
    original_name: str,
) -> list[AliasSeed]:
    aliases: list[AliasSeed] = [
        AliasSeed(alias=name_en, locale="en", alias_type="primary"),
        AliasSeed(alias=name_pt, locale="pt-BR", alias_type="primary"),
    ]
    if original_name != name_pt:
        aliases.append(
            AliasSeed(alias=original_name, locale="pt-BR", alias_type="source")
        )
    for alias, locale, alias_type in EXTRA_ALIASES_BY_CANONICAL_KEY.get(
        canonical_key,
        [],
    ):
        aliases.append(AliasSeed(alias=alias, locale=locale, alias_type=alias_type))
    return dedupe_aliases(aliases)


def build_gear_aliases(
    *,
    spec: EssentialGearSpec,
    canonical_key: str,
    original_name: str,
) -> list[AliasSeed]:
    aliases: list[AliasSeed] = [
        AliasSeed(alias=spec.name_en, locale="en", alias_type="primary"),
        AliasSeed(alias=resolve_gear_name_pt(spec), locale="pt-BR", alias_type="primary"),
    ]

    if original_name and normalize_lookup(original_name) != normalize_lookup(spec.name_en):
        aliases.append(AliasSeed(alias=original_name, locale="en", alias_type="source"))

    for alias in spec.aliases_en:
        aliases.append(AliasSeed(alias=alias, locale="en", alias_type="legacy"))
    for alias in spec.aliases_pt:
        aliases.append(AliasSeed(alias=alias, locale="pt-BR", alias_type="localized_name"))

    for alias, locale, alias_type in EXTRA_ALIASES_BY_CANONICAL_KEY.get(canonical_key, []):
        aliases.append(AliasSeed(alias=alias, locale=locale, alias_type=alias_type))

    return dedupe_aliases(aliases)


def dedupe_aliases(aliases: list[AliasSeed]) -> list[AliasSeed]:
    deduped: list[AliasSeed] = []
    seen: set[str] = set()
    for entry in aliases:
        alias_key = normalize_lookup(entry.alias)
        if not alias_key or alias_key in seen:
            continue
        seen.add(alias_key)
        deduped.append(entry)
    return deduped


def normalize_weapon_row(row: dict[str, str]) -> BaseItemSeed | None:
    name_pt = row["Nome"].strip()
    name_en = resolve_name_en(name_pt)
    if not name_en:
        LOGGER.warning("Skipping weapon without translation: %s", name_pt)
        return None

    weapon_category = WEAPON_CATEGORY_BY_PT.get(normalize_lookup(row["Categoria"]))
    if not weapon_category:
        LOGGER.warning("Skipping weapon with unknown category: %s", name_pt)
        return None

    weapon_range_type = WEAPON_RANGE_TYPE_BY_PT.get(normalize_lookup(row["Tipo"]))
    if not weapon_range_type:
        LOGGER.warning("Skipping weapon with unknown range type: %s", name_pt)
        return None

    canonical_key = resolve_canonical_key(name_pt, name_en)
    cost_quantity, cost_unit = parse_cost(row["Custo"])

    return BaseItemSeed(
        canonical_key=canonical_key,
        name_en=name_en,
        name_pt=name_pt,
        description_pt=row["Descrição curta"].strip() or None,
        item_kind=BaseItemKind.WEAPON,
        source=WEAPONS_CSV_PATH.name,
        source_ref=name_pt,
        aliases=build_aliases(
            canonical_key=canonical_key,
            name_en=name_en,
            name_pt=name_pt,
            original_name=row["Nome"].strip(),
        ),
        cost_quantity=cost_quantity,
        cost_unit=cost_unit,
        weight=parse_weight(row["Peso"]),
        weapon_category=weapon_category,
        weapon_range_type=weapon_range_type,
        damage_dice=(row["Dano"].strip() or None) if row["Dano"].strip() != "-" else None,
        damage_type=parse_damage_type(row["Tipo de dano"]),
        range_normal=parse_int_value(row["Alcance normal"]),
        range_long=parse_int_value(row["Alcance máximo"]),
        versatile_damage=(
            row["Dano versátil"].strip() or None
            if row["Dano versátil"].strip() != "-"
            else None
        ),
        weapon_properties_json=parse_properties(row["Propriedades"]),
    )


def normalize_armor_row(row: dict[str, str]) -> BaseItemSeed | None:
    name_pt = row["Nome"].strip()
    name_en = resolve_name_en(name_pt)
    if not name_en:
        LOGGER.warning("Skipping armor without translation: %s", name_pt)
        return None

    armor_category = ARMOR_CATEGORY_BY_PT.get(normalize_lookup(row["Categoria"]))
    if not armor_category:
        LOGGER.warning("Skipping armor with unknown category: %s", name_pt)
        return None

    canonical_key = resolve_canonical_key(name_pt, name_en)
    cost_quantity, cost_unit = parse_cost(row["Custo"])
    strength_requirement = parse_int_value(row["Requisito de FOR"])
    if strength_requirement == 0:
        strength_requirement = None

    return BaseItemSeed(
        canonical_key=canonical_key,
        name_en=name_en,
        name_pt=name_pt,
        description_pt=row["Descrição"].strip() or None,
        item_kind=BaseItemKind.ARMOR,
        source=ARMORS_CSV_PATH.name,
        source_ref=name_pt,
        aliases=build_aliases(
            canonical_key=canonical_key,
            name_en=name_en,
            name_pt=name_pt,
            original_name=row["Nome"].strip(),
        ),
        cost_quantity=cost_quantity,
        cost_unit=cost_unit,
        weight=parse_weight(row["Peso"]),
        armor_category=armor_category,
        armor_class_base=parse_int_value(row["CA base"]),
        dex_bonus_rule=parse_dex_bonus_rule(row["Mod DEX máximo"]),
        strength_requirement=strength_requirement,
        stealth_disadvantage=normalize_lookup(row["Desvantagem em furtividade"]) == "sim",
        is_shield=armor_category == BaseItemArmorCategory.SHIELD,
    )


def find_gear_source_entry(
    spec: EssentialGearSpec,
    gear_entries_by_key: dict[str, dict[str, object]],
) -> dict[str, object] | None:
    candidates = [
        spec.name_en,
        *spec.json_names,
        *spec.aliases_en,
    ]
    for candidate in candidates:
        raw_entry = gear_entries_by_key.get(normalize_lookup(candidate))
        if raw_entry:
            return raw_entry
    return None


def normalize_gear_item(
    spec: EssentialGearSpec,
    gear_entries_by_key: dict[str, dict[str, object]],
) -> BaseItemSeed | None:
    raw_entry = find_gear_source_entry(spec, gear_entries_by_key)
    source = GEAR_JSON_PATH.name if raw_entry else "synthetic_import"
    source_ref = str(raw_entry.get("name", "")).strip() if raw_entry else spec.name_en

    if raw_entry:
        cost_quantity, cost_unit = parse_json_cost(raw_entry.get("cost"))
        if cost_quantity is None and spec.cost:
            cost_quantity, cost_unit = parse_cost(spec.cost)
        weight = parse_json_weight(raw_entry.get("weight"))
        if weight is None:
            weight = spec.weight
        description_en = normalize_json_description(raw_entry.get("desc")) or spec.description_en
    else:
        LOGGER.warning(
            "Essential gear not found in source dataset, using synthetic seed: %s",
            spec.name_en,
        )
        cost_quantity, cost_unit = parse_cost(spec.cost) if spec.cost else (None, None)
        weight = spec.weight
        description_en = spec.description_en

    name_en = resolve_gear_name_en(spec, raw_entry)
    if not name_en:
        LOGGER.warning("Skipping gear without English name: %s", spec)
        return None

    name_pt = resolve_gear_name_pt(spec)
    canonical_key = resolve_gear_canonical_key(name_en)

    return BaseItemSeed(
        canonical_key=canonical_key,
        name_en=name_en,
        name_pt=name_pt,
        description_en=description_en,
        description_pt=spec.description_pt,
        item_kind=spec.item_kind,
        source=source,
        source_ref=source_ref,
        aliases=build_gear_aliases(
            spec=spec,
            canonical_key=canonical_key,
            original_name=source_ref,
        ),
        equipment_category=spec.equipment_category,
        cost_quantity=cost_quantity,
        cost_unit=cost_unit,
        weight=weight,
    )


def apply_seed_to_item(item: BaseItem, seed: BaseItemSeed) -> None:
    item.system = SYSTEM
    item.canonical_key = seed.canonical_key
    item.name_en = seed.name_en
    item.name_pt = seed.name_pt
    item.description_en = seed.description_en
    item.description_pt = seed.description_pt
    item.item_kind = seed.item_kind
    item.equipment_category = seed.equipment_category
    item.cost_quantity = seed.cost_quantity
    item.cost_unit = seed.cost_unit
    item.weight = seed.weight
    item.weapon_category = seed.weapon_category
    item.weapon_range_type = seed.weapon_range_type
    item.damage_dice = seed.damage_dice
    item.damage_type = seed.damage_type
    item.range_normal = seed.range_normal
    item.range_long = seed.range_long
    item.versatile_damage = seed.versatile_damage
    item.weapon_properties_json = seed.weapon_properties_json
    item.armor_category = seed.armor_category
    item.armor_class_base = seed.armor_class_base
    item.dex_bonus_rule = seed.dex_bonus_rule
    item.strength_requirement = seed.strength_requirement
    item.stealth_disadvantage = seed.stealth_disadvantage
    item.is_shield = seed.is_shield
    item.source = seed.source
    item.source_ref = seed.source_ref
    item.is_srd = False
    item.is_active = True


def sync_aliases(
    *,
    session: Session,
    item: BaseItem,
    alias_seeds: list[AliasSeed],
    aliases_by_item_id: dict[str, dict[str, BaseItemAlias]],
    alias_owner_by_key: dict[str, str],
) -> tuple[int, int]:
    created = 0
    updated = 0
    existing_aliases = aliases_by_item_id.setdefault(item.id, {})

    for alias_seed in alias_seeds:
        alias_key = normalize_lookup(alias_seed.alias)
        if not alias_key:
            continue

        owner_id = alias_owner_by_key.get(alias_key)
        if owner_id and owner_id != item.id:
            LOGGER.warning(
                "Alias conflict for %s: %s already belongs to another item (%s)",
                item.canonical_key,
                alias_seed.alias,
                owner_id,
            )
            continue

        existing = existing_aliases.get(alias_key)
        if existing:
            changed = False
            if alias_seed.locale is not None and existing.locale != alias_seed.locale:
                existing.locale = alias_seed.locale
                changed = True
            if alias_seed.alias_type is not None and existing.alias_type != alias_seed.alias_type:
                existing.alias_type = alias_seed.alias_type
                changed = True
            if changed:
                session.add(existing)
                updated += 1
            continue

        alias_record = BaseItemAlias(
            base_item_id=item.id,
            alias=alias_seed.alias,
            locale=alias_seed.locale,
            alias_type=alias_seed.alias_type,
        )
        session.add(alias_record)
        session.flush()
        existing_aliases[alias_key] = alias_record
        alias_owner_by_key[alias_key] = item.id
        created += 1

    return created, updated


def load_existing_items(
    session: Session,
) -> tuple[dict[str, BaseItem], dict[str, dict[str, BaseItemAlias]], dict[str, str]]:
    items = session.exec(
        select(BaseItem).where(BaseItem.system == SYSTEM)
    ).all()
    items_by_key = {item.canonical_key: item for item in items}

    aliases = session.exec(
        select(BaseItemAlias, BaseItem)
        .join(BaseItem, BaseItemAlias.base_item_id == BaseItem.id)  # type: ignore[arg-type]
        .where(BaseItem.system == SYSTEM)
    ).all()

    aliases_by_item_id: dict[str, dict[str, BaseItemAlias]] = {}
    alias_owner_by_key: dict[str, str] = {}

    for alias, item in aliases:
        item_aliases = aliases_by_item_id.setdefault(item.id, {})
        alias_key = normalize_lookup(alias.alias)
        if alias_key in alias_owner_by_key and alias_owner_by_key[alias_key] != item.id:
            LOGGER.warning(
                "Existing alias conflict in database: %s used by %s and %s",
                alias.alias,
                alias_owner_by_key[alias_key],
                item.id,
            )
            continue
        item_aliases[alias_key] = alias
        alias_owner_by_key[alias_key] = item.id

    return items_by_key, aliases_by_item_id, alias_owner_by_key


def run_import(*, dry_run: bool = False) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    weapon_rows = load_weapons_csv()
    armor_rows = load_armors_csv()
    gear_entries_by_key = load_gear_json()

    prepared_items: list[BaseItemSeed] = []
    seen_canonical_keys: dict[str, str] = {}
    skipped_items = 0
    synthetic_gear_names: list[str] = []

    def append_seed(seed: BaseItemSeed | None) -> None:
        nonlocal skipped_items
        if not seed:
            skipped_items += 1
            return

        previous_name = seen_canonical_keys.get(seed.canonical_key)
        if previous_name and previous_name != seed.name_pt:
            LOGGER.warning(
                "Canonical key conflict: %s maps both %s and %s. Skipping %s.",
                seed.canonical_key,
                previous_name,
                seed.name_pt,
                seed.name_pt,
            )
            skipped_items += 1
            return

        seen_canonical_keys[seed.canonical_key] = seed.name_pt
        prepared_items.append(seed)

    for row in weapon_rows:
        append_seed(normalize_weapon_row(row))

    for row in armor_rows:
        append_seed(normalize_armor_row(row))

    for spec in ESSENTIAL_GEAR_SPECS:
        seed = normalize_gear_item(spec, gear_entries_by_key)
        if seed and seed.source == "synthetic_import":
            synthetic_gear_names.append(seed.name_en)
        append_seed(seed)

    inserted_items = 0
    updated_items = 0
    created_aliases = 0
    updated_aliases = 0

    with Session(engine) as session:
        items_by_key, aliases_by_item_id, alias_owner_by_key = load_existing_items(session)

        for seed in prepared_items:
            item = items_by_key.get(seed.canonical_key)
            if item is None:
                item = BaseItem(
                    system=SYSTEM,
                    canonical_key=seed.canonical_key,
                    name_en=seed.name_en,
                    name_pt=seed.name_pt,
                    item_kind=seed.item_kind,
                )
                apply_seed_to_item(item, seed)
                session.add(item)
                session.flush()
                items_by_key[seed.canonical_key] = item
                inserted_items += 1
                LOGGER.info("Inserted %s (%s)", seed.name_en, seed.canonical_key)
            else:
                apply_seed_to_item(item, seed)
                session.add(item)
                updated_items += 1
                LOGGER.info("Updated %s (%s)", seed.name_en, seed.canonical_key)

            alias_created, alias_updated = sync_aliases(
                session=session,
                item=item,
                alias_seeds=seed.aliases,
                aliases_by_item_id=aliases_by_item_id,
                alias_owner_by_key=alias_owner_by_key,
            )
            created_aliases += alias_created
            updated_aliases += alias_updated

        if dry_run:
            session.rollback()
            LOGGER.info("Dry-run completed. Database changes were rolled back.")
        else:
            session.commit()

    if synthetic_gear_names:
        LOGGER.info(
            "Synthetic gear seeds used (%s): %s",
            len(synthetic_gear_names),
            ", ".join(synthetic_gear_names),
        )

    LOGGER.info(
        "Import summary: %s inserted, %s updated, %s aliases created, %s aliases updated, %s skipped.",
        inserted_items,
        updated_items,
        created_aliases,
        updated_aliases,
        skipped_items,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import D&D base weapons, armors, and essential gear into base_item/base_item_alias."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load and normalize data, but roll back database changes at the end.",
    )
    args = parser.parse_args()
    run_import(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
