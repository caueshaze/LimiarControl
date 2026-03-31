import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { INITIAL_SHEET } from "../model/initialSheet";
import { getClassCreationConfig } from "../data/classCreation";
import { BACKGROUNDS } from "../data/backgrounds";
import {
  applyCreationLoadoutToSheet,
  buildCreationLoadout,
  buildCreationArmorOptions,
  canonicalizeStarterItemName,
  getInitialClassEquipmentSelections,
  hasCustomCreationInventoryItems,
  hasUnresolvedCreationInventoryItems,
  syncCreationInventoryLoadoutState,
} from "./creationEquipment";
import {
  resetCreationItemCatalogForTests,
  resolveCreationItem,
  seedCreationCatalogItemsForTests,
  seedCreationItemCatalogForTests,
} from "./creationItemCatalog";
import { TEST_CREATION_BASE_ITEMS } from "./creationItemCatalog.testData";

describe("creationEquipment", () => {
  beforeEach(() => {
    seedCreationItemCatalogForTests(TEST_CREATION_BASE_ITEMS);
  });

  afterEach(() => {
    resetCreationItemCatalogForTests();
  });

  it("builds default loadout for classes with fixed equipment", () => {
    const loadout = buildCreationLoadout("wizard", "", getInitialClassEquipmentSelections("wizard"));

    expect(loadout.inventory.map((item) => item.name)).toEqual([
      "Spellbook",
      "Quarterstaff",
      "Component Pouch",
      "Scholar's Pack",
    ]);
  });

  it("changes inventory when the selected class option changes", () => {
    const selections = getInitialClassEquipmentSelections("cleric");
    const defaultLoadout = buildCreationLoadout("cleric", "", selections);
    const updatedLoadout = buildCreationLoadout("cleric", "", {
      ...selections,
      "cleric-weapon": "martelo-de-guerra",
    });

    expect(defaultLoadout.inventory.map((item) => item.name)).toContain("Mace");
    expect(updatedLoadout.inventory.map((item) => item.name)).toContain("Warhammer");
    expect(updatedLoadout.inventory.map((item) => item.name)).not.toContain("Mace");
  });

  it("anchors class equipment choices to stable catalog tokens when the catalog is loaded", () => {
    const config = getClassCreationConfig("cleric");

    expect(config?.fixedEquipment).toEqual(["catalog:shield", "catalog:holy_symbol"]);
    expect(config?.equipmentChoices.find((group) => group.id === "cleric-weapon")?.options[0]?.items).toEqual([
      "catalog:mace",
    ]);
  });

  it("preserves catalog tokens in duplicated and shielded martial weapon options", () => {
    const fighterConfig = getClassCreationConfig("fighter");
    const rangerConfig = getClassCreationConfig("ranger");
    const fighterOptions = fighterConfig?.equipmentChoices.find((group) => group.id === "fighter-main-weapon")?.options ?? [];
    const rangerOptions = rangerConfig?.equipmentChoices.find((group) => group.id === "ranger-weapons")?.options ?? [];
    const shortswordWithShield = fighterOptions.find((entry) => entry.label === "Espada Curta + Escudo");
    const shortswordPair = fighterOptions.find((entry) => entry.label === "Espada Curta x2");
    const macePair = rangerOptions.find((entry) => entry.label === "Maça x2");

    expect(fighterOptions.length).toBeGreaterThan(0);
    expect(rangerOptions.length).toBeGreaterThan(0);
    expect(shortswordWithShield?.items).toEqual(["catalog:shortsword", "catalog:shield"]);
    expect(shortswordPair?.items).toEqual(["catalog:shortsword", "catalog:shortsword"]);
    expect(macePair?.items).toEqual(["catalog:mace", "catalog:mace"]);
  });

  it("resolves problematic starter item names to canonical names", () => {
    expect(canonicalizeStarterItemName("Escudo")).toBe("Shield");
    expect(canonicalizeStarterItemName("Wooden Shield")).toBe("Shield");
    expect(canonicalizeStarterItemName("Espada Curta")).toBe("Shortsword");
    expect(canonicalizeStarterItemName("Maça")).toBe("Mace");
    expect(canonicalizeStarterItemName("Besta Leve")).toBe("Light Crossbow");
    expect(canonicalizeStarterItemName("Crossbow, light")).toBe("Light Crossbow");
    expect(canonicalizeStarterItemName("Bolt")).toBe("Crossbow bolt");
    expect(canonicalizeStarterItemName("Amulet")).toBe("Holy Symbol");
    expect(canonicalizeStarterItemName("Reliquary")).toBe("Holy Symbol");
    expect(canonicalizeStarterItemName("Holy Symbol")).toBe("Holy Symbol");
    expect(canonicalizeStarterItemName("Arcane Focus")).toBe("Arcane Focus");
  });

  it("resolves possessive pack names against canonical catalog keys", () => {
    seedCreationCatalogItemsForTests([
      {
        id: "base-adventurers-pack",
        campaignItemId: null,
        baseItemId: "base-adventurers-pack",
        canonicalKey: "adventurers_pack",
        name: "Mochila do Aventureiro",
        namePt: "Mochila do Aventureiro",
        description: "",
        descriptionPt: "",
        properties: [],
        weight: 0,
        armorPresetName: null,
        armorCategory: null,
        isShield: false,
        stealthDisadvantage: false,
        itemKind: "pack",
        weaponCategory: null,
        weaponRangeType: null,
        damageDice: null,
        damageType: null,
        weaponPropertiesJson: null,
        rangeNormalMeters: null,
        rangeLongMeters: null,
        versatileDamage: null,
        armorClassBase: null,
        dexBonusRule: null,
        strengthRequirement: null,
      },
      {
        id: "base-artisans-tools",
        campaignItemId: null,
        baseItemId: "base-artisans-tools",
        canonicalKey: "artisans_tools",
        name: "Ferramentas de Artesão",
        namePt: "Ferramentas de Artesão",
        description: "",
        descriptionPt: "",
        properties: [],
        weight: 0,
        armorPresetName: null,
        armorCategory: null,
        isShield: false,
        stealthDisadvantage: false,
        itemKind: "tool",
        weaponCategory: null,
        weaponRangeType: null,
        damageDice: null,
        damageType: null,
        weaponPropertiesJson: null,
        rangeNormalMeters: null,
        rangeLongMeters: null,
        versatileDamage: null,
        armorClassBase: null,
        dexBonusRule: null,
        strengthRequirement: null,
      },
      {
        id: "base-burglars-pack",
        campaignItemId: null,
        baseItemId: "base-burglars-pack",
        canonicalKey: "burglars_pack",
        name: "Mochila do Ladrão",
        namePt: "Mochila do Ladrão",
        description: "",
        descriptionPt: "",
        properties: [],
        weight: 0,
        armorPresetName: null,
        armorCategory: null,
        isShield: false,
        stealthDisadvantage: false,
        itemKind: "pack",
        weaponCategory: null,
        weaponRangeType: null,
        damageDice: null,
        damageType: null,
        weaponPropertiesJson: null,
        rangeNormalMeters: null,
        rangeLongMeters: null,
        versatileDamage: null,
        armorClassBase: null,
        dexBonusRule: null,
        strengthRequirement: null,
      },
      {
        id: "base-diplomats-pack",
        campaignItemId: null,
        baseItemId: "base-diplomats-pack",
        canonicalKey: "diplomats_pack",
        name: "Mochila do Diplomata",
        namePt: "Mochila do Diplomata",
        description: "",
        descriptionPt: "",
        properties: [],
        weight: 0,
        armorPresetName: null,
        armorCategory: null,
        isShield: false,
        stealthDisadvantage: false,
        itemKind: "pack",
        weaponCategory: null,
        weaponRangeType: null,
        damageDice: null,
        damageType: null,
        weaponPropertiesJson: null,
        rangeNormalMeters: null,
        rangeLongMeters: null,
        versatileDamage: null,
        armorClassBase: null,
        dexBonusRule: null,
        strengthRequirement: null,
      },
      {
        id: "base-entertainers-pack",
        campaignItemId: null,
        baseItemId: "base-entertainers-pack",
        canonicalKey: "entertainers_pack",
        name: "Mochila do Artista",
        namePt: "Mochila do Artista",
        description: "",
        descriptionPt: "",
        properties: [],
        weight: 0,
        armorPresetName: null,
        armorCategory: null,
        isShield: false,
        stealthDisadvantage: false,
        itemKind: "pack",
        weaponCategory: null,
        weaponRangeType: null,
        damageDice: null,
        damageType: null,
        weaponPropertiesJson: null,
        rangeNormalMeters: null,
        rangeLongMeters: null,
        versatileDamage: null,
        armorClassBase: null,
        dexBonusRule: null,
        strengthRequirement: null,
      },
      {
        id: "base-explorers-pack",
        campaignItemId: null,
        baseItemId: "base-explorers-pack",
        canonicalKey: "explorers_pack",
        name: "Mochila do Explorador",
        namePt: "Mochila do Explorador",
        description: "",
        descriptionPt: "",
        properties: [],
        weight: 0,
        armorPresetName: null,
        armorCategory: null,
        isShield: false,
        stealthDisadvantage: false,
        itemKind: "pack",
        weaponCategory: null,
        weaponRangeType: null,
        damageDice: null,
        damageType: null,
        weaponPropertiesJson: null,
        rangeNormalMeters: null,
        rangeLongMeters: null,
        versatileDamage: null,
        armorClassBase: null,
        dexBonusRule: null,
        strengthRequirement: null,
      },
      {
        id: "base-priests-pack",
        campaignItemId: null,
        baseItemId: "base-priests-pack",
        canonicalKey: "priests_pack",
        name: "Mochila do Sacerdote",
        namePt: "Mochila do Sacerdote",
        description: "",
        descriptionPt: "",
        properties: [],
        weight: 0,
        armorPresetName: null,
        armorCategory: null,
        isShield: false,
        stealthDisadvantage: false,
        itemKind: "pack",
        weaponCategory: null,
        weaponRangeType: null,
        damageDice: null,
        damageType: null,
        weaponPropertiesJson: null,
        rangeNormalMeters: null,
        rangeLongMeters: null,
        versatileDamage: null,
        armorClassBase: null,
        dexBonusRule: null,
        strengthRequirement: null,
      },
      {
        id: "base-scholars-pack",
        campaignItemId: null,
        baseItemId: "base-scholars-pack",
        canonicalKey: "scholars_pack",
        name: "Mochila do Estudioso",
        namePt: "Mochila do Estudioso",
        description: "",
        descriptionPt: "",
        properties: [],
        weight: 0,
        armorPresetName: null,
        armorCategory: null,
        isShield: false,
        stealthDisadvantage: false,
        itemKind: "pack",
        weaponCategory: null,
        weaponRangeType: null,
        damageDice: null,
        damageType: null,
        weaponPropertiesJson: null,
        rangeNormalMeters: null,
        rangeLongMeters: null,
        versatileDamage: null,
        armorClassBase: null,
        dexBonusRule: null,
        strengthRequirement: null,
      },
    ]);

    expect(resolveCreationItem("Adventurer's Pack")?.canonicalKey).toBe("adventurers_pack");
    expect(resolveCreationItem("Artisan's Tools")?.canonicalKey).toBe("artisans_tools");
    expect(resolveCreationItem("Burglar's Pack")?.canonicalKey).toBe("burglars_pack");
    expect(resolveCreationItem("Diplomat's Pack")?.canonicalKey).toBe("diplomats_pack");
    expect(resolveCreationItem("Entertainer's Pack")?.canonicalKey).toBe("entertainers_pack");
    expect(resolveCreationItem("Explorer's Pack")?.canonicalKey).toBe("explorers_pack");
    expect(resolveCreationItem("Priest's Pack")?.canonicalKey).toBe("priests_pack");
    expect(resolveCreationItem("Scholar's Pack")?.canonicalKey).toBe("scholars_pack");
  });

  it("persists canonical starter names even when the source option is an alias", () => {
    const loadout = buildCreationLoadout("druid", "", getInitialClassEquipmentSelections("druid"));

    expect(loadout.inventory.map((item) => item.name)).toContain("Shield");
    expect(loadout.inventory.map((item) => item.name)).not.toContain("Wooden Shield");
  });

  it("keeps classes without optional choices valid", () => {
    const loadout = buildCreationLoadout("wizard", "", {});

    expect(loadout.inventory.length).toBeGreaterThan(0);
    expect(loadout.inventory.some((item) => item.name === "Spellbook")).toBe(true);
  });

  it("derives a stable creation inventory from sheet selections", () => {
    const sheet = applyCreationLoadoutToSheet({
      ...INITIAL_SHEET,
      class: "cleric",
      background: "",
      classEquipmentSelections: getInitialClassEquipmentSelections("cleric"),
    });

    expect(sheet.inventory.map((item) => item.id)).toEqual([
      "starter:shield",
      "starter:holy-symbol",
      "starter:mace",
      "starter:scale-mail",
      "starter:light-crossbow",
      "starter:crossbow-bolt",
      "starter:priests-pack",
    ]);
    expect(sheet.inventory[0]?.canonicalKey).toBe("shield");
    expect(sheet.inventory[0]?.baseItemId).toBe("base-shield");
    expect(sheet.equippedArmorItemId).toBe("starter:scale-mail");
  });

  it("builds creation armor options from canonical inventory entries", () => {
    const loadout = buildCreationLoadout("guardian", "", getInitialClassEquipmentSelections("guardian"));

    expect(buildCreationArmorOptions(loadout.inventory)).toEqual([
      {
        value: "starter:breastplate",
        label: "Breastplate",
        detail: "AC 14",
        armor: expect.objectContaining({ name: "Breastplate", baseAC: 14 }),
      },
    ]);
  });

  it("keeps campaign-localized armor items equipable in the combat card", () => {
    seedCreationCatalogItemsForTests([
      {
        id: "base-breastplate",
        campaignItemId: "campaign-breastplate",
        baseItemId: "base-breastplate",
        canonicalKey: "breastplate",
        name: "Peitoral",
        namePt: "Peitoral",
        description: "Armadura média.",
        descriptionPt: "Armadura média.",
        properties: [],
        weight: 20,
        armorPresetName: "Peitoral",
        armorCategory: "medium",
        isShield: false,
        stealthDisadvantage: false,
        itemKind: "armor",
        weaponCategory: null,
        weaponRangeType: null,
        damageDice: null,
        damageType: null,
        weaponPropertiesJson: null,
        rangeNormalMeters: null,
        rangeLongMeters: null,
        versatileDamage: null,
        armorClassBase: 14,
        dexBonusRule: "max_2",
        strengthRequirement: null,
      },
    ]);

    expect(buildCreationArmorOptions([
      {
        id: "starter:breastplate",
        name: "Peitoral",
        quantity: 1,
        weight: 20,
        notes: "Equipamento inicial",
        canonicalKey: "breastplate",
        campaignItemId: "campaign-breastplate",
        baseItemId: "base-breastplate",
      },
    ])).toEqual([
      {
        value: "starter:breastplate",
        label: "Peitoral",
        detail: "AC 14",
        armor: expect.objectContaining({
          name: "Peitoral",
          armorType: "medium",
          baseAC: 14,
          dexCap: 2,
        }),
      },
    ]);
  });

  it("canonicalizes manually added creation items by name and keeps them equipable", () => {
    const sheet = syncCreationInventoryLoadoutState({
      ...INITIAL_SHEET,
      inventory: [
        {
          id: "custom:breastplate",
          name: "Peitoral",
          quantity: 1,
          weight: 0,
          notes: "",
          canonicalKey: null,
          baseItemId: null,
          campaignItemId: null,
        },
      ],
      equippedArmor: { ...INITIAL_SHEET.equippedArmor, name: "Breastplate", baseAC: 14, armorType: "medium", dexCap: 2 },
    });

    expect(sheet.inventory[0]?.canonicalKey).toBe("breastplate");
    expect(sheet.inventory[0]?.baseItemId).toBe("base-breastplate");
    expect(sheet.equippedArmorItemId).toBe("custom:breastplate");
    expect(sheet.equippedArmor.name).toBe("Breastplate");
  });

  it("detects only custom creation inventory items for reset confirmations", () => {
    const starterOnlyLoadout = buildCreationLoadout("guardian", "", getInitialClassEquipmentSelections("guardian"));

    expect(hasCustomCreationInventoryItems(starterOnlyLoadout.inventory)).toBe(false);
    expect(hasCustomCreationInventoryItems([
      ...starterOnlyLoadout.inventory,
      {
        id: "custom:rope",
        name: "Silk Rope",
        quantity: 1,
        weight: 0,
        notes: "",
        canonicalKey: null,
        campaignItemId: null,
        baseItemId: null,
      },
    ])).toBe(true);
  });

  it("flags unresolved creation inventory items that are outside the catalog", () => {
    expect(hasUnresolvedCreationInventoryItems([
      {
        id: "custom:unknown",
        name: "Item Inventado",
        quantity: 1,
        weight: 0,
        notes: "",
        canonicalKey: null,
        campaignItemId: null,
        baseItemId: null,
      },
    ])).toBe(true);

    const starterOnlyLoadout = buildCreationLoadout("guardian", "", getInitialClassEquipmentSelections("guardian"));
    expect(hasUnresolvedCreationInventoryItems(starterOnlyLoadout.inventory)).toBe(false);
  });

  it("normalizes literal background bundle entries into persisted base items", () => {
    const acolyteLoadout = buildCreationLoadout("", "acolyte", {});
    const sailorLoadout = buildCreationLoadout("", "sailor", {});
    const charlatanLoadout = buildCreationLoadout("", "charlatan", {});

    expect(acolyteLoadout.inventory.map((item) => ({ name: item.name, quantity: item.quantity }))).toEqual([
      { name: "Holy Symbol", quantity: 1 },
      { name: "Prayer book", quantity: 1 },
      { name: "Incense", quantity: 5 },
      { name: "Vestments", quantity: 1 },
      { name: "Common clothes", quantity: 1 },
    ]);
    expect(sailorLoadout.inventory.map((item) => ({ name: item.name, quantity: item.quantity }))).toContainEqual({
      name: "Silk Rope",
      quantity: 1,
    });
    expect(charlatanLoadout.inventory.map((item) => item.name)).toContain("Forgery Kit");
    expect(charlatanLoadout.inventory.map((item) => item.name)).not.toContain("Con tools");
  });

  it("resolves all background starting items through the persisted catalog", () => {
    for (const background of BACKGROUNDS) {
      const loadout = buildCreationLoadout("", background.id, {});
      expect(loadout.inventory.every((item) => item.canonicalKey)).toBe(true);
    }
  });
});
