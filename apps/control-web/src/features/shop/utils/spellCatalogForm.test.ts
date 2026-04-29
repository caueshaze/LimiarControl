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
  maxTargets: null,
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
  effects: null,
  onEndEffects: null,
  persistentArea: null,
  isSrd: true,
  isActive: true,
  aliases: [],
  ...overrides,
});

describe("spellCatalogForm", () => {
  it("filters unsupported legacy values from the editor state", () => {
    const state = createSpellEditorState(
      createSpell({
        classesJson: ["Wizard", "Guardian", "Psion"],
        componentsJson: ["V", "X"],
        damageType: "Void" as any,
        savingThrow: "LCK" as any,
        saveSuccessOutcome: "quarter_damage" as any,
      }),
    );

    expect(state.classesJson).toEqual(["Wizard", "Guardian"]);
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
      targetType: "ranged",
      maxTargets: "3",
      areaShape: "sphere",
      resolutionType: "damage",
      damageDiceCount: "3",
      damageDieSize: "6",
      damageFixedBonus: "",
      damageType: "Lightning",
      savingThrow: "DEX",
      saveSuccessOutcome: "half_damage",
      coverAppliesToSave: "physical",
      requiresTargetSight: false,
      requiresTargetEffect: true,
      requiresPointSight: true,
      requiresPointEffect: false,
      upcastMode: "extra_damage_dice",
      upcastDiceCount: "1",
      upcastDieSize: "6",
      upcastFixedBonus: "",
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
        targetType: "ranged",
        maxTargets: 3,
        areaShape: "sphere",
        resolutionType: "damage",
        damageDice: "3d6",
        damageType: "Lightning",
        savingThrow: "DEX",
        saveSuccessOutcome: "half_damage",
        coverAppliesToSave: "physical",
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
          baseEffectInstances: null,
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
        maxTargets: 2,
        resolutionType: "heal",
        healDice: "2d4",
        coverAppliesToSave: "none",
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
    expect(state.maxTargets).toBe("2");
    expect(state.resolutionType).toBe("heal");
    expect(state.healDice).toBe("2d4");
    expect(state.coverAppliesToSave).toBe("none");
    expect(state.requiresTargetSight).toBeNull();
    expect(state.requiresTargetEffect).toBe(true);
    expect(state.requiresPointSight).toBeNull();
    expect(state.requiresPointEffect).toBe(false);
    expect(state.upcastMode).toBe("extra_heal_dice");
    expect(state.upcastDice).toBe("1d4");
    expect(state.upcastPerLevel).toBe("1");
    expect(state.upcastMaxLevel).toBe("6");
  });

  it("hydrates and serializes declarative spell effects", () => {
    const state = createSpellEditorState(
      createSpell({
        effects: [
          {
            type: "advantage_on_checks",
            target: "caster",
            duration: { type: "rounds", rounds: 10, anchor: "caster" },
            params: { ability: "charisma" },
            stacking: "replace",
          },
        ],
        onEndEffects: [
          {
            type: "apply_condition",
            target: "selected_target",
            duration: { type: "manual" },
            params: { condition: "hostile_to_caster" },
          },
        ],
      }),
    );

    expect(state.effects).toHaveLength(1);
    expect(state.onEndEffects).toHaveLength(1);

    const payload = buildSpellUpdatePayload(state);
    expect(payload.effects).toEqual(state.effects);
    expect(payload.onEndEffects).toEqual(state.onEndEffects);
  });

  it("hydrates and serializes persistent area semantics", () => {
    const state = createSpellEditorState(
      createSpell({
        effectTiming: "persistent",
        persistentArea: {
          kind: "hazard",
          params: {
            terrainEffect: "difficult_terrain",
            movementDamageDice: "2d4",
            damageType: "Piercing",
            damagePerMeters: 1.5,
          },
        },
      }),
    );

    expect(state.persistentAreaKind).toBe("hazard");
    expect(state.persistentAreaTerrainEffect).toBe("difficult_terrain");
    expect(state.persistentAreaMovementDamageDice).toBe("2d4");
    expect(state.persistentAreaDamageType).toBe("Piercing");
    expect(state.persistentAreaDamagePerMeters).toBe("1.5");

    const payload = buildSpellUpdatePayload(state);
    expect(payload.persistentArea).toEqual({
      kind: "hazard",
      params: {
        terrainEffect: "difficult_terrain",
        movementDamageDice: "2d4",
        damageType: "Piercing",
        damagePerMeters: 1.5,
      },
    });
  });

  it("preserves structured targeting and upcast fields when building an update payload", () => {
    const payload = buildSpellUpdatePayload({
      ...createSpellEditorState(
        createSpell({
          castingTimeType: "special",
          castingTime: "When an ally falls to 0 HP",
          targetType: "ranged",
          maxTargets: 2,
          resolutionType: "heal",
          healDice: "2d4",
          coverAppliesToSave: "none",
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
    expect(payload.maxTargets).toBe(2);
    expect(payload.resolutionType).toBe("heal");
    expect(payload.coverAppliesToSave).toBeNull();
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
      baseEffectInstances: null,
      scalingKey: null,
      scalingSummary: null,
      scalingEditorial: null,
      unlockKey: null,
      unlockSummary: null,
      unlockEditorial: null,
    });
  });

  it("emits cantrip scaling only for cantrips (damage_dice)", () => {
    const payload = buildSpellUpdatePayload({
      ...createEmptySpellEditorState(),
      level: 0,
      resolutionType: "damage",
      damageDiceCount: "1",
      damageDieSize: "6",
      damageType: "Acid",
      cantripScalingEffectType: "damage_dice",
      upcastMode: "extra_damage_dice",
    });

    expect(payload.upcast).toBeNull();
    expect(payload.cantripScaling).toEqual({
      scalingMode: "character_level",
      scalingEffectType: "damage_dice",
      thresholds: [
        { characterLevel: 1, damage: { dice: "1d6" } },
        { characterLevel: 5, damage: { dice: "2d6" } },
        { characterLevel: 11, damage: { dice: "3d6" } },
        { characterLevel: 17, damage: { dice: "4d6" } },
      ],
    });
  });

  it("emits effect_instances cantrip scaling for Eldritch Blast pattern", () => {
    const payload = buildSpellUpdatePayload({
      ...createEmptySpellEditorState(),
      level: 0,
      resolutionType: "damage",
      damageDiceCount: "1",
      damageDieSize: "10",
      damageType: "Force",
      cantripScalingMode: "character_level",
      cantripScalingEffectType: "effect_instances",
      cantripLevel1InstanceCount: "1",
      cantripLevel1InstanceDiceCount: "1",
      cantripLevel1InstanceDieSize: "10",
      cantripLevel1InstanceFixedBonus: "",
      cantripLevel5InstanceCount: "2",
      cantripLevel5InstanceDiceCount: "1",
      cantripLevel5InstanceDieSize: "10",
      cantripLevel5InstanceFixedBonus: "",
      cantripLevel11InstanceCount: "3",
      cantripLevel11InstanceDiceCount: "1",
      cantripLevel11InstanceDieSize: "10",
      cantripLevel11InstanceFixedBonus: "",
      cantripLevel17InstanceCount: "4",
      cantripLevel17InstanceDiceCount: "1",
      cantripLevel17InstanceDieSize: "10",
      cantripLevel17InstanceFixedBonus: "",
    });

    expect(payload.upcast).toBeNull();
    expect(payload.cantripScaling).toEqual({
      scalingMode: "character_level",
      scalingEffectType: "effect_instances",
      thresholds: [
        { characterLevel: 1, instances: 1, instanceDamage: { dice: "1d10" } },
        { characterLevel: 5, instances: 2, instanceDamage: { dice: "1d10" } },
        { characterLevel: 11, instances: 3, instanceDamage: { dice: "1d10" } },
        { characterLevel: 17, instances: 4, instanceDamage: { dice: "1d10" } },
      ],
    });
  });

  it("hydrates effect_instances cantrip scaling from an existing spell", () => {
    const state = createSpellEditorState(
      createSpell({
        level: 0,
        cantripScaling: {
          scalingMode: "character_level",
          scalingEffectType: "effect_instances",
          thresholds: [
            { characterLevel: 1, instances: 1, instanceDamage: { dice: "1d10" } },
            { characterLevel: 5, instances: 2, instanceDamage: { dice: "1d10" } },
            { characterLevel: 11, instances: 3, instanceDamage: { dice: "1d10" } },
            { characterLevel: 17, instances: 4, instanceDamage: { dice: "1d10" } },
          ],
        },
      }),
    );

    expect(state.cantripScalingMode).toBe("character_level");
    expect(state.cantripScalingEffectType).toBe("effect_instances");
    expect(state.cantripLevel5InstanceCount).toBe("2");
    expect(state.cantripLevel11InstanceCount).toBe("3");
    expect(state.cantripLevel17InstanceCount).toBe("4");
    expect(state.cantripLevel1InstanceDiceCount).toBe("1");
    expect(state.cantripLevel1InstanceDieSize).toBe("10");
  });

  it("does not emit cantripScaling for leveled spells (Magic Missile regression)", () => {
    const payload = buildSpellUpdatePayload({
      ...createEmptySpellEditorState(),
      level: 1,
      resolutionType: "damage",
      damageDiceCount: "3",
      damageDieSize: "4",
      damageFixedBonus: "3",
      damageType: "Force",
      upcastMode: "additional_effect_instances",
      upcastDiceCount: "1",
      upcastDieSize: "4",
      upcastFixedBonus: "1",
      upcastPerLevel: "1",
    });

    expect(payload.cantripScaling).toBeNull();
    expect(payload.upcast?.mode).toBe("additional_effect_instances");
    expect(payload.upcast?.dice).toBe("1d4+1");
  });

  it("preserves coverAppliesToSave as physical in payload", () => {
    const payload = buildSpellUpdatePayload({
      ...createEmptySpellEditorState(),
      resolutionType: "damage",
      savingThrow: "DEX",
      saveSuccessOutcome: "half_damage",
      coverAppliesToSave: "physical",
      damageDiceCount: "8",
      damageDieSize: "6",
      damageType: "Fire",
    });

    expect(payload.coverAppliesToSave).toBe("physical");
  });

  it("preserves coverAppliesToSave as none in payload", () => {
    const payload = buildSpellUpdatePayload({
      ...createEmptySpellEditorState(),
      resolutionType: "control",
      savingThrow: "WIS",
      coverAppliesToSave: "none",
    });

    expect(payload.coverAppliesToSave).toBe("none");
  });

  it("does not default missing coverAppliesToSave to physical", () => {
    const payload = buildSpellUpdatePayload({
      ...createEmptySpellEditorState(),
      canonicalKey: "acid_splash",
      nameEn: "Acid Splash",
      descriptionEn: "A bubble of acid.",
      resolutionType: "damage",
      savingThrow: "DEX",
      damageDiceCount: "1",
      damageDieSize: "6",
      damageType: "Acid",
    });

    expect(payload.coverAppliesToSave).toBeNull();
  });

  it("hydrates coverAppliesToSave as physical from existing spell", () => {
    const state = createSpellEditorState(
      createSpell({
        canonicalKey: "fireball",
        resolutionType: "damage",
        savingThrow: "DEX",
        saveSuccessOutcome: "half_damage",
        coverAppliesToSave: "physical",
        damageDice: "8d6",
        damageType: "Fire",
      }),
    );

    expect(state.coverAppliesToSave).toBe("physical");
  });

  it("hydrates coverAppliesToSave as none from existing spell", () => {
    const state = createSpellEditorState(
      createSpell({
        canonicalKey: "acid_splash",
        resolutionType: "damage",
        savingThrow: "DEX",
        coverAppliesToSave: "none",
        damageDice: "1d6",
        damageType: "Acid",
      }),
    );

    expect(state.coverAppliesToSave).toBe("none");
  });

  it("keeps canonical key normalization deterministic", () => {
    expect(normalizeSpellCanonicalKey(" Détect Magic!!! ")).toBe("detect_magic");
  });

  // --- explicit dimension fields ---

  it("hydrates radiusMeters from new field for sphere", () => {
    const state = createSpellEditorState(
      createSpell({ areaShape: "sphere", radiusMeters: 6 }),
    );
    expect(state.radiusMeters).toBe("6");
  });

  it("hydrates lengthMeters from new field for cone", () => {
    const state = createSpellEditorState(
      createSpell({ areaShape: "cone", lengthMeters: 9 }),
    );
    expect(state.lengthMeters).toBe("9");
    expect(state.radiusMeters).toBe("");
    expect(state.sideMeters).toBe("");
  });

  it("hydrates sideMeters from new field for cube", () => {
    const state = createSpellEditorState(
      createSpell({ areaShape: "cube", sideMeters: 4.5 }),
    );
    expect(state.sideMeters).toBe("4.5");
  });

  it("sphere without radiusMeters results in empty string", () => {
    const state = createSpellEditorState(
      createSpell({ areaShape: "sphere", radiusMeters: null }),
    );
    expect(state.radiusMeters).toBe("");
  });

  it("buildSpellUpdatePayload emits radiusMeters for sphere", () => {
    const state = {
      ...createSpellEditorState(
        createSpell({ areaShape: "sphere", radiusMeters: 6 }),
      ),
    };
    const payload = buildSpellUpdatePayload(state);
    expect(payload.radiusMeters).toBe(6);
    expect(payload.lengthMeters).toBeNull();
    expect(payload.sideMeters).toBeNull();
  });

  it("buildSpellUpdatePayload emits lengthMeters for cone", () => {
    const state = createSpellEditorState(
      createSpell({ areaShape: "cone", lengthMeters: 9 }),
    );
    const payload = buildSpellUpdatePayload(state);
    expect(payload.lengthMeters).toBe(9);
    expect(payload.radiusMeters).toBeNull();
    expect(payload.sideMeters).toBeNull();
  });

  it("buildSpellUpdatePayload emits sideMeters for cube", () => {
    const state = createSpellEditorState(
      createSpell({ areaShape: "cube", sideMeters: 4.5 }),
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
  });

  it("buildSpellUpdatePayload accepts decimal dimension (4.5m = 3 cells clean)", () => {
    const state = createSpellEditorState(
      createSpell({ areaShape: "cone", lengthMeters: 4.5 }),
    );
    expect(state.lengthMeters).toBe("4.5");
    const payload = buildSpellUpdatePayload(state);
    expect(payload.lengthMeters).toBe(4.5);
  });

  it("includes baseEffectInstances in upcast for additional_effect_instances mode", () => {
    const payload = buildSpellUpdatePayload({
      ...createSpellEditorState(
        createSpell({
          level: 1,
          resolutionType: "damage",
          damageDice: "3d4+3",
          damageType: "Force",
          upcast: {
            mode: "additional_effect_instances",
            dice: "1d4+1",
            perLevel: 1,
            baseEffectInstances: 3,
          },
        }),
      ),
    });

    expect(payload.upcast).toEqual(
      expect.objectContaining({
        mode: "additional_effect_instances",
        baseEffectInstances: 3,
      }),
    );
  });

  it("omits baseEffectInstances for non-instance upcast modes", () => {
    const payload = buildSpellUpdatePayload({
      ...createSpellEditorState(
        createSpell({
          level: 3,
          resolutionType: "damage",
          damageDice: "8d6",
          damageType: "Fire",
          upcast: {
            mode: "extra_damage_dice",
            dice: "1d6",
            perLevel: 1,
          },
        }),
      ),
    });

    expect(payload.upcast).toEqual(
      expect.objectContaining({
        mode: "extra_damage_dice",
        baseEffectInstances: null,
      }),
    );
  });

  it("hydrates upcastBaseEffectInstances from spell data", () => {
    const state = createSpellEditorState(
      createSpell({
        level: 1,
        resolutionType: "damage",
        damageDice: "3d4+3",
        damageType: "Force",
        upcast: {
          mode: "additional_effect_instances",
          dice: "1d4+1",
          perLevel: 1,
          baseEffectInstances: 3,
        },
      }),
    );

    expect(state.upcastBaseEffectInstances).toBe("3");
  });

  it("defaults upcastBaseEffectInstances to empty string for new spells", () => {
    const state = createEmptySpellEditorState();
    expect(state.upcastBaseEffectInstances).toBe("");
  });
});
