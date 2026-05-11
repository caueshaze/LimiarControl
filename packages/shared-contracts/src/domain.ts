import { z } from "zod";

export const MAX_GRID_DIMENSION = 150;

/** Initial tactical ceiling for cell elevation in meters. Not a system rule — adjust as needed. */
export const MAX_ELEVATION_METERS = 100;

/**
 * Default map scale: 1.5 meters per cell.
 * Compatible with standard D&D 5e grids (5 ft ≈ 1.5 m per cell).
 * All meter values from the Control domain must be converted to cells
 * using this constant before being sent to the Map tactical engine.
 */
export const METERS_PER_CELL = 1.5;

export const coordinateSchema = z.object({
  x: z.number().int().nonnegative(),
  y: z.number().int().nonnegative()
});

export const gridCalibrationSchema = z
  .object({
    x: z.number().min(0).max(1),
    y: z.number().min(0).max(1),
    width: z.number().positive().max(1),
    height: z.number().positive().max(1)
  })
  .refine((value) => value.x + value.width <= 1, {
    message: "Grid calibration width exceeds image bounds"
  })
  .refine((value) => value.y + value.height <= 1, {
    message: "Grid calibration height exceeds image bounds"
  });

const gridDimensionSchema = z.number().int().positive().max(MAX_GRID_DIMENSION);

export const gridDimensionsSchema = z.object({
  gridWidth: gridDimensionSchema,
  gridHeight: gridDimensionSchema
});

export const controllerTypeSchema = z.enum(["player", "gm", "limiarControl"]);
export const actionResultSchema = z.enum(["pending", "accepted", "rejected"]);
export const combatStatusSchema = z.enum(["inactive", "active", "completed"]);
export const targetingShapeSchema = z.enum(["line", "cone", "sphere", "cube", "cylinder"]);
export const obstacleCoverSchema = z.enum(["none", "half", "threeQuarters", "full"]);
export const obstaclePaintModeSchema = z.enum(["paint", "erase"]);
export const activeAreaEffectKindSchema = z.enum(["obscurement", "hazard", "spell_area"]);

/**
 * Phase 10: Edge obstacle direction.
 * An edge is the boundary of a cell in one of the four cardinal directions.
 */
export const edgeDirectionSchema = z.enum(["N", "E", "S", "W"]);

/**
 * Phase 10: Edge obstacle representation.
 * Each edge is defined between two adjacent cells by a coordinate and direction.
 * Example: (x=5, y=5, direction="E") represents the edge between (5,5) and (6,5).
 */
export const edgeObstacleSchema = z.object({
  id: z.string(),
  battleMapId: z.string(),
  x: z.number().int().nonnegative(),
  y: z.number().int().nonnegative(),
  direction: edgeDirectionSchema,
  blocksMovement: z.boolean(),
  blocksVision: z.boolean().default(false),
  blocksEffect: z.boolean(),
  cover: obstacleCoverSchema.default("none"),
  label: z.string().optional()
});

export const battleMapSchema = z.object({
  id: z.string(),
  name: z.string(),
  gridWidth: gridDimensionSchema,
  gridHeight: gridDimensionSchema,
  imageUrl: z.string().optional(),
  terrainVersion: z.number().int().nonnegative(),
  gridCalibration: gridCalibrationSchema,
  activeEncounterId: z.string().optional()
});

const obstacleSemanticsInputSchema = z.object({
  blocksMovement: z.boolean(),
  /**
   * Authoritative Phase 2 effect-blocking flag.
   * Old payloads may still send `blocksTargeting` or `blocksSpell`; those are
   * normalized into this field for backward compatibility.
   */
  blocksEffect: z.boolean().optional(),
  /**
   * Legacy alias kept only for backward-compatible parsing of old payloads.
   * Prefer `blocksEffect` everywhere else.
   */
  blocksTargeting: z.boolean().optional(),
  /**
   * Legacy alias kept only for backward-compatible parsing of old payloads.
   * Prefer `blocksEffect` everywhere else.
   */
  blocksSpell: z.boolean().optional(),
  blocksVision: z.boolean().default(false),
  cover: obstacleCoverSchema.default("none"),
  clipsDiagonalMovement: z.boolean().default(false),
  /**
   * Phase 7: movement cost multiplier for terrain.
   * 1 = normal traversal (default, backward-compatible).
   * 2 = difficult terrain — entering this cell costs twice the base step cost.
   * Only meaningful when blocksMovement = false; blocked cells remain invalid
   * regardless of this value. Use integer multipliers only.
   */
  movementCostMultiplier: z.number().int().min(1).default(1)
});

function normalizeObstacleSemantics<T extends z.input<typeof obstacleSemanticsInputSchema>>(
  value: T
) {
  return {
    blocksMovement: value.blocksMovement,
    blocksEffect:
      value.blocksEffect ?? (value.blocksTargeting === true || value.blocksSpell === true),
    blocksVision: value.blocksVision ?? false,
    cover: value.cover ?? "none",
    clipsDiagonalMovement: value.clipsDiagonalMovement ?? false,
    movementCostMultiplier: value.movementCostMultiplier ?? 1
  };
}

