/**
 * BattleMapCanvas — Renderer PixiJS (Fase 2 + U1)
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
  EdgeDirection,
  GridCalibration,
  Obstacle,
  EdgeObstacle,
  Token
} from "@limiarmap/shared-contracts";
import type { TacticalPreviewState } from "./battle-map-store";
import type { FailureExplanation } from "../targeting/diagnostics-to-explanation";
import { canTokenAct } from "@limiarmap/tactical-engine";
import { useEncounterSnapshot } from "../../services/session-store";
import { useCurrentActor } from "../../services/centrifugo-client";
import {
  formatMovementSpeedCellsAsMeters,
  formatPathCostUnitsAsMeters
} from "../../services/movement-metrics";
import {
  postEmbeddedCellSelected,
  postEmbeddedTokenSelected
} from "../../services/embedded-map-bridge";
import { battleMapStore } from "./battle-map-store";
import { submitMovement } from "./use-movement-actions";
import { submitObstaclePaint } from "./use-obstacle-paint-actions";

import { C, COVER_RANK } from "./constants";
import type {
  GridEditInteraction,
  GridEditInteractionMode,
  ObstacleCellState
} from "./types";
import {
  clamp,
  coordKey,
  buildObstacleCellMap,
  getTokenBadgeLabel,
  cellRect
} from "./utils";
import { getConditionIndicators } from "../conditions/condition-indicators";
export function drawGrid(
  gfx: Graphics,
  cal: GridCalibration,
  gridW: number,
  gridH: number,
  canvasW: number,
  canvasH: number,
  isEditMode: boolean
): void {
  gfx.clear();

  const startX = cal.x * canvasW;
  const startY = cal.y * canvasH;
  const totalW = cal.width * canvasW;
  const totalH = cal.height * canvasH;
  const cellW = totalW / gridW;
  const cellH = totalH / gridH;

  if (isEditMode) {
    gfx
      .rect(startX, startY, totalW, totalH)
      .fill({ color: C.gridEditBg, alpha: C.gridEditBgAlpha });
  }

  // All grid lines in a single stroke call
  for (let col = 0; col <= gridW; col++) {
    const x = startX + col * cellW;
    gfx.moveTo(x, startY).lineTo(x, startY + totalH);
  }
  for (let row = 0; row <= gridH; row++) {
    const y = startY + row * cellH;
    gfx.moveTo(startX, y).lineTo(startX + totalW, y);
  }
  gfx.stroke({
    width: 1,
    color: isEditMode ? C.gridLineEdit : C.gridLine,
    alpha: isEditMode ? C.gridLineEditAlpha : C.gridLineAlpha
  });

  // Outer border
  gfx.rect(startX, startY, totalW, totalH).stroke({
    width: isEditMode ? 2 : 1,
    color: isEditMode ? C.gridBorderEdit : C.gridBorder,
    alpha: isEditMode ? C.gridBorderEditAlpha : C.gridBorderAlpha
  });
}

export function drawCellFills(
  gfx: Graphics,
  cal: GridCalibration,
  gridW: number,
  gridH: number,
  canvasW: number,
  canvasH: number,
  obstacles: Obstacle[],
  movementPreview: Coordinate[],
  targetingPreview: Coordinate[],
  embeddedPreview: Coordinate[],
  embeddedSelectedCell: Coordinate | null
): void {
  gfx.clear();

  const obstacleCellMap = buildObstacleCellMap(obstacles);
  const movementSet = new Set(movementPreview.map(coordKey));
  const targetingSet = new Set(
    [...targetingPreview, ...embeddedPreview].map(coordKey)
  );

  // Obstacle fills (highest priority)
  for (const [key, obs] of obstacleCellMap) {
    const [gxStr, gyStr] = key.split(",");
    const gx = Number(gxStr);
    const gy = Number(gyStr);
    const { x, y, w, h } = cellRect(
      gx,
      gy,
      cal,
      gridW,
      gridH,
      canvasW,
      canvasH
    );

    let color: number;
    let alpha: number;
    if (obs.blocksMovement && obs.blocksEffect) {
      color = C.obsMoveSpell;
      alpha = C.obsMoveSpellAlpha;
    } else if (obs.blocksMovement) {
      color = C.obsMove;
      alpha = C.obsMoveAlpha;
    } else if (obs.blocksEffect) {
      color = C.obsSpell;
      alpha = C.obsSpellAlpha;
    }
    // threeQuarters-cover-only: rendered as deep amber (distinct from half-cover gold)
    else if (obs.cover === "threeQuarters") {
      color = C.obsCoverThreeQ;
      alpha = C.obsCoverThreeQAlpha;
    } else if (obs.cover === "half") {
      color = C.obsCover;
      alpha = C.obsCoverAlpha;
    } else if (obs.blocksVision) {
      color = C.obsVision;
      alpha = C.obsVisionAlpha;
    }
    // Phase 7: difficult terrain — traversable but costs more to enter
    else if (obs.movementCostMultiplier > 1) {
      color = C.obsDifficultTerrain;
      alpha = C.obsDifficultTerrainAlpha;
    } else continue;

    gfx.rect(x, y, w, h).fill({ color, alpha });
    // Cover strokes: amber ring indicates cover level alongside block color
    if (obs.cover === "threeQuarters") {
      gfx.rect(x, y, w, h).stroke({ width: 1.5, color: 0xffaa44, alpha: 0.65 });
    } else if (obs.cover === "half") {
      gfx.rect(x, y, w, h).stroke({ width: 1, color: 0xffe08c, alpha: 0.55 });
    } else if (obs.movementCostMultiplier > 1) {
      // Dotted-style inner border to signal "passable but costly"
      gfx
        .rect(x + 2, y + 2, w - 4, h - 4)
        .stroke({ width: 1, color: 0xd4a870, alpha: 0.6 });
    }
  }

  // Movement preview (skips obstacle cells)
  for (const coord of movementPreview) {
    if (obstacleCellMap.has(coordKey(coord))) continue;
    const { x, y, w, h } = cellRect(
      coord.x,
      coord.y,
      cal,
      gridW,
      gridH,
      canvasW,
      canvasH
    );
    gfx
      .rect(x, y, w, h)
      .fill({ color: C.movPreview, alpha: C.movPreviewAlpha });
  }

  if (embeddedSelectedCell) {
    const { x, y, w, h } = cellRect(
      embeddedSelectedCell.x,
      embeddedSelectedCell.y,
      cal,
      gridW,
      gridH,
      canvasW,
      canvasH
    );
    gfx.rect(x, y, w, h).fill({ color: 0x7c3aed, alpha: 0.18 });
    gfx.rect(x, y, w, h).stroke({ width: 2, color: 0xc4b5fd, alpha: 0.9 });
  }

  // Targeting preview (skips obstacle cells and movement preview cells)
  for (const previewKey of targetingSet) {
    const [xValue, yValue] = previewKey.split(",");
    const coord = { x: Number(xValue), y: Number(yValue) };
    const coordHash = coordKey(coord);
    if (obstacleCellMap.has(coordHash) || movementSet.has(coordHash)) continue;
    const { x, y, w, h } = cellRect(
      coord.x,
      coord.y,
      cal,
      gridW,
      gridH,
      canvasW,
      canvasH
    );
    gfx
      .rect(x, y, w, h)
      .fill({ color: C.tgtPreview, alpha: C.tgtPreviewAlpha });
  }
}

export function drawEdgeObstacles(
  gfx: Graphics,
  cal: GridCalibration,
  gridW: number,
  gridH: number,
  canvasW: number,
  canvasH: number,
  edgeObstacles: EdgeObstacle[]
): void {
  gfx.clear();

  for (const edge of edgeObstacles) {
    const { x: gx, y: gy, direction } = edge;
    const {
      x: cellX,
      y: cellY,
      w: cellW,
      h: cellH
    } = cellRect(gx, gy, cal, gridW, gridH, canvasW, canvasH);

    let x1: number, y1: number, x2: number, y2: number;
    switch (direction) {
      case "N":
        x1 = cellX;
        y1 = cellY;
        x2 = cellX + cellW;
        y2 = cellY;
        break;
      case "S":
        x1 = cellX;
        y1 = cellY + cellH;
        x2 = cellX + cellW;
        y2 = cellY + cellH;
        break;
      case "E":
        x1 = cellX + cellW;
        y1 = cellY;
        x2 = cellX + cellW;
        y2 = cellY + cellH;
        break;
      case "W":
        x1 = cellX;
        y1 = cellY;
        x2 = cellX;
        y2 = cellY + cellH;
        break;
    }

    let color: number;
    let alpha: number;
    let width: number;

    if (edge.blocksMovement && edge.blocksEffect) {
      color = C.edgeWall;
      alpha = C.edgeWallAlpha;
      width = 3;
    } else if (edge.blocksMovement) {
      color = C.edgeBarrier;
      alpha = C.edgeBarrierAlpha;
      width = 2.5;
    } else if (edge.cover === "half") {
      color = C.edgeCoverHalf;
      alpha = C.edgeCoverHalfAlpha;
      width = 2;
    } else if (edge.cover === "threeQuarters") {
      color = C.edgeCoverThreeQ;
      alpha = C.edgeCoverThreeQAlpha;
      width = 2;
    } else if (edge.blocksVision) {
      color = C.edgeVisionBlocker;
      alpha = C.edgeVisionBlockerAlpha;
      width = 2;
    } else if (edge.blocksEffect) {
      color = C.edgeEffectBlocker;
      alpha = C.edgeEffectBlockerAlpha;
      width = 2;
    } else {
      continue;
    }

    gfx.moveTo(x1, y1).lineTo(x2, y2).stroke({ width, color, alpha });
  }
}

export function drawTokenLayer(
  container: Container,
  tokens: Token[],
  cal: GridCalibration,
  gridW: number,
  gridH: number,
  canvasW: number,
  canvasH: number,
  selectedTokenId: string | null,
  selectedCombatantId: string | null,
  activeCombatantId: string | null | undefined
): void {
  container.removeChildren();

  for (const token of tokens) {
    const { x, y, w, h } = cellRect(
      token.position.x,
      token.position.y,
      cal,
      gridW,
      gridH,
      canvasW,
      canvasH
    );
    const cx = x + w / 2;
    const cy = y + h / 2;
    const radius = Math.min(w, h) * 0.36;

    const isSelected =
      token.id === selectedTokenId ||
      (selectedCombatantId != null &&
        token.combatantId === selectedCombatantId);
    const isActive =
      token.combatantId != null && token.combatantId === activeCombatantId;

    const bg =
      token.controllerType === "player"
        ? C.tokenPlayer
        : token.controllerType === "gm"
          ? C.tokenGm
          : C.tokenNeutral;
    const borderColor = isActive
      ? C.tokenBorderActive
      : isSelected
        ? C.tokenBorderSelected
        : C.tokenBorderNormal;
    const borderAlpha = isActive || isSelected ? 1 : C.tokenBorderNormalAlpha;
    const borderWidth = isActive || isSelected ? 3 : 1.5;

    const gfx = new Graphics();
    gfx.circle(0, 0, radius).fill({ color: bg });
    gfx
      .circle(0, 0, radius)
      .stroke({ width: borderWidth, color: borderColor, alpha: borderAlpha });
    gfx.x = cx;
    gfx.y = cy;

    const label = getTokenBadgeLabel(token.label);
    const fontSize = Math.max(8, Math.min(14, radius * 0.8));
    const text = new Text({
      text: label,
      style: new TextStyle({ fill: "#ffffff", fontSize, fontWeight: "bold" })
    });
    text.anchor.set(0.5);
    text.x = cx;
    text.y = cy;

    container.addChild(gfx);
    container.addChild(text);

    // ─── Condition chips (Phase U3) ────────────────────────────────────────
    const conditions = token.conditions ?? [];
    const isInvisible = conditions.includes("invisible");

    // Ghost ring for invisible tokens — faint violet ring outside the normal border
    if (isInvisible) {
      const ghostRing = new Graphics();
      ghostRing.circle(0, 0, radius + 5).stroke({ width: 2, color: 0xc4b5fd, alpha: 0.4 });
      ghostRing.circle(0, 0, radius + 8).stroke({ width: 1, color: 0xa78bfa, alpha: 0.2 });
      ghostRing.x = cx;
      ghostRing.y = cy;
      container.addChild(ghostRing);
    }

    const indicators = getConditionIndicators(conditions);
    if (indicators.length > 0) {
      const MAX_VISIBLE = 3;
      const visible = indicators.slice(0, MAX_VISIBLE);
      const overflow = indicators.length - visible.length;
      const chipR = Math.max(3.5, Math.round(radius * 0.24));
      const chipSpacing = chipR * 2 + 2.5;
      const totalItems = visible.length + (overflow > 0 ? 1 : 0);
      const chipStartX = cx - ((totalItems - 1) * chipSpacing) / 2;
      const chipY = cy + radius + chipR + 3.5;

      for (let i = 0; i < visible.length; i++) {
        const ind = visible[i];
        const chipX = chipStartX + i * chipSpacing;
        const colorNum = parseInt(ind.colorToken.replace("#", ""), 16);
        const chipGfx = new Graphics();
        chipGfx.circle(0, 0, chipR).fill({ color: colorNum, alpha: 0.92 });
        chipGfx.circle(0, 0, chipR).stroke({ width: 0.5, color: 0x000000, alpha: 0.4 });
        chipGfx.x = chipX;
        chipGfx.y = chipY;
        container.addChild(chipGfx);
      }

      if (overflow > 0) {
        const overflowX = chipStartX + visible.length * chipSpacing;
        const overflowFontSize = Math.max(6, Math.round(chipR * 1.3));
        const overflowText = new Text({
          text: `+${overflow}`,
          style: new TextStyle({ fill: "#94a3b8", fontSize: overflowFontSize, fontWeight: "bold" })
        });
        overflowText.anchor.set(0.5);
        overflowText.x = overflowX;
        overflowText.y = chipY;
        container.addChild(overflowText);
      }
    }
  }
}

export function drawEditHandles(
  container: Container,
  cal: GridCalibration,
  canvasW: number,
  canvasH: number,
  isEditMode: boolean,
  isSaving: boolean,
  onHandleDown: (
    mode: GridEditInteractionMode,
    clientX: number,
    clientY: number
  ) => void
): void {
  container.removeChildren();
  if (!isEditMode) return;

  const gx = cal.x * canvasW;
  const gy = cal.y * canvasH;
  const gw = cal.width * canvasW;
  const gh = cal.height * canvasH;

  // "Modo editar grid" badge
  const badge = new Text({
    text: "Modo editar grid",
    style: new TextStyle({ fill: "#9ed0ff", fontSize: 11 })
  });
  badge.x = gx + 10;
  badge.y = gy + 6;
  container.addChild(badge);

  // Move area: transparent rect covering entire grid (lowest z-order)
  const moveArea = new Graphics();
  moveArea.rect(gx, gy, gw, gh).fill({ color: 0, alpha: 0 });
  moveArea.eventMode = "static";
  moveArea.cursor = "move";
  moveArea.on("pointerdown", (e: FederatedPointerEvent) => {
    e.stopPropagation();
    onHandleDown("move", e.nativeEvent.clientX, e.nativeEvent.clientY);
  });
  container.addChildAt(moveArea, 0);

  // Resize-x handle (right edge)
  const handleX = new Graphics();
  handleX
    .rect(gx + gw - 14, gy + 18, 14, Math.max(0, gh - 36))
    .fill({ color: C.handleEdge, alpha: 0.55 });
  handleX.eventMode = "static";
  handleX.cursor = isSaving ? "not-allowed" : "ew-resize";
  handleX.on("pointerdown", (e: FederatedPointerEvent) => {
    e.stopPropagation();
    if (!isSaving)
      onHandleDown("resize-x", e.nativeEvent.clientX, e.nativeEvent.clientY);
  });
  container.addChild(handleX);

  // Resize-y handle (bottom edge)
  const handleY = new Graphics();
  handleY
    .rect(gx + 18, gy + gh - 14, Math.max(0, gw - 36), 14)
    .fill({ color: C.handleEdge, alpha: 0.55 });
  handleY.eventMode = "static";
  handleY.cursor = isSaving ? "not-allowed" : "ns-resize";
  handleY.on("pointerdown", (e: FederatedPointerEvent) => {
    e.stopPropagation();
    if (!isSaving)
      onHandleDown("resize-y", e.nativeEvent.clientX, e.nativeEvent.clientY);
  });
  container.addChild(handleY);

  // Resize-both handle (bottom-right corner square)
  const handleBoth = new Graphics();
  handleBoth
    .roundRect(gx + gw - 16, gy + gh - 16, 18, 18, 4)
    .fill({ color: 0x5ca9ff, alpha: 0.95 });
  handleBoth
    .roundRect(gx + gw - 16, gy + gh - 16, 18, 18, 4)
    .stroke({ width: 2, color: 0x0a141e, alpha: 0.85 });
  handleBoth.eventMode = "static";
  handleBoth.cursor = isSaving ? "not-allowed" : "nwse-resize";
  handleBoth.on("pointerdown", (e: FederatedPointerEvent) => {
    e.stopPropagation();
    if (!isSaving)
      onHandleDown("resize-both", e.nativeEvent.clientX, e.nativeEvent.clientY);
  });
  container.addChild(handleBoth);
}

export function drawHUD(
  container: Container,
  mapName: string,
  gridW: number,
  gridH: number,
  selectedToken: Token | null,
  isObstacleMode: boolean,
  brushRadius: number,
  isEditMode: boolean,
  canvasW: number,
  canvasH: number,
  activeBrushPresetLabel?: string,
  obstaclePaintTarget?: "cell" | "edge",
  edgeDirection?: EdgeDirection
): void {
  container.removeChildren();

  // Map name badge (top-left)
  const nameLabel = new Text({
    text: `${mapName} · ${gridW}×${gridH}`,
    style: new TextStyle({ fill: "#b5c4d8", fontSize: 10 })
  });
  nameLabel.x = 8 + 8;
  nameLabel.y = 8 + 3;
  const nameBg = new Graphics();
  nameBg
    .roundRect(8, 8, nameLabel.width + 16, nameLabel.height + 6, 4)
    .fill({ color: 0, alpha: 0.6 });
  container.addChild(nameBg);
  container.addChild(nameLabel);

  // Obstacle mode badge (top-right)
  if (isObstacleMode) {
    const presetSuffix = activeBrushPresetLabel
      ? ` · ${activeBrushPresetLabel}`
      : "";
    const modeSuffix =
      obstaclePaintTarget === "edge"
        ? ` · borda ${edgeDirection ?? ""}${presetSuffix}`
        : ` · raio ${brushRadius}${presetSuffix}`;
    const obsLabel = new Text({
      text: `Modo obstaculos${modeSuffix}`,
      style: new TextStyle({ fill: "#ffbf78", fontSize: 10 })
    });
    const obsBgW = obsLabel.width + 16;
    const obsBgX = canvasW - obsBgW - 8;
    obsLabel.x = obsBgX + 8;
    obsLabel.y = 8 + 3;
    const obsBg = new Graphics();
    obsBg
      .roundRect(obsBgX, 8, obsBgW, obsLabel.height + 6, 4)
      .fill({ color: 0, alpha: 0.72 });
    obsBg
      .roundRect(obsBgX, 8, obsBgW, obsLabel.height + 6, 4)
      .stroke({ width: 1, color: 0xff9060, alpha: 0.3 });
    container.addChild(obsBg);
    container.addChild(obsLabel);
  }

  // Selected token indicator (bottom-center)
  if (selectedToken && !isEditMode) {
    const selLabel = new Text({
      text: `${selectedToken.label} — clique em uma celula para mover`,
      style: new TextStyle({ fill: "#00e676", fontSize: 12 })
    });
    const selW = selLabel.width + 24;
    const selX = (canvasW - selW) / 2;
    const selH = selLabel.height + 10;
    const selY = canvasH - 12 - selH;
    selLabel.x = selX + 12;
    selLabel.y = selY + 5;
    const selBg = new Graphics();
    selBg.roundRect(selX, selY, selW, selH, 4).fill({ color: 0, alpha: 0.8 });
    selBg
      .roundRect(selX, selY, selW, selH, 4)
      .stroke({ width: 1, color: 0x00e676, alpha: 1 });
    container.addChild(selBg);
    container.addChild(selLabel);
  }
}

// ─── Phase U1: Tactical Preview ──────────────────────────────────────────────

/**
 * drawReachAndAoe — fills reach overlay + AoE footprint cells.
 *
 * Rendered as the FIRST layer in cellFillsGfx so obstacle colors paint
 * on top (they remain readable) while the reach tint is still visible.
 * Call this before drawCellFills so the obstacle layer takes priority.
 */
