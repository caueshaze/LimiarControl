import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { buildCreationSetField } from "./useCharacterSheet.setters";
import { normalizeCreationAfterClassChange } from "./useCharacterSheet.creation";
import { INITIAL_SHEET } from "../model/initialSheet";
import { seedSpellCatalogCache } from "../../../entities/dnd-base";
import {
  resetCreationItemCatalogForTests,
  seedCreationItemCatalogForTests
} from "../utils/creationItemCatalog";
import { TEST_CREATION_BASE_ITEMS } from "../utils/creationItemCatalog.testData";
import { getClassCreationConfig } from "../data/classCreation";
import {
  getAvailableCreationSpells,
  getCreationSpellLimits
} from "../utils/creationSpells";

describe("paladin and ranger creation spellcasting", () => {
  beforeEach(() => {
    seedCreationItemCatalogForTests(TEST_CREATION_BASE_ITEMS);
    seedSpellCatalogCache([
      {
        canonicalKey: "bless",
        name: "Bless",
        level: 1,
        school: "Enchantment",
        castingTime: "1 action",
        range: "9 m",
        components: "V, S, M",
        duration: "Concentration, up to 1 minute",
        concentration: true,
        ritual: false,
        description: "",
        damageType: null,
        savingThrow: null,
        classes: ["Cleric", "Paladin"]
      },
      {
        canonicalKey: "cure_wounds",
        name: "Cure Wounds",
        level: 1,
        school: "Evocation",
        castingTime: "1 action",
        range: "Touch",
        components: "V, S",
        duration: "Instantaneous",
        concentration: false,
        ritual: false,
        description: "",
        damageType: null,
        savingThrow: null,
        classes: ["Bard", "Cleric", "Druid", "Paladin", "Ranger"]
      },
      {
        canonicalKey: "detect_magic",
        name: "Detect Magic",
        level: 1,
        school: "Divination",
        castingTime: "1 action",
        range: "Self",
        components: "V, S",
        duration: "Concentration, up to 10 minutes",
        concentration: true,
        ritual: true,
        description: "",
        damageType: null,
        savingThrow: null,
        classes: ["Bard", "Cleric", "Druid", "Paladin", "Ranger", "Sorcerer", "Wizard"]
      },
      {
        canonicalKey: "animal_friendship",
        name: "Animal Friendship",
        level: 1,
        school: "Enchantment",
        castingTime: "1 action",
        range: "9 m",
        components: "V, S, M",
        duration: "24 hours",
        concentration: false,
        ritual: false,
        description: "",
        damageType: null,
        savingThrow: "WIS",
        classes: ["Bard", "Druid", "Ranger"]
      },
      {
        canonicalKey: "hunters_mark",
        name: "Hunter's Mark",
        level: 1,
        school: "Divination",
        castingTime: "1 bonus action",
        range: "27 m",
        components: "V",
        duration: "Concentration, up to 1 hour",
        concentration: true,
        ritual: false,
        description: "",
        damageType: null,
        savingThrow: null,
        classes: ["Ranger"]
      },
      {
        canonicalKey: "goodberry",
        name: "Goodberry",
        level: 1,
        school: "Transmutation",
        castingTime: "1 action",
        range: "Touch",
        components: "V, S, M",
        duration: "Instantaneous",
        concentration: false,
        ritual: false,
        description: "",
        damageType: null,
        savingThrow: null,
        classes: ["Druid", "Ranger"]
      }
    ]);
  });

  afterEach(() => {
    resetCreationItemCatalogForTests();
  });

  it("keeps paladin without spellcasting below level 2 and initializes it at level 2", () => {
    const level1Paladin = normalizeCreationAfterClassChange(
      {
        ...INITIAL_SHEET,
        level: 1,
        race: "human",
        background: "soldier"
      },
      "paladin"
    );

    expect(level1Paladin.spellcasting).toBeNull();
    expect(getCreationSpellLimits("paladin", level1Paladin.abilities, 1)).toBeNull();

    const level2Paladin = normalizeCreationAfterClassChange(
      {
        ...INITIAL_SHEET,
        level: 2,
        race: "human",
        background: "soldier"
      },
      "paladin"
    );

    expect(level2Paladin.spellcasting).toMatchObject({
      ability: "charisma",
      mode: "prepared",
      slots: {
        1: { max: 2, used: 0 }
      }
    });
    expect(level2Paladin.spellcasting?.spells).toEqual([]);
    expect(getAvailableCreationSpells("paladin", 2).leveled.map((spell) => spell.canonicalKey)).toEqual([
      "bless",
      "cure_wounds",
      "detect_magic"
    ]);
    expect(getClassCreationConfig("paladin")?.startingSpells).toBeTruthy();
    expect(getCreationSpellLimits("paladin", level2Paladin.abilities, 2)).toMatchObject({
      cantrips: 0,
      leveledSpells: 1,
      leveledMode: "prepared",
      levelOneSlots: 2,
      slots: {
        1: 2,
      },
    });
  });

  it("keeps ranger without spellcasting below level 2 and initializes it at level 2", () => {
    const level1Ranger = normalizeCreationAfterClassChange(
      {
        ...INITIAL_SHEET,
        level: 1,
        race: "human",
        background: "soldier"
      },
      "ranger"
    );

    expect(level1Ranger.spellcasting).toBeNull();
    expect(getCreationSpellLimits("ranger", level1Ranger.abilities, 1)).toBeNull();

    const level2Ranger = normalizeCreationAfterClassChange(
      {
        ...INITIAL_SHEET,
        level: 2,
        race: "human",
        background: "soldier"
      },
      "ranger"
    );

    expect(level2Ranger.spellcasting).toMatchObject({
      ability: "wisdom",
      mode: "known",
      slots: {
        1: { max: 2, used: 0 }
      }
    });
    expect(level2Ranger.spellcasting?.spells).toEqual([]);
    expect(getAvailableCreationSpells("ranger", 2).leveled.map((spell) => spell.canonicalKey)).toEqual(
      expect.arrayContaining([
        "animal_friendship",
        "cure_wounds",
        "detect_magic",
        "goodberry",
        "hunters_mark"
      ])
    );
    expect(getAvailableCreationSpells("ranger", 2).leveled).toHaveLength(5);
    expect(getClassCreationConfig("ranger")?.startingSpells).toBeTruthy();
    expect(getCreationSpellLimits("ranger", level2Ranger.abilities, 2)).toMatchObject({
      cantrips: 0,
      leveledSpells: 2,
      leveledMode: "known",
      levelOneSlots: 2
    });
  });

  it("unlocks paladin and ranger spellcasting when leveling from 1 to 2", () => {
    const setField = buildCreationSetField("creation", null);
    const level1Paladin = normalizeCreationAfterClassChange(
      { ...INITIAL_SHEET, level: 1, race: "human", background: "soldier" },
      "paladin"
    );
    const level1Ranger = normalizeCreationAfterClassChange(
      { ...INITIAL_SHEET, level: 1, race: "human", background: "soldier" },
      "ranger"
    );

    const level2Paladin = setField(level1Paladin, "level", 2);
    const level2Ranger = setField(level1Ranger, "level", 2);

    expect(level2Paladin.spellcasting?.ability).toBe("charisma");
    expect(level2Paladin.spellcasting?.mode).toBe("prepared");
    expect(level2Ranger.spellcasting?.ability).toBe("wisdom");
    expect(level2Ranger.spellcasting?.mode).toBe("known");
  });
});
