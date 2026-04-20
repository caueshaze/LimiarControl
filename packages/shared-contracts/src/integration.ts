import { z } from "zod";
import {
  battleMapSchema,
  combatStateSchema,
  coordinateSchema,
  controllerTypeSchema,
  edgeObstacleSchema,
  obstacleCoverSchema,
  obstacleSchema,
  tokenSchema
} from "./domain";

// ---------------------------------------------------------------------------
// Requests — LimiarControl → LimiarMap
// ---------------------------------------------------------------------------

/**
 * A single combatant entry with its initiative score.
 * LimiarControl sorts and sends this list; LimiarMap derives the turn order.
 */
export const initiativeEntrySchema = z.object({
  /** ID used in CombatState.initiativeOrder and Token.combatantId */
  combatantId: z.string(),
  /** Higher score acts first. Ties preserved in submission order. */
  initiativeScore: z.number()
});

/**
 * A single per-cell obstacle authored at the campaign level.
 * Canonical path for maps created after the semantic obstacle feature;
 * supersedes `blockedCells` when present.
 */
export const campaignObstacleInputSchema = z.object({
  x: z.number().int().min(0),
  y: z.number().int().min(0),
  blocksMovement: z.boolean(),
  blocksEffect: z.boolean().default(false),
  blocksVision: z.boolean().default(false),
  cover: obstacleCoverSchema.default("none"),
  clipsDiagonalMovement: z.boolean().default(false),
  movementCostMultiplier: z.number().int().min(1).default(1)
});

export type CampaignObstacleInput = z.infer<typeof campaignObstacleInputSchema>;

/**
 * A single edge obstacle authored at the campaign level.
 * Canonical path for edge-based tactical boundaries created from the
 * campaign map configuration UI.
 */
export const campaignEdgeObstacleInputSchema = z.object({
  x: z.number().int().min(0),
  y: z.number().int().min(0),
  direction: z.enum(["N", "E", "S", "W"]),
  blocksMovement: z.boolean(),
  blocksVision: z.boolean().default(false),
  blocksEffect: z.boolean().default(false),
  cover: obstacleCoverSchema.default("none")
});

export type CampaignEdgeObstacleInput = z.infer<
  typeof campaignEdgeObstacleInputSchema
>;

export const integrationBattleMapSchema = z.object({
  name: z.string(),
  gridWidth: z.number().int().positive().max(150),
  gridHeight: z.number().int().positive().max(150),
  gridCalibration: battleMapSchema.shape.gridCalibration,
  imageUrl: z.string(),
  sourceImageUrl: z.string().nullable().optional(),
  // Canonical semantic obstacles (Phase 2+): each entry maps a single cell to
  // its full tactical semantics. When present, `blockedCells` is ignored.
  obstacles: z.array(campaignObstacleInputSchema).optional(),
  // Canonical semantic edge obstacles authored between adjacent cells.
  edgeObstacles: z.array(campaignEdgeObstacleInputSchema).optional(),
  // Phase 1 legacy: movement-only blocked cells. Kept for backward compat with
  // old campaign maps that pre-date semantic obstacles.
  blockedCells: z.array(coordinateSchema).optional()
});

/**
 * Start combat from scratch. Sets status → "active", round 1, turn 0.
 * Idempotency: repeated calls with the same actionId are no-ops.
 * Can also restart a completed combat.
 */
export const startCombatRequestSchema = z.object({
  actionId: z.string(),
  combatants: z.array(initiativeEntrySchema).min(1),
  battleMap: integrationBattleMapSchema.optional()
});

/**
 * Replace the initiative order at any point (before or during combat).
 * If the current active combatant is still in the new list their position
 * is preserved; otherwise the first combatant in the new order becomes active.
 */
export const setInitiativeRequestSchema = z.object({
  actionId: z.string(),
  combatants: z.array(initiativeEntrySchema).min(1)
});

/**
 * Advance to the next turn. Usable as a plain HTTP call for server-to-server integration.
 */
export const advanceTurnRequestSchema = z.object({
  actionId: z.string()
});

/**
 * End combat. Sets status → "completed" and clears the active combatant.
 */
export const endCombatRequestSchema = z.object({
  actionId: z.string()
});

