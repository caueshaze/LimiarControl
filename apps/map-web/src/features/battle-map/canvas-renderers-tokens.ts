import {
  Container,
  type FederatedPointerEvent,
  Graphics,
  Text,
  TextStyle
} from "pixi.js";
import type {
  GridCalibration,
  EdgeDirection,
  Token
} from "@limiarmap/shared-contracts";
import { C } from "./constants";
import type { GridEditInteractionMode } from "./types";
import { getTokenBadgeLabel, cellRect } from "./utils";
import { getConditionIndicators } from "../conditions/condition-indicators";

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

    const conditions = token.conditions ?? [];
    const isInvisible = conditions.includes("invisible");

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

  const badge = new Text({
    text: "Modo editar grid",
    style: new TextStyle({ fill: "#9ed0ff", fontSize: 11 })
  });
  badge.x = gx + 10;
  badge.y = gy + 6;
  container.addChild(badge);

  const moveArea = new Graphics();
  moveArea.rect(gx, gy, gw, gh).fill({ color: 0, alpha: 0 });
  moveArea.eventMode = "static";
  moveArea.cursor = "move";
  moveArea.on("pointerdown", (e: FederatedPointerEvent) => {
    e.stopPropagation();
    onHandleDown("move", e.nativeEvent.clientX, e.nativeEvent.clientY);
  });
  container.addChildAt(moveArea, 0);

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
