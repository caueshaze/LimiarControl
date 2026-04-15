import { describe, expect, it, vi, beforeEach } from "vitest";
import { combatRepo } from "../../../shared/api/combatRepo";
import { http } from "../../../shared/api/http";
import {
  canConfirmMovementPreview,
  getMovementPreviewReasonLabel,
  pathCostUnitsToMeters,
} from "./useMovementPreview";

vi.mock("../../../shared/api/http", () => ({
  http: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    del: vi.fn(),
  },
}));

describe("movement preview helpers", () => {
  it("converts path cost units to meters", () => {
    expect(pathCostUnitsToMeters(5)).toBe(1.5);
    expect(pathCostUnitsToMeters(15)).toBe(4.5);
  });

  it("maps invalid preview reasons to a clear label", () => {
    expect(getMovementPreviewReasonLabel("movement_budget_exceeded")).toContain("deslocamento restante");
    expect(getMovementPreviewReasonLabel("blocked_path")).toContain("bloqueado");
  });

  it("disables movement confirmation when preview is invalid", () => {
    expect(
      canConfirmMovementPreview(
        {
          is_valid: false,
          reason: "blocked_path",
          destination_cell: { x: 3, y: 3 },
          path: [],
          path_cost_units: 0,
          movement_budget: 30,
          movement_speed_cells: 6,
          remaining_budget: 30,
        },
        false,
      ),
    ).toBe(false);
  });

  it("enables movement confirmation only when preview is valid and settled", () => {
    expect(
      canConfirmMovementPreview(
        {
          is_valid: true,
          reason: null,
          destination_cell: { x: 3, y: 3 },
          path: [{ x: 2, y: 2 }, { x: 3, y: 3 }],
          path_cost_units: 10,
          movement_budget: 30,
          movement_speed_cells: 6,
          remaining_budget: 20,
        },
        false,
      ),
    ).toBe(true);
    expect(
      canConfirmMovementPreview(
        {
          is_valid: true,
          reason: null,
          destination_cell: { x: 3, y: 3 },
          path: [],
          path_cost_units: 10,
          movement_budget: 30,
          movement_speed_cells: 6,
          remaining_budget: 20,
        },
        true,
      ),
    ).toBe(false);
  });
});

describe("combatRepo movement requests", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("posts movement preview requests to the movement preview endpoint", async () => {
    vi.mocked(http.post).mockResolvedValueOnce({
      is_valid: true,
      destination_cell: { x: 4, y: 4 },
      path: [],
      path_cost_units: 0,
      movement_budget: 30,
      movement_speed_cells: 6,
      remaining_budget: 30,
    } as never);

    await combatRepo.previewMovement("session-1", {
      actor_participant_id: "participant-1",
      destination_cell: { x: 4, y: 4 },
    });

    expect(http.post).toHaveBeenCalledWith(
      "/sessions/session-1/combat/action/move/preview",
      {
        actor_participant_id: "participant-1",
        destination_cell: { x: 4, y: 4 },
      },
    );
  });

  it("posts confirmed movement to the correct endpoint", async () => {
    vi.mocked(http.post).mockResolvedValueOnce({
      is_valid: true,
      destination_cell: { x: 5, y: 2 },
      path: [{ x: 5, y: 2 }],
      path_cost_units: 5,
      movement_budget: 30,
      movement_speed_cells: 6,
      remaining_budget: 25,
    } as never);

    await combatRepo.confirmMovement("session-2", {
      actor_participant_id: "participant-2",
      destination_cell: { x: 5, y: 2 },
    });

    expect(http.post).toHaveBeenCalledWith(
      "/sessions/session-2/combat/action/move",
      {
        actor_participant_id: "participant-2",
        destination_cell: { x: 5, y: 2 },
      },
    );
  });
});
