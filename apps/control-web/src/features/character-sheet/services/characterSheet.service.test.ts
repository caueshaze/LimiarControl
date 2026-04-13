import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { INITIAL_SHEET } from "../model/initialSheet";
import { prepareCharacterSheetForSave } from "./characterSheet.service";
import { applyCreationLoadoutToSheet } from "../utils/creationEquipment";
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

  it("preserves existing creation inventory instead of rebuilding it on save", () => {
    const sheet = applyCreationLoadoutToSheet({
      ...INITIAL_SHEET,
      class: "cleric",
      background: "",
      classEquipmentSelections: {
        "cleric-weapon": "martelo-de-guerra",
        "cleric-armor": "cota-de-malha",
        "cleric-ranged": "besta-leve-20-virotes",
        "cleric-pack": "priest-s-pack",
      },
    });

    const prepared = prepareCharacterSheetForSave(
      {
        ...sheet,
        inventory: [
          ...sheet.inventory,
          {
            id: "custom:rope",
            name: "Silk Rope",
            quantity: 1,
            weight: 0,
            notes: "GM custom item",
            canonicalKey: null,
            campaignItemId: null,
            baseItemId: null,
          },
        ],
      },
      "creation",
    );

    expect(prepared.inventory.map((item) => ({ id: item.id, name: item.name }))).toContainEqual({
      id: "custom:rope",
      name: "Silk Rope",
    });
    expect(prepared.inventory.find((item) => item.id === "custom:rope")?.canonicalKey).toBe("silk_rope");
  });

  it("serializes guardian starter inventory with canonical links for loadout/combat", () => {
    const prepared = applyCreationLoadoutToSheet(
      {
        ...INITIAL_SHEET,
        class: "guardian",
        background: "",
      },
    );

    expect(prepared.inventory.map((item) => ({
      name: item.name,
      canonicalKey: item.canonicalKey,
      baseItemId: item.baseItemId,
      quantity: item.quantity,
    }))).toEqual([
      { name: "Breastplate", canonicalKey: "breastplate", baseItemId: "base-breastplate", quantity: 1 },
      { name: "Longbow", canonicalKey: "longbow", baseItemId: "base-longbow", quantity: 1 },
      { name: "Quiver", canonicalKey: "quiver", baseItemId: "base-quiver", quantity: 1 },
      { name: "Arrow", canonicalKey: "arrow", baseItemId: "base-arrow", quantity: 20 },
      { name: "Shortsword", canonicalKey: "shortsword", baseItemId: "base-shortsword", quantity: 2 },
    ]);
    expect(prepared.equippedArmorItemId).toBe("starter:breastplate");
  });

  it("does not rebuild play sheets", () => {
    const prepared = prepareCharacterSheetForSave(INITIAL_SHEET, "play");
    expect(prepared).toStrictEqual(INITIAL_SHEET);
  });
});
