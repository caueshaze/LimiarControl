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

// ── Registry ────────────────────────────────────────────────────────────────

export const CLASS_EQUIPMENT_RULES: Record<string, ClassEquipmentRules> = {};
