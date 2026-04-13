import type {
  Coordinate,
  EncounterSnapshotResponse,
  GridCalibration,
  ObstaclePaintMode,
  EdgeDirection
} from "@limiarmap/shared-contracts";
import { sessionStore } from "../../services/session-store";
import type {
  ObstacleBrushPresetId,
  EdgeBrushPresetId
} from "./obstacle-presets";

type Listener = () => void;

// ─── Tactical Preview (Phase U1) ──────────────────────────────────────────────

export interface TacticalDiagnostics {
  isValid: boolean;
  failureReasons: string[];
  checks: Record<string, boolean>;
  metadata: Record<string, number | string | boolean>;
}

export interface TacticalPreviewState {
  /** True while a token is selected or embedded selection mode is active. */
  active: boolean;
  sourceTokenId: string | null;
  /** Interaction context: movement reach or targeting intent. */
  actionType: "move" | "attack" | "spell" | null;
  /** Currently-hovered grid cell. */
  targetCell: Coordinate | null;
  /** ref_id of the currently-hovered entity (if any). */
  targetEntityId: string | null;
  /** Last diagnostics returned from the preview API (null when no target). */
  diagnostics: TacticalDiagnostics | null;
  /** AoE footprint cells when casting an area spell. */
  aoeCells: Coordinate[];
  /** All cells reachable by sourceToken (Chebyshev circle, movement context). */
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
  movementPreview: Coordinate[];
  targetingPreview: Coordinate[];
  embeddedSelectionMode: EmbeddedSelectionMode;
  embeddedPreview: Coordinate[];
  embeddedSelectedCell?: Coordinate;
  embeddedSelectedTargetRefId?: string;
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

class BattleMapStore {
  private state: BattleMapUIState = {
    movementPreview: [],
    targetingPreview: [],
    embeddedSelectionMode: "none",
    embeddedPreview: [],
    isGridEditMode: false,
    isObstaclePaintMode: false,
    obstacleBrushRadius: 1,
    obstacleBrushMode: "paint",
    obstacleBrushPresetId: "solid_wall",
    mapImageAspectRatio: 1,
    mapImageNaturalWidthPx: 0,
    mapImageNaturalHeightPx: 0,
    mapFrameWidthPx: 0,
    mapFrameHeightPx: 0,
    lastMovementRejectionByTokenId: {},
    tacticalPreview: {
      active: false,
      sourceTokenId: null,
      actionType: null,
      targetCell: null,
      targetEntityId: null,
      diagnostics: null,
      aoeCells: [],
      reachableCells: []
    },
    obstaclePaintTarget: "cell" as "cell" | "edge",
    edgeDirection: "E" as EdgeDirection,
    edgeBrushPresetId: "edge_wall" as EdgeBrushPresetId,
    pendingEdgePaintActionId: undefined
  };
  private readonly listeners = new Set<Listener>();

  getEncounter(): EncounterSnapshotResponse | null {
    return sessionStore.getSnapshot();
  }

  getState(): BattleMapUIState {
    return this.state;
  }

  setMovementPreview(movementPreview: Coordinate[]): void {
    this.state = { ...this.state, movementPreview };
    this.emit();
  }

  setTargetingPreview(targetingPreview: Coordinate[]): void {
    this.state = { ...this.state, targetingPreview };
    this.emit();
  }

  setEmbeddedInteractionContext(context: {
    selectionMode: EmbeddedSelectionMode;
    previewCells: Coordinate[];
    selectedCell?: Coordinate | null;
    selectedTargetRefId?: string | null;
  }): void {
    this.state = {
      ...this.state,
      embeddedSelectionMode: context.selectionMode,
      embeddedPreview: context.previewCells,
      embeddedSelectedCell: context.selectedCell ?? undefined,
      embeddedSelectedTargetRefId: context.selectedTargetRefId ?? undefined
    };
    this.emit();
  }

  setEmbeddedSelectedCell(selectedCell?: Coordinate | null): void {
    this.state = {
      ...this.state,
      embeddedSelectedCell: selectedCell ?? undefined
    };
    this.emit();
  }

  clearEmbeddedInteraction(): void {
    this.state = {
      ...this.state,
      embeddedSelectionMode: "none",
      embeddedPreview: [],
      embeddedSelectedCell: undefined,
      embeddedSelectedTargetRefId: undefined
    };
    this.emit();
  }

  setMessage(message?: string): void {
    this.state = { ...this.state, message };
    this.emit();
  }

  setTokenMovementRejection(rejection: TokenMovementRejectionState): void {
    this.state = {
      ...this.state,
      lastMovementRejectionByTokenId: {
        ...this.state.lastMovementRejectionByTokenId,
        [rejection.tokenId]: rejection
      }
    };
    this.emit();
  }

