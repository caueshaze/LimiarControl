import { describe, expect, it } from "vitest";

import { getRace, normalizeRaceState, RACES } from "./races";

describe("races model", () => {
  it("exposes gnome as a selectable base race", () => {
    expect(RACES.some((race) => race.id === "gnome")).toBe(true);
    expect(RACES.some((race) => race.id === "forest-gnome")).toBe(false);
    expect(RACES.some((race) => race.id === "rock-gnome")).toBe(false);
  });

  it("derives the forest gnome bonuses from raceConfig", () => {
    const race = getRace("gnome", { gnomeSubrace: "forest" });

    expect(race?.name).toBe("Gnomo da Floresta");
    expect(race?.abilityBonuses).toMatchObject({
      intelligence: 2,
      dexterity: 1,
    });
  });

  it("normalizes legacy gnome aliases into the new race model", () => {
    expect(normalizeRaceState("forest-gnome", null)).toEqual({
      raceId: "gnome",
      raceConfig: { gnomeSubrace: "forest" },
    });
  });

  it("normalizes legacy dragonborn ancestry config into draconicAncestry", () => {
    expect(normalizeRaceState("dragonborn", { dragonbornAncestry: "red" })).toEqual({
      raceId: "dragonborn",
      raceConfig: { draconicAncestry: "red" },
    });
  });

  it("derives dragonborn ancestry mechanics from raceConfig", () => {
    const race = getRace("dragonborn", { draconicAncestry: "silver" });

    expect(race?.name).toBe("Draconato (Prata)");
    expect(race?.traits).toContain("Ancestralidade Dracônica: Prata");
    expect(race?.traits).toContain("Resistência: Frio");
    expect(race?.traits).toContain("Sopro de Dragão: Frio, cone 4.5m, teste Constituição");
  });

  it("derives half-elf bonuses and skill versatility from raceConfig", () => {
    const race = getRace("half-elf", {
      halfElfAbilityChoices: ["constitution", "wisdom"],
      halfElfSkillChoices: ["insight", "persuasion"],
    });

    expect(race?.abilityBonuses).toMatchObject({
      charisma: 2,
      constitution: 1,
      wisdom: 1,
    });
    expect(race?.skillProficiencies).toEqual(["insight", "persuasion"]);
    expect(race?.traits).toContain("Ancestralidade Feérica");
    expect(race?.traits).toContain("Versatilidade em Perícias");
  });

  it("keeps half-elf incomplete state semantically safe when raceConfig is missing", () => {
    const race = getRace("half-elf", null);

    expect(race?.abilityBonuses).toEqual({ charisma: 2 });
    expect(race?.skillProficiencies).toEqual([]);
    expect(race?.traits).toContain("Ancestralidade Feérica");
    expect(race?.traits).toContain("Versatilidade em Perícias");
  });

  it("exposes half-orc racial rules as structured features", () => {
    const race = getRace("half-orc");
    const relentlessEndurance = race?.structuredFeatures.find((feature) => feature.id === "relentless_endurance");
    const savageAttacks = race?.structuredFeatures.find((feature) => feature.id === "savage_attacks");

    expect(race?.skillProficiencies).toContain("intimidation");
    expect(relentlessEndurance).toMatchObject({
      kind: "rule",
      ruleId: "relentless_endurance",
      trigger: "on_drop_to_zero_hp",
      effect: "set_hp_to_1",
      uses: 1,
      recharge: "long_rest",
    });
    expect(savageAttacks).toMatchObject({
      kind: "rule",
      ruleId: "savage_attacks",
      trigger: "on_melee_critical_hit",
      effect: "extra_weapon_damage_die",
    });
    expect(race?.traits).toContain("Ameaçador");
    expect(race?.traits).toContain("Resistência Implacável");
    expect(race?.traits).toContain("Ataques Selvagens");
  });

  it("exposes tiefling resistance and infernal legacy as structured features", () => {
    const race = getRace("tiefling");
    const infernalResistance = race?.structuredFeatures.find((feature) => feature.id === "infernal_resistance");
    const thaumaturgy = race?.structuredFeatures.find((feature) => feature.id === "thaumaturgy");
    const hellishRebuke = race?.structuredFeatures.find((feature) => feature.id === "hellish_rebuke");
    const darkness = race?.structuredFeatures.find((feature) => feature.id === "darkness");

    expect(infernalResistance).toMatchObject({
      kind: "rule",
      ruleId: "infernal_resistance",
      effect: "damage_resistance",
      damageType: "fire",
    });
    expect(thaumaturgy).toMatchObject({
      kind: "spell",
      spellCanonicalKey: "thaumaturgy",
      ability: "charisma",
      minLevel: 1,
      known: true,
    });
    expect(hellishRebuke).toMatchObject({
      kind: "spell",
      spellCanonicalKey: "hellish_rebuke",
      ability: "charisma",
      minLevel: 3,
      uses: 1,
      recharge: "long_rest",
      castAtLevel: 2,
    });
    expect(darkness).toMatchObject({
      kind: "spell",
      spellCanonicalKey: "darkness",
      ability: "charisma",
      minLevel: 5,
      uses: 1,
      recharge: "long_rest",
    });
    expect(race?.traits).toContain("Resistência Infernal");
    expect(race?.traits).toContain("Thaumaturgy");
    expect(race?.traits).toContain("Hellish Rebuke");
    expect(race?.traits).toContain("Darkness");
  });
});