/**
 * Patch specific token fields that LimiarControl owns:
 * combatantId, movement speed, and who controls the token on the map.
 * Only provided fields are updated.
 *
 * All numeric values here are in map units (cells), not Control-domain meters.
 * Conversion: speedMeters / METERS_PER_CELL = movementSpeedCells (floor).
 */
export const tokenSyncEntrySchema = z.object({
  tokenId: z.string(),
  combatantId: z.string().optional(),
  /**
   * Maximum movement per turn, in grid cells.
   * Example: 9 m speed → 6 cells (with metersPerCell = 1.5).
   */
  movementSpeedCells: z.number().int().positive().optional(),
  label: z.string().min(1).optional(),
  controllerId: z.string().optional(),
  controllerType: controllerTypeSchema.optional(),
  /**
   * Active condition codes for this token (e.g. ["blinded", "stunned"]).
   * LimiarControl pushes the current condition list after each state-changing
   * action. Omit to leave existing conditions unchanged; send [] to clear all.
   */
  conditions: z.array(z.string()).optional()
});

/**
 * Bulk-update token metadata. Safe to call after character sheet changes.
 * Call this at session start to link your combatantIds to the GM's map tokens.
 */
export const syncTokensRequestSchema = z.object({
  tokens: z.array(tokenSyncEntrySchema).min(1)
});

/**
 * Validate a single-target attack or ability.
 *
 * LimiarMap resolves:
 *  - Whether both combatants are linked to tokens on the map
 *  - Whether the target is within range (if range is provided)
 *
 * Range is measured in grid cells using the Chebyshev distance
 * (max of |Δx|, |Δy|) — the standard D&D 5e grid metric.
 *
 * Set range to null to skip distance validation (e.g. for spells with
 * unlimited range, or when LimiarControl already handled range gating).
 *
 * Future extension point: area/shape targeting will be a separate endpoint
 * once the basic single-target flow is stable.
 */
export const singleTargetRequestSchema = z.object({
  actionId: z.string(),
  /** The acting combatant (attacker / caster) */
  combatantId: z.string(),
  /** The combatant being targeted */
  targetCombatantId: z.string(),
  /**
   * Maximum range in grid cells (Chebyshev distance). Null skips distance validation.
   * Must be a positive integer when provided.
   * Conversion from Control domain: rangeCells = round(rangeMeters / METERS_PER_CELL).
   */
  rangeCells: z.number().int().positive().nullable(),
  /**
   * When true, LimiarMap checks that no obstacle with `blocksVision` lies on
   * the line between attacker and target. Defaults to false (skip LoS check).
   */
  requiresSight: z.boolean().default(false),
  /**
   * When true, LimiarMap checks that no obstacle with `blocksEffect` lies on
   * the line between attacker and target. Defaults to false (skip LoE check).
   */
  requiresEffect: z.boolean().default(false)
});

/**
 * Validate an area-of-effect action.
 *
 * LimiarControl remains the authority for rules and only asks LimiarMap to
 * resolve geometry and which combatants/tokens are affected.
 */
export const areaTargetShapeSchema = z.enum(["sphere", "cone", "line", "cube"]);

/**
 * All numeric dimensions in this schema are in grid cells, not meters.
 * The LimiarControl boundary must convert meter values before sending:
 *   rangeCells = round(rangeMeters / METERS_PER_CELL)
 *   sizeCells  = round(sizeMeters  / METERS_PER_CELL)
 */
export const areaTargetRequestSchema = z.object({
  actionId: z.string(),
  combatantId: z.string(),
  shape: areaTargetShapeSchema,
  originCell: coordinateSchema,
  anchorCell: coordinateSchema,
  /** Maximum distance from origin to anchor, in grid cells (Chebyshev). Null skips range check. */
  rangeCells: z.number().int().positive().nullable(),
  /** AoE radius / dimension, in grid cells. */
  sizeCells: z.number().int().positive(),
  /**
   * When true, checks line of sight from origin to anchor cell.
   * Defaults to false (skip LoS check).
   */
  requiresSight: z.boolean().default(false),
  /**
   * When true, checks line of effect from origin to anchor cell using
   * obstacles with `blocksEffect === true`.
   */
  requiresEffect: z.boolean().default(false)
});

