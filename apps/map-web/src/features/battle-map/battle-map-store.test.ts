import { beforeEach, describe, expect, it } from "vitest";
import { battleMapStore } from "./battle-map-store";

describe("battleMapStore two-point calibration flow", () => {
  beforeEach(() => {
    battleMapStore.cancelGridEdit();
  });

  it("captures first and second points while grid edit is active", () => {
    battleMapStore.startGridEdit(
      { x: 0, y: 0, width: 1, height: 1 },
      20,
      14
    );

    battleMapStore.startTwoPointGridCalibration();
    battleMapStore.captureTwoPointGridCalibrationPoint({ x: 100, y: 120 });
    battleMapStore.captureTwoPointGridCalibrationPoint({ x: 420, y: 540 });

    const state = battleMapStore.getState();
    expect(state.isGridEditMode).toBe(true);
    expect(state.isTwoPointCalibrationMode).toBe(true);
    expect(state.twoPointCalibrationFirstPoint).toEqual({ x: 100, y: 120 });
    expect(state.twoPointCalibrationSecondPoint).toEqual({ x: 420, y: 540 });
  });

  it("clears the temporary two-point state on cancel", () => {
    battleMapStore.startGridEdit(
      { x: 0.1, y: 0.1, width: 0.8, height: 0.8 },
      10,
      10
    );
    battleMapStore.startTwoPointGridCalibration();
    battleMapStore.captureTwoPointGridCalibrationPoint({ x: 50, y: 50 });

    battleMapStore.cancelTwoPointGridCalibration();

    const state = battleMapStore.getState();
    expect(state.isGridEditMode).toBe(true);
    expect(state.isTwoPointCalibrationMode).toBe(false);
    expect(state.twoPointCalibrationFirstPoint).toBeUndefined();
    expect(state.twoPointCalibrationSecondPoint).toBeUndefined();
  });
});
