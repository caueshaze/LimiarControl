import { describe, expect, it } from "vitest";

import { seedSpellCatalogCache } from "../../../entities/dnd-base";
import { ITEM_TYPES } from "../../../entities/item";
import type { InventoryItem } from "../../../entities/inventory";
import type { Item } from "../../../entities/item";
import type { CharacterSheet } from "../../../features/character-sheet/model/characterSheet.types";
import { buildSpellOptions } from "./usePlayerCombatModeHelpers";

describe("buildSpellOptions", () => {
  it("prefers campaignSpellId over stale canonicalKey and name for sheet spell resolution", () => {
    seedSpellCatalogCache(
      [
        {
          campaignSpellId: "camp-spell-1",
          canonicalKey: "spike_growth",
          name: "Spike Growth",
          level: 2,
          school: "transmutation",
          castingTimeType: "action",
          castingTime: "1 action",
          range: "45 m",
          components: "V, S, M",
          duration: "Up to 10 minutes",
          concentration: true,
          ritual: false,
          description: "Test spell.",
          resolutionType: "control",
          targetType: "ranged", areaShape: "sphere",
          damageType: null,
          savingThrow: "DEX",
          saveSuccessOutcome: "none",
          healDice: null,
          upcast: null,
          classes: ["Druid", "Ranger"],
        },
      ],
      "camp-authority",
    );

    const playerSheet = {
      abilities: {
        strength: 10,
        dexterity: 10,
        constitution: 10,
        intelligence: 10,
        wisdom: 16,
        charisma: 10,
      },
      alignment: "neutral",
      background: "outlander",
      class: "ranger",
      classEquipmentSelections: {},
      classFeatures: [],
      classSkillChoices: [],
      classToolProficiencyChoices: [],
      conditions: {},
      currentHP: 10,
      currentWeaponId: null,
      deathSaves: { failures: 0, successes: 0 },
      equippedArmor: { armorType: "none", baseAC: 10, dexCap: null, name: "None" },
      equippedArmorItemId: null,
      equippedShield: null,
      experiencePoints: 0,
      expertiseChoices: [],
      fightingStyle: null,
      hitDiceRemaining: 2,
      hitDiceTotal: 2,
      inspiration: false,
      inventory: [],
      languageChoices: [],
      level: 2,
      maxHP: 10,
      name: "Ranger",
      pendingLevelUp: false,
      playerName: "Player",
      race: "human",
      raceConfig: {},
      raceToolProficiencyChoices: [],
      restState: "exploration",
      savingThrowProficiencies: {
        strength: false,
        dexterity: true,
        constitution: false,
        intelligence: false,
        wisdom: true,
        charisma: false,
      },
      schemaVersion: 1,
      skillProficiencies: {
        acrobatics: 0,
        animalHandling: 0,
        arcana: 0,
        athletics: 0,
        deception: 0,
        history: 0,
        insight: 0,
        intimidation: 0,
        investigation: 0,
        medicine: 0,
        nature: 0,
        perception: 0,
        performance: 0,
        persuasion: 0,
        religion: 0,
        sleightOfHand: 0,
        stealth: 0,
        survival: 1,
      },
      spellcasting: {
        ability: "wisdom",
        mode: "known",
        slots: {
          1: { max: 0, used: 0 },
          2: { max: 2, used: 0 },
        },
        spells: [
          {
            id: "spell-1",
            name: "Outdated Spell Name",
            canonicalKey: "outdated_key",
            campaignSpellId: "camp-spell-1",
            level: 2,
            school: "illusion",
            prepared: true,
            notes: "",
          },
        ],
      },
      subclass: null,
      subclassConfig: {},
      temporaryHP: 0,
      weapons: [],
      currency: { copperValue: 0 },
    } as CharacterSheet;

    expect(buildSpellOptions(playerSheet, "camp-authority")).toEqual([
      expect.objectContaining({
        id: "spell-1",
        campaignSpellId: "camp-spell-1",
        canonicalKey: "spike_growth",
        actionCost: "action",
        targetType: "ranged", areaShape: "sphere",
        savingThrow: "DEX",
        availableSlotLevels: [2],
      }),
    ]);
  });

  it("still resolves base sheet spells by canonicalKey when campaignSpellId is absent", () => {
    seedSpellCatalogCache([
      {
        campaignSpellId: null,
        canonicalKey: "magic_missile",
        name: "Magic Missile",
        level: 1,
        school: "evocation",
        castingTimeType: "action",
        castingTime: "1 action",
        range: "36 m",
        components: "V, S",
        duration: "Instantaneous",
        concentration: false,
        ritual: false,
        description: "Test spell.",
        resolutionType: "damage",
        damageType: "Force",
        savingThrow: null,
        saveSuccessOutcome: null,
        healDice: null,
        upcast: null,
        classes: ["Wizard"],
      },
    ]);

    const playerSheet = {
      spellcasting: {
        ability: "intelligence",
        mode: "known",
        slots: { 1: { max: 2, used: 0 } },
        spells: [
          {
            id: "spell-1",
            name: "Outdated Name",
            canonicalKey: "magic_missile",
            campaignSpellId: null,
            level: 1,
            school: "evocation",
            prepared: true,
            notes: "",
          },
        ],
      },
    } as CharacterSheet;

    expect(buildSpellOptions(playerSheet)).toEqual([
      expect.objectContaining({
        id: "spell-1",
        campaignSpellId: null,
        canonicalKey: "magic_missile",
        actionCost: "action",
        damageType: "Force",
        availableSlotLevels: [1],
      }),
    ]);
  });

  it("does not offer unprepared leveled known spells that backend rejects", () => {
    seedSpellCatalogCache([
      {
        campaignSpellId: null,
        canonicalKey: "magic_missile",
        name: "Magic Missile",
        level: 1,
        school: "evocation",
        castingTimeType: "action",
        castingTime: "1 action",
        range: "36 m",
        components: "V, S",
        duration: "Instantaneous",
        concentration: false,
        ritual: false,
        description: "Test spell.",
        resolutionType: "damage",
        damageType: "Force",
        savingThrow: null,
        saveSuccessOutcome: null,
        healDice: null,
        upcast: null,
        classes: ["Wizard"],
      },
      {
        campaignSpellId: null,
        canonicalKey: "fire_bolt",
        name: "Fire Bolt",
        level: 0,
        school: "evocation",
        castingTimeType: "action",
        castingTime: "1 action",
        range: "36 m",
        components: "V, S",
        duration: "Instantaneous",
        concentration: false,
        ritual: false,
        description: "Test cantrip.",
        resolutionType: "damage",
        damageType: "Fire",
        savingThrow: null,
        saveSuccessOutcome: null,
        healDice: null,
        upcast: null,
        classes: ["Wizard"],
      },
    ]);

    const playerSheet = {
      spellcasting: {
        ability: "intelligence",
        mode: "known",
        slots: { 1: { max: 2, used: 0 } },
        spells: [
          {
            id: "spell-1",
            name: "Magic Missile",
            canonicalKey: "magic_missile",
            campaignSpellId: null,
            level: 1,
            school: "evocation",
            prepared: false,
            notes: "",
          },
          {
            id: "spell-2",
            name: "Fire Bolt",
            canonicalKey: "fire_bolt",
            campaignSpellId: null,
            level: 0,
            school: "evocation",
            prepared: false,
            notes: "",
          },
        ],
      },
    } as CharacterSheet;

    expect(buildSpellOptions(playerSheet)).toEqual([
      expect.objectContaining({
        id: "spell-2",
        canonicalKey: "fire_bolt",
        level: 0,
      }),
    ]);
  });

  it("includes cast_spell magic items from inventory without requiring spellcasting", () => {
    seedSpellCatalogCache([
      {
        campaignSpellId: null,
        canonicalKey: "magic_missile",
        name: "Magic Missile",
        level: 1,
        school: "evocation",
        castingTimeType: "action",
        castingTime: "1 action",
        range: "36 m",
        components: "V, S",
        duration: "Instantaneous",
        concentration: false,
        ritual: false,
        description: "Test spell.",
        resolutionType: "damage",
        damageType: "Force",
        savingThrow: null,
        saveSuccessOutcome: null,
        healDice: null,
        upcast: null,
        classes: ["Wizard"],
      },
    ], "camp-bracelet");

    const inventory: InventoryItem[] = [
      {
        id: "inv-1",
        itemId: "item-1",
        memberId: "member-1",
        quantity: 1,
        chargesCurrent: 1,
        isEquipped: false,
      },
    ];
    const itemsById: Record<string, Item> = {
      "item-1": {
        id: "item-1",
        name: "Bracelete de Phantyr: Mísseis Mágicos",
        type: ITEM_TYPES.MAGIC,
        description: "Bracelete de uso único.",
        chargesMax: 1,
        rechargeType: "none",
        magicEffect: {
          type: "cast_spell",
          spellCanonicalKey: "magic_missile",
          castLevel: 1,
          ignoreComponents: true,
          noFreeHandRequired: true,
        },
      },
    };

    const options = buildSpellOptions(null, "camp-bracelet", inventory, itemsById);

    expect(options).toEqual([
      expect.objectContaining({
        id: "magic-item:inv-1",
        campaignSpellId: null,
        canonicalKey: "magic_missile",
        sourceType: "magic_item",
        sourceItemName: "Bracelete de Phantyr: Mísseis Mágicos",
        inventoryItemId: "inv-1",
        chargesCurrent: 1,
        chargesMax: 1,
        fixedCastLevel: 1,
        ignoreComponents: true,
        noFreeHandRequired: true,
      }),
    ]);
  });

  it("resolves campaign-backed magic item spells by campaignSpellId", () => {
    seedSpellCatalogCache(
      [
        {
          campaignSpellId: "camp-spell-1",
          canonicalKey: "spike_growth",
          name: "Spike Growth",
          level: 2,
          school: "transmutation",
          castingTimeType: "action",
          castingTime: "1 action",
          range: "45 m",
          components: "V, S, M",
          duration: "Up to 10 minutes",
          concentration: true,
          ritual: false,
          description: "Test spell.",
          resolutionType: "control",
          targetType: "ranged", areaShape: "sphere",
          damageType: null,
          savingThrow: "DEX",
          saveSuccessOutcome: "none",
          healDice: null,
          upcast: null,
          classes: ["Druid", "Ranger"],
        },
      ],
      "camp-magic-item",
    );

    const options = buildSpellOptions(
      null,
      "camp-magic-item",
      [
        {
          id: "inv-1",
          itemId: "item-1",
          memberId: "member-1",
          quantity: 1,
          chargesCurrent: 1,
          isEquipped: false,
        },
      ],
      {
        "item-1": {
          id: "item-1",
          name: "Cajado de Espinhos",
          type: ITEM_TYPES.MAGIC,
          description: "Canaliza Spike Growth.",
          chargesMax: 3,
          rechargeType: "dawn",
          magicEffect: {
            type: "cast_spell",
            campaignSpellId: "camp-spell-1",
            spellCanonicalKey: "outdated_key",
            castLevel: 2,
            ignoreComponents: true,
            noFreeHandRequired: false,
          },
        },
      },
    );

    expect(options).toEqual([
      expect.objectContaining({
        id: "magic-item:inv-1",
        campaignSpellId: "camp-spell-1",
        canonicalKey: "spike_growth",
        name: "Spike Growth",
        sourceType: "magic_item",
        actionCost: "action",
        targetType: "ranged", areaShape: "sphere",
        savingThrow: "DEX",
        availableSlotLevels: [2],
      }),
    ]);
  });

  it("does not fall back to canonicalKey when a magic item campaignSpellId is present but invalid", () => {
    seedSpellCatalogCache(
      [
        {
          campaignSpellId: "camp-spell-2",
          canonicalKey: "magic_missile",
          name: "Magic Missile",
          level: 1,
          school: "evocation",
          castingTimeType: "action",
          castingTime: "1 action",
          range: "36 m",
          components: "V, S",
          duration: "Instantaneous",
          concentration: false,
          ritual: false,
          description: "Test spell.",
          resolutionType: "damage",
          damageType: "Force",
          savingThrow: null,
          saveSuccessOutcome: null,
          healDice: null,
          upcast: null,
          classes: ["Wizard"],
        },
      ],
      "camp-magic-item-mismatch",
    );

    const options = buildSpellOptions(
      null,
      "camp-magic-item-mismatch",
      [
        {
          id: "inv-1",
          itemId: "item-1",
          memberId: "member-1",
          quantity: 1,
          chargesCurrent: 1,
          isEquipped: false,
        },
      ],
      {
        "item-1": {
          id: "item-1",
          name: "Bracelete Quebrado",
          type: ITEM_TYPES.MAGIC,
          description: "Tem uma referencia de spell quebrada.",
          chargesMax: 1,
          rechargeType: "none",
          magicEffect: {
            type: "cast_spell",
            campaignSpellId: "camp-spell-1",
            spellCanonicalKey: "magic_missile",
            castLevel: 1,
            ignoreComponents: true,
            noFreeHandRequired: true,
          },
        },
      },
    );

    expect(options).toEqual([]);
  });

  it("hides exhausted magic items from combat spell options", () => {
    seedSpellCatalogCache([
      {
        campaignSpellId: null,
        canonicalKey: "detect_magic",
        name: "Detect Magic",
        level: 1,
        school: "divination",
        castingTimeType: "action",
        castingTime: "1 action",
        range: "Self",
        components: "V, S",
        duration: "10 minutes",
        concentration: true,
        ritual: true,
        description: "Test spell.",
        resolutionType: "utility",
        damageType: null,
        savingThrow: null,
        saveSuccessOutcome: null,
        healDice: null,
        upcast: null,
        classes: ["Wizard"],
      },
    ], "camp-bracelet-exhausted");

    const options = buildSpellOptions(
      null,
      "camp-bracelet-exhausted",
      [
        {
          id: "inv-1",
          itemId: "item-1",
          memberId: "member-1",
          quantity: 1,
          chargesCurrent: 0,
          isEquipped: false,
        },
      ],
      {
        "item-1": {
          id: "item-1",
          name: "Bracelete de Phantyr: Detectar Magia",
          type: ITEM_TYPES.MAGIC,
          description: "Bracelete descarregado.",
          chargesMax: 1,
          rechargeType: "none",
          magicEffect: {
            type: "cast_spell",
            spellCanonicalKey: "detect_magic",
            castLevel: 1,
            ignoreComponents: true,
            noFreeHandRequired: true,
          },
        },
      },
    );

    expect(options).toEqual([]);
  });

  it("uses attackType rather than targetType/range to choose spell attack mode", () => {
    seedSpellCatalogCache([
      {
        campaignSpellId: null,
        canonicalKey: "thorn_whip",
        name: "Thorn Whip",
        level: 0,
        school: "transmutation",
        castingTimeType: "action",
        castingTime: "1 action",
        range: "9 m",
        rangeMeters: 9,
        components: "V, S, M",
        duration: "Instantaneous",
        concentration: false,
        ritual: false,
        description: "Test spell.",
        resolutionType: "damage",
        targetType: "ranged",
        selectionType: "creature",
        attackType: "melee_spell",
        rangeKind: "distance",
        effectTiming: "immediate",
        damageType: "Piercing",
        savingThrow: null,
        saveSuccessOutcome: null,
        healDice: null,
        upcast: null,
        classes: ["Druid"],
      },
      {
        campaignSpellId: null,
        canonicalKey: "magic_missile",
        name: "Magic Missile",
        level: 1,
        school: "evocation",
        castingTimeType: "action",
        castingTime: "1 action",
        range: "36 m",
        rangeMeters: 36,
        components: "V, S",
        duration: "Instantaneous",
        concentration: false,
        ritual: false,
        description: "Test spell.",
        resolutionType: "damage",
        targetType: "ranged",
        selectionType: "creature",
        attackType: "none",
        rangeKind: "distance",
        effectTiming: "immediate",
        damageType: "Force",
        savingThrow: null,
        saveSuccessOutcome: null,
        healDice: null,
        upcast: null,
        classes: ["Wizard"],
      },
    ]);

    const options = buildSpellOptions({
      spellcasting: {
        ability: "wisdom",
        mode: "known",
        slots: { 1: { max: 1, used: 0 } },
        spells: [
          {
            id: "spell-1",
            name: "Thorn Whip",
            canonicalKey: "thorn_whip",
            campaignSpellId: null,
            level: 0,
            school: "transmutation",
            prepared: true,
            notes: "",
          },
          {
            id: "spell-2",
            name: "Magic Missile",
            canonicalKey: "magic_missile",
            campaignSpellId: null,
            level: 1,
            school: "evocation",
            prepared: true,
            notes: "",
          },
        ],
      },
    } as CharacterSheet);

    expect(options).toEqual([
      expect.objectContaining({
        canonicalKey: "thorn_whip",
        attackType: "melee_spell",
        suggestedMode: "spell_attack",
      }),
      expect.objectContaining({
        canonicalKey: "magic_missile",
        attackType: "none",
        suggestedMode: "direct_damage",
      }),
    ]);
  });

  it("routes persistent and triggered spell semantics to utility mode", () => {
    seedSpellCatalogCache([
      {
        campaignSpellId: null,
        canonicalKey: "spike_growth",
        name: "Spike Growth",
        level: 2,
        school: "transmutation",
        castingTimeType: "action",
        castingTime: "1 action",
        range: "45 m",
        rangeMeters: 45,
        components: "V, S, M",
        duration: "Concentration, up to 10 minutes",
        concentration: true,
        ritual: false,
        description: "Test spell.",
        resolutionType: "damage",
        targetType: "ranged",
        selectionType: "point",
        areaShape: "sphere",
        attackType: "none",
        rangeKind: "distance",
        effectTiming: "persistent",
        damageType: "Piercing",
        savingThrow: null,
        saveSuccessOutcome: null,
        healDice: null,
        upcast: null,
        classes: ["Druid"],
      },
      {
        campaignSpellId: null,
        canonicalKey: "hail_of_thorns",
        name: "Hail of Thorns",
        level: 1,
        school: "conjuration",
        castingTimeType: "bonus_action",
        castingTime: "1 bonus action",
        range: "Self",
        rangeMeters: 0,
        components: "V",
        duration: "Concentration, up to 1 minute",
        concentration: true,
        ritual: false,
        description: "Test spell.",
        resolutionType: "damage",
        targetType: "self",
        selectionType: "none",
        attackType: "none",
        rangeKind: "self",
        effectTiming: "triggered",
        damageType: "Piercing",
        savingThrow: null,
        saveSuccessOutcome: null,
        healDice: null,
        upcast: null,
        classes: ["Ranger"],
      },
    ]);

    const options = buildSpellOptions({
      spellcasting: {
        ability: "wisdom",
        mode: "known",
        slots: { 1: { max: 1, used: 0 }, 2: { max: 1, used: 0 } },
        spells: [
          {
            id: "spell-1",
            name: "Spike Growth",
            canonicalKey: "spike_growth",
            campaignSpellId: null,
            level: 2,
            school: "transmutation",
            prepared: true,
            notes: "",
          },
          {
            id: "spell-2",
            name: "Hail of Thorns",
            canonicalKey: "hail_of_thorns",
            campaignSpellId: null,
            level: 1,
            school: "conjuration",
            prepared: true,
            notes: "",
          },
        ],
      },
    } as CharacterSheet);

    expect(options).toEqual([
      expect.objectContaining({
        canonicalKey: "hail_of_thorns",
        selectionType: "none",
        suggestedMode: "utility",
      }),
      expect.objectContaining({
        canonicalKey: "spike_growth",
        selectionType: "point",
        suggestedMode: "utility",
      }),
    ]);
  });
});