export const obstacleStyleSchema = obstacleSemanticsInputSchema.transform((value) =>
  normalizeObstacleSemantics(value)
);

export const obstacleSchema = obstacleSemanticsInputSchema
  .extend({
    id: z.string(),
    battleMapId: z.string(),
    cells: z.array(coordinateSchema),
    label: z.string().optional()
  })
  .transform((value) => ({
    id: value.id,
    battleMapId: value.battleMapId,
    cells: value.cells,
    ...(value.label !== undefined ? { label: value.label } : {}),
    ...normalizeObstacleSemantics(value)
  }));

// ── Creature Size (declared early so tokenSchema can reference it) ────────────

export const creatureSizeSchema = z.enum(["Tiny", "Small", "Medium", "Large", "Huge", "Gargantuan"]);

export type CreatureSize = "Tiny" | "Small" | "Medium" | "Large" | "Huge" | "Gargantuan";

export const CREATURE_SIZE_ORDER: CreatureSize[] = ["Tiny", "Small", "Medium", "Large", "Huge", "Gargantuan"];

export const SIZE_MODIFIER_EFFECT_TYPE = "size_modifier" as const;
export type SizeModifierEffectType = typeof SIZE_MODIFIER_EFFECT_TYPE;

export const sizeStepDeltaSchema = z.union([z.literal(-1), z.literal(1)]);
export type SizeStepDelta = z.infer<typeof sizeStepDeltaSchema>;

export const DEFAULT_CREATURE_SIZE: CreatureSize = "Medium";

export const sizeTierToFootprint = {
  Tiny: { width: 1, height: 1 },
  Small: { width: 1, height: 1 },
  Medium: { width: 1, height: 1 },
  Large: { width: 2, height: 2 },
  Huge: { width: 3, height: 3 },
  Gargantuan: { width: 4, height: 4 }
} as const satisfies Record<CreatureSize, { width: number; height: number }>;

export const footprintSchema = z.object({
  width: z.number().int().positive(),
  height: z.number().int().positive()
});

export type Footprint = z.infer<typeof footprintSchema>;

export function getBaseSize(token: { base_size?: CreatureSize }): CreatureSize {
  return token.base_size ?? DEFAULT_CREATURE_SIZE;
}

export function getEffectiveSize(baseSize: CreatureSize, stepDeltas: number[]): CreatureSize {
  const baseIdx = CREATURE_SIZE_ORDER.indexOf(baseSize);
  const sum = stepDeltas.reduce((acc, delta) => acc + delta, 0);
  const rawIdx = baseIdx + sum;
  if (rawIdx < 0) return "Tiny";
  if (rawIdx >= CREATURE_SIZE_ORDER.length) return "Gargantuan";
  return CREATURE_SIZE_ORDER[rawIdx]!;
}

export function getEffectiveFootprint(size: CreatureSize): { width: number; height: number } {
  return sizeTierToFootprint[size];
}

export const tokenSchema = z.object({
  id: z.string(),
  battleMapId: z.string(),
  label: z.string(),
  kind: z.enum(["playerCharacter", "ally", "enemy", "neutral"]),
  controllerType: controllerTypeSchema,
  controllerId: z.string(),
  position: coordinateSchema,
  /**
   * Maximum movement per turn, in grid cells.
   * The tactical engine internally multiplies this by 5 to obtain the
   * movement budget in path-cost units (5 units per orthogonal step).
   * Conversion: speedMeters / METERS_PER_CELL = movementSpeedCells (floor).
   */
  movementSpeedCells: z.number().int().positive(),
  /**
   * Remaining movement budget for the current turn, in path-cost units
   * (5 units = 1 orthogonal cell, matches D&D 5-foot-square grid).
   * Reset to movementSpeedCells * 5 at the start of each turn.
   */
  movementBudget: z.number().int().nonnegative(),
  combatantId: z.string().optional(),
  /**
   * Active condition codes on this token (e.g. "blinded", "stunned").
   * Pushed by LimiarControl via syncTokens; empty when no conditions are active.
   * These are canonical machine-readable codes — the UI presentation layer
   * (condition-indicators.ts) maps them to labels, colours, and priority order.
   */
  conditions: z.array(z.string()).default([]),
  /**
   * Base creature size, used to derive the effective footprint.
   * When absent, defaults to Medium (1x1).
   * The effective size may differ from base_size when active size modifiers
   * (e.g. Enlarge/Reduce) are applied — see effective_size on sync payloads.
   */
  base_size: creatureSizeSchema.optional(),
  effective_size: creatureSizeSchema.optional(),
  effective_footprint: footprintSchema.optional()
});

export const combatStateSchema = z.object({
  id: z.string(),
  battleMapId: z.string(),
  status: combatStatusSchema,
  roundNumber: z.number().int().nonnegative(),
  turnIndex: z.number().int().nonnegative(),
  activeCombatantId: z.string().nullable(),
  initiativeOrder: z.array(z.string()),
  advancedBy: z.literal("LimiarControl"),
  version: z.number().int().nonnegative()
});

