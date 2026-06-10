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
import React, { useEffect, useRef, useState, useSyncExternalStore } from "react";
import {
  Application,
  Container,
  type FederatedPointerEvent,
  Graphics,
  Sprite,
  Text,
  TextStyle,
  Texture,
} from "pixi.js";
import type { CombatState, Coordinate, GridCalibration, Obstacle, Token } from "@limiarmap/shared-contracts";
import { getOccupiedCells, getTokenFootprint } from "@limiarmap/tactical-engine";
import { canTokenAct } from "@limiarmap/tactical-engine";
import { useEncounterSnapshot } from "../../services/session-store";
import { useCurrentActor } from "../../services/centrifugo-client";
import {
  formatMovementSpeedCellsAsMeters,
  formatPathCostUnitsAsMeters,
} from "../../services/movement-metrics";
import {
  postEmbeddedCellSelected,
  postEmbeddedTokenSelected,
} from "../../services/embedded-map-bridge";
import { battleMapStore } from "./battle-map-store";
import { submitMovement } from "./use-movement-actions";
import { submitObstaclePaint } from "./use-obstacle-paint-actions";


import { C, COVER_RANK } from "./constants";
import type { GridEditInteraction, GridEditInteractionMode, ObstacleCellState } from "./types";
import type { GridCalibrationPixelPoint } from "./battle-map-store.types";
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

export function coordKey(c: Coordinate): string {
  return `${c.x},${c.y}`;
}

/**
 * Resolve a token portrait URL into something the map web app can load
 * same-origin. Control-server-hosted assets (onboarding presets and uploads)
 * are routed through the map server's `/sessions/:id/asset` proxy to avoid
 * cross-origin/CORS failures; absolute and already-proxied URLs pass through.
 */
export function resolveTokenImageUrl(sessionId: string, imageUrl: string): string {
  if (/^https?:\/\//.test(imageUrl) || imageUrl.startsWith("/sessions/")) {
    return imageUrl;
  }
  if (imageUrl.startsWith("/api/assets/") || imageUrl.startsWith("/onboarding/")) {
    return `/sessions/${encodeURIComponent(sessionId)}/asset?src=${encodeURIComponent(imageUrl)}`;
  }
  return imageUrl;
}

export function getTokenBadgeLabel(label: string): string {
  const words = label.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) {
    return "?";
  }
  if (words.length === 1) {
    return words[0].slice(0, 2).toUpperCase();
  }
  return `${words[0][0] ?? ""}${words[words.length - 1][0] ?? ""}`.toUpperCase();
}

/** Convert canvas-space pixel position to grid cell coordinate. Returns null if outside grid. */
export function pixelToGrid(
  px: number, py: number,
  cal: GridCalibration, gridW: number, gridH: number,
  canvasW: number, canvasH: number,
): Coordinate | null {
  const relX = px / canvasW;
  const relY = py / canvasH;
  if (relX < cal.x || relX >= cal.x + cal.width) return null;
  if (relY < cal.y || relY >= cal.y + cal.height) return null;
  const gx = Math.floor(((relX - cal.x) / cal.width) * gridW);
  const gy = Math.floor(((relY - cal.y) / cal.height) * gridH);
  if (gx < 0 || gx >= gridW || gy < 0 || gy >= gridH) return null;
  return { x: gx, y: gy };
}

/** Return the canvas-space rect for a given grid cell. */
export function cellRect(
  gx: number, gy: number,
  cal: GridCalibration, gridW: number, gridH: number,
  canvasW: number, canvasH: number,
): { x: number; y: number; w: number; h: number } {
  const w = (cal.width / gridW) * canvasW;
  const h = (cal.height / gridH) * canvasH;
  const x = (cal.x + (gx / gridW) * cal.width) * canvasW;
  const y = (cal.y + (gy / gridH) * cal.height) * canvasH;
  return { x, y, w, h };
}

export function tokenOccupiesCell(token: Token, cell: Coordinate): boolean {
  return getOccupiedCells(token.position, getTokenFootprint(token)).some(
    (occupied) => occupied.x === cell.x && occupied.y === cell.y
  );
}

export function findTokenAtCell(tokens: Token[], cell: Coordinate): Token | undefined {
  return tokens.find((token) => tokenOccupiesCell(token, cell));
}

