import {
  Assets,
  Container,
  type FederatedPointerEvent,
  Graphics,
  Sprite,
  Text,
  TextStyle,
  Texture
} from "pixi.js";
import type {
  GridCalibration,
  EdgeDirection,
  Token
} from "@limiarmap/shared-contracts";
import { C } from "./constants";
import type { GridEditInteractionMode } from "./types";
import { getTokenBadgeLabel, cellRect, resolveTokenImageUrl } from "./utils";
import { getTokenFootprint } from "@limiarmap/tactical-engine";
import { getConditionIndicators } from "../conditions/condition-indicators";

// Token portraits load asynchronously via Assets. Cache resolved textures so
// repeated redraws are synchronous, and dedupe in-flight loads by URL. Failed
// loads are remembered so we don't retry (and re-warn) every frame.
const tokenTextureCache = new Map<string, Texture>();
const tokenTextureLoading = new Map<string, Promise<void>>();
const tokenTextureFailed = new Set<string>();

/**
 * Assign the portrait texture to `sprite`, loading it on first use. The Pixi
 * ticker re-renders continuously, so the sprite updates once the load resolves
 * even without a fresh draw pass. Until then the colored base disc shows.
 */
function applyTokenPortrait(sprite: Sprite, url: string, diameter: number): void {
  const assign = (texture: Texture): void => {
    sprite.texture = texture;
    sprite.width = diameter;
    sprite.height = diameter;
  };
  const cached = tokenTextureCache.get(url);
  if (cached) {
    assign(cached);
    return;
  }
  if (tokenTextureFailed.has(url)) return;
  if (!tokenTextureLoading.has(url)) {
    // Force the texture parser: the proxied URL ends in `/asset` (the real
    // extension is in the query string), so Pixi's format auto-detection fails.
    const loading = Assets.load({ src: url, parser: "loadTextures" })
      .then((texture: Texture) => {
        tokenTextureCache.set(url, texture);
      })
      .catch(() => {
        tokenTextureFailed.add(url);
      })
      .finally(() => {
        tokenTextureLoading.delete(url);
      });
    tokenTextureLoading.set(url, loading);
  }
  void tokenTextureLoading.get(url)?.then(() => {
    const texture = tokenTextureCache.get(url);
    if (texture) assign(texture);
  });
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
  activeCombatantId: string | null | undefined,
  sessionId: string
): void {
  container.removeChildren();

  for (const token of tokens) {
    const footprint = getTokenFootprint(token);
    const { x, y, w, h } = cellRect(
      token.position.x,
      token.position.y,
      cal,
      gridW,
      gridH,
      canvasW,
      canvasH
    );
    const tokenW = w * footprint.width;
    const tokenH = h * footprint.height;
    const cx = x + tokenW / 2;
    const cy = y + tokenH / 2;
    const radius = Math.min(tokenW, tokenH) * 0.36;

    const isSelected =
      token.id === selectedTokenId ||
      (selectedCombatantId != null &&
        token.combatantId === selectedCombatantId);
    const isActive =
      token.combatantId != null && token.combatantId === activeCombatantId;

    const defaultBg =
      token.controllerType === "player"
        ? C.tokenPlayer
        : token.controllerType === "gm"
          ? C.tokenGm
          : C.tokenNeutral;
    const bg = token.color
      ? parseInt(token.color.replace("#", "").slice(0, 6), 16)
      : defaultBg;
    const borderColor = isActive
      ? C.tokenBorderActive
      : isSelected
        ? C.tokenBorderSelected
        : C.tokenBorderNormal;
    const borderAlpha = isActive || isSelected ? 1 : C.tokenBorderNormalAlpha;
    const borderWidth = isActive || isSelected ? 3 : 1.5;

    // Base disc — solid color (also the fallback when an image fails to load).
    const gfx = new Graphics();
    gfx.circle(0, 0, radius).fill({ color: bg });
    gfx.x = cx;
    gfx.y = cy;
    container.addChild(gfx);

    if (token.imageUrl) {
      // Token portrait chosen at onboarding, clipped to the disc. Starts empty
      // (color disc shows through) and fills in once the texture loads.
      const sprite = new Sprite(Texture.EMPTY);
      sprite.anchor.set(0.5);
      sprite.x = cx;
      sprite.y = cy;
      const mask = new Graphics();
      mask.circle(cx, cy, radius).fill({ color: 0xffffff });
      sprite.mask = mask;
      container.addChild(mask);
      container.addChild(sprite);
      applyTokenPortrait(sprite, resolveTokenImageUrl(sessionId, token.imageUrl), radius * 2);
    } else {
      const label = getTokenBadgeLabel(token.label);
      const fontSize = Math.max(8, Math.min(14, radius * 0.8));
      const text = new Text({
        text: label,
        style: new TextStyle({ fill: "#ffffff", fontSize, fontWeight: "bold" })
      });
      text.anchor.set(0.5);
      text.x = cx;
      text.y = cy;
      container.addChild(text);
    }

    // Border ring on top of the fill/portrait (active/selected/normal states).
    const ring = new Graphics();
    ring
      .circle(cx, cy, radius)
      .stroke({ width: borderWidth, color: borderColor, alpha: borderAlpha });
    container.addChild(ring);

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
  edgeDirection?: EdgeDirection,
  gridEditStatus?: string
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

  if (gridEditStatus && isEditMode) {
    const statusLabel = new Text({
      text: gridEditStatus,
      style: new TextStyle({ fill: "#8cbcff", fontSize: 10 })
    });
    const statusBgW = statusLabel.width + 16;
    const statusBgX = canvasW - statusBgW - 8;
    statusLabel.x = statusBgX + 8;
    statusLabel.y = 30;
    const statusBg = new Graphics();
    statusBg
      .roundRect(statusBgX, 27, statusBgW, statusLabel.height + 8, 4)
      .fill({ color: 0, alpha: 0.72 });
    statusBg
      .roundRect(statusBgX, 27, statusBgW, statusLabel.height + 8, 4)
      .stroke({ width: 1, color: 0x5ca9ff, alpha: 0.3 });
    container.addChild(statusBg);
    container.addChild(statusLabel);
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
