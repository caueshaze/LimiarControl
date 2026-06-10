import type { Dispatch, MutableRefObject, SetStateAction } from "react";
import { Application, Container, Graphics, Sprite, Texture, type FederatedPointerEvent } from "pixi.js";
import type { BattleMapUIState } from "./battle-map-store";
import type { BattleMapCamera } from "./battle-map-camera";
import type { GridEditInteraction } from "./types";
import { battleMapStore } from "./battle-map-store";
import { C } from "./constants";
import { submitMovement } from "./use-movement-actions";
import { submitEdgeObstaclePaint, submitObstaclePaint } from "./use-obstacle-paint-actions";
import { submitElevationPaint } from "./use-elevation-paint-actions";
import { submitPlacement } from "./use-placement-actions";
import { getEdgeBrushPreset, getObstacleBrushPreset } from "./obstacle-presets";
import { HttpClient } from "../../services/http-client";
import { postEmbeddedCellHovered, postEmbeddedCellSelected, postEmbeddedTokenSelected } from "../../services/embedded-map-bridge";
import { buildFailureExplanation } from "../targeting/diagnostics-to-explanation";
import { drawCellFills, drawEdgeObstacles, drawCellElevationBadges, drawEditHandles, drawGrid, drawHUD, drawPreviewHint, drawReachAndAoe, drawSpellHighlightRings, drawTacticalTokenOverlay, drawTokenLayer, drawTwoPointCalibrationOverlay } from "./canvas-renderers";
import { canControlToken, canInteractWithToken, clamp, computePath, findTokenAtCell, getSelectionBlockedMessage, pixelToGrid } from "./utils";

type Snapshot = {
  selectedTokenId: string | null;
  encounter: any;
  currentActor: { actorId: string; actorType: "player" | "gm" };
  uiState: BattleMapUIState;
};

export type BattleMapPixiRefs = {
  appRef: MutableRefObject<Application | null>;
  worldContainerRef: MutableRefObject<Container | null>;
  bgSpriteRef: MutableRefObject<Sprite | null>;
  backgroundUrlRef: MutableRefObject<string | null>;
  reachAoeGfxRef: MutableRefObject<Graphics | null>;
  gridGfxRef: MutableRefObject<Graphics | null>;
  cellFillsGfxRef: MutableRefObject<Graphics | null>;
  edgeObstaclesGfxRef: MutableRefObject<Graphics | null>;
  tokenContainerRef: MutableRefObject<Container | null>;
  spellHighlightContainerRef: MutableRefObject<Container | null>;
  tacticalOverlayContainerRef: MutableRefObject<Container | null>;
  editHandlesContainerRef: MutableRefObject<Container | null>;
  hudContainerRef: MutableRefObject<Container | null>;
};

export function attachPixiLayers(app: Application, refs: BattleMapPixiRefs): void {
  // World container holds every layer that should pan/zoom with the camera.
  // It is drawn at screen size (base scale 1) so renderers stay unchanged.
  const worldContainer = new Container();
  worldContainer.eventMode = "none";
  app.stage.addChild(worldContainer);
  refs.worldContainerRef.current = worldContainer;

  const bgSprite = Sprite.from(Texture.WHITE);
  bgSprite.tint = C.bg;
  bgSprite.width = app.screen.width;
  bgSprite.height = app.screen.height;
  worldContainer.addChild(bgSprite);
  refs.bgSpriteRef.current = bgSprite;

  const reachAoeGfx = new Graphics();
  const cellFillsGfx = new Graphics();
  const gridGfx = new Graphics();
  const edgeObstaclesGfx = new Graphics();
  const tokenContainer = new Container();
  const spellHighlightContainer = new Container();
  const tacticalOverlayContainer = new Container();
  const editHandlesContainer = new Container();
  const hudContainer = new Container();

  spellHighlightContainer.eventMode = "none";
  tacticalOverlayContainer.eventMode = "none";
  editHandlesContainer.eventMode = "passive";
  hudContainer.eventMode = "none";

  // World layers (pan/zoom with the camera).
  worldContainer.addChild(reachAoeGfx);
  worldContainer.addChild(cellFillsGfx);
  worldContainer.addChild(gridGfx);
  worldContainer.addChild(edgeObstaclesGfx);
  worldContainer.addChild(tokenContainer);
  worldContainer.addChild(spellHighlightContainer);
  worldContainer.addChild(tacticalOverlayContainer);
  // Screen-fixed layers (never scale): grid-edit handles + HUD.
  app.stage.addChild(editHandlesContainer);
  app.stage.addChild(hudContainer);

  refs.reachAoeGfxRef.current = reachAoeGfx;
  refs.cellFillsGfxRef.current = cellFillsGfx;
  refs.gridGfxRef.current = gridGfx;
  refs.edgeObstaclesGfxRef.current = edgeObstaclesGfx;
  refs.tokenContainerRef.current = tokenContainer;
  refs.spellHighlightContainerRef.current = spellHighlightContainer;
  refs.tacticalOverlayContainerRef.current = tacticalOverlayContainer;
  refs.editHandlesContainerRef.current = editHandlesContainer;
  refs.hudContainerRef.current = hudContainer;
}

