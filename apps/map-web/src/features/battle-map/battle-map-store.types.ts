import type {
  Coordinate,
  ActiveAreaEffect,
  GridCalibration,
  ObstaclePaintMode,
  EdgeDirection
} from "@limiarmap/shared-contracts";
import type {
  ObstacleBrushPresetId,
  EdgeBrushPresetId
} from "./obstacle-presets";

export interface TacticalDiagnostics {
  isValid: boolean;
  failureReasons: string[];
  checks: Record<string, boolean>;
  metadata: Record<string, number | string | boolean>;
}

export interface TacticalPreviewState {
  active: boolean;
  sourceTokenId: string | null;
  actionType: "move" | "attack" | "spell" | null;
  targetCell: Coordinate | null;
  targetEntityId: string | null;
  diagnostics: TacticalDiagnostics | null;
  aoeCells: Coordinate[];
  reachableCells: Coordinate[];
}

export interface TokenMovementRejectionState {
  tokenId: string;
  reason: string;
  message: string;
  pathCostUnits?: number;
  movementBudget?: number;
  exceededBy?: number;
}

export type SpellMapHighlightKind = "target" | "instance-target" | "area-cell" | "affected-token";
export type SpellMapHighlightStatus = "valid" | "invalid" | "partial" | "unknown";
export type SpellMapHighlight = {
  kind: SpellMapHighlightKind;
  status: SpellMapHighlightStatus;
  targetRefId?: string | null;
  instanceIndex?: number | null;
  cell?: { x: number; y: number } | null;
  label?: string | null;
  reason?: string | null;
};

export interface BattleMapUIState {
  selectedTokenId?: string;
  placingTokenId: string | null;
  movementPreview: Coordinate[];
  targetingPreview: Coordinate[];
  embeddedSelectionMode: EmbeddedSelectionMode;
  embeddedPreview: Coordinate[];
  embeddedActiveAreaEffects: ActiveAreaEffect[];
  embeddedSelectedCell?: Coordinate;
  embeddedSelectedTargetRefId?: string;
  embeddedCombatPhase?: EmbeddedCombatPhase;
  embeddedSpellHighlights: SpellMapHighlight[];
  message?: string;
  isGridEditMode: boolean;
  isObstaclePaintMode: boolean;
  gridCalibrationDraft?: GridCalibration;
  gridWidthDraft?: number;
  gridHeightDraft?: number;
  pendingGridCalibrationActionId?: string;
  pendingObstaclePaintActionId?: string;
  obstacleBrushRadius: number;
  obstacleBrushMode: ObstaclePaintMode;
  obstacleBrushPresetId: ObstacleBrushPresetId;
  obstaclePaintTarget: "cell" | "edge";
  edgeDirection: EdgeDirection;
  edgeBrushPresetId: EdgeBrushPresetId;
  pendingEdgePaintActionId?: string;
  isElevationPaintMode: boolean;
  elevationBrushPresetMeters: number;
  elevationBrushRadius: number;
  elevationBrushMode: "paint" | "erase";
  pendingElevationPaintActionId?: string;
  mapImageAspectRatio: number;
  mapImageNaturalWidthPx: number;
  mapImageNaturalHeightPx: number;
  mapFrameWidthPx: number;
  mapFrameHeightPx: number;
  lastMovementRejectionByTokenId: Record<string, TokenMovementRejectionState>;
  tacticalPreview: TacticalPreviewState;
}

export type EmbeddedSelectionMode = "none" | "select-token" | "select-cell";

export type EmbeddedCombatPhase = "initiative" | "placement" | "active" | "ended";
