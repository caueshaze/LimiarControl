import { describe, expect, it } from "vitest";

import { INITIAL_SHEET } from "./initialSheet";
import { parseCharacterSheet } from "./characterSheet.schema";

describe("characterSheet schema spell parsing", () => {
  it("preserves campaignSpellId when present on parsed sheets", () => {
    const parsed = parseCharacterSheet({
      ...INITIAL_SHEET,
      spellcasting: {
        ability: "intelligence",
        mode: "spellbook",
        slots: { 1: { max: 2, used: 0 } },
        spells: [
          {
            id: "spell-1",
            name: "Magic Missile",
            canonicalKey: "magic_missile",
            campaignSpellId: "camp-spell-1",
            level: 1,
            school: "Evocation",
            prepared: false,
            notes: "",
          },
        ],
      },
    });

    expect(parsed.spellcasting?.spells[0]?.campaignSpellId).toBe("camp-spell-1");
  });

  it("accepts legacy sheets without campaignSpellId", () => {
    const parsed = parseCharacterSheet({
      ...INITIAL_SHEET,
      spellcasting: {
        ability: "wisdom",
        mode: "prepared",
        slots: { 1: { max: 2, used: 0 } },
        spells: [
          {
            id: "spell-1",
            name: "Bless",
            canonicalKey: "bless",
            level: 1,
            school: "Enchantment",
            prepared: true,
            notes: "",
          },
        ],
      },
    });

    expect(parsed.spellcasting?.spells[0]?.canonicalKey).toBe("bless");
    expect(parsed.spellcasting?.spells[0]?.campaignSpellId).toBeUndefined();
  });
});