export function drawReachAndAoe(
  gfx: Graphics,
  cal: GridCalibration,
  gridW: number,
  gridH: number,
  canvasW: number,
  canvasH: number,
  reachableCells: Coordinate[],
  aoeCells: Coordinate[]
): void {
  // Reach overlay (soft blue tint)
  for (const coord of reachableCells) {
    const { x, y, w, h } = cellRect(coord.x, coord.y, cal, gridW, gridH, canvasW, canvasH);
    gfx.rect(x, y, w, h).fill({ color: C.previewReach, alpha: C.previewReachAlpha });
  }

  // AoE footprint (warm amber)
  for (const coord of aoeCells) {
    const { x, y, w, h } = cellRect(coord.x, coord.y, cal, gridW, gridH, canvasW, canvasH);
    gfx.rect(x, y, w, h).fill({ color: C.previewAoe, alpha: C.previewAoeAlpha });
    gfx.rect(x, y, w, h).stroke({ width: 1, color: C.previewAoeBorder, alpha: C.previewAoeBorderAlpha });
  }
}

/**
 * drawTacticalTokenOverlay — draws a validity ring around a hovered target token.
 *
 * Green ring = valid target, red ring = invalid target.
 * Rendered in a dedicated container ABOVE tokenContainer so it never
 * gets clipped by the token fill.
 */
