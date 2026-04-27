import { describe, expect, it } from "vitest";
import { METERS_PER_CELL } from "../../../features/combat-ui/hooks/useTargetingPreview";
import { buildSpellMapPreviewModel } from "./spellMapPreviewModel";
import type { SpellAreaSpatialValidation, SpellCoverPreview } from "./spellMapPreviewModel";
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
  coverAppliesToSave: null,
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
    expect(model.reason).toBe("out_of_range");
  });

  it("returns unknown when casterPosition is absent", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: baseSingleTargetModel,
      casterPosition: null,
      selectedTargetRefId: "enemy-1",
      targetPositions: [{ refId: "enemy-1", cell: TARGET_IN_RANGE }],
    });
    expect(model.status).toBe("unknown");
    expect(model.reason).toBe("missing_position");
  });

  it("returns unknown when targetRefId is absent", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: baseSingleTargetModel,
      casterPosition: CASTER,
      selectedTargetRefId: null,
      targetPositions: [{ refId: "enemy-1", cell: TARGET_IN_RANGE }],
    });
    expect(model.status).toBe("unknown");
    expect(model.reason).toBe("missing_position");
  });

  it("returns unknown when target position is not in targetPositions list", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: baseSingleTargetModel,
      casterPosition: CASTER,
      selectedTargetRefId: "enemy-1",
      targetPositions: [],
    });
    expect(model.status).toBe("unknown");
    expect(model.reason).toBe("missing_position");
  });

  it("returns unknown when rangeMeters is null (range unresolved)", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: { ...baseSingleTargetModel, rangeMeters: null },
      casterPosition: CASTER,
      selectedTargetRefId: "enemy-1",
      targetPositions: [{ refId: "enemy-1", cell: TARGET_IN_RANGE }],
    });
    expect(model.status).toBe("unknown");
    expect(model.reason).toBe("missing_position");
  });

  it("returns unknown when all spatial data is absent", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: baseSingleTargetModel,
    });
    expect(model.status).toBe("unknown");
    expect(model.reason).toBe("missing_position");
  });

  it("always uses effectInstanceCount from SpellPreviewModel without recalculating", () => {
    // The model says 1 instance (single-target), even if the spell could upcast
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: { ...baseSingleTargetModel, effectInstanceCount: 1 },
    });
    expect(model.effectInstanceCount).toBe(1);
  });

  it("returns invalid when target is in range and line of sight is blocked", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: baseSingleTargetModel,
      casterPosition: CASTER,
      selectedTargetRefId: "enemy-1",
      targetPositions: [{ refId: "enemy-1", cell: TARGET_IN_RANGE }],
      spatialValidations: {
        targets: [{ targetRefId: "enemy-1", hasLineOfSight: false }],
      },
    });

    expect(model.status).toBe("invalid");
    expect(model.reason).toBe("blocked_line_of_sight");
  });

  it("returns invalid when target is in range and line of effect is blocked", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: baseSingleTargetModel,
      casterPosition: CASTER,
      selectedTargetRefId: "enemy-1",
      targetPositions: [{ refId: "enemy-1", cell: TARGET_IN_RANGE }],
      spatialValidations: {
        targets: [{ targetRefId: "enemy-1", hasLineOfSight: true, hasLineOfEffect: false }],
      },
    });

    expect(model.status).toBe("invalid");
    expect(model.reason).toBe("blocked_line_of_effect");
  });

  it("prioritizes out_of_range over line of sight failure", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: baseSingleTargetModel,
      casterPosition: CASTER,
      selectedTargetRefId: "enemy-1",
      targetPositions: [{ refId: "enemy-1", cell: TARGET_OUT_OF_RANGE }],
      spatialValidations: {
        targets: [{ targetRefId: "enemy-1", hasLineOfSight: false }],
      },
    });

    expect(model.status).toBe("invalid");
    expect(model.reason).toBe("out_of_range");
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
    coverAppliesToSave: null,
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
    coverAppliesToSave: null,
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
    expect(model.instanceStatuses?.every((s) => s.reason === "missing_position")).toBe(true);
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

  it("returns partial when one instance target has line of effect blocked", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: magicMissileSlot3,
      casterPosition: CASTER,
      effectInstanceTargets: [
        { instance_index: 1, target_ref_id: "near-a" },
        { instance_index: 2, target_ref_id: "near-a" },
        { instance_index: 3, target_ref_id: "blocked-b" },
        { instance_index: 4, target_ref_id: "blocked-b" },
        { instance_index: 5, target_ref_id: "near-c" },
      ],
      targetPositions: [
        { refId: "near-a", cell: TARGET_IN_RANGE },
        { refId: "blocked-b", cell: TARGET_IN_RANGE },
        { refId: "near-c", cell: TARGET_IN_RANGE },
      ],
      spatialValidations: {
        instances: [
          { instanceIndex: 3, targetRefId: "blocked-b", hasLineOfSight: true, hasLineOfEffect: false },
          { instanceIndex: 4, targetRefId: "blocked-b", hasLineOfSight: true, hasLineOfEffect: false },
        ],
      },
    });

    expect(model.status).toBe("partial");
    expect(model.instanceStatuses?.[2]).toMatchObject({
      status: "invalid",
      reason: "blocked_line_of_effect",
    });
    expect(model.instanceStatuses?.[3]).toMatchObject({
      status: "invalid",
      reason: "blocked_line_of_effect",
    });
  });

  it("returns invalid when all instances are line-of-sight blocked", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: magicMissileSlot3,
      casterPosition: CASTER,
      effectInstanceTargets: Array.from({ length: 5 }, (_, index) => ({
        instance_index: index + 1,
        target_ref_id: `enemy-${index + 1}`,
      })),
      targetPositions: Array.from({ length: 5 }, (_, index) => ({
        refId: `enemy-${index + 1}`,
        cell: TARGET_IN_RANGE,
      })),
      spatialValidations: {
        instances: Array.from({ length: 5 }, (_, index) => ({
          instanceIndex: index + 1,
          targetRefId: `enemy-${index + 1}`,
          hasLineOfSight: false,
        })),
      },
    });

    expect(model.status).toBe("invalid");
    expect(model.instanceStatuses?.every((status) => status.reason === "blocked_line_of_sight")).toBe(true);
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
    coverAppliesToSave: null,
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

  it("returns partial when one beam is line-of-sight blocked", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: eldritchBlastLvl5,
      casterPosition: CASTER,
      effectInstanceTargets: [
        { instance_index: 1, target_ref_id: "e1" },
        { instance_index: 2, target_ref_id: "e2" },
      ],
      targetPositions: [
        { refId: "e1", cell: { x: 10, y: 0 } },
        { refId: "e2", cell: { x: 10, y: 0 } },
      ],
      spatialValidations: {
        instances: [{ instanceIndex: 2, targetRefId: "e2", hasLineOfSight: false }],
      },
    });

    expect(model.status).toBe("partial");
    expect(model.instanceStatuses?.[0]).toMatchObject({ status: "valid", reason: null });
    expect(model.instanceStatuses?.[1]).toMatchObject({
      status: "invalid",
      reason: "blocked_line_of_sight",
    });
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
    coverAppliesToSave: null,
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
    expect(model.reason).toBe("missing_map_data");
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

  it("returns invalid when area origin is out of range", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: fireballModel,
      spatialValidations: {
        area: {
          originCell: { x: 40, y: 0 },
          inRange: false,
        },
      },
    });

    expect(model.status).toBe("invalid");
    expect(model.reason).toBe("out_of_range");
  });

  it("returns invalid when area origin has line of sight blocked", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: fireballModel,
      spatialValidations: {
        area: {
          originCell: { x: 5, y: 5 },
          inRange: true,
          hasLineOfSight: false,
        },
      },
    });

    expect(model.status).toBe("invalid");
    expect(model.reason).toBe("blocked_line_of_sight");
  });

  it("returns invalid when area origin has line of effect blocked", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: fireballModel,
      spatialValidations: {
        area: {
          originCell: { x: 5, y: 5 },
          inRange: true,
          hasLineOfSight: true,
          hasLineOfEffect: false,
        },
      },
    });

    expect(model.status).toBe("invalid");
    expect(model.reason).toBe("blocked_line_of_effect");
  });
});