export function buildObstacleCellMap(obstacles: Obstacle[]): Map<string, ObstacleCellState> {
  const map = new Map<string, ObstacleCellState>();
  for (const obs of obstacles) {
    for (const cell of obs.cells) {
      const key = coordKey(cell);
      const cur = map.get(key) ?? {
        blocksMovement: false,
        blocksEffect: false,
        blocksVision: false,
        cover: "none" as const,
        movementCostMultiplier: 1,
      };
      map.set(key, {
        blocksMovement: cur.blocksMovement || obs.blocksMovement,
        blocksEffect: cur.blocksEffect || obs.blocksEffect,
        blocksVision: cur.blocksVision || obs.blocksVision,
        cover: COVER_RANK[obs.cover] > COVER_RANK[cur.cover] ? obs.cover : cur.cover,
        // Phase 7: highest multiplier wins when obstacles overlap on the same cell.
        movementCostMultiplier: Math.max(cur.movementCostMultiplier, obs.movementCostMultiplier),
      });
    }
  }
  return map;
}

export function canControlToken(actor: { actorId: string; actorType: string }, token: Token): boolean {
  if (actor.actorType === "gm") return true;
  return token.controllerId === actor.actorId && token.controllerType === actor.actorType;
}

export function canInteractWithToken(
  actor: { actorId: string; actorType: string },
  token: Token,
  combatState: CombatState,
): boolean {
  return canControlToken(actor, token) && canTokenAct(combatState, token.combatantId);
}

export function getSelectionBlockedMessage(
  actor: { actorId: string; actorType: string },
  token: Token,
  combatState: CombatState,
): string {
  if (!canControlToken(actor, token)) {
    return `${token.label} esta sob controle do ${token.controllerType === "gm" ? "mestre" : "jogador autorizado"}.`;
  }
  if (token.combatantId !== combatState.activeCombatantId) {
    return `Nao e o turno de ${token.label}.`;
  }
  return `${token.label} nao pode agir agora.`;
}

export function computePath(from: Coordinate, to: Coordinate): Coordinate[] {
  const path: Coordinate[] = [];
  let { x, y } = from;
  while (x !== to.x || y !== to.y) {
    x += Math.sign(to.x - x);
    y += Math.sign(to.y - y);
    path.push({ x, y });
  }
  return path;
}

export function applyGridCalibrationInteraction(
  interaction: GridEditInteraction,
  xDelta: number,
  yDelta: number,
  minWidth: number,
  minHeight: number,
): GridCalibration {
  const { startCalibration: sc, mode } = interaction;
  if (mode === "move") {
    return {
      ...sc,
      x: clamp(sc.x + xDelta, 0, 1 - sc.width),
      y: clamp(sc.y + yDelta, 0, 1 - sc.height),
    };
  }
  if (mode === "resize-x") {
    return { ...sc, width: clamp(sc.width + xDelta, minWidth, 1 - sc.x) };
  }
  if (mode === "resize-y") {
    return { ...sc, height: clamp(sc.height + yDelta, minHeight, 1 - sc.y) };
  }
  return {
    ...sc,
    width: clamp(sc.width + xDelta, minWidth, 1 - sc.x),
    height: clamp(sc.height + yDelta, minHeight, 1 - sc.y),
  };
}

export function deriveGridCalibrationFromTwoPoints(
  pointA: GridCalibrationPixelPoint,
  pointB: GridCalibrationPixelPoint,
  squaresX: number,
  squaresY: number,
  imageWidth: number,
  imageHeight: number,
): { gridCalibration: GridCalibration; gridWidth: number; gridHeight: number } {
  if (!Number.isFinite(imageWidth) || imageWidth <= 0 || !Number.isFinite(imageHeight) || imageHeight <= 0) {
    throw new Error("invalid_image_dimensions");
  }
  if (!Number.isInteger(squaresX) || squaresX <= 0 || !Number.isInteger(squaresY) || squaresY <= 0) {
    throw new Error("invalid_grid_dimensions");
  }

  const minX = Math.min(pointA.x, pointB.x);
  const minY = Math.min(pointA.y, pointB.y);
  const deltaX = Math.abs(pointB.x - pointA.x);
  const deltaY = Math.abs(pointB.y - pointA.y);

  if (deltaX <= 0 || deltaY <= 0) {
    throw new Error("invalid_calibration_segment");
  }

  const gridCalibration: GridCalibration = {
    x: clamp(minX / imageWidth, 0, 1),
    y: clamp(minY / imageHeight, 0, 1),
    width: clamp(deltaX / imageWidth, 1 / imageWidth, 1),
    height: clamp(deltaY / imageHeight, 1 / imageHeight, 1),
  };

  if (gridCalibration.x + gridCalibration.width > 1 || gridCalibration.y + gridCalibration.height > 1) {
    throw new Error("calibration_out_of_bounds");
  }

  return {
    gridCalibration,
    gridWidth: squaresX,
    gridHeight: squaresY,
  };
}

// ─── Drawing export functions ────────────────────────────────────────────────────────