export function drawTacticalTokenOverlay(
  container: Container,
  tokens: Token[],
  cal: GridCalibration,
  gridW: number,
  gridH: number,
  canvasW: number,
  canvasH: number,
  preview: TacticalPreviewState
): void {
  container.removeChildren();

  if (!preview.active || !preview.targetCell) return;

  const targetToken = tokens.find(
    (t) =>
      t.position.x === preview.targetCell!.x &&
      t.position.y === preview.targetCell!.y
  );
  if (!targetToken) return;

  const { x, y, w, h } = cellRect(
    targetToken.position.x,
    targetToken.position.y,
    cal,
    gridW,
    gridH,
    canvasW,
    canvasH
  );
  const cx = x + w / 2;
  const cy = y + h / 2;
  const radius = Math.min(w, h) * 0.36;

  const isValid = preview.diagnostics == null || preview.diagnostics.isValid;
  const ringColor = isValid ? C.previewTargetValid : C.previewTargetInvalid;
  const ringAlpha = isValid ? C.previewTargetValidAlpha : C.previewTargetInvalidAlpha;

  const ring = new Graphics();
  ring.circle(0, 0, radius + 4).stroke({ width: 3, color: ringColor, alpha: ringAlpha });
  ring.x = cx;
  ring.y = cy;
  container.addChild(ring);
}