  clearTokenMovementRejection(tokenId: string): void {
    if (!this.state.lastMovementRejectionByTokenId[tokenId]) {
      return;
    }
    const next = { ...this.state.lastMovementRejectionByTokenId };
    delete next[tokenId];
    this.state = {
      ...this.state,
      lastMovementRejectionByTokenId: next
    };
    this.emit();
  }

  setMapImageAspectRatio(mapImageAspectRatio: number): void {
    if (this.state.mapImageAspectRatio === mapImageAspectRatio) {
      return;
    }

    this.state = { ...this.state, mapImageAspectRatio };
    this.emit();
  }

  setMapImageNaturalSize(
    mapImageNaturalWidthPx: number,
    mapImageNaturalHeightPx: number
  ): void {
    if (
      this.state.mapImageNaturalWidthPx === mapImageNaturalWidthPx &&
      this.state.mapImageNaturalHeightPx === mapImageNaturalHeightPx
    ) {
      return;
    }

    this.state = {
      ...this.state,
      mapImageNaturalWidthPx,
      mapImageNaturalHeightPx
    };
    this.emit();
  }

  setMapFrameSize(mapFrameWidthPx: number, mapFrameHeightPx: number): void {
    if (
      this.state.mapFrameWidthPx === mapFrameWidthPx &&
      this.state.mapFrameHeightPx === mapFrameHeightPx
    ) {
      return;
    }

    this.state = {
      ...this.state,
      mapFrameWidthPx,
      mapFrameHeightPx
    };
    this.emit();
  }

  startGridEdit(
    gridCalibration: GridCalibration,
    gridWidth: number,
    gridHeight: number
  ): void {
    this.state = {
      ...this.state,
      isGridEditMode: true,
      isObstaclePaintMode: false,
      gridCalibrationDraft: gridCalibration,
      gridWidthDraft: gridWidth,
      gridHeightDraft: gridHeight,
      pendingGridCalibrationActionId: undefined,
      pendingObstaclePaintActionId: undefined,
      message: undefined
    };
    this.emit();
  }

  updateGridCalibrationDraft(gridCalibration: GridCalibration): void {
    this.state = {
      ...this.state,
      gridCalibrationDraft: gridCalibration
    };
    this.emit();
  }

  setGridDimensionsDraft(gridWidth: number, gridHeight: number): void {
    if (
      this.state.gridWidthDraft === gridWidth &&
      this.state.gridHeightDraft === gridHeight
    ) {
      return;
    }

    this.state = {
      ...this.state,
      gridWidthDraft: gridWidth,
      gridHeightDraft: gridHeight
    };
    this.emit();
  }

  cancelGridEdit(): void {
    this.state = {
      ...this.state,
      isGridEditMode: false,
      gridCalibrationDraft: undefined,
      gridWidthDraft: undefined,
      gridHeightDraft: undefined,
      pendingGridCalibrationActionId: undefined
    };
    this.emit();
  }

  startObstaclePaint(): void {
    this.state = {
      ...this.state,
      isObstaclePaintMode: true,
      isGridEditMode: false,
      gridCalibrationDraft: undefined,
      gridWidthDraft: undefined,
      gridHeightDraft: undefined,
      pendingGridCalibrationActionId: undefined,
      pendingObstaclePaintActionId: undefined,
      pendingEdgePaintActionId: undefined,
      message: undefined
    };
    this.emit();
  }

  cancelObstaclePaint(): void {
    this.state = {
      ...this.state,
      isObstaclePaintMode: false,
      pendingObstaclePaintActionId: undefined,
      pendingEdgePaintActionId: undefined
    };
    this.emit();
  }

  setObstacleBrushRadius(obstacleBrushRadius: number): void {
    if (this.state.obstacleBrushRadius === obstacleBrushRadius) {
      return;
    }

    this.state = {
      ...this.state,
      obstacleBrushRadius
    };
    this.emit();
  }

  setObstacleBrushMode(obstacleBrushMode: ObstaclePaintMode): void {
    if (this.state.obstacleBrushMode === obstacleBrushMode) {
      return;
    }

    this.state = {
      ...this.state,
      obstacleBrushMode
    };
    this.emit();
  }

  setObstacleBrushPreset(obstacleBrushPresetId: ObstacleBrushPresetId): void {
    if (this.state.obstacleBrushPresetId === obstacleBrushPresetId) {
      return;
    }

    this.state = {
      ...this.state,
      obstacleBrushPresetId
    };
    this.emit();
  }

  markObstaclePaintPending(actionId: string): void {
    this.state = {
      ...this.state,
      pendingObstaclePaintActionId: actionId
    };
    this.emit();
  }

  markGridCalibrationPending(actionId: string): void {
    this.state = {
      ...this.state,
      pendingGridCalibrationActionId: actionId
    };
    this.emit();
  }

