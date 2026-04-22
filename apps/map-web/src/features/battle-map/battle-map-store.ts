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
import type {
  TacticalDiagnostics,
  TacticalPreviewState,
  BattleMapUIState,
  EmbeddedCombatPhase,
  EmbeddedSelectionMode,
  TokenMovementRejectionState
} from "./battle-map-store.types";

export type {
  TacticalDiagnostics,
  TacticalPreviewState,
  TokenMovementRejectionState,
  BattleMapUIState,
  EmbeddedCombatPhase,
  EmbeddedSelectionMode
} from "./battle-map-store.types";

type Listener = () => void;

class BattleMapStore {
  private state: BattleMapUIState = {
    placingTokenId: null,
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

  private set(patch: Partial<BattleMapUIState>): void {
    this.state = { ...this.state, ...patch };
    this.listeners.forEach((l) => l());
  }

  private setIfChanged(patch: Partial<BattleMapUIState>, changed: boolean): void {
    if (changed) this.set(patch);
  }

  setPlacingTokenId(placingTokenId: string | null): void { this.set({ placingTokenId }); }

  setMovementPreview(movementPreview: Coordinate[]): void { this.set({ movementPreview }); }
  setTargetingPreview(targetingPreview: Coordinate[]): void { this.set({ targetingPreview }); }
  setMessage(message?: string): void { this.set({ message }); }

  setMapImageAspectRatio(r: number): void { this.setIfChanged({ mapImageAspectRatio: r }, this.state.mapImageAspectRatio !== r); }
  setMapImageNaturalSize(w: number, h: number): void { this.setIfChanged({ mapImageNaturalWidthPx: w, mapImageNaturalHeightPx: h }, this.state.mapImageNaturalWidthPx !== w || this.state.mapImageNaturalHeightPx !== h); }
  setMapFrameSize(w: number, h: number): void { this.setIfChanged({ mapFrameWidthPx: w, mapFrameHeightPx: h }, this.state.mapFrameWidthPx !== w || this.state.mapFrameHeightPx !== h); }
  setObstacleBrushRadius(r: number): void { this.setIfChanged({ obstacleBrushRadius: r }, this.state.obstacleBrushRadius !== r); }
  setObstacleBrushMode(m: ObstaclePaintMode): void { this.setIfChanged({ obstacleBrushMode: m }, this.state.obstacleBrushMode !== m); }
  setObstacleBrushPreset(p: ObstacleBrushPresetId): void { this.setIfChanged({ obstacleBrushPresetId: p }, this.state.obstacleBrushPresetId !== p); }
  setObstaclePaintTarget(t: "cell" | "edge"): void { this.setIfChanged({ obstaclePaintTarget: t }, this.state.obstaclePaintTarget !== t); }
  setEdgeDirection(d: EdgeDirection): void { this.setIfChanged({ edgeDirection: d }, this.state.edgeDirection !== d); }
  setEdgeBrushPreset(p: EdgeBrushPresetId): void { this.setIfChanged({ edgeBrushPresetId: p }, this.state.edgeBrushPresetId !== p); }
  setGridDimensionsDraft(w: number, h: number): void { this.setIfChanged({ gridWidthDraft: w, gridHeightDraft: h }, this.state.gridWidthDraft !== w || this.state.gridHeightDraft !== h); }

  setEmbeddedInteractionContext(ctx: {
    selectionMode: EmbeddedSelectionMode;
    previewCells: Coordinate[];
    selectedCell?: Coordinate | null;
    selectedTargetRefId?: string | null;
    combatPhase?: EmbeddedCombatPhase | null;
  }): void {
    this.set({
      embeddedSelectionMode: ctx.selectionMode,
      embeddedPreview: ctx.previewCells,
      embeddedSelectedCell: ctx.selectedCell ?? undefined,
      embeddedSelectedTargetRefId: ctx.selectedTargetRefId ?? undefined,
      embeddedCombatPhase: ctx.combatPhase ?? undefined
    });
  }

  setEmbeddedSelectedCell(c?: Coordinate | null): void { this.set({ embeddedSelectedCell: c ?? undefined }); }

  clearEmbeddedInteraction(): void {
    this.set({ embeddedSelectionMode: "none", embeddedPreview: [], embeddedSelectedCell: undefined, embeddedSelectedTargetRefId: undefined, embeddedCombatPhase: undefined });
  }

  setTokenMovementRejection(rejection: TokenMovementRejectionState): void {
    this.state = {
      ...this.state,
      lastMovementRejectionByTokenId: {
        ...this.state.lastMovementRejectionByTokenId,
        [rejection.tokenId]: rejection
      }
    };
    this.listeners.forEach((l) => l());
  }

  clearTokenMovementRejection(tokenId: string): void {
    if (!this.state.lastMovementRejectionByTokenId[tokenId]) return;
    const next = { ...this.state.lastMovementRejectionByTokenId };
    delete next[tokenId];
    this.set({ lastMovementRejectionByTokenId: next });
  }

  startGridEdit(cal: GridCalibration, gw: number, gh: number): void {
    this.set({ isGridEditMode: true, isObstaclePaintMode: false, gridCalibrationDraft: cal, gridWidthDraft: gw, gridHeightDraft: gh, pendingGridCalibrationActionId: undefined, pendingObstaclePaintActionId: undefined, message: undefined });
  }

  updateGridCalibrationDraft(cal: GridCalibration): void { this.set({ gridCalibrationDraft: cal }); }

  cancelGridEdit(): void {
    this.set({ isGridEditMode: false, gridCalibrationDraft: undefined, gridWidthDraft: undefined, gridHeightDraft: undefined, pendingGridCalibrationActionId: undefined });
  }

  startObstaclePaint(): void {
    this.set({ isObstaclePaintMode: true, isGridEditMode: false, gridCalibrationDraft: undefined, gridWidthDraft: undefined, gridHeightDraft: undefined, pendingGridCalibrationActionId: undefined, pendingObstaclePaintActionId: undefined, pendingEdgePaintActionId: undefined, message: undefined });
  }

  cancelObstaclePaint(): void {
    this.set({ isObstaclePaintMode: false, pendingObstaclePaintActionId: undefined, pendingEdgePaintActionId: undefined });
  }

  markObstaclePaintPending(id: string): void { this.set({ pendingObstaclePaintActionId: id }); }
  markGridCalibrationPending(id: string): void { this.set({ pendingGridCalibrationActionId: id }); }
  markEdgePaintPending(id: string): void { this.set({ pendingEdgePaintActionId: id }); }

  private completePending(key: keyof BattleMapUIState, actionId?: string): boolean {
    if (!actionId || this.state[key] !== actionId) return false;
    this.set({ [key]: undefined } as Partial<BattleMapUIState>);
    return true;
  }

  completeGridCalibrationUpdate(id?: string): boolean {
    if (!id || this.state.pendingGridCalibrationActionId !== id) return false;
    this.set({ isGridEditMode: false, gridCalibrationDraft: undefined, gridWidthDraft: undefined, gridHeightDraft: undefined, pendingGridCalibrationActionId: undefined });
    return true;
  }

  completeObstaclePaintUpdate(id?: string): boolean { return this.completePending("pendingObstaclePaintActionId", id); }
  failGridCalibrationUpdate(id?: string): boolean { return this.completePending("pendingGridCalibrationActionId", id); }
  failObstaclePaintUpdate(id?: string): boolean { return this.completePending("pendingObstaclePaintActionId", id); }
  completeEdgePaintUpdate(id?: string): boolean { return this.completePending("pendingEdgePaintActionId", id); }
  failEdgePaintUpdate(id?: string): boolean { return this.completePending("pendingEdgePaintActionId", id); }

  activateTacticalPreview(sourceTokenId: string, actionType: "move" | "attack" | "spell"): void {
    this.state = { ...this.state, tacticalPreview: { ...this.state.tacticalPreview, active: true, sourceTokenId, actionType } };
    this.listeners.forEach((l) => l());
  }

  deactivateTacticalPreview(): void {
    this.set({
      tacticalPreview: { active: false, sourceTokenId: null, actionType: null, targetCell: null, targetEntityId: null, diagnostics: null, aoeCells: [], reachableCells: [] }
    });
  }

  setTacticalPreviewTarget(targetCell: Coordinate | null, targetEntityId: string | null): void {
    const prev = this.state.tacticalPreview;
    if (prev.targetCell?.x === targetCell?.x && prev.targetCell?.y === targetCell?.y && prev.targetEntityId === targetEntityId) return;
    this.state = { ...this.state, tacticalPreview: { ...prev, targetCell, targetEntityId } };
    this.listeners.forEach((l) => l());
  }

  setTacticalPreviewDiagnostics(d: TacticalDiagnostics | null): void {
    this.state = { ...this.state, tacticalPreview: { ...this.state.tacticalPreview, diagnostics: d } };
    this.listeners.forEach((l) => l());
  }

  setTacticalPreviewReachableCells(c: Coordinate[]): void {
    this.state = { ...this.state, tacticalPreview: { ...this.state.tacticalPreview, reachableCells: c } };
    this.listeners.forEach((l) => l());
  }

  setTacticalPreviewAoeCells(c: Coordinate[]): void {
    this.state = { ...this.state, tacticalPreview: { ...this.state.tacticalPreview, aoeCells: c } };
    this.listeners.forEach((l) => l());
  }

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }
}

export const battleMapStore = new BattleMapStore();
