import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { INITIAL_SHEET } from "../model/initialSheet";
import type { CharacterSheet } from "../model/characterSheet.types";
import { createBaseSheetActions } from "./useCharacterSheetActions.base";
import { seedSpellCatalogCache } from "../../../entities/dnd-base";
import {
  resetCreationItemCatalogForTests,
  seedCreationItemCatalogForTests,
} from "../utils/creationItemCatalog";
import { TEST_CREATION_BASE_ITEMS } from "../utils/creationItemCatalog.testData";

describe("createBaseSheetActions", () => {
  beforeEach(() => {
    seedCreationItemCatalogForTests(TEST_CREATION_BASE_ITEMS);
    seedSpellCatalogCache([
      {
        canonicalKey: "guidance",
        name: "Guidance",
        level: 0,
        school: "Divination",
        castingTime: "1 action",
        range: "Touch",
        components: "V, S",
        duration: "Up to 1 minute",
        concentration: true,
        ritual: false,
        description: "",
        damageType: null,
        savingThrow: null,
        classes: ["Cleric", "Druid"],
      },
      {
        canonicalKey: "bless",
        name: "Bless",
        level: 1,
        school: "Enchantment",
        castingTime: "1 action",
        range: "9 m",
        components: "V, S, M",
        duration: "Up to 1 minute",
        concentration: true,
        ritual: false,
        description: "",
        damageType: null,
        savingThrow: null,
        classes: ["Cleric", "Paladin"],
      },
    ]);
  });

  afterEach(() => {
    resetCreationItemCatalogForTests();
  });

  it("keeps skill proficiencies locked in regular creation mode", () => {
    let current = {
      ...INITIAL_SHEET,
      skillProficiencies: { ...INITIAL_SHEET.skillProficiencies },
    };

    const actions = createBaseSheetActions(
      (updater) => {
        current = updater(current);
      },
      () => {},
      "creation",
    );

    actions.cycleSkillProf("animalHandling");

    expect(current.skillProficiencies.animalHandling).toBe(0);
  });

  it("allows skill and save editing in GM draft creation mode", () => {
    let current = {
      ...INITIAL_SHEET,
      skillProficiencies: { ...INITIAL_SHEET.skillProficiencies },
      savingThrowProficiencies: { ...INITIAL_SHEET.savingThrowProficiencies },
    };

    const actions = createBaseSheetActions(
      (updater) => {
        current = updater(current);
      },
      () => {},
      "creation",
      { allowCreationEditing: true },
    );

    actions.cycleSkillProf("animalHandling");
    actions.toggleSaveProf("wisdom");

    expect(current.skillProficiencies.animalHandling).toBe(0.5);
    expect(current.savingThrowProficiencies.wisdom).toBe(true);
  });

  it("adds and keeps creation inventory items canonical in GM draft mode", () => {
    let current: CharacterSheet = {
      ...INITIAL_SHEET,
      inventory: [],
    };

    const actions = createBaseSheetActions(
      (updater) => {
        current = updater(current);
      },
      () => {},
      "creation",
      { allowCreationEditing: true },
    );

    actions.addItem();

    expect(current.inventory).toHaveLength(1);
    expect(current.inventory[0]?.canonicalKey).toBeTruthy();
    expect(current.inventory[0]?.baseItemId).toBeTruthy();

    actions.selectInventoryCatalogItem(current.inventory[0]!.id, "longbow");

    expect(current.inventory[0]?.canonicalKey).toBe("longbow");
    expect(current.inventory[0]?.name).toBe("Longbow");
    expect(current.inventory[0]?.baseItemId).toBe("base-longbow");
  });

  it("adds and switches draft spells through the catalog in creation mode", () => {
    let current: CharacterSheet = {
      ...INITIAL_SHEET,
      class: "cleric",
      spellcasting: {
        ability: "wisdom",
        mode: "known",
        slots: { 1: { max: 2, used: 0 } },
        spells: [],
      },
    };

    const actions = createBaseSheetActions(
      (updater) => {
        current = updater(current);
      },
      () => {},
      "creation",
      { allowCreationEditing: true },
    );

    actions.addSpell();

    expect(current.spellcasting?.spells).toHaveLength(1);
    expect(current.spellcasting?.spells[0]?.canonicalKey).toBe("guidance");
    expect(current.spellcasting?.spells[0]?.name).toBe("Guidance");

    actions.selectCatalogSpell(current.spellcasting!.spells[0]!.id, "bless");

    expect(current.spellcasting?.spells[0]?.canonicalKey).toBe("bless");
    expect(current.spellcasting?.spells[0]?.name).toBe("Bless");
    expect(current.spellcasting?.spells[0]?.level).toBe(1);
    expect(current.spellcasting?.spells[0]?.school).toBe("Enchantment");
  });
});
