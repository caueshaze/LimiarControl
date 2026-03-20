import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { INITIAL_SHEET } from "../model/initialSheet";
import { prepareCharacterSheetForSave } from "./characterSheet.service";
import {
  resetCreationItemCatalogForTests,
  seedCreationItemCatalogForTests,
} from "../utils/creationItemCatalog";
import { TEST_CREATION_BASE_ITEMS } from "../utils/creationItemCatalog.testData";

describe("prepareCharacterSheetForSave", () => {
  beforeEach(() => {
    seedCreationItemCatalogForTests(TEST_CREATION_BASE_ITEMS);
  });

  afterEach(() => {
    resetCreationItemCatalogForTests();
  });

  it("serializes creation sheets with the derived starter inventory", () => {
    const prepared = prepareCharacterSheetForSave(
      {
        ...INITIAL_SHEET,
        class: "cleric",
        background: "",
        classEquipmentSelections: {
          "cleric-weapon": "martelo-de-guerra",
          "cleric-armor": "cota-de-malha",
          "cleric-ranged": "besta-leve-20-virotes",
          "cleric-pack": "priest-s-pack",
        },
      },
      "creation",
    );

    expect(prepared.inventory.map((item) => ({ name: item.name, quantity: item.quantity }))).toEqual([
      { name: "Shield", quantity: 1 },
      { name: "Holy Symbol", quantity: 1 },
      { name: "Warhammer", quantity: 1 },
      { name: "Chain Mail", quantity: 1 },
      { name: "Light Crossbow", quantity: 1 },
      { name: "Crossbow bolt", quantity: 20 },
      { name: "Priest's Pack", quantity: 1 },
    ]);
    expect(prepared.inventory[0]?.canonicalKey).toBe("shield");
    expect(prepared.inventory[0]?.baseItemId).toBe("base-shield");
  });

  it("does not rebuild play sheets", () => {
    const prepared = prepareCharacterSheetForSave(INITIAL_SHEET, "play");
    expect(prepared).toBe(INITIAL_SHEET);
  });
});