describe("buildSpellMapPreviewModel – Chebyshev distance boundary", () => {
  // The tactical engine uses Chebyshev distance: max(|dx|, |dy|), the
  // king-move metric where diagonals cost the same as cardinals.
  // These tests guard against accidental regression to Euclidean.

  it("target exactly at axial range boundary is valid", () => {
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

  it("target one cell beyond axial range boundary is invalid", () => {
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

  it("diagonal target at Chebyshev boundary is valid (would be invalid with Euclidean)", () => {
    // (20, 20): Chebyshev = max(20,20) = 20 cells = 30m → valid at range 30m.
    // Euclidean would be sqrt(20²+20²) ≈ 28.28 cells = 42.43m → invalid.
    const rangeMeters = 30;
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: { ...baseSingleTargetModel, rangeMeters },
      casterPosition: CASTER,
      selectedTargetRefId: "e1",
      targetPositions: [{ refId: "e1", cell: { x: 20, y: 20 } }],
    });
    expect(model.status).toBe("valid");
  });

  it("diagonal target one Chebyshev cell beyond boundary is invalid", () => {
    // (21, 21): Chebyshev = 21 cells = 31.5m > 30m → invalid.
    const rangeMeters = 30;
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: { ...baseSingleTargetModel, rangeMeters },
      casterPosition: CASTER,
      selectedTargetRefId: "e1",
      targetPositions: [{ refId: "e1", cell: { x: 21, y: 21 } }],
    });
    expect(model.status).toBe("invalid");
  });
});

