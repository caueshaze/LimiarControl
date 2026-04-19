/**
 * BattleMapCanvas — Renderer PixiJS (Fase 2)
 *
 * Substitui BattleMapGrid (CSS Grid) por renderização GPU-acelerada.
 * Ative via URL param: ?renderer=pixi
 *
 * Camadas (ordem de desenho, baixo → alto):
 *   bgSprite           — imagem do mapa
 *   cellFillsGfx       — fills de célula (obstáculos, preview de movimento/targeting)
 *   gridGfx            — linhas do grid (1 draw call)
 *   tokenContainer     — marcadores de token
 *   editHandlesContainer — handles de drag (modo edição)
 *   hudContainer       — labels e badges de status
 */
import React, {
  useEffect,
  useRef,
  useState,
  useSyncExternalStore
} from "react";
import {
  Application,
  Container,
  type FederatedPointerEvent,
  Graphics,
  Sprite,
  Text,
  TextStyle,
  Texture
} from "pixi.js";
import type {
  CombatState,
  Coordinate,
  GridCalibration,
  Obstacle,
  Token
} from "@limiarmap/shared-contracts";
import { findReachableCells } from "@limiarmap/tactical-engine";
import { useEncounterSnapshot } from "../../services/session-store";
import { useCurrentActor } from "../../services/centrifugo-client";
import {
  formatMovementSpeedCellsAsMeters,
  formatPathCostUnitsAsMeters
} from "../../services/movement-metrics";
import {
  postEmbeddedCellHovered,
  postEmbeddedCellSelected,
  postEmbeddedTokenSelected
} from "../../services/embedded-map-bridge";
import { battleMapStore } from "./battle-map-store";
import { submitMovement } from "./use-movement-actions";
import {
  submitObstaclePaint,
  submitEdgeObstaclePaint
} from "./use-obstacle-paint-actions";
import { getObstacleBrushPreset, getEdgeBrushPreset } from "./obstacle-presets";

import { DEFAULT_MAP_IMAGE_URL, C } from "./constants";
import type {
  GridEditInteraction,
  GridEditInteractionMode,
  ObstacleCellState
} from "./types";
import {
  clamp,
  coordKey,
  pixelToGrid,
  buildObstacleCellMap,
  canControlToken,
  canInteractWithToken,
  getSelectionBlockedMessage,
  computePath,
  applyGridCalibrationInteraction,
  getTokenBadgeLabel
} from "./utils";
import {
  drawGrid,
  drawCellFills,
  drawEdgeObstacles,
  drawTokenLayer,
  drawEditHandles,
  drawHUD,
  drawReachAndAoe,
  drawTacticalTokenOverlay,
  drawPreviewHint
} from "./canvas-renderers";
import { HttpClient } from "../../services/http-client";
import { buildFailureExplanation } from "../targeting/diagnostics-to-explanation";
import { getConditionIndicators } from "../conditions/condition-indicators";

