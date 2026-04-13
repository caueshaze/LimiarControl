import { describe, expect, it, afterEach } from "vitest";
import { seedSpellCatalogCache } from "../../../entities/dnd-base";
import { INITIAL_SHEET } from "../model/initialSheet";
import {
  normalizeCreationSpellSelection,
  selectCatalogSpellForSheet
} from "./creationSpells";

const BASE_SPELL = {
  campaignSpellId: null as string | null,
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
  description: "A bright streak...",
  damageType: "fire",
  savingThrow: "DEX",
  classes: ["Wizard", "Sorcerer"],
};

afterEach(() => {
  // Reset to base scope
  seedSpellCatalogCache([]);
});

describe("toSheetSpell / selectCatalogSpellForSheet", () => {
  it("includes campaignSpellId from catalog entry when scope is campaign", () => {
    seedSpellCatalogCache(
      [{ ...BASE_SPELL, campaignSpellId: "cs-fireball" }],
      "camp-1",
    );

    const result = selectCatalogSpellForSheet(
      "fireball",
      "wizard",
      "spellbook",
      "camp-1",
    );

    expect(result).not.toBeNull();
    expect(result?.campaignSpellId).toBe("cs-fireball");
    expect(result?.canonicalKey).toBe("fireball");
  });

  it("sets campaignSpellId to null for base-scope catalog entries", () => {
    seedSpellCatalogCache([{ ...BASE_SPELL, campaignSpellId: null }]);

    const result = selectCatalogSpellForSheet(
      "fireball",
      "wizard",
      "spellbook",
      null,
    );

    expect(result).not.toBeNull();
    expect(result?.campaignSpellId).toBeNull();
  });

  it("preserves existing spell id and notes when swapping catalog spell", () => {
    seedSpellCatalogCache(
      [{ ...BASE_SPELL, campaignSpellId: "cs-fireball" }],
      "camp-1",
    );

    const existing = {
      id: "existing-id",
      name: "Old Spell",
      canonicalKey: "old_spell",
      campaignSpellId: "cs-old",
      level: 1,
      school: "Abjuration",
      prepared: false,
      notes: "My note",
    };

    const result = selectCatalogSpellForSheet(
      "fireball",
      "wizard",
      "spellbook",
      "camp-1",
      existing,
    );

    expect(result?.id).toBe("existing-id");
    expect(result?.notes).toBe("My note");
    expect(result?.campaignSpellId).toBe("cs-fireball");
  });

  it("preserves campaignSpellId during creation normalization for fixed spells", () => {
    seedSpellCatalogCache(
      [
        {
          campaignSpellId: "camp-animal-friendship",
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
          campaignSpellId: "camp-hunters-mark",
          canonicalKey: "hunters_mark",
          name: "Hunter's Mark",
          level: 1,
          school: "Divination",
          castingTime: "1 bonus action",
          range: "27 m",
          components: "V",
          duration: "1 hour",
          concentration: true,
          ritual: false,
          description: "",
          damageType: null,
          savingThrow: null,
          classes: ["Ranger"],
        },
      ],
      "camp-1",
    );

    const normalized = normalizeCreationSpellSelection(
      {
        ability: "wisdom",
        mode: "known",
        slots: { 1: { max: 2, used: 0 } },
        spells: [
          {
            id: "spell-1",
            name: "Animal Friendship",
            canonicalKey: "animal_friendship",
            campaignSpellId: "camp-animal-friendship",
            level: 1,
            school: "Enchantment",
            prepared: true,
            notes: "",
          },
          {
            id: "spell-2",
            name: "Hunter's Mark",
            canonicalKey: "hunters_mark",
            campaignSpellId: "camp-hunters-mark",
            level: 1,
            school: "Divination",
            prepared: true,
            notes: "",
          },
        ],
      },
      "guardian",
      INITIAL_SHEET.abilities,
      2,
      "camp-1",
    );

    expect(normalized?.spells).toEqual([
      expect.objectContaining({
        canonicalKey: "animal_friendship",
        campaignSpellId: "camp-animal-friendship",
      }),
      expect.objectContaining({
        canonicalKey: "hunters_mark",
        campaignSpellId: "camp-hunters-mark",
      }),
    ]);
  });

  it("keeps campaign-authoritative fixed spells even when weaker identifiers drift", () => {
    seedSpellCatalogCache(
      [
        {
          campaignSpellId: "camp-animal-friendship",
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
          campaignSpellId: "camp-hunters-mark",
          canonicalKey: "hunters_mark",
          name: "Hunter's Mark",
          level: 1,
          school: "Divination",
          castingTime: "1 bonus action",
          range: "27 m",
          components: "V",
          duration: "1 hour",
          concentration: true,
          ritual: false,
          description: "",
          damageType: null,
          savingThrow: null,
          classes: ["Ranger"],
        },
      ],
      "camp-2",
    );

    const normalized = normalizeCreationSpellSelection(
      {
        ability: "wisdom",
        mode: "known",
        slots: { 1: { max: 2, used: 0 } },
        spells: [
          {
            id: "spell-1",
            name: "Outdated Spell Name",
            canonicalKey: "outdated_key",
            campaignSpellId: "camp-animal-friendship",
            level: 1,
            school: "Enchantment",
            prepared: true,
            notes: "",
          },
        ],
      },
      "guardian",
      INITIAL_SHEET.abilities,
      2,
      "camp-2",
    );

    expect(normalized?.spells).toHaveLength(2);
    expect(normalized?.spells).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          canonicalKey: "animal_friendship",
          campaignSpellId: "camp-animal-friendship",
        }),
        expect.objectContaining({
          canonicalKey: "hunters_mark",
          campaignSpellId: "camp-hunters-mark",
        }),
      ]),
    );
  });
});
