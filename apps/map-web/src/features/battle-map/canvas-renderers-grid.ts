import { Graphics } from "pixi.js";
import type {
  CellElevation,
  Coordinate,
  ActiveAreaEffect,
  EdgeDirection,
  GridCalibration,
  Obstacle,
  EdgeObstacle
} from "@limiarmap/shared-contracts";
import { C } from "./constants";
import { coordKey, buildObstacleCellMap, cellRect } from "./utils";

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
  embeddedActiveAreaEffects: ActiveAreaEffect[],
  embeddedSelectedCell: Coordinate | null
): void {
  gfx.clear();

  const obstacleCellMap = buildObstacleCellMap(obstacles);
  const movementSet = new Set(movementPreview.map(coordKey));
  const targetingSet = new Set(
    [...targetingPreview, ...embeddedPreview].map(coordKey)
  );
  const activeAreaCells = embeddedActiveAreaEffects.flatMap((effect) =>
    effect.affectedCells.map((cell) => ({
      cell,
      effectKind: effect.effectKind,
    }))
  );

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
    else if (obs.movementCostMultiplier > 1) {
      color = C.obsDifficultTerrain;
      alpha = C.obsDifficultTerrainAlpha;
    } else continue;

    gfx.rect(x, y, w, h).fill({ color, alpha });
    if (obs.cover === "threeQuarters") {
      gfx.rect(x, y, w, h).stroke({ width: 1.5, color: 0xffaa44, alpha: 0.65 });
    } else if (obs.cover === "half") {
      gfx.rect(x, y, w, h).stroke({ width: 1, color: 0xffe08c, alpha: 0.55 });
    } else if (obs.movementCostMultiplier > 1) {
      gfx
        .rect(x + 2, y + 2, w - 4, h - 4)
        .stroke({ width: 1, color: 0xd4a870, alpha: 0.6 });
    }
  }

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

  for (const entry of activeAreaCells) {
    const coordHash = coordKey(entry.cell);
    if (obstacleCellMap.has(coordHash) || movementSet.has(coordHash)) continue;
    const { x, y, w, h } = cellRect(
      entry.cell.x,
      entry.cell.y,
      cal,
      gridW,
      gridH,
      canvasW,
      canvasH
    );
    const isHazard = entry.effectKind === "hazard";
    const color = isHazard ? 0xdc2626 : 0x94a3b8;
    gfx.rect(x, y, w, h).fill({ color, alpha: isHazard ? 0.22 : 0.2 });
    gfx.rect(x + 2, y + 2, w - 4, h - 4).stroke({
      width: 1.2,
      color: isHazard ? 0xfca5a5 : 0xe2e8f0,
      alpha: 0.65,
    });
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

const ELEVATION_COLORS: Record<number, number> = {
  0: 0x4b5563,
  3: 0x3b82f6,
  6: 0x8b5cf6,
  9: 0xec4899,
  12: 0xef4444,
};

function getElevationColor(meters: number): number {
  // Find the closest preset color
  const keys = Object.keys(ELEVATION_COLORS).map(Number).sort((a, b) => a - b);
  let color = ELEVATION_COLORS[0];
  for (const key of keys) {
    if (meters >= key) {
      color = ELEVATION_COLORS[key];
    }
  }
  return color;
}

export function drawCellElevationBadges(
  gfx: Graphics,
  cal: GridCalibration,
  gridW: number,
  gridH: number,
  canvasW: number,
  canvasH: number,
  cellElevations: CellElevation[]
): void {
  for (const entry of cellElevations) {
    if (entry.elevationMeters <= 0) continue;

    const { x, y, w, h } = cellRect(entry.cell.x, entry.cell.y, cal, gridW, gridH, canvasW, canvasH);
    const badgeSize = Math.max(6, Math.min(w, h) * 0.25);
    const color = getElevationColor(entry.elevationMeters);

    // Small colored square in the top-right corner
    gfx.rect(x + w - badgeSize - 2, y + 2, badgeSize, badgeSize)
      .fill({ color, alpha: 0.85 })
      .stroke({ width: 1, color: 0x000000, alpha: 0.4 });
  }
}
