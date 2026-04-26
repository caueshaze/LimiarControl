import { describe, expect, it, vi } from "vitest";
import {
  buildInstanceSpatialValidations,
  buildSingleTargetSpatialValidations,
  buildTargetSpatialValidationFromPreview,
  buildUniqueTargetRefIds,
  createPreviewRequestGate,
  fetchPreviewValidationsByTargetRefId,
} from "./spellPreviewSpatialValidations";

describe("spellPreviewSpatialValidations", () => {
  it("maps no_line_of_sight to blocked LoS semantics", () => {
    expect(
      buildTargetSpatialValidationFromPreview({
        diagnostics: {
          isValid: false,
          failureReasons: ["no_line_of_sight"],
          checks: { in_range: true },
          metadata: {},
        },
        targetRefId: "enemy-1",
      }),
    ).toMatchObject({
      targetRefId: "enemy-1",
      inRange: true,
      hasLineOfSight: false,
      hasLineOfEffect: null,
      unavailableReason: null,
    });
  });

  it("maps full_cover to blocked LoE only in preview normalization", () => {
    expect(
      buildTargetSpatialValidationFromPreview({
        diagnostics: {
          isValid: false,
          failureReasons: ["full_cover"],
          checks: { in_range: true },
          metadata: {},
        },
        targetRefId: "enemy-1",
      }),
    ).toMatchObject({
      targetRefId: "enemy-1",
      inRange: true,
      hasLineOfSight: true,
      hasLineOfEffect: false,
    });
  });

  it("builds single-target unavailable validation when preview hook errors", () => {
    expect(
      buildSingleTargetSpatialValidations(
        {
          loading: false,
          error: "preview failed",
          diagnostics: null,
          distanceMeters: null,
          normalRangeMeters: null,
          maxRangeMeters: null,
          rangeStatus: "unknown",
          hasDisadvantage: false,
          failureReasons: [],
        },
        "enemy-1",
      ),
    ).toEqual([
      {
        targetRefId: "enemy-1",
        inRange: null,
        hasLineOfSight: null,
        hasLineOfEffect: null,
        unavailableReason: "missing_map_data",
      },
    ]);
  });

  it("deduplicates repeated targetRefIds before preview fanout", () => {
    expect(
      buildUniqueTargetRefIds([
        "enemy-1",
        "enemy-2",
        "enemy-1",
        null,
        "enemy-2",
        "enemy-3",
      ]),
    ).toEqual(["enemy-1", "enemy-2", "enemy-3"]);
  });

  it("calls preview once per unique targetRefId and localizes partial failures", async () => {
    const previewAction = vi.fn(async (_sessionId: string, payload: { target_ref_id: string }) => {
      if (payload.target_ref_id === "enemy-2") {
        throw new Error("preview failed");
      }
      return {
        diagnostics: {
          isValid: true,
          failureReasons: [],
          checks: { in_range: true },
          metadata: {},
        },
        effectiveReachCells: 24,
        aoeCells: [],
      };
    });

    const validations = await fetchPreviewValidationsByTargetRefId({
      actorRefId: "player:1",
      previewAction,
      rangeMeters: 36,
      sessionId: "session-1",
      targetRefIds: ["enemy-1", "enemy-2", "enemy-1"],
    });

    expect(previewAction).toHaveBeenCalledTimes(2);
    expect(validations.get("enemy-1")).toMatchObject({
      targetRefId: "enemy-1",
      inRange: true,
      unavailableReason: null,
    });
    expect(validations.get("enemy-2")).toMatchObject({
      targetRefId: "enemy-2",
      unavailableReason: "missing_map_data",
    });
  });

  it("fans per-target validations back into per-instance validations", () => {
    const validations = new Map([
      [
        "enemy-1",
        {
          targetRefId: "enemy-1",
          inRange: true,
          hasLineOfSight: null,
          hasLineOfEffect: null,
          unavailableReason: null,
        },
      ],
      [
        "enemy-2",
        {
          targetRefId: "enemy-2",
          inRange: null,
          hasLineOfSight: null,
          hasLineOfEffect: null,
          unavailableReason: "missing_map_data" as const,
        },
      ],
    ]);

    expect(
      buildInstanceSpatialValidations(
        [
          { instance_index: 1, target_ref_id: "enemy-1" },
          { instance_index: 2, target_ref_id: "enemy-2" },
          { instance_index: 3, target_ref_id: "enemy-2" },
        ],
        validations,
      ),
    ).toEqual([
      {
        instanceIndex: 1,
        targetRefId: "enemy-1",
        inRange: true,
        hasLineOfSight: null,
        hasLineOfEffect: null,
        unavailableReason: null,
      },
      {
        instanceIndex: 2,
        targetRefId: "enemy-2",
        inRange: null,
        hasLineOfSight: null,
        hasLineOfEffect: null,
        unavailableReason: "missing_map_data",
      },
      {
        instanceIndex: 3,
        targetRefId: "enemy-2",
        inRange: null,
        hasLineOfSight: null,
        hasLineOfEffect: null,
        unavailableReason: "missing_map_data",
      },
    ]);
  });

  it("ignores stale request ids via the request gate", () => {
    const gate = createPreviewRequestGate();
    const first = gate.issue();
    const second = gate.issue();

    expect(gate.isCurrent(first)).toBe(false);
    expect(gate.isCurrent(second)).toBe(true);
  });
});
