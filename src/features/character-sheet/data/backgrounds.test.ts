import { describe, expect, it } from "vitest";

import { BACKGROUNDS, getBackground } from "./backgrounds";
import { LANGUAGE_CHOICE_SLOT } from "./languages";

describe("backgrounds", () => {
  it("uses snake_case ids for exported backgrounds", () => {
    expect(BACKGROUNDS.every((background) => !background.id.includes("-"))).toBe(true);
  });

  it("keeps aliases for legacy hyphenated background ids", () => {
    expect(getBackground("folk-hero")?.id).toBe("folk_hero");
    expect(getBackground("guild-artisan")?.id).toBe("guild_artisan");
  });

  it("structures background features instead of plain text", () => {
    const acolyte = getBackground("acolyte");

    expect(acolyte?.feature).toEqual({
      id: "shelter_of_the_faithful",
      label: "Abrigo dos Fiéis",
      description: "Você recebe apoio básico de templos e fiéis da sua religião.",
    });
  });

  it("stores tool proficiencies as canonical keys and exposes display labels", () => {
    const sailor = getBackground("sailor");

    expect(sailor?.toolProficiencyCanonicalKeys).toEqual([
      "navigators_tools",
      "vehicles_water",
    ]);
    expect(sailor?.toolProficiencies).toEqual([
      "Ferramentas de Navegação",
      "Veículos (aquáticos)",
    ]);
  });

  it("uses canonical starter tokens for background equipment", () => {
    const acolyte = getBackground("acolyte");
    const folkHero = getBackground("folk_hero");

    expect(acolyte?.startingEquipment).toEqual([
      "catalog:holy_symbol",
      "catalog:prayer_book",
      "catalog:incense x5",
      "catalog:vestments",
      "catalog:common_clothes",
      "15 gp",
    ]);
    expect(folkHero?.startingEquipment).toContain("catalog:artisans_tools");
  });

  it("preserves PHB language choice slots where backgrounds grant free languages", () => {
    const acolyte = getBackground("acolyte");
    const sage = getBackground("sage");

    expect(acolyte?.languages).toEqual([LANGUAGE_CHOICE_SLOT, LANGUAGE_CHOICE_SLOT]);
    expect(sage?.languages).toEqual([LANGUAGE_CHOICE_SLOT, LANGUAGE_CHOICE_SLOT]);
  });

  it("matches the PHB tool setup for criminal", () => {
    const criminal = getBackground("criminal");

    expect(criminal?.toolProficiencyCanonicalKeys).toEqual([
      "thieves_tools",
      "gaming_set",
    ]);
  });
});
