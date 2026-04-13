import { describe, expect, it, afterEach } from "vitest";
import { seedSpellCatalogCache } from "../../../entities/dnd-base";
import { selectCatalogSpellForSheet } from "./creationSpells";

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
});
