import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { buildCreationSetField } from "./useCharacterSheet.setters";
import { normalizeCreationAfterClassChange } from "./useCharacterSheet.creation";
import { INITIAL_SHEET } from "../model/initialSheet";
import { computeSpellSaveDC, computeWeaponAttack } from "../utils/calculations";
import {
  seedSpellCatalogCache,
  resolveSpellSourceClassId,
  getSpellAvailabilityClassIds,
} from "../../../entities/dnd-base";
import {
  resetCreationItemCatalogForTests,
  seedCreationItemCatalogForTests
} from "../utils/creationItemCatalog";
import { TEST_CREATION_BASE_ITEMS } from "../utils/creationItemCatalog.testData";
import {
  getAvailableStartingSpells,
  selectCatalogSpellForSheet
} from "../utils/creationSpells";
import { validateCreationSheet } from "../utils/creationValidation";
import { getInitialClassEquipmentSelections } from "../utils/creationEquipment";
import {
  getClass,
  hasFightingStyleAtCreation,
  isSubclassUnlocked,
} from "../data/classes";

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
        classes: ["Ranger"]
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
        classes: ["Ranger"]
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
        classes: ["Druid", "Ranger", "Wizard"]
      },
      {
        canonicalKey: "guardian_beacon",
        name: "Guardian Beacon",
        level: 1,
        school: "Abjuration",
        castingTime: "1 action",
        range: "9 m",
        components: "V, S",
        duration: "1 minute",
        concentration: false,
        ritual: false,
        description: "",
        damageType: null,
        savingThrow: null,
        classes: ["Guardian"]
      }
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
        background: "soldier"
      },
      "guardian"
    );

    expect(sheet.spellcasting).toBeNull();
    expect(sheet.classFeatures.map((feature) => feature.id)).not.toContain(
      "spellcasting_guardian"
    );
  });

  it("builds guardian spellcasting with animal_friendship and hunters_mark fixed at level 2", () => {
    const sheet = normalizeCreationAfterClassChange(
      {
        ...INITIAL_SHEET,
        level: 2,
        race: "human",
        background: "soldier"
      },
      "guardian"
    );

    expect(sheet.spellcasting?.ability).toBe("wisdom");
    expect(sheet.spellcasting?.slots[1]).toEqual({ max: 2, used: 0 });
    expect(
      sheet.spellcasting?.spells.map((spell) => spell.canonicalKey)
    ).toEqual(["animal_friendship", "hunters_mark"]);
  });

  it("unlocks guardian spellcasting when the draft level changes from 1 to 2", () => {
    const level1Guardian = normalizeCreationAfterClassChange(
      {
        ...INITIAL_SHEET,
        level: 1,
        race: "human",
        background: "soldier"
      },
      "guardian"
    );
    const setField = buildCreationSetField("creation", null);
    const level2Guardian = setField(level1Guardian, "level", 2);

    expect(level2Guardian.spellcasting?.ability).toBe("wisdom");
    expect(level2Guardian.spellcasting?.slots[1]).toEqual({ max: 2, used: 0 });
    expect(
      level2Guardian.spellcasting?.spells.map((spell) => spell.canonicalKey)
    ).toEqual(["animal_friendship", "hunters_mark"]);
    expect(level2Guardian.classFeatures.map((feature) => feature.id)).toContain(
      "spellcasting_guardian"
    );
  });

  it("computes guardian spell save DC from wisdom and proficiency", () => {
    const level2Guardian = normalizeCreationAfterClassChange(
      {
        ...INITIAL_SHEET,
        level: 2,
        race: "human",
        background: "soldier"
      },
      "guardian"
    );

    expect(level2Guardian.spellcasting?.ability).toBe("wisdom");
    expect(
      computeSpellSaveDC(level2Guardian.level, level2Guardian.abilities.wisdom)
    ).toBe(10);

    const wiseGuardian = normalizeCreationAfterClassChange(
      {
        ...INITIAL_SHEET,
        level: 2,
        race: "human",
        background: "soldier",
        abilities: {
          ...INITIAL_SHEET.abilities,
          wisdom: 14
        }
      },
      "guardian"
    );

    expect(
      computeSpellSaveDC(wiseGuardian.level, wiseGuardian.abilities.wisdom)
    ).toBe(12);
  });

  it("builds the fixed guardian progression at level 3 including goodberry", () => {
    const sheet = normalizeCreationAfterClassChange(
      {
        ...INITIAL_SHEET,
        level: 3,
        race: "human",
        background: "soldier"
      },
      "guardian"
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
      "hunter_colossus_slayer"
    ]);
    expect(
      sheet.inventory.map((item) => ({
        name: item.name,
        quantity: item.quantity
      }))
    ).toEqual(
      expect.arrayContaining([
        { name: "Breastplate", quantity: 1 },
        { name: "Longbow", quantity: 1 },
        { name: "Quiver", quantity: 1 },
        { name: "Arrow", quantity: 20 },
        { name: "Shortsword", quantity: 2 },
        { name: "Insignia of rank", quantity: 1 },
        { name: "Trophy from fallen enemy", quantity: 1 },
        { name: "Gaming Set", quantity: 1 },
        { name: "Common clothes", quantity: 1 }
      ])
    );
    expect(sheet.spellcasting?.ability).toBe("wisdom");
    expect(sheet.spellcasting?.slots[1]).toEqual({ max: 3, used: 0 });
    expect(
      sheet.spellcasting?.spells.map((spell) => spell.canonicalKey)
    ).toEqual(["animal_friendship", "goodberry", "hunters_mark"]);
  });

  it("applies the fixed ASI at level 4 and archery to ranged attacks", () => {
    const level3Guardian = normalizeCreationAfterClassChange(
      {
        ...INITIAL_SHEET,
        level: 3,
        race: "human",
        background: "soldier"
      },
      "guardian"
    );
    const setField = buildCreationSetField("creation", null);
    const level4Guardian = setField(level3Guardian, "level", 4);
    const longbow = level4Guardian.weapons.find(
      (weapon) => weapon.name === "Arco Longo" || weapon.name === "Longbow"
    );

    expect(level4Guardian.abilities.dexterity).toBe(
      level3Guardian.abilities.dexterity + 2
    );
    expect(level4Guardian.classFeatures.map((feature) => feature.id)).toContain(
      "asi_guardian_dexterity_2"
    );
    expect(level4Guardian.spellcasting?.slots[1]).toEqual({ max: 3, used: 0 });
    expect(longbow).toBeTruthy();
    expect(
      computeWeaponAttack(
        longbow!,
        level4Guardian.abilities,
        level4Guardian.level,
        level4Guardian.fightingStyle
      )
    ).toBe(7);
  });

  it("preserves guardian class identity in saved sheet data, not rewritten to ranger", () => {
    const sheet = normalizeCreationAfterClassChange(
      {
        ...INITIAL_SHEET,
        level: 3,
        race: "human",
        background: "soldier"
      },
      "guardian"
    );

    expect(sheet.class).toBe("guardian");
    expect(sheet.subclass).toBe("hunter");

    const cls = getClass(sheet.class);
    expect(cls).toBeTruthy();
    expect(cls!.id).toBe("guardian");
    expect(cls!.name).toBe("Guardião");
    expect(cls!.spellcastingAbility).toBe("wisdom");
  });

  it("treats guardian as its own class identity in display and choice flows", () => {
    const guardianClass = getClass("guardian");
    const rangerClass = getClass("ranger");

    expect(guardianClass?.id).toBe("guardian");
    expect(guardianClass?.name).toBe("Guardião");
    expect(rangerClass?.id).toBe("ranger");
    expect(rangerClass?.name).toBe("Patrulheiro");
    expect(guardianClass?.subclassLabel).toBe("Arquétipo de Guardião");
    expect(rangerClass?.subclassLabel).toBe("Arquétipo de Patrulheiro");
    expect(hasFightingStyleAtCreation(guardianClass!, 2)).toBe(true);
    expect(isSubclassUnlocked(guardianClass!, 3)).toBe(true);
  });

  it("preserves guardian identity when leveling from 1 to 4", () => {
    const level1 = normalizeCreationAfterClassChange(
      { ...INITIAL_SHEET, level: 1, race: "human", background: "soldier" },
      "guardian"
    );
    const setField = buildCreationSetField("creation", null);
    const level2 = setField(level1, "level", 2);
    const level3 = setField(level2, "level", 3);
    const level4 = setField(level3, "level", 4);

    for (const sheet of [level1, level2, level3, level4]) {
      expect(sheet.class).toBe("guardian");
    }

    expect(level2.subclass).toBeNull();
    expect(level3.subclass).toBe("hunter");
    expect(level4.subclass).toBe("hunter");
    expect(level4.fightingStyle).toBe("archery");
  });

  it("resolves spell source class id for guardian without leaking identity", () => {
    expect(resolveSpellSourceClassId("guardian")).toBe("ranger");
    expect(resolveSpellSourceClassId("ranger")).toBe("ranger");
    expect(resolveSpellSourceClassId("wizard")).toBe("wizard");
  });

  it("builds guardian spell availability from ranger inheritance plus explicit guardian extensions", () => {
    expect(getSpellAvailabilityClassIds("guardian")).toEqual([
      "guardian",
      "ranger",
    ]);
    expect(getSpellAvailabilityClassIds("ranger")).toEqual(["ranger"]);
  });

  it("provides ranger-tagged spells for guardian through mechanics-family inheritance", () => {
    const guardianSpells = getAvailableStartingSpells("guardian");
    const rangerSpells = getAvailableStartingSpells("ranger");

    expect(guardianSpells.leveled.map((s) => s.canonicalKey)).toEqual(
      expect.arrayContaining(rangerSpells.leveled.map((s) => s.canonicalKey))
    );
    expect(guardianSpells.leveled.map((s) => s.canonicalKey)).toContain(
      "guardian_beacon"
    );
    expect(guardianSpells.leveled.length).toBeGreaterThan(0);
  });

  it("allows selecting ranger-tagged catalog spells for guardian sheets", () => {
    const spell = selectCatalogSpellForSheet(
      "animal_friendship",
      "guardian",
      "known"
    );
    expect(spell).not.toBeNull();
    expect(spell!.canonicalKey).toBe("animal_friendship");
    expect(spell!.name).toBe("Animal Friendship");
  });

  it("allows selecting guardian-only catalog spells for guardian sheets", () => {
    const spell = selectCatalogSpellForSheet(
      "guardian_beacon",
      "guardian",
      "known"
    );
    expect(spell).not.toBeNull();
    expect(spell!.canonicalKey).toBe("guardian_beacon");
    expect(spell!.name).toBe("Guardian Beacon");
  });

  it("does not expose guardian-only catalog spells to ranger sheets", () => {
    const spell = selectCatalogSpellForSheet(
      "guardian_beacon",
      "ranger",
      "known"
    );
    expect(spell).toBeNull();
  });

  it("does not allow non-ranger spells for guardian sheets", () => {
    seedSpellCatalogCache([
      ...currentSeedSpells(),
      {
        canonicalKey: "fireball",
        name: "Fireball",
        level: 3,
        school: "Evocation",
        castingTime: "1 action",
        range: "45 m",
        components: "V, S, M",
        duration: "Instantaneous",
        concentration: false,
        ritual: false,
        description: "",
        damageType: "Fire",
        savingThrow: "DEX",
        classes: ["Wizard", "Sorcerer"]
      }
    ]);
    const spell = selectCatalogSpellForSheet("fireball", "guardian", "known");
    expect(spell).toBeNull();
  });

  it("validates guardian level 2 creation without manual spell picks", () => {
    const sheet = normalizeCreationAfterClassChange(
      { ...INITIAL_SHEET, level: 2, race: "human", background: "soldier" },
      "guardian"
    );
    const result = validateCreationSheet({
      ...sheet,
      name: "Test",
      alignment: "Neutral",
      playerName: "Player",
      classSkillChoices: getClass("guardian")!.skillChoices.slice(0, 3),
      classEquipmentSelections: getInitialClassEquipmentSelections("guardian")
    });
    expect(result.missingRequiredFields).not.toContain("leveledSpells");
  });

  it("does not require manual subclass or fighting style choices for guardian", () => {
    const sheet = normalizeCreationAfterClassChange(
      { ...INITIAL_SHEET, level: 3, race: "human", background: "soldier" },
      "guardian"
    );
    const result = validateCreationSheet({
      ...sheet,
      name: "Guardian",
      alignment: "Neutral",
      playerName: "Player",
      classSkillChoices: getClass("guardian")!.skillChoices.slice(0, 3),
      classEquipmentSelections: getInitialClassEquipmentSelections("guardian"),
    });

    expect(result.missingRequiredFields).not.toContain("subclass");
    expect(result.missingRequiredFields).not.toContain("fightingStyle");
  });

  it("keeps ranger normal choice flows independent from guardian", () => {
    const ranger = normalizeCreationAfterClassChange(
      { ...INITIAL_SHEET, level: 3, race: "human", background: "soldier" },
      "ranger"
    );
    const result = validateCreationSheet({
      ...ranger,
      name: "Ranger",
      alignment: "Neutral",
      playerName: "Player",
      classSkillChoices: getClass("ranger")!.skillChoices.slice(0, 3),
      classEquipmentSelections: getInitialClassEquipmentSelections("ranger"),
    });

    expect(ranger.class).toBe("ranger");
    expect(ranger.subclass).toBeNull();
    expect(ranger.fightingStyle).toBeNull();
    expect(ranger.classFeatures).toEqual([]);
    expect(result.missingRequiredFields).toContain("subclass");
    expect(result.missingRequiredFields).toContain("fightingStyle");
  });

  it("maintains consistent spellcasting through level 4 progression", () => {
    const level2 = normalizeCreationAfterClassChange(
      { ...INITIAL_SHEET, level: 2, race: "human", background: "soldier" },
      "guardian"
    );
    const setField = buildCreationSetField("creation", null);
    const level3 = setField(level2, "level", 3);
    const level4 = setField(level3, "level", 4);

    expect(level2.spellcasting).not.toBeNull();
    expect(level3.spellcasting).not.toBeNull();
    expect(level4.spellcasting).not.toBeNull();

    expect(level2.spellcasting!.ability).toBe("wisdom");
    expect(level3.spellcasting!.ability).toBe("wisdom");
    expect(level4.spellcasting!.ability).toBe("wisdom");

    expect(level2.spellcasting!.spells.map((s) => s.canonicalKey)).toEqual([
      "animal_friendship",
      "hunters_mark"
    ]);
    expect(level3.spellcasting!.spells.map((s) => s.canonicalKey)).toEqual([
      "animal_friendship",
      "goodberry",
      "hunters_mark"
    ]);
    expect(level4.spellcasting!.spells.map((s) => s.canonicalKey)).toEqual([
      "animal_friendship",
      "goodberry",
      "hunters_mark"
    ]);
    expect(level4.spellcasting!.slots[1]).toEqual({ max: 3, used: 0 });
  });
});

const currentSeedSpells = () => [
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
    classes: ["Ranger"]
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
    classes: ["Druid", "Ranger", "Wizard"]
  }
];