  completeGridCalibrationUpdate(actionId?: string): boolean {
    if (!actionId || this.state.pendingGridCalibrationActionId !== actionId) {
      return false;
    }

    this.state = {
      ...this.state,
      isGridEditMode: false,
      gridCalibrationDraft: undefined,
      gridWidthDraft: undefined,
      gridHeightDraft: undefined,
      pendingGridCalibrationActionId: undefined
    };
    this.emit();
    return true;
  }

  completeObstaclePaintUpdate(actionId?: string): boolean {
    if (!actionId || this.state.pendingObstaclePaintActionId !== actionId) {
      return false;
    }

    this.state = {
      ...this.state,
      pendingObstaclePaintActionId: undefined
    };
    this.emit();
    return true;
  }

  failGridCalibrationUpdate(actionId?: string): boolean {
    if (!actionId || this.state.pendingGridCalibrationActionId !== actionId) {
      return false;
    }

    this.state = {
      ...this.state,
      pendingGridCalibrationActionId: undefined
    };
    this.emit();
    return true;
  }

  failObstaclePaintUpdate(actionId?: string): boolean {
    if (!actionId || this.state.pendingObstaclePaintActionId !== actionId) {
      return false;
    }

    this.state = {
      ...this.state,
      pendingObstaclePaintActionId: undefined
    };
    this.emit();
    return true;
  }

  setObstaclePaintTarget(target: "cell" | "edge"): void {
    if (this.state.obstaclePaintTarget === target) {
      return;
    }

    this.state = {
      ...this.state,
      obstaclePaintTarget: target
    };
    this.emit();
  }

  setEdgeDirection(direction: EdgeDirection): void {
    if (this.state.edgeDirection === direction) {
      return;
    }

    this.state = {
      ...this.state,
      edgeDirection: direction
    };
    this.emit();
  }

  setEdgeBrushPreset(presetId: EdgeBrushPresetId): void {
    if (this.state.edgeBrushPresetId === presetId) {
      return;
    }

    this.state = {
      ...this.state,
      edgeBrushPresetId: presetId
    };
    this.emit();
  }

  markEdgePaintPending(actionId: string): void {
    this.state = {
      ...this.state,
      pendingEdgePaintActionId: actionId
    };
    this.emit();
  }

  completeEdgePaintUpdate(actionId?: string): boolean {
    if (!actionId || this.state.pendingEdgePaintActionId !== actionId) {
      return false;
    }

    this.state = {
      ...this.state,
      pendingEdgePaintActionId: undefined
    };
    this.emit();
    return true;
  }

  failEdgePaintUpdate(actionId?: string): boolean {
    if (!actionId || this.state.pendingEdgePaintActionId !== actionId) {
      return false;
    }

    this.state = {
      ...this.state,
      pendingEdgePaintActionId: undefined
    };
    this.emit();
    return true;
  }

  // ─── Tactical preview ──────────────────────────────────────────────────

  activateTacticalPreview(
    sourceTokenId: string,
    actionType: "move" | "attack" | "spell"
  ): void {
    this.state = {
      ...this.state,
      tacticalPreview: {
        ...this.state.tacticalPreview,
        active: true,
        sourceTokenId,
        actionType
      }
    };
    this.emit();
  }

  deactivateTacticalPreview(): void {
    this.state = {
      ...this.state,
      tacticalPreview: {
        active: false,
        sourceTokenId: null,
        actionType: null,
        targetCell: null,
        targetEntityId: null,
        diagnostics: null,
        aoeCells: [],
        reachableCells: []
      }
    };
    this.emit();
  }

  setTacticalPreviewTarget(
    targetCell: Coordinate | null,
    targetEntityId: string | null
  ): void {
    const prev = this.state.tacticalPreview;
    if (
      prev.targetCell?.x === targetCell?.x &&
      prev.targetCell?.y === targetCell?.y &&
      prev.targetEntityId === targetEntityId
    ) {
      return;
    }
    this.state = {
      ...this.state,
      tacticalPreview: { ...prev, targetCell, targetEntityId }
    };
    this.emit();
  }

  setTacticalPreviewDiagnostics(
    diagnostics: TacticalDiagnostics | null
  ): void {
    this.state = {
      ...this.state,
      tacticalPreview: { ...this.state.tacticalPreview, diagnostics }
    };
    this.emit();
  }

  setTacticalPreviewReachableCells(reachableCells: Coordinate[]): void {
    this.state = {
      ...this.state,
      tacticalPreview: { ...this.state.tacticalPreview, reachableCells }
    };
    this.emit();
  }

  setTacticalPreviewAoeCells(aoeCells: Coordinate[]): void {
    this.state = {
      ...this.state,
      tacticalPreview: { ...this.state.tacticalPreview, aoeCells }
    };
    this.emit();
  }

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private emit(): void {
    this.listeners.forEach((listener) => listener());
  }
}

export const battleMapStore = new BattleMapStore();
