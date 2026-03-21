import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { INITIAL_SHEET } from "../model/initialSheet";
import { getClassCreationConfig } from "../data/classCreation";
import { BACKGROUNDS } from "../data/backgrounds";
import {
  applyCreationLoadoutToSheet,
  buildCreationLoadout,
  canonicalizeStarterItemName,
  getInitialClassEquipmentSelections,
} from "./creationEquipment";
import {
  resetCreationItemCatalogForTests,
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