// ---------------------------------------------------------------------------
// Responses — LimiarMap → LimiarControl
// ---------------------------------------------------------------------------

/**
 * Integration-specific encounter snapshot.
 * Extends the standard snapshot with a top-level `version` field so external
 * consumers can track state without diving into combatState.
 */
export const integrationStateResponseSchema = z.object({
  sessionId: z.string(),
  version: z.number().int().nonnegative(),
  battleMap: battleMapSchema,
  combatState: combatStateSchema,
  tokens: z.array(tokenSchema),
  obstacles: z.array(obstacleSchema),
  edgeObstacles: z.array(edgeObstacleSchema).default([])
});

/**
 * Returned by the single-target targeting endpoint.
 * Carries enough context for LimiarControl to confirm the action was processed.
 */
export const singleTargetResponseSchema = z.object({
  isValid: z.boolean(),
  /** Machine-readable rejection reason. Null when isValid is true. */
  reason: z.string().nullable(),
  sessionId: z.string(),
  actionId: z.string(),
  version: z.number().int().nonnegative(),
  /** Present when isValid is true. Null otherwise. */
  sourceTokenId: z.string().nullable(),
  /** Present when isValid is true. Null otherwise. */
  targetTokenId: z.string().nullable(),
  /** Chebyshev distance between source and target, in cells, when resolved. */
  distanceCells: z.number().int().nonnegative().nullable().optional(),
  /**
   * Cover level evaluated along the line between source and target.
   * Evaluated independently of LoS/LoE. Defaults to "none".
   *
   * Values: "none" | "half" | "threeQuarters" | "full"
   *
   * - "full" causes isValid=false with reason="full_cover" for direct attacks
   * - "half" / "threeQuarters" are informational for downstream AC modifiers
   */
  cover: obstacleCoverSchema.default("none")
});

export const areaTargetResponseSchema = z.object({
  isValid: z.boolean(),
  reason: z.string().nullable(),
  sessionId: z.string(),
  actionId: z.string(),
  version: z.number().int().nonnegative(),
  shape: areaTargetShapeSchema,
  sourceTokenId: z.string().nullable(),
  affectedCells: z.array(coordinateSchema),
  affectedTokenIds: z.array(z.string()),
  affectedCombatantIds: z.array(z.string())
});

export const areaTargetPreviewResponseSchema = areaTargetResponseSchema;

export const movementPreviewRequestSchema = z.object({
  actionId: z.string(),
  combatantId: z.string(),
  destinationCell: coordinateSchema
});

export const movementPreviewResponseSchema = z.object({
  isValid: z.boolean(),
  reason: z.string().nullable(),
  sessionId: z.string(),
  actionId: z.string(),
  version: z.number().int().nonnegative(),
  tokenId: z.string().nullable(),
  combatantId: z.string().nullable(),
  sourceCell: coordinateSchema.nullable(),
  destinationCell: coordinateSchema,
  path: z.array(coordinateSchema),
  pathCostUnits: z.number().int().nonnegative(),
  movementBudget: z.number().int().nonnegative(),
  movementSpeedCells: z.number().int().positive(),
  remainingBudget: z.number().int().nonnegative()
});

/**
 * Uniform error response for all integration endpoints.
 * Use `reason` for programmatic handling, `message` for human-readable logs.
 */
export const integrationErrorResponseSchema = z.object({
  message: z.string(),
  /** Machine-readable code. See integration-errors.ts for the full list. */
  reason: z.string()
});

// ---------------------------------------------------------------------------
// Realtime envelopes — LimiarMap → Centrifugo / transitional transports
// ---------------------------------------------------------------------------

/**
 * Authoritative spatial events emitted by LimiarMap via Centrifugo.
 */
export const integrationSpatialEventTypeSchema = z.enum([
  "movement.applied",
  "tokens.synced",
  "combat.started",
  "combat.advanced",
  "combat.ended",
  "initiative.updated",
  "targeting.resolved",
  "action.rejected",
  "obstacles.updated",
  "edge_obstacles.updated",
  "grid.calibration.updated"
]);

