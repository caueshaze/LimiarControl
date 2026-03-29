import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { INITIAL_SHEET } from "../model/initialSheet";
import type { CharacterSheet } from "../model/characterSheet.types";
import { applyCreationLoadoutToSheet } from "../utils/creationEquipment";
import { createCreationSheetActions } from "./useCharacterSheetActions.creation";
import {
  resetCreationItemCatalogForTests,
  seedCreationItemCatalogForTests,
} from "../utils/creationItemCatalog";
import { TEST_CREATION_BASE_ITEMS } from "../utils/creationItemCatalog.testData";

describe("createCreationSheetActions", () => {
  beforeEach(() => {
    seedCreationItemCatalogForTests(TEST_CREATION_BASE_ITEMS);
  });

  afterEach(() => {
    resetCreationItemCatalogForTests();
  });

  it("can reset creation inventory when changing race after custom item edits", () => {
    let current = {
      ...applyCreationLoadoutToSheet({
        ...INITIAL_SHEET,
        class: "guardian",
        background: "soldier",
        race: "half-elf",
      }),
      inventory: [
        ...applyCreationLoadoutToSheet({
          ...INITIAL_SHEET,
          class: "guardian",
          background: "soldier",
          race: "half-elf",
        }).inventory,
        {
          id: "custom:rope",
          name: "Silk Rope",
          quantity: 1,
          weight: 0,
          notes: "custom",
          canonicalKey: null,
          campaignItemId: null,
          baseItemId: null,
        },
      ],
    };

    const actions = createCreationSheetActions({
      mode: "creation",
      campaignId: null,
      guardedUpdate: (updater) => {
        current = updater(current);
      },
      update: (updater) => {
        current = updater(current);
      },
      set: (key, value) => {
        current = { ...current, [key]: value };
      },
      dispatch: () => {},
      importRef: { current: null },
      sheet: current,
    });

    actions.selectRace("human", { resetInventory: true });

    expect(current.race).toBe("human");
    expect(current.inventory.some((item) => item.id === "custom:rope")).toBe(false);
    expect(current.inventory.map((item) => item.id)).toEqual(
      expect.arrayContaining([
        "starter:breastplate",
        "starter:longbow",
        "starter:quiver",
        "starter:arrow",
        "starter:shortsword",
      ]),
    );
  });

  it("clears draconic ancestry when changing away from Draconic Bloodline", () => {
    let current: CharacterSheet = {
      ...INITIAL_SHEET,
      class: "sorcerer",
      subclass: "draconic_bloodline",
      subclassConfig: { draconicAncestry: "red" },
    };

    const actions = createCreationSheetActions({
      mode: "creation",
      campaignId: null,
      guardedUpdate: (updater) => {
        current = updater(current);
      },
      update: (updater) => {
        current = updater(current);
      },
      set: (key, value) => {
        current = { ...current, [key]: value };
      },
      dispatch: () => {},
      importRef: { current: null },
      sheet: current,
    });

    actions.selectSubclass("wild_magic");

    expect(current.subclass).toBe("wild_magic");
    expect(current.subclassConfig).toBeNull();
  });

  it("clears racial draconic ancestry when changing away from dragonborn", () => {
    let current: CharacterSheet = {
      ...INITIAL_SHEET,
      race: "dragonborn",
      raceConfig: { draconicAncestry: "red" },
    };

    const actions = createCreationSheetActions({
      mode: "creation",
      campaignId: null,
      guardedUpdate: (updater) => {
        current = updater(current);
      },
      update: (updater) => {
        current = updater(current);
      },
      set: (key, value) => {
        current = { ...current, [key]: value };
      },
      dispatch: () => {},
      importRef: { current: null },
      sheet: current,
    });

    actions.selectRace("human");

    expect(current.race).toBe("human");
    expect(current.raceConfig).toBeNull();
  });
});
