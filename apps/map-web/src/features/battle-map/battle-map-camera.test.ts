import { describe, it, expect } from "vitest";
import { createCamera, MIN_SCALE, MAX_SCALE } from "./battle-map-camera";

function setup(width = 800, height = 600) {
  const world = {
    scale: { x: 1, y: 1, set(s: number) { this.x = s; this.y = s; } },
    position: { x: 0, y: 0, set(x: number, y: number) { this.x = x; this.y = y; } },
  };
  const app = { screen: { width, height } };
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const camera = createCamera(app as any, world as any);
  return { camera, world };
}

describe("battle-map-camera", () => {
  it("starts at the fit view (scale 1, identity mapping)", () => {
    const { camera } = setup();
    expect(camera.getScale()).toBe(1);
    expect(camera.screenToWorld(100, 50)).toEqual({ x: 100, y: 50 });
  });

  it("keeps the point under the cursor fixed while zooming", () => {
    const { camera } = setup();
    const before = camera.screenToWorld(400, 300);
    camera.zoomAt(400, 300, 2);
    expect(camera.getScale()).toBe(2);
    const after = camera.screenToWorld(400, 300);
    expect(after.x).toBeCloseTo(before.x);
    expect(after.y).toBeCloseTo(before.y);
  });

  it("clamps scale to MAX_SCALE", () => {
    const { camera } = setup();
    camera.zoomCenter(100);
    expect(camera.getScale()).toBe(MAX_SCALE);
  });

  it("never zooms below MIN_SCALE", () => {
    const { camera } = setup();
    camera.zoomCenter(0.01);
    expect(camera.getScale()).toBe(MIN_SCALE);
  });

  it("ignores panning at fit scale (clamped to no offset)", () => {
    const { camera } = setup();
    camera.panBy(100, 100);
    expect(camera.screenToWorld(0, 0)).toEqual({ x: 0, y: 0 });
  });

  it("pans within bounds when zoomed in", () => {
    const { camera } = setup();
    camera.zoomAt(0, 0, 2);
    camera.panBy(-100, -50);
    expect(camera.screenToWorld(0, 0)).toEqual({ x: 50, y: 25 });
  });

  it("clamps pan so the map cannot be dragged off-screen", () => {
    const { camera } = setup();
    camera.zoomAt(0, 0, 2);
    camera.panBy(1000, 1000); // try to overshoot the positive bound
    expect(camera.screenToWorld(0, 0)).toEqual({ x: 0, y: 0 });
  });

  it("does nothing while locked", () => {
    const { camera } = setup();
    camera.setLocked(true);
    camera.zoomCenter(2);
    camera.panBy(100, 100);
    expect(camera.getScale()).toBe(1);
  });

  it("reset returns to the fit view", () => {
    const { camera } = setup();
    camera.zoomAt(0, 0, 3);
    camera.reset();
    expect(camera.getScale()).toBe(1);
    expect(camera.screenToWorld(123, 45)).toEqual({ x: 123, y: 45 });
  });

  it("notifies onChange subscribers", () => {
    const { camera } = setup();
    let calls = 0;
    camera.setOnChange(() => { calls += 1; });
    camera.zoomCenter(2);
    expect(calls).toBeGreaterThan(0);
  });

  it("syncs the world container transform", () => {
    const { camera, world } = setup();
    camera.zoomAt(0, 0, 2);
    expect(world.scale.x).toBe(2);
    expect(world.position.x).toBe(0);
  });
});
