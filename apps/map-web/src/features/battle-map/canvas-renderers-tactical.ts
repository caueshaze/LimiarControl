import {
  Container,
  Graphics,
  Text,
  TextStyle
} from "pixi.js";
import type {
  Coordinate,
  GridCalibration,
  Token
} from "@limiarmap/shared-contracts";
import type {
  TacticalPreviewState,
  SpellMapHighlight,
  SpellMapHighlightStatus,
  GridCalibrationPixelPoint
} from "./battle-map-store";
import type { FailureExplanation } from "../targeting/diagnostics-to-explanation";
import { C } from "./constants";
import { cellRect } from "./utils";

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
  for (const coord of reachableCells) {
    const { x, y, w, h } = cellRect(coord.x, coord.y, cal, gridW, gridH, canvasW, canvasH);
    gfx.rect(x, y, w, h).fill({ color: C.previewReach, alpha: C.previewReachAlpha });
  }

  for (const coord of aoeCells) {
    const { x, y, w, h } = cellRect(coord.x, coord.y, cal, gridW, gridH, canvasW, canvasH);
    gfx.rect(x, y, w, h).fill({ color: C.previewAoe, alpha: C.previewAoeAlpha });
    gfx.rect(x, y, w, h).stroke({ width: 1, color: C.previewAoeBorder, alpha: C.previewAoeBorderAlpha });
  }
}

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

function drawPointMarker(
  container: Container,
  point: GridCalibrationPixelPoint,
  label: string,
  fillColor: number,
  strokeColor: number,
  imageWidth: number,
  imageHeight: number,
  canvasW: number,
  canvasH: number
): void {
  const x = (point.x / imageWidth) * canvasW;
  const y = (point.y / imageHeight) * canvasH;

  const marker = new Graphics();
  marker.circle(0, 0, 10).fill({ color: fillColor, alpha: 0.92 });
  marker.circle(0, 0, 10).stroke({ width: 2, color: strokeColor, alpha: 0.95 });
  marker.x = x;
  marker.y = y;
  container.addChild(marker);

  const badge = new Text({
    text: label,
    style: new TextStyle({
      fill: "#ffffff",
      fontSize: 11,
      fontWeight: "bold",
    }),
  });
  badge.anchor.set(0.5);
  badge.x = x;
  badge.y = y - 0.5;
  container.addChild(badge);
}

export function drawTwoPointCalibrationOverlay(
  container: Container,
  firstPoint: GridCalibrationPixelPoint | undefined,
  secondPoint: GridCalibrationPixelPoint | undefined,
  imageWidth: number,
  imageHeight: number,
  canvasW: number,
  canvasH: number
): void {
  container.removeChildren();

  if (!firstPoint || imageWidth <= 0 || imageHeight <= 0) return;

  const firstX = (firstPoint.x / imageWidth) * canvasW;
  const firstY = (firstPoint.y / imageHeight) * canvasH;

  if (secondPoint) {
    const secondX = (secondPoint.x / imageWidth) * canvasW;
    const secondY = (secondPoint.y / imageHeight) * canvasH;
    const minX = Math.min(firstX, secondX);
    const minY = Math.min(firstY, secondY);
    const width = Math.abs(secondX - firstX);
    const height = Math.abs(secondY - firstY);

    const rect = new Graphics();
    rect.rect(minX, minY, width, height).fill({ color: 0x5ca9ff, alpha: 0.08 });
    rect.rect(minX, minY, width, height).stroke({
      width: 2,
      color: 0x8cbcff,
      alpha: 0.9,
    });
    rect.moveTo(firstX, firstY).lineTo(secondX, secondY).stroke({
      width: 1.5,
      color: 0xb9d8ff,
      alpha: 0.7,
    });
    container.addChild(rect);
  }

  drawPointMarker(
    container,
    firstPoint,
    "1",
    0x22c55e,
    0xdcfce7,
    imageWidth,
    imageHeight,
    canvasW,
    canvasH
  );

  if (secondPoint) {
    drawPointMarker(
      container,
      secondPoint,
      "2",
      0xef4444,
      0xfee2e2,
      imageWidth,
      imageHeight,
      canvasW,
      canvasH
    );
  }
}

const STATUS_PRIORITY: Record<SpellMapHighlightStatus, number> = {
  invalid: 3,
  partial: 2,
  valid: 1,
  unknown: 0,
};

const resolveRingStyle = (status: SpellMapHighlightStatus): { color: number; alpha: number } | null => {
  switch (status) {
    case "valid":
      return { color: C.previewTargetValid, alpha: C.previewTargetValidAlpha };
    case "invalid":
      return { color: C.previewTargetInvalid, alpha: C.previewTargetInvalidAlpha };
    case "partial":
      return { color: C.spellHighlightPartial, alpha: C.spellHighlightPartialAlpha };
    case "unknown":
      return null;
  }
  return null;
};

export function drawSpellHighlightRings(
  container: Container,
  tokens: Token[],
  cal: GridCalibration,
  gridW: number,
  gridH: number,
  canvasW: number,
  canvasH: number,
  highlights: SpellMapHighlight[],
): void {
  container.removeChildren();

  // Group highlights by targetRefId, resolving worst status per token
  const statusByRef = new Map<string, SpellMapHighlightStatus>();
  for (const h of highlights) {
    if (!h.targetRefId) continue;
    const current = statusByRef.get(h.targetRefId);
    if (!current || STATUS_PRIORITY[h.status] > STATUS_PRIORITY[current]) {
      statusByRef.set(h.targetRefId, h.status);
    }
  }

  // TODO(spell-preview): area-cell highlights are emitted by buildSpellMapPreviewHighlights
  // but this renderer only draws token rings (highlights with targetRefId). Cell footprint
  // rendering should be added as a dedicated pass in drawCellFills, not here.
  for (const [refId, status] of statusByRef) {
    const style = resolveRingStyle(status);
    if (!style) continue;

    const token = tokens.find((t) => t.combatantId === refId);
    if (!token) continue;

    const { x, y, w, h } = cellRect(token.position.x, token.position.y, cal, gridW, gridH, canvasW, canvasH);
    const cx = x + w / 2;
    const cy = y + h / 2;
    const radius = Math.min(w, h) * 0.36;

    // TODO(perf): consider reusing Graphics instances via pool instead of recreating
    // per-token per-redraw for encounters with many highlighted targets.
    const ring = new Graphics();
    // Slightly larger + thinner than tactical overlay ring to distinguish preview from selection
    ring.circle(0, 0, radius + 7).stroke({ width: 2, color: style.color, alpha: style.alpha });
    ring.x = cx;
    ring.y = cy;
    container.addChild(ring);
  }
}

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

  const primaryText = new Text({
    text: explanation.primary,
    style: new TextStyle({
      fill: style.textColor,
      fontSize: 11,
      fontWeight: "bold",
    }),
  });

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
