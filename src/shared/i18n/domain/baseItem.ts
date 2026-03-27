import type {
  BaseItemArmorCategory,
  BaseItemCostUnit,
  BaseItemDexBonusRule,
  BaseItemEquipmentCategory,
  BaseItemKind,
  BaseItemSource,
  BaseItemWeaponCategory,
  BaseItemWeaponRangeType,
} from "../../../entities/base-item";
import { localizeDamageAdminFallback } from "./damage";
import {
  displayLabel,
  label,
  normalizeLookup,
  type LabelEntry,
  type LocaleLike,
} from "./shared";

const BASE_ITEM_KIND_LABELS: Record<BaseItemKind, LabelEntry> = {
  weapon: label("Weapon", "Arma"),
  armor: label("Armor", "Armadura"),
  gear: label("Gear", "Equipamento"),
  tool: label("Tool", "Ferramenta"),
  consumable: label("Consumable", "Consumível"),
  focus: label("Focus", "Foco"),
  ammo: label("Ammunition", "Munição"),
  pack: label("Pack", "Mochila"),
};

const BASE_ITEM_EQUIPMENT_CATEGORY_LABELS: Record<BaseItemEquipmentCategory, LabelEntry> = {
  adventuring_pack: label("Adventuring pack", "Pacote de aventura"),
  ammunition: label("Ammunition", "Munição"),
  book: label("Book", "Livro"),
  clothing: label("Clothing", "Vestuário"),
  consumable_supply: label("Consumable supply", "Suprimento consumível"),
  container: label("Container", "Recipiente"),
  document: label("Document", "Documento"),
  gaming_set: label("Gaming set", "Jogo de mesa"),
  insignia: label("Insignia", "Insígnia"),
  jewelry: label("Jewelry", "Joia"),
  memento: label("Memento", "Lembrança"),
  musical_instrument: label("Musical instrument", "Instrumento musical"),
  pet: label("Pet", "Mascote"),
  rope: label("Rope", "Corda"),
  sailing_gear: label("Sailing gear", "Equipamento náutico"),
  spellcasting_focus: label("Spellcasting focus", "Foco de conjuração"),
  spellcasting_gear: label("Spellcasting gear", "Equipamento de conjuração"),
  supplies: label("Supplies", "Suprimentos"),
  tools: label("Tools", "Ferramentas"),
  trophy: label("Trophy", "Troféu"),
  utility_tool: label("Utility tool", "Ferramenta utilitária"),
  vehicle_proficiency: label("Vehicle proficiency", "Proficiência em veículos"),
  writing_supply: label("Writing supply", "Material de escrita"),
};

const BASE_ITEM_COST_UNIT_LABELS: Record<BaseItemCostUnit, LabelEntry> = {
  cp: label("CP", "PC"),
  sp: label("SP", "PP"),
  ep: label("EP", "PE"),
  gp: label("GP", "PO"),
  pp: label("PP", "PL"),
};

const BASE_ITEM_WEAPON_CATEGORY_LABELS: Record<BaseItemWeaponCategory, LabelEntry> = {
  simple: label("Simple", "Simples"),
  martial: label("Martial", "Marcial"),
};

const BASE_ITEM_WEAPON_RANGE_TYPE_LABELS: Record<BaseItemWeaponRangeType, LabelEntry> = {
  melee: label("Melee", "Corpo a corpo"),
  ranged: label("Ranged", "À distância"),
};

const BASE_ITEM_ARMOR_CATEGORY_LABELS: Record<BaseItemArmorCategory, LabelEntry> = {
  light: label("Light", "Leve"),
  medium: label("Medium", "Média"),
  heavy: label("Heavy", "Pesada"),
  shield: label("Shield", "Escudo"),
};

const BASE_ITEM_DEX_BONUS_RULE_LABELS: Record<BaseItemDexBonusRule, LabelEntry> = {
  full: label("Full DEX", "DEX completo"),
  max_2: label("Max +2 DEX", "Máx. +2 DEX"),
  none: label("No DEX bonus", "Sem bônus de DEX"),
};

const BASE_ITEM_SOURCE_LABELS: Record<BaseItemSource, LabelEntry> = {
  admin_panel: label("Admin panel", "Painel admin"),
  seed_json_bootstrap: label("Seed bootstrap", "Carga inicial por seed"),
};

export const localizeBaseItemKind = (value: BaseItemKind, locale: LocaleLike) =>
  displayLabel(BASE_ITEM_KIND_LABELS[value], locale);

export const localizeBaseItemEquipmentCategory = (
  value: BaseItemEquipmentCategory,
  locale: LocaleLike,
) => displayLabel(BASE_ITEM_EQUIPMENT_CATEGORY_LABELS[value], locale);

export const localizeBaseItemCostUnit = (value: BaseItemCostUnit, locale: LocaleLike) =>
  displayLabel(BASE_ITEM_COST_UNIT_LABELS[value], locale);

export const localizeBaseItemWeaponCategory = (
  value: BaseItemWeaponCategory,
  locale: LocaleLike,
) => displayLabel(BASE_ITEM_WEAPON_CATEGORY_LABELS[value], locale);

export const localizeBaseItemWeaponRangeType = (
  value: BaseItemWeaponRangeType,
  locale: LocaleLike,
) => displayLabel(BASE_ITEM_WEAPON_RANGE_TYPE_LABELS[value], locale);

export const localizeBaseItemArmorCategory = (
  value: BaseItemArmorCategory,
  locale: LocaleLike,
) => displayLabel(BASE_ITEM_ARMOR_CATEGORY_LABELS[value], locale);

export const localizeBaseItemDexBonusRule = (
  value: BaseItemDexBonusRule | null | undefined,
  locale: LocaleLike,
) => (value ? displayLabel(BASE_ITEM_DEX_BONUS_RULE_LABELS[value], locale) : null);

export const localizeBaseItemSource = (value: BaseItemSource, locale: LocaleLike) =>
  displayLabel(BASE_ITEM_SOURCE_LABELS[value], locale);

export const localizeBaseItemAdminValue = (value: string, locale: LocaleLike) => {
  const normalized = normalizeLookup(value).replace(/\s+/g, "_");
  const maps: Record<string, LabelEntry>[] = [
    BASE_ITEM_KIND_LABELS as Record<string, LabelEntry>,
    BASE_ITEM_EQUIPMENT_CATEGORY_LABELS as Record<string, LabelEntry>,
    BASE_ITEM_WEAPON_CATEGORY_LABELS as Record<string, LabelEntry>,
    BASE_ITEM_WEAPON_RANGE_TYPE_LABELS as Record<string, LabelEntry>,
    BASE_ITEM_ARMOR_CATEGORY_LABELS as Record<string, LabelEntry>,
    BASE_ITEM_DEX_BONUS_RULE_LABELS as Record<string, LabelEntry>,
    BASE_ITEM_SOURCE_LABELS as Record<string, LabelEntry>,
    BASE_ITEM_COST_UNIT_LABELS as Record<string, LabelEntry>,
  ];

  for (const map of maps) {
    if (map[normalized]) {
      return displayLabel(map[normalized], locale);
    }
  }

  return localizeDamageAdminFallback(value, locale);
};
