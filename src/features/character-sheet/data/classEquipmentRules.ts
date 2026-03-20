/**
 * Declarative equipment rules for D&D 5e character creation.
 *
 * Each class defines its PHB starting equipment as a set of fixed items
 * and choice groups. The rule schema is resolved at runtime against the
 * base-item catalog (DB) to produce the concrete ClassCreationConfig
 * consumed by the existing UI.
 *
 * This file encodes *game rules* (structure of choices), not item data.
 * Item names, weights, and stats come from the catalog.
 */

import type { BaseItemWeaponCategory, BaseItemWeaponRangeType } from "../../../entities/base-item";

// ── Option sources ──────────────────────────────────────────────────────────

/** Produces one option per weapon matching the filter. */
export type WeaponFilterSource = {
  kind: "weapon_filter";
  category: BaseItemWeaponCategory;
  rangeType?: BaseItemWeaponRangeType;
};

/** A single selectable option made of one or more specific items. */
export type SpecificItemsSource = {
  kind: "specific_items";
  labelPt: string;
  items: { canonicalKey: string; quantity?: number }[];
};

/** A pack choice (e.g. Explorer's Pack vs Dungeoneer's Pack). */
export type PackChoiceSource = {
  kind: "pack_choice";
  packs: { labelPt: string; canonicalKey: string }[];
};

export type EquipmentOptionSource =
  | WeaponFilterSource
  | SpecificItemsSource
  | PackChoiceSource;

// ── Choice group ────────────────────────────────────────────────────────────

export type EquipmentChoiceRule = {
  id: string;
  labelPt: string;
  sources: EquipmentOptionSource[];
};

// ── Full class rules ────────────────────────────────────────────────────────

export type ClassEquipmentRules = {
  fixedItems: { canonicalKey: string; quantity?: number }[];
  choices: EquipmentChoiceRule[];
};

// ── Barbarian ───────────────────────────────────────────────────────────────

/**
 * PHB p.48 — Equipamento do Bárbaro:
 *  - (a) um machado grande ou (b) qualquer arma marcial corpo-a-corpo
 *  - (a) dois machados de mão ou (b) qualquer arma simples
 *  - Um pacote de aventureiro e quatro azagaias (fixo)
 */
export const BARBARIAN_EQUIPMENT_RULES: ClassEquipmentRules = {
  fixedItems: [
    { canonicalKey: "explorers_pack" },
    { canonicalKey: "javelin", quantity: 4 },
  ],
  choices: [
    {
      id: "barbarian-weapon-1",
      labelPt: "Escolha 1: Arma principal",
      sources: [
        // (a) Greataxe or (b) any martial MELEE weapon — PHB restricts to melee
        { kind: "weapon_filter", category: "martial", rangeType: "melee" },
      ],
    },
    {
      id: "barbarian-weapon-2",
      labelPt: "Escolha 2: Arma secundária",
      sources: [
        // (a) two handaxes
        {
          kind: "specific_items",
          labelPt: "Machadinha x2",
          items: [
            { canonicalKey: "handaxe", quantity: 2 },
          ],
        },
        // (b) any simple weapon
        { kind: "weapon_filter", category: "simple" },
      ],
    },
  ],
};

// ── Registry ────────────────────────────────────────────────────────────────

export const CLASS_EQUIPMENT_RULES: Record<string, ClassEquipmentRules> = {
  barbarian: BARBARIAN_EQUIPMENT_RULES,
};