const baseAreaModel: SpellPreviewModel = {
  resolutionType: "direct_damage",
  damagePreview: "8d6",
  damageType: "fire",
  effectInstanceCount: 1,
  effectInstanceDice: null,
  targetType: "area",
  selectionType: "point",
  areaShape: "sphere",
  areaSizeMeters: 6,
  rangeMeters: 36,
  requiresAttackRoll: false,
  requiresSavingThrow: true,
  saveAbility: "dexterity",
  coverAppliesToSave: null,
  source: "resolved",
};

const ANCHOR = { x: 10, y: 0 };

const areaPreviewResult = {
  is_valid: true,
  reason: null,
  shape: "sphere" as const,
  affected_cells: [{ x: 9, y: 0 }, { x: 10, y: 0 }, { x: 11, y: 0 }],
  affected_target_ref_ids: ["goblin-a", "goblin-b"],
  affected_token_ids: ["t1", "t2"],
};

describe("buildSpellMapPreviewModel – área com spatialValidations.area", () => {
  const buildAreaModel = (area: SpellAreaSpatialValidation | null) =>
    buildSpellMapPreviewModel({
      spellPreviewModel: baseAreaModel,
      existingAreaPreviewResult: areaPreviewResult,
      spatialValidations: { area },
    });

  it("área totalmente válida retorna valid", () => {
    const model = buildAreaModel({ originCell: ANCHOR, inRange: true, hasLineOfSight: null, hasLineOfEffect: null, unavailableReason: null });
    expect(model.status).toBe("valid");
    expect(model.reason).toBeNull();
  });

  it("inRange false retorna invalid / out_of_range", () => {
    const model = buildAreaModel({ originCell: ANCHOR, inRange: false, hasLineOfSight: null, hasLineOfEffect: null, unavailableReason: null });
    expect(model.status).toBe("invalid");
    expect(model.reason).toBe("out_of_range");
  });

  it("hasLineOfSight false retorna invalid / blocked_line_of_sight", () => {
    const model = buildAreaModel({ originCell: ANCHOR, inRange: true, hasLineOfSight: false, hasLineOfEffect: null, unavailableReason: null });
    expect(model.status).toBe("invalid");
    expect(model.reason).toBe("blocked_line_of_sight");
  });

  it("hasLineOfEffect false retorna invalid / blocked_line_of_effect", () => {
    const model = buildAreaModel({ originCell: ANCHOR, inRange: true, hasLineOfSight: null, hasLineOfEffect: false, unavailableReason: null });
    expect(model.status).toBe("invalid");
    expect(model.reason).toBe("blocked_line_of_effect");
  });

  it("unavailableReason missing_map_data retorna unknown", () => {
    const model = buildAreaModel({ originCell: ANCHOR, inRange: null, hasLineOfSight: null, hasLineOfEffect: null, unavailableReason: "missing_map_data" });
    expect(model.status).toBe("unknown");
  });

  it("inRange null sem unavailableReason retorna unknown / missing_position", () => {
    const model = buildAreaModel({ originCell: ANCHOR, inRange: null, hasLineOfSight: null, hasLineOfEffect: null, unavailableReason: null });
    expect(model.status).toBe("unknown");
    expect(model.reason).toBe("missing_position");
  });

  it("spatialValidations.area tem prioridade sobre existingAreaPreviewResult para status", () => {
    const invalidArea: SpellAreaSpatialValidation = { originCell: ANCHOR, inRange: false, hasLineOfSight: null, hasLineOfEffect: null, unavailableReason: null };
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: baseAreaModel,
      existingAreaPreviewResult: { ...areaPreviewResult, is_valid: true },
      spatialValidations: { area: invalidArea },
    });
    expect(model.status).toBe("invalid");
    expect(model.reason).toBe("out_of_range");
  });

  it("existingAreaPreviewResult ainda fornece affectedTargetCount quando spatialValidations.area existe", () => {
    const model = buildAreaModel({ originCell: ANCHOR, inRange: true, hasLineOfSight: null, hasLineOfEffect: null, unavailableReason: null });
    expect(model.affectedTargetCount).toBe(2);
  });

  it("sem spatialValidations.area, existingAreaPreviewResult é usado como fallback", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: baseAreaModel,
      existingAreaPreviewResult: areaPreviewResult,
    });
    expect(model.status).toBe("valid");
    expect(model.affectedTargetCount).toBe(2);
  });
});

