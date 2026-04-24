import { describe, expect, it } from "vitest";
import { SpellSchool, type BaseSpell } from "../../../entities/base-spell";
import {
  buildSpellCreatePayload,
  buildSpellUpdatePayload,
  createEmptySpellEditorState,
  createSpellEditorState,
  getUnsupportedSpellEditorValues,
  normalizeSpellCanonicalKey,
} from "./spellCatalogForm";

const createSpell = (overrides: Partial<BaseSpell> = {}): BaseSpell => ({
  id: "spell-1",
  system: "DND5E",
  canonicalKey: "magic_missile",
  nameEn: "Magic Missile",
  namePt: "Missil Magico",
  descriptionEn: "Three glowing darts of magical force.",
  descriptionPt: "Tres dardos de energia magica.",
  level: 1,
  school: SpellSchool.EVOCATION,
  classesJson: ["Wizard", "Sorcerer"],
  castingTime: "1 action",
  rangeMeters: 36,
  rangeText: "36 m",
  duration: "Instantaneous",
  componentsJson: ["V", "S", "M"],
  materialComponentText: "A bit of phosphorus.",
  concentration: false,
  ritual: false,
  damageType: null,
  savingThrow: null,
  saveSuccessOutcome: null,
  source: "seed_json_bootstrap",
  sourceRef: null,
  isSrd: true,
  isActive: true,
  aliases: [],
  ...overrides,
});