export const integrationSpatialEventEnvelopeSchema = z.object({
  eventId: z.string(),
  eventType: integrationSpatialEventTypeSchema,
  encounterId: z.string(),
  version: z.number().int().nonnegative(),
  actionId: z.string().optional(),
  payload: z.record(z.unknown()),
  replaySafe: z.boolean().default(true)
});

// ---------------------------------------------------------------------------
// Broadcast event payloads (Centrifugo → all web clients)
// ---------------------------------------------------------------------------

export const combatStartedPayloadSchema = z.object({
  roundNumber: z.number().int().nonnegative(),
  turnIndex: z.number().int().nonnegative(),
  activeCombatantId: z.string().nullable(),
  initiativeOrder: z.array(z.string())
});

export const combatEndedPayloadSchema = z.object({
  roundNumber: z.number().int().nonnegative()
});

export const initiativeUpdatedPayloadSchema = z.object({
  initiativeOrder: z.array(z.string()),
  activeCombatantId: z.string().nullable(),
  turnIndex: z.number().int().nonnegative()
});

export const tokensSyncedPayloadSchema = z.object({
  tokens: z.array(tokenSchema)
});

export const singleTargetResolvedPayloadSchema = z.object({
  sourceTokenId: z.string(),
  targetTokenId: z.string(),
  isValid: z.boolean(),
  reason: z.string().nullable(),
  /** Cover level for the resolved targeting action. */
  cover: obstacleCoverSchema.default("none")
});

export const areaTargetResolvedPayloadSchema = z.object({
  sourceTokenId: z.string(),
  shape: areaTargetShapeSchema,
  affectedCells: z.array(coordinateSchema),
  affectedTokenIds: z.array(z.string()),
  affectedCombatantIds: z.array(z.string()),
  isValid: z.boolean(),
  reason: z.string().nullable()
});

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type InitiativeEntry = z.infer<typeof initiativeEntrySchema>;
export type StartCombatRequest = z.infer<typeof startCombatRequestSchema>;
export type SetInitiativeRequest = z.infer<typeof setInitiativeRequestSchema>;
export type AdvanceTurnRequest = z.infer<typeof advanceTurnRequestSchema>;
export type EndCombatRequest = z.infer<typeof endCombatRequestSchema>;
export type TokenSyncEntry = z.infer<typeof tokenSyncEntrySchema>;
export type SyncTokensRequest = z.infer<typeof syncTokensRequestSchema>;
export type SingleTargetRequest = z.infer<typeof singleTargetRequestSchema>;
export type AreaTargetShape = z.infer<typeof areaTargetShapeSchema>;
export type AreaTargetRequest = z.infer<typeof areaTargetRequestSchema>;
export type IntegrationStateResponse = z.infer<
  typeof integrationStateResponseSchema
>;
export type SingleTargetResponse = z.infer<typeof singleTargetResponseSchema>;
export type AreaTargetResponse = z.infer<typeof areaTargetResponseSchema>;
export type AreaTargetPreviewResponse = z.infer<
  typeof areaTargetPreviewResponseSchema
>;
export type MovementPreviewRequest = z.infer<typeof movementPreviewRequestSchema>;
export type MovementPreviewResponse = z.infer<typeof movementPreviewResponseSchema>;
export type IntegrationErrorResponse = z.infer<
  typeof integrationErrorResponseSchema
>;
export type IntegrationSpatialEventType = z.infer<
  typeof integrationSpatialEventTypeSchema
>;
export type IntegrationSpatialEventEnvelope = z.infer<
  typeof integrationSpatialEventEnvelopeSchema
>;
export type CombatStartedPayload = z.infer<typeof combatStartedPayloadSchema>;
export type CombatEndedPayload = z.infer<typeof combatEndedPayloadSchema>;
export type InitiativeUpdatedPayload = z.infer<
  typeof initiativeUpdatedPayloadSchema
>;
export type TokensSyncedPayload = z.infer<typeof tokensSyncedPayloadSchema>;
export type SingleTargetResolvedPayload = z.infer<
  typeof singleTargetResolvedPayloadSchema
>;
export type AreaTargetResolvedPayload = z.infer<
  typeof areaTargetResolvedPayloadSchema
>;