export const movementActionSchema = z.object({
  actionId: z.string(),
  tokenId: z.string(),
  requestedPath: z.array(coordinateSchema),
  submittedBy: z.string(),
  submittedAtVersion: z.number().int().nonnegative(),
  result: actionResultSchema.default("pending"),
  rejectionReason: z.string().optional()
});

export const targetingTemplateSchema = z.object({
  actionId: z.string(),
  tokenId: z.string(),
  shape: targetingShapeSchema,
  originCell: coordinateSchema,
  anchorCell: coordinateSchema,
  /** Maximum reach from the origin, in grid cells (Chebyshev distance). */
  rangeCells: z.number().int().positive(),
  /** AoE radius / dimension, in grid cells. */
  sizeCells: z.number().int().positive(),
  affectedCells: z.array(coordinateSchema).default([]),
  result: actionResultSchema.default("pending"),
  rejectionReason: z.string().optional()
});

export const activeAreaEffectSchema = z.object({
  id: z.string(),
  sourceSpellCanonicalKey: z.string().nullable().optional(),
  sourceSpellName: z.string(),
  casterParticipantId: z.string(),
  casterRefId: z.string().nullable().optional(),
  casterCharacterId: z.string().nullable().optional(),
  originPoint: coordinateSchema,
  anchorCell: coordinateSchema,
  areaShape: targetingShapeSchema,
  sizeMeters: z.number().positive(),
  radiusMeters: z.number().positive().nullable().optional(),
  lengthMeters: z.number().positive().nullable().optional(),
  sideMeters: z.number().positive().nullable().optional(),
  affectedCells: z.array(coordinateSchema).default([]),
  effectKind: activeAreaEffectKindSchema,
  duration: z.string().nullable().optional(),
  concentrationOwnerParticipantId: z.string().nullable().optional(),
  concentrationOwnerRefId: z.string().nullable().optional(),
  createdRound: z.number().int().nonnegative().nullable().optional(),
  createdTurnIndex: z.number().int().nonnegative().nullable().optional(),
  obscurement: z.string().nullable().optional(),
  terrainEffect: z.string().nullable().optional(),
  movementDamageDice: z.string().nullable().optional(),
  damageType: z.string().nullable().optional(),
  damagePerMeters: z.number().positive().nullable().optional()
});

export const spellAnchorMovementSchema = z.object({
  maxMetersPerFollowUp: z.number().positive().nullable().optional()
});

export const spellAnchorSchema = z.object({
  id: z.string(),
  sourceSpellKey: z.string(),
  sourceSpellName: z.string().nullable().optional(),
  ownerParticipantId: z.string(),
  createdByParticipantId: z.string(),
  position: coordinateSchema,
  durationType: z.literal("rounds"),
  remainingRounds: z.number().int().positive().nullable().optional(),
  expiresOn: z.enum(["turn_start", "turn_end"]).nullable().optional(),
  expiresAtParticipantId: z.string().nullable().optional(),
  renderKind: z.string().default("generic"),
  movement: spellAnchorMovementSchema.nullable().optional(),
  metadata: z.record(z.unknown()).default({})
});

export const realtimeActionEventSchema = z.object({
  eventId: z.string(),
  eventType: z.string(),
  encounterId: z.string(),
  version: z.number().int().nonnegative(),
  actionId: z.string().optional(),
  payload: z.record(z.unknown()),
  replaySafe: z.boolean().default(true)
});

export const cellElevationSchema = z.object({
  cell: coordinateSchema,
  elevationMeters: z.number().finite().min(0).max(MAX_ELEVATION_METERS),
});

export type Coordinate = z.infer<typeof coordinateSchema>;
export type GridCalibration = z.infer<typeof gridCalibrationSchema>;
export type GridDimensions = z.infer<typeof gridDimensionsSchema>;
export type ControllerType = z.infer<typeof controllerTypeSchema>;
export type ObstacleCover = z.infer<typeof obstacleCoverSchema>;
export type ObstaclePaintMode = z.infer<typeof obstaclePaintModeSchema>;
export type ActiveAreaEffectKind = z.infer<typeof activeAreaEffectKindSchema>;
export type EdgeDirection = z.infer<typeof edgeDirectionSchema>;
export type BattleMap = z.infer<typeof battleMapSchema>;
export type ObstacleStyle = z.infer<typeof obstacleStyleSchema>;
export type Obstacle = z.infer<typeof obstacleSchema>;
export type EdgeObstacle = z.infer<typeof edgeObstacleSchema>;
export type Token = z.infer<typeof tokenSchema>;
export type CombatState = z.infer<typeof combatStateSchema>;
export type MovementAction = z.infer<typeof movementActionSchema>;
export type TargetingTemplate = z.infer<typeof targetingTemplateSchema>;
export type ActiveAreaEffect = z.infer<typeof activeAreaEffectSchema>;
export type SpellAnchorMovement = z.infer<typeof spellAnchorMovementSchema>;
export type SpellAnchor = z.infer<typeof spellAnchorSchema>;
export type RealtimeActionEvent = z.infer<typeof realtimeActionEventSchema>;
export type CellElevation = z.infer<typeof cellElevationSchema>;
