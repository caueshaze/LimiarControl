import type { Application, Container } from "pixi.js";

export const MIN_SCALE = 1;
export const MAX_SCALE = 6;

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

export interface BattleMapCamera {
  /** Zoom keeping the world point under (globalX, globalY) fixed on screen. */
  zoomAt(globalX: number, globalY: number, factor: number): void;
  /** Zoom around the current viewport center. */
  zoomCenter(factor: number): void;
  /** Translate the world by a screen-space delta. */
  panBy(dx: number, dy: number): void;
  /** Reset to the fit view (scale 1, no offset). */
  reset(): void;
  getScale(): number;
  /** Convert a stage-global point to world (unscaled, screen-sized) coordinates. */
  screenToWorld(globalX: number, globalY: number): { x: number; y: number };
  setLocked(locked: boolean): void;
  isLocked(): boolean;
  /** Re-clamp after a viewport resize. */
  refresh(): void;
  /** Subscribe to camera changes (scale/position). */
  setOnChange(cb: (() => void) | null): void;
}

/**
 * Hand-rolled camera over a single `world` Container. The world layers are drawn
 * at screen size (base scale 1), so the camera is transparent to the renderers
 * and to `pixelToGrid`/`cellRect`: only pointer input is pre-transformed via
 * `screenToWorld`. State lives here (not in the store) so pan/zoom never trigger
 * React re-renders or full redraws — the Pixi ticker re-renders the transform.
 */
export function createCamera(app: Application, world: Container): BattleMapCamera {
  let scale = 1;
  let x = 0;
  let y = 0;
  let locked = false;
  let onChange: (() => void) | null = null;

  function clampState(): void {
    scale = clamp(scale, MIN_SCALE, MAX_SCALE);
    const sw = app.screen.width;
    const sh = app.screen.height;
    // World is drawn at screen size, so its scaled width is sw*scale. Keep it
    // from being dragged entirely off-screen: position in [screen - screen*scale, 0].
    x = clamp(x, sw - sw * scale, 0);
    y = clamp(y, sh - sh * scale, 0);
  }

  function apply(): void {
    clampState();
    world.scale.set(scale);
    world.position.set(x, y);
    onChange?.();
  }

  return {
    zoomAt(globalX, globalY, factor) {
      if (locked) return;
      const prevScale = scale;
      const next = clamp(scale * factor, MIN_SCALE, MAX_SCALE);
      if (next === prevScale) return;
      // Keep the world point under the cursor fixed: wx = (g - pos) / scale.
      const wx = (globalX - x) / prevScale;
      const wy = (globalY - y) / prevScale;
      scale = next;
      x = globalX - wx * scale;
      y = globalY - wy * scale;
      apply();
    },
    zoomCenter(factor) {
      this.zoomAt(app.screen.width / 2, app.screen.height / 2, factor);
    },
    panBy(dx, dy) {
      if (locked) return;
      x += dx;
      y += dy;
      apply();
    },
    reset() {
      scale = 1;
      x = 0;
      y = 0;
      apply();
    },
    getScale() {
      return scale;
    },
    screenToWorld(globalX, globalY) {
      return { x: (globalX - x) / scale, y: (globalY - y) / scale };
    },
    setLocked(value) {
      locked = value;
    },
    isLocked() {
      return locked;
    },
    refresh() {
      apply();
    },
    setOnChange(cb) {
      onChange = cb;
    },
  };
}
