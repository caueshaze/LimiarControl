import type {
  Coordinate,
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

export interface BattleMapUIState {
  selectedTokenId?: string;
  placingTokenId: string | null;
  movementPreview: Coordinate[];
  targetingPreview: Coordinate[];
  embeddedSelectionMode: EmbeddedSelectionMode;
  embeddedPreview: Coordinate[];
  embeddedSelectedCell?: Coordinate;
  embeddedSelectedTargetRefId?: string;
  embeddedCombatPhase?: EmbeddedCombatPhase;
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
