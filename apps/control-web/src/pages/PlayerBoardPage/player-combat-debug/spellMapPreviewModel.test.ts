import { describe, expect, it } from "vitest";
import { METERS_PER_CELL } from "../../../features/combat-ui/hooks/useTargetingPreview";
import { buildSpellMapPreviewModel } from "./spellMapPreviewModel";
import type { SpellPreviewModel } from "./spellPreviewModel";

// Base SpellPreviewModel representing a resolved backend context
const baseSingleTargetModel: SpellPreviewModel = {
  resolutionType: "direct_damage",
  damagePreview: "3d4+3",
  damageType: "force",
  effectInstanceCount: 1,
  effectInstanceDice: null,
  targetType: "ranged",
  selectionType: "creature",
  areaShape: null,
  areaSizeMeters: null,
  rangeMeters: 36,
  requiresAttackRoll: false,
  requiresSavingThrow: false,
  saveAbility: null,
  source: "resolved",
};

const CASTER = { x: 0, y: 0 };

// At range exactly: 24 cells * 1.5 m/cell = 36m
const TARGET_IN_RANGE = { x: 24, y: 0 };
// One cell beyond: 25 * 1.5 = 37.5m > 36m
const TARGET_OUT_OF_RANGE = { x: 25, y: 0 };

describe("buildSpellMapPreviewModel – single-target", () => {
  it("returns valid when target is within rangeMeters", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: baseSingleTargetModel,
      casterPosition: CASTER,
      selectedTargetRefId: "enemy-1",
      targetPositions: [{ refId: "enemy-1", cell: TARGET_IN_RANGE }],
    });

    expect(model.status).toBe("valid");
    expect(model.rangeMeters).toBe(36);
    expect(model.effectInstanceCount).toBe(1);
  });

  it("returns invalid when target is beyond rangeMeters", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: baseSingleTargetModel,
      casterPosition: CASTER,
      selectedTargetRefId: "enemy-1",
      targetPositions: [{ refId: "enemy-1", cell: TARGET_OUT_OF_RANGE }],
    });

    expect(model.status).toBe("invalid");
    expect(model.reason).toBeTruthy();
  });

  it("returns unknown when casterPosition is absent", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: baseSingleTargetModel,
      casterPosition: null,
      selectedTargetRefId: "enemy-1",
      targetPositions: [{ refId: "enemy-1", cell: TARGET_IN_RANGE }],
    });
    expect(model.status).toBe("unknown");
  });

  it("returns unknown when targetRefId is absent", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: baseSingleTargetModel,
      casterPosition: CASTER,
      selectedTargetRefId: null,
      targetPositions: [{ refId: "enemy-1", cell: TARGET_IN_RANGE }],
    });
    expect(model.status).toBe("unknown");
  });

  it("returns unknown when target position is not in targetPositions list", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: baseSingleTargetModel,
      casterPosition: CASTER,
      selectedTargetRefId: "enemy-1",
      targetPositions: [],
    });
    expect(model.status).toBe("unknown");
  });

  it("returns unknown when rangeMeters is null (range unresolved)", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: { ...baseSingleTargetModel, rangeMeters: null },
      casterPosition: CASTER,
      selectedTargetRefId: "enemy-1",
      targetPositions: [{ refId: "enemy-1", cell: TARGET_IN_RANGE }],
    });
    expect(model.status).toBe("unknown");
  });

  it("returns unknown when all spatial data is absent", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: baseSingleTargetModel,
    });
    expect(model.status).toBe("unknown");
  });

  it("always uses effectInstanceCount from SpellPreviewModel without recalculating", () => {
    // The model says 1 instance (single-target), even if the spell could upcast
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: { ...baseSingleTargetModel, effectInstanceCount: 1 },
    });
    expect(model.effectInstanceCount).toBe(1);
  });
});

describe("buildSpellMapPreviewModel – Acid Splash (saving throw, single-instance)", () => {
  const acidSplashModel: SpellPreviewModel = {
    resolutionType: "saving_throw",
    damagePreview: "2d6",
    damageType: "acid",
    effectInstanceCount: 1,
    effectInstanceDice: null,
    targetType: "ranged",
    selectionType: "creature",
    areaShape: null,
    areaSizeMeters: null,
    rangeMeters: 18,
    requiresAttackRoll: false,
    requiresSavingThrow: true,
    saveAbility: "dexterity",
    source: "resolved",
  };

  it("treats Acid Splash as single-target, no instanceStatuses", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: acidSplashModel,
      casterPosition: CASTER,
      selectedTargetRefId: "enemy-1",
      targetPositions: [{ refId: "enemy-1", cell: { x: 5, y: 0 } }],
    });

    expect(model.effectInstanceCount).toBe(1);
    expect(model.instanceStatuses).toBeUndefined();
    expect(model.status).toBe("valid");
  });

  it("does not expose instanceStatuses for single-instance saving throw spell", () => {
    const model = buildSpellMapPreviewModel({ spellPreviewModel: acidSplashModel });
    expect(model.instanceStatuses).toBeUndefined();
  });
});