const halfCover: SpellCoverPreview = { rank: "half", bonus: 2 };
const threeQuartersCover: SpellCoverPreview = { rank: "three_quarters", bonus: 5 };

describe("buildSpellMapPreviewModel – cover metadata", () => {
  it("single-target preserva half cover no modelo", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: baseSingleTargetModel,
      casterPosition: CASTER,
      selectedTargetRefId: "enemy-1",
      targetPositions: [{ refId: "enemy-1", cell: TARGET_IN_RANGE }],
      spatialValidations: {
        targets: [{ targetRefId: "enemy-1", inRange: true, hasLineOfSight: null, hasLineOfEffect: null, unavailableReason: null, cover: halfCover }],
      },
    });
    expect(model.status).toBe("valid");
    expect(model.cover).toEqual(halfCover);
  });

  it("single-target preserva three_quarters cover no modelo", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: baseSingleTargetModel,
      casterPosition: CASTER,
      selectedTargetRefId: "enemy-1",
      targetPositions: [{ refId: "enemy-1", cell: TARGET_IN_RANGE }],
      spatialValidations: {
        targets: [{ targetRefId: "enemy-1", inRange: true, hasLineOfSight: null, hasLineOfEffect: null, unavailableReason: null, cover: threeQuartersCover }],
      },
    });
    expect(model.cover).toEqual(threeQuartersCover);
  });

  it("cover não altera status valid para invalid", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: baseSingleTargetModel,
      casterPosition: CASTER,
      selectedTargetRefId: "enemy-1",
      targetPositions: [{ refId: "enemy-1", cell: TARGET_IN_RANGE }],
      spatialValidations: {
        targets: [{ targetRefId: "enemy-1", inRange: true, hasLineOfSight: null, hasLineOfEffect: null, unavailableReason: null, cover: halfCover }],
      },
    });
    expect(model.status).toBe("valid");
    expect(model.reason).toBeNull();
  });

  it("cover não sobrescreve reason out_of_range", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: baseSingleTargetModel,
      casterPosition: CASTER,
      selectedTargetRefId: "enemy-1",
      targetPositions: [{ refId: "enemy-1", cell: TARGET_OUT_OF_RANGE }],
      spatialValidations: {
        targets: [{ targetRefId: "enemy-1", inRange: false, hasLineOfSight: null, hasLineOfEffect: null, unavailableReason: null, cover: halfCover }],
      },
    });
    expect(model.status).toBe("invalid");
    expect(model.reason).toBe("out_of_range");
  });

  it("multi-instância preserva cover por instância", () => {
    const multiInstanceModel: SpellPreviewModel = { ...baseSingleTargetModel, effectInstanceCount: 2 };
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: multiInstanceModel,
      effectInstanceTargets: [
        { instance_index: 1, target_ref_id: "enemy-1" },
        { instance_index: 2, target_ref_id: "enemy-2" },
      ],
      targetPositions: [
        { refId: "enemy-1", cell: TARGET_IN_RANGE },
        { refId: "enemy-2", cell: TARGET_IN_RANGE },
      ],
      spatialValidations: {
        instances: [
          { instanceIndex: 1, targetRefId: "enemy-1", inRange: true, hasLineOfSight: null, hasLineOfEffect: null, unavailableReason: null, cover: halfCover },
          { instanceIndex: 2, targetRefId: "enemy-2", inRange: true, hasLineOfSight: null, hasLineOfEffect: null, unavailableReason: null, cover: threeQuartersCover },
        ],
      },
    });
    expect(model.instanceStatuses?.[0].cover).toEqual(halfCover);
    expect(model.instanceStatuses?.[1].cover).toEqual(threeQuartersCover);
  });
});

