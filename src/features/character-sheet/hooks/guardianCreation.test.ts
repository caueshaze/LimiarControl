import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { buildCreationSetField } from "./useCharacterSheet.setters";
import { normalizeCreationAfterClassChange } from "./useCharacterSheet.creation";
import { INITIAL_SHEET } from "../model/initialSheet";
import { computeSpellSaveDC, computeWeaponAttack } from "../utils/calculations";
import { seedSpellCatalogCache } from "../../../entities/dnd-base";
import {
  resetCreationItemCatalogForTests,
  seedCreationItemCatalogForTests,
} from "../utils/creationItemCatalog";
import { TEST_CREATION_BASE_ITEMS } from "../utils/creationItemCatalog.testData";

describe("guardian creation flow", () => {
  beforeEach(() => {
    seedCreationItemCatalogForTests(TEST_CREATION_BASE_ITEMS);
    seedSpellCatalogCache([
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
        classes: ["Ranger"],
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
        classes: ["Bard", "Druid", "Ranger"],
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
        classes: ["Druid", "Ranger"],
      },
      {
        canonicalKey: "ensnaring_strike",
        name: "Ensnaring Strike",
        level: 1,
        school: "Conjuration",
        castingTime: "1 bonus action",
        range: "Self",
        components: "V",
        duration: "Concentration, up to 1 minute",
        concentration: true,
        ritual: false,
        description: "",
        damageType: null,
        savingThrow: "STR",
        classes: ["Ranger"],
      },
      {
        canonicalKey: "longstrider",
        name: "Longstrider",
        level: 1,
        school: "Transmutation",
        castingTime: "1 action",
        range: "Touch",
        components: "V, S, M",
        duration: "1 hour",
        concentration: false,
        ritual: false,
        description: "",
        damageType: null,
        savingThrow: null,
        classes: ["Druid", "Ranger", "Wizard"],
      },
    ]);
  });

  afterEach(() => {
    resetCreationItemCatalogForTests();
  });

  it("keeps guardian without spellcasting at level 1", () => {
    const sheet = normalizeCreationAfterClassChange(
      {
        ...INITIAL_SHEET,
        level: 1,
        race: "human",
        background: "soldier",
      },
      "guardian",
    );

    expect(sheet.spellcasting).toBeNull();
    expect(sheet.classFeatures.map((feature) => feature.id)).not.toContain("spellcasting_guardian");
  });

  it("builds guardian spellcasting with hunters_mark fixed and 1 open choice at level 2", () => {
    const sheet = normalizeCreationAfterClassChange(
      {
        ...INITIAL_SHEET,
        level: 2,
        race: "human",
        background: "soldier",
      },
      "guardian",
    );

    expect(sheet.spellcasting?.ability).toBe("wisdom");
    expect(sheet.spellcasting?.slots[1]).toEqual({ max: 2, used: 0 });
    // hunters_mark is the only fixed spell; player must choose 1 more from the catalog
    expect(sheet.spellcasting?.spells.map((spell) => spell.canonicalKey)).toEqual(["hunters_mark"]);
  });

  it("unlocks guardian spellcasting when the draft level changes from 1 to 2", () => {
    const level1Guardian = normalizeCreationAfterClassChange(
      {
        ...INITIAL_SHEET,
        level: 1,
        race: "human",
        background: "soldier",
      },
      "guardian",
    );
    const setField = buildCreationSetField("creation", null);
    const level2Guardian = setField(level1Guardian, "level", 2);

    expect(level2Guardian.spellcasting?.ability).toBe("wisdom");
    expect(level2Guardian.spellcasting?.slots[1]).toEqual({ max: 2, used: 0 });
    expect(level2Guardian.spellcasting?.spells.map((spell) => spell.canonicalKey)).toEqual(["hunters_mark"]);
    expect(level2Guardian.classFeatures.map((feature) => feature.id)).toContain("spellcasting_guardian");
  });

  it("computes guardian spell save DC from wisdom and proficiency", () => {
    const level2Guardian = normalizeCreationAfterClassChange(
      {
        ...INITIAL_SHEET,
        level: 2,
        race: "human",
        background: "soldier",
      },
      "guardian",
    );

    expect(level2Guardian.spellcasting?.ability).toBe("wisdom");
    expect(computeSpellSaveDC(level2Guardian.level, level2Guardian.abilities.wisdom)).toBe(10);

    const wiseGuardian = normalizeCreationAfterClassChange(
      {
        ...INITIAL_SHEET,
        level: 2,
        race: "human",
        background: "soldier",
        abilities: {
          ...INITIAL_SHEET.abilities,
          wisdom: 14,
        },
      },
      "guardian",
    );

    expect(computeSpellSaveDC(wiseGuardian.level, wiseGuardian.abilities.wisdom)).toBe(12);
  });

  it("builds the fixed guardian progression at level 3", () => {
    const sheet = normalizeCreationAfterClassChange(
      {
        ...INITIAL_SHEET,
        level: 3,
        race: "human",
        background: "soldier",
      },
      "guardian",
    );

    expect(sheet.subclass).toBe("hunter");
    expect(sheet.fightingStyle).toBe("archery");
    expect(sheet.classFeatures.map((feature) => feature.id)).toEqual([
      "favored_enemy_beasts",
      "natural_explorer_forest",
      "fighting_style_archery",
      "spellcasting_guardian",
      "primeval_awareness",
      "subclass_hunter",
      "hunter_colossus_slayer",
    ]);
    expect(sheet.inventory.map((item) => ({ name: item.name, quantity: item.quantity }))).toEqual(expect.arrayContaining([
      { name: "Breastplate", quantity: 1 },
      { name: "Longbow", quantity: 1 },
      { name: "Quiver", quantity: 1 },
      { name: "Arrow", quantity: 20 },
      { name: "Shortsword", quantity: 2 },
      { name: "Insignia of rank", quantity: 1 },
      { name: "Trophy from fallen enemy", quantity: 1 },
      { name: "Gaming Set", quantity: 1 },
      { name: "Common clothes", quantity: 1 },
    ]));
    expect(sheet.spellcasting?.ability).toBe("wisdom");
    expect(sheet.spellcasting?.slots[1]).toEqual({ max: 3, used: 0 });
    // hunters_mark is always present; player may choose up to 2 additional spells from catalog
    expect(sheet.spellcasting?.spells.map((spell) => spell.canonicalKey)).toContain("hunters_mark");
  });

  it("applies the fixed ASI at level 4 and archery to ranged attacks", () => {
    const level3Guardian = normalizeCreationAfterClassChange(
      {
        ...INITIAL_SHEET,
        level: 3,
        race: "human",
        background: "soldier",
      },
      "guardian",
    );
    const setField = buildCreationSetField("creation", null);
    const level4Guardian = setField(level3Guardian, "level", 4);
    const longbow = level4Guardian.weapons.find((weapon) => weapon.name === "Arco Longo" || weapon.name === "Longbow");

    expect(level4Guardian.abilities.dexterity).toBe(level3Guardian.abilities.dexterity + 2);
    expect(level4Guardian.classFeatures.map((feature) => feature.id)).toContain("asi_guardian_dexterity_2");
    expect(level4Guardian.spellcasting?.slots[1]).toEqual({ max: 3, used: 0 });
    expect(longbow).toBeTruthy();
    expect(computeWeaponAttack(longbow!, level4Guardian.abilities, level4Guardian.level, level4Guardian.fightingStyle)).toBe(7);
  });
});