describe("buildSpellMapPreviewModel – Magic Missile slot 3 (effectInstanceCount = 5)", () => {
  const magicMissileSlot3: SpellPreviewModel = {
    resolutionType: "direct_damage",
    damagePreview: "5d4+5",
    damageType: "force",
    effectInstanceCount: 5,
    effectInstanceDice: "1d4+1",
    targetType: "ranged",
    selectionType: "creature",
    areaShape: null,
    areaSizeMeters: null,
    rangeMeters: 36,
    requiresAttackRoll: false,
    requiresSavingThrow: false,
    saveAbility: null,
    source: "resolved",
  };

  it("uses effectInstanceCount = 5 from SpellPreviewModel", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: magicMissileSlot3,
    });
    expect(model.effectInstanceCount).toBe(5);
  });

  it("returns unknown overall when no instance targets are provided", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: magicMissileSlot3,
      casterPosition: CASTER,
      effectInstanceTargets: [],
      targetPositions: [],
    });

    expect(model.status).toBe("unknown");
    expect(model.instanceStatuses).toHaveLength(5);
    expect(model.instanceStatuses?.every((s) => s.status === "unknown")).toBe(true);
  });

  it("returns valid when all 5 instances target in-range enemies", () => {
    const inRangeTargets = [
      { refId: "e1", cell: { x: 5, y: 0 } },
      { refId: "e2", cell: { x: 6, y: 0 } },
    ];

    const model = buildSpellMapPreviewModel({
      spellPreviewModel: magicMissileSlot3,
      casterPosition: CASTER,
      effectInstanceTargets: [
        { instance_index: 1, target_ref_id: "e1" },
        { instance_index: 2, target_ref_id: "e2" },
        { instance_index: 3, target_ref_id: "e1" },
        { instance_index: 4, target_ref_id: "e2" },
        { instance_index: 5, target_ref_id: "e1" },
      ],
      targetPositions: inRangeTargets,
    });

    expect(model.status).toBe("valid");
    expect(model.instanceStatuses).toHaveLength(5);
    expect(model.instanceStatuses?.every((s) => s.status === "valid")).toBe(true);
  });

  it("returns invalid when all 5 instances target out-of-range enemy", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: magicMissileSlot3,
      casterPosition: CASTER,
      effectInstanceTargets: Array.from({ length: 5 }, (_, i) => ({
        instance_index: i + 1,
        target_ref_id: "far-enemy",
      })),
      targetPositions: [{ refId: "far-enemy", cell: TARGET_OUT_OF_RANGE }],
    });

    expect(model.status).toBe("invalid");
    expect(model.instanceStatuses?.every((s) => s.status === "invalid")).toBe(true);
  });

  it("returns partial when some instances are in range and some are not", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: magicMissileSlot3,
      casterPosition: CASTER,
      effectInstanceTargets: [
        { instance_index: 1, target_ref_id: "near-enemy" },
        { instance_index: 2, target_ref_id: "far-enemy" },
        { instance_index: 3, target_ref_id: "near-enemy" },
        { instance_index: 4, target_ref_id: "far-enemy" },
        { instance_index: 5, target_ref_id: "near-enemy" },
      ],
      targetPositions: [
        { refId: "near-enemy", cell: TARGET_IN_RANGE },
        { refId: "far-enemy", cell: TARGET_OUT_OF_RANGE },
      ],
    });

    expect(model.status).toBe("partial");
  });
});