describe("buildSpellMapPreviewModel – area spatial metadata propagation", () => {
  const metadataPayload = [
    { target_ref_id: "goblin-a", target_display_name: "Goblin A", cover: "half", base_save_dc: 15, effective_save_dc: 13, cover_modifier: 2 },
    { target_ref_id: "orc-b", target_display_name: "Orc B", cover: null, base_save_dc: 15, effective_save_dc: 15, cover_modifier: 0 },
  ];

  it("fallback path: existingAreaPreviewResult com metadata popula affectedTargetSpatialMetadata", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: baseAreaModel,
      existingAreaPreviewResult: {
        ...areaPreviewResult,
        affected_target_spatial_metadata: metadataPayload,
      },
    });

    expect(model.affectedTargetSpatialMetadata).toHaveLength(2);
    expect(model.affectedTargetSpatialMetadata?.[0]).toEqual({
      targetRefId: "goblin-a",
      targetDisplayName: "Goblin A",
      cover: "half",
      baseSaveDc: 15,
      effectiveSaveDc: 13,
      coverModifier: 2,
    });
    expect(model.affectedTargetSpatialMetadata?.[1]).toEqual({
      targetRefId: "orc-b",
      targetDisplayName: "Orc B",
      cover: null,
      baseSaveDc: 15,
      effectiveSaveDc: 15,
      coverModifier: 0,
    });
  });

  it("spatialValidations.area path: metadata é propagada quando area validation existe", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: baseAreaModel,
      existingAreaPreviewResult: {
        ...areaPreviewResult,
        affected_target_spatial_metadata: metadataPayload,
      },
      spatialValidations: {
        area: { originCell: ANCHOR, inRange: true, hasLineOfSight: null, hasLineOfEffect: null, unavailableReason: null },
      },
    });

    expect(model.affectedTargetSpatialMetadata).toHaveLength(2);
    expect(model.affectedTargetSpatialMetadata?.[0].targetRefId).toBe("goblin-a");
  });

  it("empty metadata array → affectedTargetSpatialMetadata is undefined", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: baseAreaModel,
      existingAreaPreviewResult: {
        ...areaPreviewResult,
        affected_target_spatial_metadata: [],
      },
    });

    expect(model.affectedTargetSpatialMetadata).toBeUndefined();
  });

  it("missing metadata field → affectedTargetSpatialMetadata is undefined", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: baseAreaModel,
      existingAreaPreviewResult: areaPreviewResult,
    });

    expect(model.affectedTargetSpatialMetadata).toBeUndefined();
  });

  it("metadata does not alter status or reason", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: baseAreaModel,
      existingAreaPreviewResult: {
        ...areaPreviewResult,
        affected_target_spatial_metadata: metadataPayload,
      },
    });

    expect(model.status).toBe("valid");
    expect(model.reason).toBeNull();
  });

  it("metadata does not alter affectedTargetCount or affectedTargetNames", () => {
    const model = buildSpellMapPreviewModel({
      spellPreviewModel: baseAreaModel,
      existingAreaPreviewResult: {
        ...areaPreviewResult,
        affected_target_spatial_metadata: metadataPayload,
      },
      targetPositions: [
        { refId: "goblin-a", cell: { x: 9, y: 0 }, displayName: "Goblin A" },
      ],
    });

    expect(model.affectedTargetCount).toBe(2);
    expect(model.affectedTargetNames).toEqual(["Goblin A"]);
  });
});