/** Min screen-pixel travel before a single-pointer drag is treated as a pan (not a tap). */
const PAN_THRESHOLD = 8;
const WHEEL_ZOOM_STEP = 1.12;

export function bindPixiStageEvents(
  app: Application,
  cbRef: MutableRefObject<Snapshot>,
  previewTimerRef: MutableRefObject<ReturnType<typeof setTimeout> | null>,
  setSelectedTokenId: Dispatch<SetStateAction<string | null>>,
  setGridEditInteraction: Dispatch<SetStateAction<GridEditInteraction | null>>,
  cameraRef: MutableRefObject<BattleMapCamera | null>,
): void {
  app.stage.eventMode = "static";
  app.stage.hitArea = app.screen;

  // Execute a tap/click action. (worldX, worldY) are world-space coordinates
  // (already un-zoomed); they equal screen coords when the camera is locked.
  function handleTap(worldX: number, worldY: number): void {
    const { encounter, currentActor, uiState, selectedTokenId } = cbRef.current;
    if (!encounter) return;
    if (uiState.isGridEditMode) {
      if (currentActor.actorType !== "gm") return;
      if (!uiState.isTwoPointCalibrationMode) return;
      const sourceWidthPx = uiState.mapImageNaturalWidthPx || uiState.mapFrameWidthPx;
      const sourceHeightPx = uiState.mapImageNaturalHeightPx || uiState.mapFrameHeightPx;
      if (sourceWidthPx <= 0 || sourceHeightPx <= 0) {
        battleMapStore.setMessage("Nao foi possivel ler o tamanho da imagem para calibrar com 2 pontos.");
        return;
      }
      battleMapStore.captureTwoPointGridCalibrationPoint({
        x: clamp((worldX / app.screen.width) * sourceWidthPx, 0, sourceWidthPx),
        y: clamp((worldY / app.screen.height) * sourceHeightPx, 0, sourceHeightPx),
      });
      return;
    }
    const calibration = uiState.gridCalibrationDraft ?? encounter.battleMap.gridCalibration;
    const gridWidth = uiState.gridWidthDraft ?? encounter.battleMap.gridWidth;
    const gridHeight = uiState.gridHeightDraft ?? encounter.battleMap.gridHeight;
    const coord = pixelToGrid(worldX, worldY, calibration, gridWidth, gridHeight, app.screen.width, app.screen.height);
    if (!coord) return;
    if (uiState.placingTokenId) {
      submitPlacement(encounter.sessionId, uiState.placingTokenId, coord);
      battleMapStore.setPlacingTokenId(null);
      return;
    }
    if (uiState.isObstaclePaintMode) {
      if (currentActor.actorType === "gm" && !uiState.pendingObstaclePaintActionId && !uiState.pendingEdgePaintActionId) {
        if (uiState.obstaclePaintTarget === "edge") submitEdgeObstaclePaint(encounter.sessionId, coord, uiState.edgeDirection);
        else submitObstaclePaint(encounter.sessionId, coord);
      }
      return;
    }
    if (uiState.isElevationPaintMode) {
      if (currentActor.actorType === "gm" && !uiState.pendingElevationPaintActionId) {
        submitElevationPaint(encounter.sessionId, coord);
      }
      return;
    }
    const tokenAtCell = findTokenAtCell(encounter.tokens, coord);
    if (uiState.embeddedCombatPhase === "placement") {
      if (tokenAtCell) {
        if (!canControlToken(currentActor, tokenAtCell)) {
          battleMapStore.setMessage(getSelectionBlockedMessage(currentActor, tokenAtCell, encounter.combatState));
          setSelectedTokenId(null);
          return;
        }
        battleMapStore.setMessage(undefined);
        setSelectedTokenId((prev) => (prev === tokenAtCell.id ? null : tokenAtCell.id));
        return;
      }
      const selectedToken = encounter.tokens.find((token: any) => token.id === selectedTokenId) ?? null;
      if (selectedToken && canControlToken(currentActor, selectedToken)) {
        submitPlacement(encounter.sessionId, selectedToken.id, coord);
        setSelectedTokenId(selectedToken.id);
      }
      return;
    }
    if (uiState.embeddedSelectionMode !== "none") {
      battleMapStore.setMessage(undefined);
      if (uiState.embeddedSelectionMode === "select-token") {
        if (tokenAtCell) {
          setSelectedTokenId(tokenAtCell.id);
          postEmbeddedTokenSelected(encounter.sessionId, tokenAtCell);
        }
        return;
      }
      setSelectedTokenId(null);
      battleMapStore.setEmbeddedSelectedCell(coord);
      postEmbeddedCellSelected(encounter.sessionId, coord, tokenAtCell ?? null);
      return;
    }
    if (tokenAtCell) {
      if (!canInteractWithToken(currentActor, tokenAtCell, encounter.combatState)) {
        battleMapStore.setMovementPreview([]);
        battleMapStore.setMessage(getSelectionBlockedMessage(currentActor, tokenAtCell, encounter.combatState));
        setSelectedTokenId(null);
        return;
      }
      battleMapStore.setMessage(undefined);
      setSelectedTokenId((prev) => (prev === tokenAtCell.id ? null : tokenAtCell.id));
      return;
    }
    const selectedToken = encounter.tokens.find((token: any) => token.id === selectedTokenId) ?? null;
    if (selectedToken) {
      const path = computePath(selectedToken.position, coord);
      if (path.length > 0) submitMovement(encounter.sessionId, selectedToken.id, path);
      setSelectedTokenId(selectedToken.id);
    }
  }

  // Hover / tactical-preview handling. (worldX, worldY) are world-space.
  function handleHover(worldX: number, worldY: number): void {
    const { encounter, uiState } = cbRef.current;
    if (!encounter || uiState.isGridEditMode || uiState.isObstaclePaintMode) return;
    const calibration = uiState.gridCalibrationDraft ?? encounter.battleMap.gridCalibration;
    const gridWidth = uiState.gridWidthDraft ?? encounter.battleMap.gridWidth;
    const gridHeight = uiState.gridHeightDraft ?? encounter.battleMap.gridHeight;
    const coord = pixelToGrid(worldX, worldY, calibration, gridWidth, gridHeight, app.screen.width, app.screen.height);
    if (uiState.embeddedSelectionMode === "select-cell") {
      if (!coord) postEmbeddedCellHovered(encounter.sessionId, null, null);
      else {
        const hoveredToken = findTokenAtCell(encounter.tokens, coord);
        postEmbeddedCellHovered(encounter.sessionId, coord, hoveredToken ?? null);
      }
    }
    if (!uiState.tacticalPreview.active || !coord) return;
    const tokenAtCell = findTokenAtCell(encounter.tokens, coord);
    battleMapStore.setTacticalPreviewTarget(coord, tokenAtCell?.combatantId ?? null);
    if (previewTimerRef.current) clearTimeout(previewTimerRef.current);
    if (tokenAtCell && uiState.tacticalPreview.actionType !== "move" && uiState.tacticalPreview.sourceTokenId) {
      const sourceToken = encounter.tokens.find((token: any) => token.id === uiState.tacticalPreview.sourceTokenId);
      if (sourceToken) {
        previewTimerRef.current = setTimeout(() => {
          void new HttpClient()
            .fetchCombatPreview(encounter.sessionId, {
              source_ref_id: sourceToken.combatantId ?? sourceToken.id,
              action_type: uiState.tacticalPreview.actionType ?? "attack",
              target_ref_id: tokenAtCell.combatantId ?? tokenAtCell.id,
              source_position: sourceToken.position,
              target_position: tokenAtCell.position,
              reach_cells: 1,
            })
            .then((response) => {
              battleMapStore.setTacticalPreviewDiagnostics(response.diagnostics);
              battleMapStore.setTacticalPreviewAoeCells(response.aoeCells);
            })
            .catch(() => undefined);
        }, 80);
      }
    } else if (!tokenAtCell) {
      battleMapStore.setTacticalPreviewDiagnostics(null);
      battleMapStore.setTacticalPreviewAoeCells([]);
    }
  }

  // ── Gesture state ───────────────────────────────────────────────────────────
  const pointers = new Map<number, { x: number; y: number }>();
  let downPointer: { id: number; startX: number; startY: number; lastX: number; lastY: number } | null = null;
  let panning = false;
  let pinchPrevDist: number | null = null;

  const toWorld = (gx: number, gy: number): { x: number; y: number } =>
    cameraRef.current ? cameraRef.current.screenToWorld(gx, gy) : { x: gx, y: gy };

  app.stage.on("pointerdown", (event: FederatedPointerEvent) => {
    const camera = cameraRef.current;
    pointers.set(event.pointerId, { x: event.global.x, y: event.global.y });

    // Edit modes lock the camera → act immediately, as the legacy renderer did.
    if (!camera || camera.isLocked()) {
      const w = toWorld(event.global.x, event.global.y);
      handleTap(w.x, w.y);
      return;
    }

    if (pointers.size >= 2) {
      const pts = [...pointers.values()];
      pinchPrevDist = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
      downPointer = null;
      panning = false;
      return;
    }

    // Single pointer: defer the tap to pointerup so a drag can become a pan.
    downPointer = { id: event.pointerId, startX: event.global.x, startY: event.global.y, lastX: event.global.x, lastY: event.global.y };
    panning = false;
  });

  app.stage.on("pointermove", (event: FederatedPointerEvent) => {
    const camera = cameraRef.current;
    if (pointers.has(event.pointerId)) pointers.set(event.pointerId, { x: event.global.x, y: event.global.y });

    // Two-finger pinch zoom around the midpoint.
    if (camera && !camera.isLocked() && pointers.size >= 2 && pinchPrevDist != null) {
      const pts = [...pointers.values()];
      const dist = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
      if (dist > 0 && pinchPrevDist > 0) {
        camera.zoomAt((pts[0].x + pts[1].x) / 2, (pts[0].y + pts[1].y) / 2, dist / pinchPrevDist);
      }
      pinchPrevDist = dist;
      return;
    }

    // Single-pointer drag: pan once past the threshold.
    if (camera && !camera.isLocked() && downPointer && event.pointerId === downPointer.id) {
      if (!panning) {
        const moved = Math.hypot(event.global.x - downPointer.startX, event.global.y - downPointer.startY);
        if (moved > PAN_THRESHOLD) panning = true;
      }
      if (panning) {
        camera.panBy(event.global.x - downPointer.lastX, event.global.y - downPointer.lastY);
        downPointer.lastX = event.global.x;
        downPointer.lastY = event.global.y;
        return;
      }
      downPointer.lastX = event.global.x;
      downPointer.lastY = event.global.y;
    }

    const w = toWorld(event.global.x, event.global.y);
    handleHover(w.x, w.y);
  });

  const endPointer = (event: FederatedPointerEvent): void => {
    const camera = cameraRef.current;
    const wasTapCandidate = downPointer != null && event.pointerId === downPointer.id && !panning;
    pointers.delete(event.pointerId);
    if (pointers.size < 2) pinchPrevDist = null;

    // A clean single tap (no pan, no second finger) fires the tap action.
    if (wasTapCandidate && pointers.size === 0 && (!camera || !camera.isLocked())) {
      const w = toWorld(event.global.x, event.global.y);
      handleTap(w.x, w.y);
    }
    if (pointers.size === 0) {
      downPointer = null;
      panning = false;
    }
  };
  app.stage.on("pointerup", endPointer);
  app.stage.on("pointerupoutside", endPointer);

  // Wheel zoom around the cursor (desktop).
  app.canvas.addEventListener(
    "wheel",
    (event: WheelEvent) => {
      const camera = cameraRef.current;
      if (!camera || camera.isLocked()) return;
      event.preventDefault();
      const rect = app.canvas.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) return;
      const gx = (event.clientX - rect.left) * (app.screen.width / rect.width);
      const gy = (event.clientY - rect.top) * (app.screen.height / rect.height);
      camera.zoomAt(gx, gy, event.deltaY < 0 ? WHEEL_ZOOM_STEP : 1 / WHEEL_ZOOM_STEP);
    },
    { passive: false },
  );

  app.renderer.on("resize", () => {
    if (app.stage.hitArea) app.stage.hitArea = app.screen;
    cameraRef.current?.refresh();
  });
}