describe("spellCatalogForm", () => {
  it("filters unsupported legacy values from the editor state", () => {
    const state = createSpellEditorState(
      createSpell({
        classesJson: ["Wizard", "Psion"],
        componentsJson: ["V", "X"],
        damageType: "Void" as any,
        savingThrow: "LCK" as any,
        saveSuccessOutcome: "quarter_damage" as any,
      }),
    );

    expect(state.classesJson).toEqual(["Wizard"]);
    expect(state.componentsJson).toEqual(["V"]);
    expect(state.damageType).toBe("");
    expect(state.savingThrow).toBe("");
    expect(state.saveSuccessOutcome).toBe("");
  });

  it("reports unsupported legacy values", () => {
    expect(
      getUnsupportedSpellEditorValues(
        createSpell({
          classesJson: ["Wizard", "Psion"],
          componentsJson: ["V", "X"],
          damageType: "Void" as any,
          saveSuccessOutcome: "quarter_damage" as any,
        }),
      ),
    ).toEqual(["Psion", "X", "Void", "quarter_damage"]);
  });

  it("clears material component text when M is not selected", () => {
    const payload = buildSpellUpdatePayload({
      ...createSpellEditorState(createSpell()),
      componentsJson: ["V", "S"],
      materialComponentText: "A bit of phosphorus.",
    });

    expect(payload.componentsJson).toEqual(["V", "S"]);
    expect(payload.materialComponentText).toBeNull();
    expect(payload.rangeMeters).toBe(36);
    expect(payload).not.toHaveProperty("canonicalKey");
  });

  it("builds campaign spell create payload with normalized canonical key", () => {
    const payload = buildSpellCreatePayload({
      ...createEmptySpellEditorState(),
      canonicalKey: "  Relampago do Cão  ",
      nameEn: "  Hound Lightning  ",
      descriptionEn: "  Strikes a spectral hound with lightning.  ",
      descriptionPt: "  Atinge um cao espectral com relampago.  ",
      level: 2,
      school: SpellSchool.EVOCATION,
      classesJson: ["Wizard"],
      castingTimeType: "bonus_action",
      rangeMeters: "18",
      rangeText: "18 m",
      targetType: "ranged", areaShape: "sphere",
      resolutionType: "damage",
      damageDice: "3d6",
      damageType: "Lightning",
      savingThrow: "DEX",
      saveSuccessOutcome: "half_damage",
      requiresTargetSight: false,
      requiresTargetEffect: true,
      requiresPointSight: true,
      requiresPointEffect: false,
      upcastMode: "extra_damage_dice",
      upcastDice: "1d6",
      upcastPerLevel: "1",
      upcastMaxLevel: "5",
    });

    expect(payload).toEqual(
      expect.objectContaining({
        canonicalKey: "relampago_do_cao",
        nameEn: "Hound Lightning",
        descriptionEn: "Strikes a spectral hound with lightning.",
        descriptionPt: "Atinge um cao espectral com relampago.",
        level: 2,
        school: SpellSchool.EVOCATION,
        classesJson: ["Wizard"],
        castingTimeType: "bonus_action",
        castingTime: "1 bonus action",
        rangeMeters: 18,
        rangeText: "18 m",
        targetType: "ranged", areaShape: "sphere",
        resolutionType: "damage",
        damageDice: "3d6",
        damageType: "Lightning",
        savingThrow: "DEX",
        saveSuccessOutcome: "half_damage",
        requiresTargetSight: false,
        requiresTargetEffect: true,
        requiresPointSight: true,
        requiresPointEffect: false,
        upcast: {
          mode: "extra_damage_dice",
          dice: "1d6",
          flat: null,
          perLevel: 1,
          maxLevel: 5,
          scalingKey: null,
          scalingSummary: null,
          scalingEditorial: null,
          unlockKey: null,
          unlockSummary: null,
          unlockEditorial: null,
        },
      }),
    );
  });

  it("hydrates structured combat fields from an existing spell", () => {
    const state = createSpellEditorState(
      createSpell({
        castingTimeType: "special",
        castingTime: "When an ally falls to 0 HP",
        targetType: "ranged",
        resolutionType: "heal",
        healDice: "2d4",
        requiresTargetSight: null,
        requiresTargetEffect: true,
        requiresPointSight: null,
        requiresPointEffect: false,
        upcast: {
          mode: "extra_heal_dice",
          dice: "1d4",
          perLevel: 1,
          maxLevel: 6,
        },
      }),
    );

    expect(state.castingTimeType).toBe("special");
    expect(state.castingTime).toBe("When an ally falls to 0 HP");
    expect(state.targetType).toBe("ranged");
    expect(state.resolutionType).toBe("heal");
    expect(state.healDice).toBe("2d4");
    expect(state.requiresTargetSight).toBeNull();
    expect(state.requiresTargetEffect).toBe(true);
    expect(state.requiresPointSight).toBeNull();
    expect(state.requiresPointEffect).toBe(false);
    expect(state.upcastMode).toBe("extra_heal_dice");
    expect(state.upcastDice).toBe("1d4");
    expect(state.upcastPerLevel).toBe("1");
    expect(state.upcastMaxLevel).toBe("6");
  });

  it("preserves structured targeting and upcast fields when building an update payload", () => {
    const payload = buildSpellUpdatePayload({
      ...createSpellEditorState(
        createSpell({
          castingTimeType: "special",
          castingTime: "When an ally falls to 0 HP",
          targetType: "ranged",
          resolutionType: "heal",
          healDice: "2d4",
          requiresTargetSight: null,
          requiresTargetEffect: true,
          requiresPointSight: null,
          requiresPointEffect: false,
          upcast: {
            mode: "extra_heal_dice",
            dice: "1d4",
            perLevel: 1,
            maxLevel: 6,
          },
        }),
      ),
    });

    expect(payload.castingTimeType).toBe("special");
    expect(payload.castingTime).toBe("When an ally falls to 0 HP");
    expect(payload.targetType).toBe("ranged");
    expect(payload.resolutionType).toBe("heal");
    expect(payload.damageDice).toBeNull();
    expect(payload.healDice).toBe("2d4");
    expect(payload.requiresTargetSight).toBeNull();
    expect(payload.requiresTargetEffect).toBe(true);
    expect(payload.requiresPointSight).toBeNull();
    expect(payload.requiresPointEffect).toBe(false);
    expect(payload.upcast).toEqual({
      mode: "extra_heal_dice",
      dice: "1d4",
      flat: null,
      perLevel: 1,
      maxLevel: 6,
      scalingKey: null,
      scalingSummary: null,
      scalingEditorial: null,
      unlockKey: null,
      unlockSummary: null,
      unlockEditorial: null,
    });
  });

  it("keeps canonical key normalization deterministic", () => {
    expect(normalizeSpellCanonicalKey(" Détect Magic!!! ")).toBe("detect_magic");
  });

  // --- explicit dimension fields ---

  it("hydrates radiusMeters from new field for sphere", () => {
    const state = createSpellEditorState(
      createSpell({ areaShape: "sphere", radiusMeters: 6, areaSizeMeters: null }),
    );
    expect(state.radiusMeters).toBe("6");
    expect(state.areaSizeMeters).toBe("");
  });

  it("falls back to areaSizeMeters for sphere when radiusMeters is absent", () => {
    const state = createSpellEditorState(
      createSpell({ areaShape: "sphere", radiusMeters: null, areaSizeMeters: 6 }),
    );
    expect(state.radiusMeters).toBe("6");
  });

  it("hydrates lengthMeters from new field for cone", () => {
    const state = createSpellEditorState(
      createSpell({ areaShape: "cone", lengthMeters: 9, areaSizeMeters: null }),
    );
    expect(state.lengthMeters).toBe("9");
    expect(state.radiusMeters).toBe("");
    expect(state.sideMeters).toBe("");
  });

  it("hydrates sideMeters from new field for cube", () => {
    const state = createSpellEditorState(
      createSpell({ areaShape: "cube", sideMeters: 4.5, areaSizeMeters: null }),
    );
    expect(state.sideMeters).toBe("4.5");
  });

  it("buildSpellUpdatePayload emits radiusMeters for sphere", () => {
    const state = {
      ...createSpellEditorState(
        createSpell({ areaShape: "sphere", radiusMeters: 6, areaSizeMeters: null }),
      ),
    };
    const payload = buildSpellUpdatePayload(state);
    expect(payload.radiusMeters).toBe(6);
    expect(payload.lengthMeters).toBeNull();
    expect(payload.sideMeters).toBeNull();
  });

  it("buildSpellUpdatePayload emits lengthMeters for cone", () => {
    const state = createSpellEditorState(
      createSpell({ areaShape: "cone", lengthMeters: 9, areaSizeMeters: null }),
    );
    const payload = buildSpellUpdatePayload(state);
    expect(payload.lengthMeters).toBe(9);
    expect(payload.radiusMeters).toBeNull();
    expect(payload.sideMeters).toBeNull();
  });

  it("buildSpellUpdatePayload emits sideMeters for cube", () => {
    const state = createSpellEditorState(
      createSpell({ areaShape: "cube", sideMeters: 4.5, areaSizeMeters: null }),
    );
    const payload = buildSpellUpdatePayload(state);
    expect(payload.sideMeters).toBe(4.5);
    expect(payload.radiusMeters).toBeNull();
    expect(payload.lengthMeters).toBeNull();
  });

  it("buildSpellUpdatePayload emits null dimension fields when no areaShape", () => {
    const state = createSpellEditorState(createSpell({ areaShape: null }));
    const payload = buildSpellUpdatePayload(state);
    expect(payload.radiusMeters).toBeNull();
    expect(payload.lengthMeters).toBeNull();
    expect(payload.sideMeters).toBeNull();
  });

  it("initializes all dimension fields as empty string for new spells", () => {
    const state = createEmptySpellEditorState();
    expect(state.radiusMeters).toBe("");
    expect(state.lengthMeters).toBe("");
    expect(state.sideMeters).toBe("");
    expect(state.areaSizeMeters).toBe("");
  });

  it("buildSpellUpdatePayload never serializes areaSizeMeters", () => {
    // New spells must not send the deprecated field — the backend still accepts
    // it for compat, but the frontend should stop emitting it so the contract
    // is explicit-fields-only going forward.
    const withArea = buildSpellUpdatePayload(
      createSpellEditorState(createSpell({ areaShape: "sphere", radiusMeters: 6 })),
    );
    expect(Object.prototype.hasOwnProperty.call(withArea, "areaSizeMeters")).toBe(false);

    const noArea = buildSpellUpdatePayload(
      createSpellEditorState(createSpell({ areaShape: null })),
    );
    expect(Object.prototype.hasOwnProperty.call(noArea, "areaSizeMeters")).toBe(false);
  });

  it("buildSpellUpdatePayload accepts decimal dimension (4.5m = 3 cells clean)", () => {
    const state = createSpellEditorState(
      createSpell({ areaShape: "cone", lengthMeters: 4.5, areaSizeMeters: null }),
    );
    expect(state.lengthMeters).toBe("4.5");
    const payload = buildSpellUpdatePayload(state);
    expect(payload.lengthMeters).toBe(4.5);
  });
});