export function BattleMapCanvas(): React.JSX.Element {
  const [selectedTokenId, setSelectedTokenId] = useState<string | null>(null);
  const [imageAspectRatio, setImageAspectRatio] = useState(16 / 9);
  const [gridEditInteraction, setGridEditInteraction] =
    useState<GridEditInteraction | null>(null);
  const [isRendererReady, setIsRendererReady] = useState(false);

  const encounter = useEncounterSnapshot();
  const currentActor = useCurrentActor();
  const uiState = useSyncExternalStore(
    (cb) => battleMapStore.subscribe(cb),
    () => battleMapStore.getState(),
    () => battleMapStore.getState()
  );
  const selectedToken =
    encounter?.tokens.find((token) => token.id === selectedTokenId) ?? null;
  const selectedTokenMovementRejection =
    selectedTokenId != null
      ? (uiState.lastMovementRejectionByTokenId[selectedTokenId] ?? null)
      : null;

  // DOM ref for the canvas container
  const containerRef = useRef<HTMLDivElement>(null);

  // PixiJS layer refs
  const appRef = useRef<Application | null>(null);
  const bgSpriteRef = useRef<Sprite | null>(null);
  const backgroundUrlRef = useRef<string | null>(null);
  const reachAoeGfxRef = useRef<Graphics | null>(null);
  const gridGfxRef = useRef<Graphics | null>(null);
  const cellFillsGfxRef = useRef<Graphics | null>(null);
  const edgeObstaclesGfxRef = useRef<Graphics | null>(null);
  const tokenContainerRef = useRef<Container | null>(null);
  const tacticalOverlayContainerRef = useRef<Container | null>(null);
  const editHandlesContainerRef = useRef<Container | null>(null);
  const hudContainerRef = useRef<Container | null>(null);

  // Debounce timer for preview API calls
  const previewTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Mutable snapshot of current state for use inside PixiJS callbacks (avoids stale closures)
  const cbRef = useRef({ selectedTokenId, encounter, currentActor, uiState });
  useEffect(() => {
    cbRef.current = { selectedTokenId, encounter, currentActor, uiState };
  });

  // Draw function stored in a ref so it can be called from both effects and the init async block
  const drawRef = useRef<(() => void) | null>(null);

  // ─── PixiJS Initialization (runs once on mount) ──────────────────────────

  useEffect(() => {
    let cancelled = false;

    async function init(): Promise<void> {
      if (!containerRef.current) return;

      const app = new Application();
      try {
        await app.init({
          resizeTo: containerRef.current,
          background: C.bg,
          preference: "webgl",
          antialias: true,
          autoDensity: true,
          resolution: window.devicePixelRatio ?? 1
        });
      } catch (error) {
        if (!cancelled) {
          console.error(
            "[map-web] failed to initialize Pixi application",
            error
          );
          battleMapStore.setMessage(
            "Nao foi possivel inicializar o renderer tatico do mapa."
          );
        }
        app.destroy(true);
        return;
      }

      if (cancelled) {
        app.destroy(true);
        return;
      }

      appRef.current = app;
      containerRef.current.appendChild(app.canvas);

      // ─── Load background image ──────────────────────────────────────────

      const bgSprite = Sprite.from(Texture.WHITE);
      bgSprite.width = app.screen.width;
      bgSprite.height = app.screen.height;
      app.stage.addChild(bgSprite);
      bgSpriteRef.current = bgSprite;
      setIsRendererReady(true);

      // ─── Create layers ──────────────────────────────────────────────────
      // Layer order (bottom → top):
      //   bgSprite → reachAoeGfx → cellFillsGfx → gridGfx →
      //   edgeObstaclesGfx → tokenContainer → tacticalOverlayContainer →
      //   editHandlesContainer → hudContainer

      const reachAoeGfx = new Graphics();
      app.stage.addChild(reachAoeGfx);
      reachAoeGfxRef.current = reachAoeGfx;

      const cellFillsGfx = new Graphics();
      app.stage.addChild(cellFillsGfx);
      cellFillsGfxRef.current = cellFillsGfx;

      const gridGfx = new Graphics();
      app.stage.addChild(gridGfx);
      gridGfxRef.current = gridGfx;

      const edgeObstaclesGfx = new Graphics();
      app.stage.addChild(edgeObstaclesGfx);
      edgeObstaclesGfxRef.current = edgeObstaclesGfx;

      const tokenContainer = new Container();
      app.stage.addChild(tokenContainer);
      tokenContainerRef.current = tokenContainer;

      const tacticalOverlayContainer = new Container();
      tacticalOverlayContainer.eventMode = "none";
      app.stage.addChild(tacticalOverlayContainer);
      tacticalOverlayContainerRef.current = tacticalOverlayContainer;

      const editHandlesContainer = new Container();
      editHandlesContainer.eventMode = "passive";
      app.stage.addChild(editHandlesContainer);
      editHandlesContainerRef.current = editHandlesContainer;

      const hudContainer = new Container();
      hudContainer.eventMode = "none";
      app.stage.addChild(hudContainer);
      hudContainerRef.current = hudContainer;

      // ─── Stage pointer events (movement + obstacle paint) ───────────────

      app.stage.eventMode = "static";
      app.stage.hitArea = app.screen;
      app.stage.on("pointerdown", (e: FederatedPointerEvent) => {
        const {
          encounter: enc,
          currentActor: actor,
          uiState: ui,
          selectedTokenId: selId
        } = cbRef.current;
        if (!enc) return;
        if (ui.isGridEditMode) return; // edit handles manage their own events

        const cal = ui.gridCalibrationDraft ?? enc.battleMap.gridCalibration;
        const gridW = ui.gridWidthDraft ?? enc.battleMap.gridWidth;
        const gridH = ui.gridHeightDraft ?? enc.battleMap.gridHeight;

        const coord = pixelToGrid(
          e.global.x,
          e.global.y,
          cal,
          gridW,
          gridH,
          app.screen.width,
          app.screen.height
        );
        if (!coord) return;

        // Obstacle paint mode
        if (ui.isObstaclePaintMode) {
          if (
            actor.actorType === "gm" &&
            !ui.pendingObstaclePaintActionId &&
            !ui.pendingEdgePaintActionId
          ) {
            if (ui.obstaclePaintTarget === "edge") {
              submitEdgeObstaclePaint(enc.sessionId, coord, ui.edgeDirection);
            } else {
              submitObstaclePaint(enc.sessionId, coord);
            }
          }
          return;
        }

        const tokenAtCell = enc.tokens.find(
          (t) => t.position.x === coord.x && t.position.y === coord.y
        );

        if (ui.embeddedSelectionMode !== "none") {
          battleMapStore.setMessage(undefined);
          if (ui.embeddedSelectionMode === "select-token") {
            if (tokenAtCell) {
              setSelectedTokenId(tokenAtCell.id);
              postEmbeddedTokenSelected(enc.sessionId, tokenAtCell);
            }
            return;
          }

          setSelectedTokenId(null);
          battleMapStore.setEmbeddedSelectedCell(coord);
          postEmbeddedCellSelected(enc.sessionId, coord, tokenAtCell ?? null);
          return;
        }

        if (tokenAtCell) {
          if (!canInteractWithToken(actor, tokenAtCell, enc.combatState)) {
            battleMapStore.setMovementPreview([]);
            battleMapStore.setMessage(
              getSelectionBlockedMessage(actor, tokenAtCell, enc.combatState)
            );
            setSelectedTokenId(null);
            return;
          }
          battleMapStore.setMessage(undefined);
          setSelectedTokenId((prev) =>
            prev === tokenAtCell.id ? null : tokenAtCell.id
          );
          return;
        }

        const selectedToken = enc.tokens.find((t) => t.id === selId) ?? null;
        if (selectedToken) {
          const path = computePath(selectedToken.position, coord);
          if (path.length > 0)
            submitMovement(enc.sessionId, selectedToken.id, path);
          setSelectedTokenId(selectedToken.id);
        }
      });

      // ─── Hover handler (tactical preview) ──────────────────────────────

      app.stage.on("pointermove", (e: FederatedPointerEvent) => {
        const { encounter: enc, uiState: ui } = cbRef.current;
        if (!enc || ui.isGridEditMode || ui.isObstaclePaintMode) return;

        const cal = ui.gridCalibrationDraft ?? enc.battleMap.gridCalibration;
        const gridW = ui.gridWidthDraft ?? enc.battleMap.gridWidth;
        const gridH = ui.gridHeightDraft ?? enc.battleMap.gridHeight;

        const coord = pixelToGrid(
          e.global.x, e.global.y, cal, gridW, gridH,
          app.screen.width, app.screen.height
        );

        if (ui.embeddedSelectionMode === "select-cell") {
          if (!coord) {
            postEmbeddedCellHovered(enc.sessionId, null, null);
          } else {
            const hoveredToken = enc.tokens.find(
              (t) => t.position.x === coord.x && t.position.y === coord.y
            );
            postEmbeddedCellHovered(enc.sessionId, coord, hoveredToken ?? null);
          }
        }

        if (!ui.tacticalPreview.active) return;
        if (!coord) return;

        const tokenAtCell = enc.tokens.find(
          (t) => t.position.x === coord.x && t.position.y === coord.y
        );
        const entityId = tokenAtCell?.combatantId ?? null;

        battleMapStore.setTacticalPreviewTarget(coord, entityId);

        // Debounced preview API call (attack/spell context only)
        if (previewTimerRef.current) clearTimeout(previewTimerRef.current);
        if (
          tokenAtCell &&
          ui.tacticalPreview.actionType !== "move" &&
          ui.tacticalPreview.sourceTokenId
        ) {
          const sourceToken = enc.tokens.find(
            (t) => t.id === ui.tacticalPreview.sourceTokenId
          );
          const targetToken = tokenAtCell;
          if (sourceToken) {
            previewTimerRef.current = setTimeout(() => {
              void new HttpClient()
                .fetchCombatPreview(enc.sessionId, {
                  source_ref_id: sourceToken.combatantId ?? sourceToken.id,
                  action_type: ui.tacticalPreview.actionType ?? "attack",
                  target_ref_id: targetToken.combatantId ?? targetToken.id,
                  source_position: sourceToken.position,
                  target_position: targetToken.position,
                  reach_cells: 1
                  // aoe_shape / aoe_size_cells are omitted here — they will
                  // be populated once spell-selection context is wired into
                  // the preview state (future feature).  When present, the
                  // backend returns aoeCells from the same LimiarMap spatial
                  // engine used for the final cast.
                })
                .then((res) => {
                  battleMapStore.setTacticalPreviewDiagnostics(res.diagnostics);
                  battleMapStore.setTacticalPreviewAoeCells(res.aoeCells);
                })
                .catch(() => {
                  // Preview errors are silent — don't disrupt UX
                });
            }, 80);
          }
        } else if (!tokenAtCell) {
          // Moved off a token — clear diagnostics and AoE cells, keep cell position
          battleMapStore.setTacticalPreviewDiagnostics(null);
          battleMapStore.setTacticalPreviewAoeCells([]);
        }
      });

      // ─── Resize handler ─────────────────────────────────────────────────

      app.renderer.on("resize", () => {
        if (bgSpriteRef.current) {
          bgSpriteRef.current.width = app.screen.width;
          bgSpriteRef.current.height = app.screen.height;
        }
        app.stage.hitArea = app.screen;
        drawRef.current?.();
      });

      // ─── Draw function ──────────────────────────────────────────────────

      drawRef.current = () => {
        const {
          encounter: enc,
          uiState: ui,
          selectedTokenId: selId
        } = cbRef.current;
        if (!enc || !appRef.current) return;

        const { screen } = appRef.current;
        const cal = ui.gridCalibrationDraft ?? enc.battleMap.gridCalibration;
        const gridW = ui.gridWidthDraft ?? enc.battleMap.gridWidth;
        const gridH = ui.gridHeightDraft ?? enc.battleMap.gridHeight;

        if (gridGfxRef.current) {
          drawGrid(
            gridGfxRef.current,
            cal,
            gridW,
            gridH,
            screen.width,
            screen.height,
            ui.isGridEditMode
          );
        }

        if (reachAoeGfxRef.current) {
          reachAoeGfxRef.current.clear();
          drawReachAndAoe(
            reachAoeGfxRef.current,
            cal,
            gridW,
            gridH,
            screen.width,
            screen.height,
            ui.tacticalPreview.reachableCells,
            ui.tacticalPreview.aoeCells
          );
        }

        if (cellFillsGfxRef.current) {
          drawCellFills(
            cellFillsGfxRef.current,
            cal,
            gridW,
            gridH,
            screen.width,
            screen.height,
            enc.obstacles,
            ui.movementPreview,
            ui.targetingPreview,
            ui.embeddedPreview,
            ui.embeddedSelectedCell ?? null
          );
        }

        if (edgeObstaclesGfxRef.current) {
          drawEdgeObstacles(
            edgeObstaclesGfxRef.current,
            cal,
            gridW,
            gridH,
            screen.width,
            screen.height,
            enc.edgeObstacles ?? []
          );
        }

        if (tokenContainerRef.current) {
          drawTokenLayer(
            tokenContainerRef.current,
            enc.tokens,
            cal,
            gridW,
            gridH,
            screen.width,
            screen.height,
            selId,
            ui.embeddedSelectedTargetRefId ?? null,
            enc.combatState.activeCombatantId
          );
        }

        if (tacticalOverlayContainerRef.current) {
          drawTacticalTokenOverlay(
            tacticalOverlayContainerRef.current,
            enc.tokens,
            cal,
            gridW,
            gridH,
            screen.width,
            screen.height,
            ui.tacticalPreview
          );
        }

        if (editHandlesContainerRef.current) {
          drawEditHandles(
            editHandlesContainerRef.current,
            cal,
            screen.width,
            screen.height,
            ui.isGridEditMode,
            Boolean(ui.pendingGridCalibrationActionId),
            (mode, clientX, clientY) => {
              setGridEditInteraction({
                mode,
                startClientX: clientX,
                startClientY: clientY,
                startCalibration: cal
              });
            }
          );
        }

        if (hudContainerRef.current) {
          const selectedToken = enc.tokens.find((t) => t.id === selId) ?? null;
          const activeBrushPresetLabel = ui.isObstaclePaintMode
            ? ui.obstaclePaintTarget === "edge"
              ? getEdgeBrushPreset(ui.edgeBrushPresetId).label
              : getObstacleBrushPreset(ui.obstacleBrushPresetId).label
            : undefined;
          drawHUD(
            hudContainerRef.current,
            enc.battleMap.name,
            gridW,
            gridH,
            selectedToken,
            ui.isObstaclePaintMode,
            ui.obstacleBrushRadius,
            ui.isGridEditMode,
            screen.width,
            screen.height,
            activeBrushPresetLabel,
            ui.obstaclePaintTarget,
            ui.edgeDirection
          );
          drawPreviewHint(
            hudContainerRef.current,
            screen.width,
            screen.height,
            ui.tacticalPreview.diagnostics
              ? buildFailureExplanation(ui.tacticalPreview.diagnostics)
              : null
          );
        }
      };

      drawRef.current();
    }

    void init();

    return () => {
      cancelled = true;
      drawRef.current = null;
      setIsRendererReady(false);
      if (previewTimerRef.current) clearTimeout(previewTimerRef.current);
      if (appRef.current) {
        appRef.current.destroy(true, { children: true });
        appRef.current = null;
      }
      bgSpriteRef.current = null;
      reachAoeGfxRef.current = null;
      gridGfxRef.current = null;
      cellFillsGfxRef.current = null;
      edgeObstaclesGfxRef.current = null;
      tokenContainerRef.current = null;
      tacticalOverlayContainerRef.current = null;
      editHandlesContainerRef.current = null;
      hudContainerRef.current = null;
    };
  }, []);

  // ─── Redraw on state changes ────────────────────────────────────────────

  useEffect(() => {
    drawRef.current?.();
  }, [encounter, uiState, selectedTokenId]);

  useEffect(() => {
    const nextBackgroundUrl =
      encounter?.battleMap.imageUrl ?? DEFAULT_MAP_IMAGE_URL;
    if (
      !bgSpriteRef.current ||
      backgroundUrlRef.current === nextBackgroundUrl
    ) {
      return;
    }

    let cancelled = false;
    const image = new Image();
    image.decoding = "async";
    image.onload = () => {
      if (cancelled || !bgSpriteRef.current) {
        return;
      }

      const texture = Texture.from(image);
      backgroundUrlRef.current = nextBackgroundUrl;
      bgSpriteRef.current.texture = texture;

      if (image.naturalWidth > 0 && image.naturalHeight > 0) {
        const ratio = image.naturalWidth / image.naturalHeight;
        setImageAspectRatio(ratio);
        battleMapStore.setMapImageAspectRatio(ratio);
        battleMapStore.setMapImageNaturalSize(
          image.naturalWidth,
          image.naturalHeight
        );
      }

      battleMapStore.setMessage(undefined);
      drawRef.current?.();
    };
    image.onerror = () => {
      if (cancelled) {
        return;
      }
      battleMapStore.setMessage(
        "Nao foi possivel carregar o background do mapa."
      );
    };
    image.src = nextBackgroundUrl;

    return () => {
      cancelled = true;
    };
  }, [encounter?.battleMap.imageUrl, isRendererReady]);

  // ─── Grid calibration drag (window-level events) ────────────────────────

  useEffect(() => {
    if (!gridEditInteraction || !encounter) return;

    const minWidth =
      1 / (uiState.gridWidthDraft ?? encounter.battleMap.gridWidth);
    const minHeight =
      1 / (uiState.gridHeightDraft ?? encounter.battleMap.gridHeight);

    function handleMove(e: PointerEvent): void {
      if (!containerRef.current) return;
      const bounds = containerRef.current.getBoundingClientRect();
      if (bounds.width === 0 || bounds.height === 0) return;
      const xDelta =
        (e.clientX - gridEditInteraction!.startClientX) / bounds.width;
      const yDelta =
        (e.clientY - gridEditInteraction!.startClientY) / bounds.height;
      battleMapStore.updateGridCalibrationDraft(
        applyGridCalibrationInteraction(
          gridEditInteraction!,
          xDelta,
          yDelta,
          minWidth,
          minHeight
        )
      );
    }

    function handleUp(): void {
      setGridEditInteraction(null);
    }

    window.addEventListener("pointermove", handleMove);
    window.addEventListener("pointerup", handleUp);
    return () => {
      window.removeEventListener("pointermove", handleMove);
      window.removeEventListener("pointerup", handleUp);
    };
  }, [
    gridEditInteraction,
    encounter,
    uiState.gridWidthDraft,
    uiState.gridHeightDraft
  ]);

  // ─── Deselect token when permissions change ─────────────────────────────

  useEffect(() => {
    if (!encounter || !selectedTokenId) return;
    const token = encounter.tokens.find((t) => t.id === selectedTokenId);
    if (
      !token ||
      !canInteractWithToken(currentActor, token, encounter.combatState)
    ) {
      setSelectedTokenId(null);
    }
  }, [currentActor, encounter, selectedTokenId]);

  useEffect(() => {
    if (
      (uiState.isGridEditMode || uiState.isObstaclePaintMode) &&
      selectedTokenId
    ) {
      setSelectedTokenId(null);
    }
  }, [selectedTokenId, uiState.isGridEditMode, uiState.isObstaclePaintMode]);

  // ─── Tactical preview: activate on token select, compute reach cells ───

  useEffect(() => {
    if (!selectedToken || !encounter) {
      battleMapStore.deactivateTacticalPreview();
      return;
    }

    battleMapStore.activateTacticalPreview(selectedToken.id, "move");

    battleMapStore.setTacticalPreviewReachableCells(
      findReachableCells(
        {
          map: encounter.battleMap,
          obstacles: encounter.obstacles,
          edgeObstacles: encounter.edgeObstacles,
          tokens: encounter.tokens
        },
        selectedToken,
        encounter.combatState
      )
    );
  }, [selectedTokenId, selectedToken?.movementBudget, encounter]);

  // ─── Publish map frame size to store ───────────────────────────────────

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const publish = (): void => {
      const b = container.getBoundingClientRect();
      battleMapStore.setMapFrameSize(b.width, b.height);
    };
    publish();
    const obs = new ResizeObserver(publish);
    obs.observe(container);
    return () => obs.disconnect();
  }, [imageAspectRatio]);

  // ─── Cursor ─────────────────────────────────────────────────────────────

  const cursor = uiState.isGridEditMode
    ? "grab"
    : uiState.isObstaclePaintMode
      ? "cell"
      : uiState.embeddedSelectionMode !== "none"
        ? "crosshair"
        : selectedTokenId
          ? "crosshair"
          : "default";

  return (
    <div style={{ overflow: "auto", maxWidth: "100%", maxHeight: "100%" }}>
      <div style={{ position: "relative" }}>
        <div
          ref={containerRef}
          style={{
            width: "100%",
            aspectRatio: imageAspectRatio,
            borderRadius: 6,
            overflow: "hidden",
            cursor,
            backgroundColor: "#111923",
            boxShadow: "0 8px 28px rgba(0,0,0,0.35)",
            touchAction: uiState.isGridEditMode ? "none" : "auto"
          }}
        />
        {!encounter ? (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#666",
              fontStyle: "italic",
              pointerEvents: "none"
            }}
          >
            Aguardando dados do servidor…
          </div>
        ) : null}
        {selectedToken ? (
          <div
            style={{
              position: "absolute",
              right: 12,
              bottom: 12,
              width: "min(320px, calc(100% - 24px))",
              borderRadius: 12,
              border: "1px solid rgba(148,163,184,0.22)",
              background:
                "linear-gradient(180deg, rgba(15,23,42,0.88), rgba(2,6,23,0.94))",
              boxShadow: "0 18px 40px rgba(2, 6, 23, 0.38)",
              padding: "12px 14px",
              display: "flex",
              flexDirection: "column",
              gap: 8,
              pointerEvents: "none"
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: "999px",
                  display: "grid",
                  placeItems: "center",
                  background:
                    selectedToken.controllerType === "player"
                      ? "rgba(59,130,246,0.22)"
                      : "rgba(239,68,68,0.22)",
                  border: "1px solid rgba(255,255,255,0.16)",
                  color: "#f8fafc",
                  fontSize: 12,
                  fontWeight: 700,
                  letterSpacing: "0.08em"
                }}
              >
                {getTokenBadgeLabel(selectedToken.label)}
              </div>
              <div style={{ minWidth: 0 }}>
                <div
                  style={{ color: "#f8fafc", fontSize: 14, fontWeight: 700 }}
                >
                  {selectedToken.label}
                </div>
                <div style={{ color: "#94a3b8", fontSize: 11 }}>
                  {selectedToken.controllerType === "gm"
                    ? "Controlado pelo mestre"
                    : `Controlado pelo player ${selectedToken.controllerId}`}
                </div>
              </div>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                gap: 8
              }}
            >
              <div
                style={{
                  borderRadius: 10,
                  background: "rgba(15,23,42,0.64)",
                  padding: "8px 10px"
                }}
              >
                <div
                  style={{
                    color: "#64748b",
                    fontSize: 10,
                    textTransform: "uppercase",
                    letterSpacing: "0.08em"
                  }}
                >
                  Movimento
                </div>
                <div
                  style={{ color: "#e2e8f0", fontSize: 14, fontWeight: 700 }}
                >
                  {formatPathCostUnitsAsMeters(selectedToken.movementBudget)} /{" "}
                  {formatMovementSpeedCellsAsMeters(
                    selectedToken.movementSpeedCells
                  )}{" "}
                  m
                </div>
              </div>
              <div
                style={{
                  borderRadius: 10,
                  background: "rgba(15,23,42,0.64)",
                  padding: "8px 10px"
                }}
              >
                <div
                  style={{
                    color: "#64748b",
                    fontSize: 10,
                    textTransform: "uppercase",
                    letterSpacing: "0.08em"
                  }}
                >
                  Turno
                </div>
                <div
                  style={{
                    color:
                      selectedToken.combatantId != null &&
                      selectedToken.combatantId ===
                        encounter?.combatState.activeCombatantId
                        ? "#facc15"
                        : "#cbd5e1",
                    fontSize: 14,
                    fontWeight: 700
                  }}
                >
                  {selectedToken.combatantId != null &&
                  selectedToken.combatantId ===
                    encounter?.combatState.activeCombatantId
                    ? "Ativo"
                    : "Aguardando"}
                </div>
              </div>
            </div>

            {(selectedToken.conditions ?? []).length > 0 ? (
              <div
                style={{
                  borderRadius: 10,
                  background: "rgba(15,23,42,0.64)",
                  padding: "8px 10px",
                  display: "flex",
                  flexDirection: "column",
                  gap: 5
                }}
              >
                <div
                  style={{
                    color: "#64748b",
                    fontSize: 10,
                    textTransform: "uppercase",
                    letterSpacing: "0.08em"
                  }}
                >
                  Condições
                </div>
                {getConditionIndicators(selectedToken.conditions ?? []).map((ind) => (
                  <div
                    key={ind.conditionType}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 7
                    }}
                  >
                    <div
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: "50%",
                        background: ind.colorToken,
                        flexShrink: 0
                      }}
                    />
                    <span
                      style={{
                        color: ind.colorToken,
                        fontSize: 12,
                        fontWeight: 600
                      }}
                    >
                      {ind.label}
                    </span>
                  </div>
                ))}
              </div>
            ) : null}

            {selectedTokenMovementRejection ? (
              <div
                style={{
                  borderRadius: 10,
                  border:
                    selectedTokenMovementRejection.reason ===
                    "movement_budget_exceeded"
                      ? "1px solid rgba(248,113,113,0.42)"
                      : "1px solid rgba(251,191,36,0.32)",
                  background:
                    selectedTokenMovementRejection.reason ===
                    "movement_budget_exceeded"
                      ? "rgba(127,29,29,0.22)"
                      : "rgba(120,53,15,0.18)",
                  padding: "10px 12px",
                  display: "flex",
                  flexDirection: "column",
                  gap: 4
                }}
              >
                <div
                  style={{ color: "#fca5a5", fontSize: 11, fontWeight: 700 }}
                >
                  {selectedTokenMovementRejection.message}
                </div>
                {selectedTokenMovementRejection.pathCostUnits !== undefined ||
                selectedTokenMovementRejection.movementBudget !== undefined ? (
                  <div
                    style={{ color: "#fecaca", fontSize: 12, lineHeight: 1.5 }}
                  >
                    {selectedTokenMovementRejection.movementBudget !== undefined
                      ? `Disponivel: ${formatPathCostUnitsAsMeters(selectedTokenMovementRejection.movementBudget)} m. `
                      : ""}
                    {selectedTokenMovementRejection.pathCostUnits !== undefined
                      ? `Tentativa: ${formatPathCostUnitsAsMeters(selectedTokenMovementRejection.pathCostUnits)} m. `
                      : ""}
                    {selectedTokenMovementRejection.exceededBy !== undefined
                      ? `Excedente: ${formatPathCostUnitsAsMeters(selectedTokenMovementRejection.exceededBy)} m.`
                      : ""}
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