export function buildDrawFunction(
  refs: BattleMapPixiRefs,
  cbRef: MutableRefObject<Snapshot>,
  setGridEditInteraction: Dispatch<SetStateAction<GridEditInteraction | null>>,
): () => void {
  return () => {
    const { encounter, uiState, selectedTokenId } = cbRef.current;
    const app = refs.appRef.current;
    if (!encounter || !app) return;
    const calibration = uiState.gridCalibrationDraft ?? encounter.battleMap.gridCalibration;
    const gridWidth = uiState.gridWidthDraft ?? encounter.battleMap.gridWidth;
    const gridHeight = uiState.gridHeightDraft ?? encounter.battleMap.gridHeight;
    const { screen } = app;

    if (refs.gridGfxRef.current) drawGrid(refs.gridGfxRef.current, calibration, gridWidth, gridHeight, screen.width, screen.height, uiState.isGridEditMode);
    if (refs.reachAoeGfxRef.current) {
      refs.reachAoeGfxRef.current.clear();
      drawReachAndAoe(refs.reachAoeGfxRef.current, calibration, gridWidth, gridHeight, screen.width, screen.height, uiState.tacticalPreview.reachableCells, uiState.tacticalPreview.aoeCells);
    }
    if (refs.cellFillsGfxRef.current) {
      drawCellFills(refs.cellFillsGfxRef.current, calibration, gridWidth, gridHeight, screen.width, screen.height, encounter.obstacles, uiState.movementPreview, uiState.targetingPreview, uiState.embeddedPreview, [...(encounter.activeAreaEffects ?? []), ...uiState.embeddedActiveAreaEffects], [...(encounter.spellAnchors ?? []), ...uiState.embeddedSpellAnchors], uiState.embeddedSelectedCell ?? null);
    }
    if (refs.edgeObstaclesGfxRef.current) drawEdgeObstacles(refs.edgeObstaclesGfxRef.current, calibration, gridWidth, gridHeight, screen.width, screen.height, encounter.edgeObstacles ?? []);
    if (refs.edgeObstaclesGfxRef.current) drawCellElevationBadges(refs.edgeObstaclesGfxRef.current, calibration, gridWidth, gridHeight, screen.width, screen.height, encounter.cellElevations ?? []);
    if (refs.tokenContainerRef.current) drawTokenLayer(refs.tokenContainerRef.current, encounter.tokens, calibration, gridWidth, gridHeight, screen.width, screen.height, selectedTokenId, uiState.embeddedSelectedTargetRefId ?? null, encounter.combatState.activeCombatantId, encounter.sessionId);
    if (refs.spellHighlightContainerRef.current) drawSpellHighlightRings(refs.spellHighlightContainerRef.current, encounter.tokens, calibration, gridWidth, gridHeight, screen.width, screen.height, uiState.embeddedSpellHighlights);
    if (refs.tacticalOverlayContainerRef.current) drawTacticalTokenOverlay(refs.tacticalOverlayContainerRef.current, encounter.tokens, calibration, gridWidth, gridHeight, screen.width, screen.height, uiState.tacticalPreview);
    if (refs.tacticalOverlayContainerRef.current && uiState.isGridEditMode && uiState.isTwoPointCalibrationMode) {
      drawTwoPointCalibrationOverlay(
        refs.tacticalOverlayContainerRef.current,
        uiState.twoPointCalibrationFirstPoint,
        uiState.twoPointCalibrationSecondPoint,
        uiState.mapImageNaturalWidthPx || uiState.mapFrameWidthPx,
        uiState.mapImageNaturalHeightPx || uiState.mapFrameHeightPx,
        screen.width,
        screen.height
      );
    }
    if (refs.editHandlesContainerRef.current) {
      drawEditHandles(refs.editHandlesContainerRef.current, calibration, screen.width, screen.height, uiState.isGridEditMode && !uiState.isTwoPointCalibrationMode, Boolean(uiState.pendingGridCalibrationActionId), (mode, clientX, clientY) => {
        if (!uiState.isTwoPointCalibrationMode) {
          setGridEditInteraction({ mode, startClientX: clientX, startClientY: clientY, startCalibration: calibration });
        }
      });
    }
    if (refs.hudContainerRef.current) {
      const selectedToken = encounter.tokens.find((token: any) => token.id === selectedTokenId) ?? null;
      const activeBrushPresetLabel = uiState.isObstaclePaintMode ? (uiState.obstaclePaintTarget === "edge" ? getEdgeBrushPreset(uiState.edgeBrushPresetId).label : getObstacleBrushPreset(uiState.obstacleBrushPresetId).label) : undefined;
      const twoPointStatus = !uiState.isTwoPointCalibrationMode
        ? undefined
        : !uiState.twoPointCalibrationFirstPoint
          ? "2 pontos: clique no primeiro cruzamento"
          : !uiState.twoPointCalibrationSecondPoint
            ? "2 pontos: clique no segundo cruzamento"
            : "2 pontos: informe as celulas entre os pontos · Esc cancela";
      drawHUD(refs.hudContainerRef.current, encounter.battleMap.name, gridWidth, gridHeight, selectedToken, uiState.isObstaclePaintMode, uiState.obstacleBrushRadius, uiState.isGridEditMode, screen.width, screen.height, activeBrushPresetLabel, uiState.obstaclePaintTarget, uiState.edgeDirection, twoPointStatus);
      drawPreviewHint(refs.hudContainerRef.current, screen.width, screen.height, uiState.tacticalPreview.diagnostics ? buildFailureExplanation(uiState.tacticalPreview.diagnostics) : null);
    }
  };
}

export function resetPixiRefs(refs: BattleMapPixiRefs): void {
  refs.appRef.current = null;
  refs.worldContainerRef.current = null;
  refs.bgSpriteRef.current = null;
  refs.reachAoeGfxRef.current = null;
  refs.gridGfxRef.current = null;
  refs.cellFillsGfxRef.current = null;
  refs.edgeObstaclesGfxRef.current = null;
  refs.tokenContainerRef.current = null;
  refs.spellHighlightContainerRef.current = null;
  refs.tacticalOverlayContainerRef.current = null;
  refs.editHandlesContainerRef.current = null;
  refs.hudContainerRef.current = null;
}