describe("buildSpellMapPreviewModel – Eldritch Blast level 5 (effectInstanceCount = 2)", () => {
  const eldritchBlastLvl5: SpellPreviewModel = {
    resolutionType: "spell_attack",
    damagePreview: "2d10",
    damageType: "force",
    effectInstanceCount: 2,
    effectInstanceDice: "1d10",
    targetType: "ranged",
    selectionType: "creature",
    areaShape: null,
    areaSizeMeters: null,
    rangeMeters: 27,
    requiresAttackRoll: true,
    requiresSavingThrow: false,
    saveAbility: null,
    source: "resolved",
  };

  it("uses effectInstanceCount = 2 from SpellPreviewModel", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: eldritchBlastLvl5,
    });
    expect(model.effectInstanceCount).toBe(2);
  });

  it("produces instanceStatuses with 2 entries", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: eldritchBlastLvl5,
      casterPosition: CASTER,
      effectInstanceTargets: [
        { instance_index: 1, target_ref_id: "e1" },
        { instance_index: 2, target_ref_id: "e1" },
      ],
      targetPositions: [{ refId: "e1", cell: { x: 10, y: 0 } }],
    });

    expect(model.instanceStatuses).toHaveLength(2);
    // 10 cells * 1.5 = 15m < 27m → valid
    expect(model.instanceStatuses?.every((s) => s.status === "valid")).toBe(true);
    expect(model.status).toBe("valid");
  });
});

describe("buildSpellMapPreviewModel – Fireball (area spell)", () => {
  const fireballModel: SpellPreviewModel = {
    resolutionType: "saving_throw",
    damagePreview: "8d6",
    damageType: "fire",
    effectInstanceCount: 1,
    effectInstanceDice: null,
    targetType: "ranged",
    selectionType: "point",
    areaShape: "sphere",
    areaSizeMeters: 6,
    rangeMeters: 45,
    requiresAttackRoll: false,
    requiresSavingThrow: true,
    saveAbility: "dexterity",
    source: "resolved",
  };

  it("uses areaShape and areaSizeMeters from SpellPreviewModel", () => {
    const model = buildSpellMapPreviewModel({ spellPreviewModel: fireballModel });

    expect(model.areaShape).toBe("sphere");
    expect(model.areaSizeMeters).toBe(6);
    expect(model.rangeMeters).toBe(45);
  });

  it("returns unknown when no area preview result is available", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: fireballModel,
      casterPosition: CASTER,
    });
    expect(model.status).toBe("unknown");
  });

  it("uses existing area preview result as validity source", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: fireballModel,
      casterPosition: CASTER,
      existingAreaPreviewResult: {
        is_valid: true,
        reason: null,
        shape: "sphere",
        affected_cells: [{ x: 5, y: 5 }],
        affected_target_ref_ids: ["e1", "e2"],
        affected_token_ids: ["tok-1", "tok-2"],
      },
    });

    expect(model.status).toBe("valid");
    expect(model.affectedTargetCount).toBe(2);
  });

  it("reflects invalid area preview result", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: fireballModel,
      existingAreaPreviewResult: {
        is_valid: false,
        reason: "Fora do alcance",
        shape: "sphere",
        affected_cells: [],
        affected_target_ref_ids: [],
        affected_token_ids: [],
      },
    });

    expect(model.status).toBe("invalid");
    expect(model.reason).toBe("Fora do alcance");
  });

  it("does not produce instanceStatuses for area spells", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: fireballModel,
      existingAreaPreviewResult: {
        is_valid: true,
        reason: null,
        shape: "sphere",
        affected_cells: [],
        affected_target_ref_ids: [],
        affected_token_ids: [],
      },
    });
    expect(model.instanceStatuses).toBeUndefined();
  });
});

describe("buildSpellMapPreviewModel – METERS_PER_CELL boundary", () => {
  it("uses METERS_PER_CELL from useTargetingPreview for distance calculation", () => {
    // A target exactly at range boundary: cells = rangeMeters / METERS_PER_CELL
    const rangeMeters = 30;
    const exactCells = rangeMeters / METERS_PER_CELL; // 20 cells
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: { ...baseSingleTargetModel, rangeMeters },
      casterPosition: CASTER,
      selectedTargetRefId: "e1",
      targetPositions: [{ refId: "e1", cell: { x: exactCells, y: 0 } }],
    });
    expect(model.status).toBe("valid");
  });

  it("treats target one cell beyond range boundary as invalid", () => {
    const rangeMeters = 30;
    const beyondCells = rangeMeters / METERS_PER_CELL + 1; // 21 cells = 31.5m
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: { ...baseSingleTargetModel, rangeMeters },
      casterPosition: CASTER,
      selectedTargetRefId: "e1",
      targetPositions: [{ refId: "e1", cell: { x: beyondCells, y: 0 } }],
    });
    expect(model.status).toBe("invalid");
  });
});