// ─── Severity → visual tokens ─────────────────────────────────────────────────

const SEVERITY_STYLES = {
  orange: {
    textColor: "#f97316",
    detailColor: "#fdba74",
    bgColor: 0x1a0a00,
    borderColor: 0xff7a28,
  },
  red: {
    textColor: "#ff7070",
    detailColor: "#fca5a5",
    bgColor: 0x1a0000,
    borderColor: 0xff4444,
  },
  purple: {
    textColor: "#c084fc",
    detailColor: "#d8b4fe",
    bgColor: 0x0d0014,
    borderColor: 0x9333ea,
  },
  gray: {
    textColor: "#94a3b8",
    detailColor: "#cbd5e1",
    bgColor: 0x0f172a,
    borderColor: 0x475569,
  },
} as const;

/**
 * drawPreviewHint — renders a structured failure explanation badge
 * near the bottom of the canvas, above the token card (Phase U2).
 *
 * Shows:
 *   - primary message (bold, severity-coloured)
 *   - up to 2 detail lines (smaller, lighter)
 *
 * Pass null to clear any existing badge.
 */
export function drawPreviewHint(
  container: Container,
  canvasW: number,
  canvasH: number,
  explanation: FailureExplanation | null
): void {
  const existing = container.children.find((c) => c.label === "preview-hint");
  if (existing) container.removeChild(existing);

  if (!explanation) return;

  const style = SEVERITY_STYLES[explanation.severity];
  const PAD_X = 12;
  const PAD_Y = 6;
  const LINE_GAP = 3;

  // Primary text
  const primaryText = new Text({
    text: explanation.primary,
    style: new TextStyle({
      fill: style.textColor,
      fontSize: 11,
      fontWeight: "bold",
    }),
  });

  // Detail texts (max 2)
  const detailTexts = explanation.details.slice(0, 2).map(
    (line) =>
      new Text({
        text: line,
        style: new TextStyle({
          fill: style.detailColor,
          fontSize: 10,
          fontWeight: "normal",
        }),
      })
  );

  // Measure total height and max width
  const allTexts = [primaryText, ...detailTexts];
  const contentW = Math.max(...allTexts.map((t) => t.width));
  const contentH =
    primaryText.height +
    detailTexts.reduce((sum, t) => sum + t.height + LINE_GAP, 0);

  const bgW = contentW + PAD_X * 2;
  const bgH = contentH + PAD_Y * 2;
  const bgX = (canvasW - bgW) / 2;
  const bgY = canvasH - 48 - bgH;

  const bg = new Graphics();
  bg.roundRect(bgX, bgY, bgW, bgH, 5).fill({
    color: style.bgColor,
    alpha: 0.88,
  });
  bg.roundRect(bgX, bgY, bgW, bgH, 5).stroke({
    width: 1,
    color: style.borderColor,
    alpha: 0.6,
  });

  // Position texts
  let curY = bgY + PAD_Y;
  primaryText.x = bgX + PAD_X;
  primaryText.y = curY;
  curY += primaryText.height + LINE_GAP;

  for (const dt of detailTexts) {
    dt.x = bgX + PAD_X;
    dt.y = curY;
    curY += dt.height + LINE_GAP;
  }

  const wrapper = new Container();
  wrapper.label = "preview-hint";
  wrapper.addChild(bg);
  wrapper.addChild(primaryText);
  for (const dt of detailTexts) wrapper.addChild(dt);
  container.addChild(wrapper);
}

// ─── Main Component ────────────────────────────────────────────────────────────
