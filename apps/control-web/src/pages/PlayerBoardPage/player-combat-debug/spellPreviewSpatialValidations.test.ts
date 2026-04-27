import { describe, expect, it, vi } from "vitest";
import {
  buildAreaSpatialValidationFromPreview,
  buildInstanceSpatialValidations,
  buildSingleTargetSpatialValidations,
  buildSpellCoverPreviewFromDiagnostics,
  buildSpellPreviewFanoutKey,
  buildTargetSpatialValidationFromPreview,
  buildUniqueTargetRefIds,
  createPreviewRequestGate,
  fetchAreaSpatialValidation,
  fetchPreviewValidationsByTargetRefId,
  fetchPreviewValidationsWithCache,
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
        cover: null,
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

const okResponse = {
  diagnostics: { isValid: true, failureReasons: [], checks: { in_range: true }, metadata: {} },
  effectiveReachCells: 24,
  aoeCells: [],
};

const baseArgs = {
  actorRefId: "player:1",
  rangeMeters: 36,
  sessionId: "session-1",
};

describe("fetchPreviewValidationsWithCache", () => {
  it("cache hit: segunda chamada com mesma chave não dispara request real", async () => {
    const cache = new Map();
    const inFlight = new Map();
    const previewAction = vi.fn().mockResolvedValue(okResponse);
    const buildKey = (t: string) => `ctx|${t}`;

    await fetchPreviewValidationsWithCache({ ...baseArgs, buildKey, cache, inFlight, previewAction, targetRefIds: ["enemy-1"] });
    expect(previewAction).toHaveBeenCalledTimes(1);

    await fetchPreviewValidationsWithCache({ ...baseArgs, buildKey, cache, inFlight, previewAction, targetRefIds: ["enemy-1"] });
    expect(previewAction).toHaveBeenCalledTimes(1);
  });

  it("in-flight dedupe: duas chamadas simultâneas com mesma chave disparam apenas uma request", async () => {
    const cache = new Map();
    const inFlight = new Map();
    let resolveRequest!: (v: typeof okResponse) => void;
    const requestPromise = new Promise<typeof okResponse>((res) => { resolveRequest = res; });
    const previewAction = vi.fn(() => requestPromise);
    const buildKey = (t: string) => `ctx|${t}`;

    const p1 = fetchPreviewValidationsWithCache({ ...baseArgs, buildKey, cache, inFlight, previewAction, targetRefIds: ["enemy-1"] });
    const p2 = fetchPreviewValidationsWithCache({ ...baseArgs, buildKey, cache, inFlight, previewAction, targetRefIds: ["enemy-1"] });

    resolveRequest(okResponse);
    const [r1, r2] = await Promise.all([p1, p2]);

    expect(previewAction).toHaveBeenCalledTimes(1);
    expect(r1.get("enemy-1")?.inRange).toBe(true);
    expect(r2.get("enemy-1")?.inRange).toBe(true);
  });

  it("cache invalidation por slot: chave diferente re-fetcha", async () => {
    const cache = new Map();
    const inFlight = new Map();
    const previewAction = vi.fn().mockResolvedValue(okResponse);

    await fetchPreviewValidationsWithCache({ ...baseArgs, buildKey: (t) => `slot1|${t}`, cache, inFlight, previewAction, targetRefIds: ["enemy-1"] });
    await fetchPreviewValidationsWithCache({ ...baseArgs, buildKey: (t) => `slot2|${t}`, cache, inFlight, previewAction, targetRefIds: ["enemy-1"] });

    expect(previewAction).toHaveBeenCalledTimes(2);
  });

  it("cache invalidation por spell: chave diferente re-fetcha", async () => {
    const cache = new Map();
    const inFlight = new Map();
    const previewAction = vi.fn().mockResolvedValue(okResponse);

    await fetchPreviewValidationsWithCache({ ...baseArgs, buildKey: (t) => `spellA|${t}`, cache, inFlight, previewAction, targetRefIds: ["enemy-1"] });
    await fetchPreviewValidationsWithCache({ ...baseArgs, buildKey: (t) => `spellB|${t}`, cache, inFlight, previewAction, targetRefIds: ["enemy-1"] });

    expect(previewAction).toHaveBeenCalledTimes(2);
  });

  it("falha não envenena cache: segunda chamada com mesma chave após falha dispara nova request", async () => {
    const cache = new Map();
    const inFlight = new Map();
    const buildKey = (t: string) => `ctx|${t}`;
    const previewAction = vi.fn()
      .mockRejectedValueOnce(new Error("network error"))
      .mockResolvedValueOnce(okResponse);

    const first = await fetchPreviewValidationsWithCache({ ...baseArgs, buildKey, cache, inFlight, previewAction, targetRefIds: ["enemy-1"] });
    expect(first.get("enemy-1")?.unavailableReason).toBe("missing_map_data");
    expect(cache.size).toBe(0);

    const second = await fetchPreviewValidationsWithCache({ ...baseArgs, buildKey, cache, inFlight, previewAction, targetRefIds: ["enemy-1"] });
    expect(second.get("enemy-1")?.unavailableReason).toBeNull();
    expect(previewAction).toHaveBeenCalledTimes(2);
  });

  it("falha parcial não afeta outros targets: target ok vai ao cache, target falho não", async () => {
    const cache = new Map();
    const inFlight = new Map();
    const buildKey = (t: string) => `ctx|${t}`;
    const previewAction = vi.fn(async (_: string, payload: { target_ref_id: string }) => {
      if (payload.target_ref_id === "enemy-2") throw new Error("fail");
      return okResponse;
    });

    const result = await fetchPreviewValidationsWithCache({ ...baseArgs, buildKey, cache, inFlight, previewAction, targetRefIds: ["enemy-1", "enemy-2"] });

    expect(result.get("enemy-1")?.unavailableReason).toBeNull();
    expect(result.get("enemy-2")?.unavailableReason).toBe("missing_map_data");
    expect(cache.has("ctx|enemy-1")).toBe(true);
    expect(cache.has("ctx|enemy-2")).toBe(false);
  });

  it("buildSpellPreviewFanoutKey gera chaves distintas para slot, spell e target diferentes", () => {
    const base = { sessionId: "s1", actorRefId: "p1", spellId: "magic_missile", slotLevel: 2, targetRefId: "goblin-a" };

    expect(buildSpellPreviewFanoutKey({ ...base, slotLevel: 3 })).not.toBe(buildSpellPreviewFanoutKey(base));
    expect(buildSpellPreviewFanoutKey({ ...base, spellId: "eldritch_blast" })).not.toBe(buildSpellPreviewFanoutKey(base));
    expect(buildSpellPreviewFanoutKey({ ...base, targetRefId: "orc-b" })).not.toBe(buildSpellPreviewFanoutKey(base));
    expect(buildSpellPreviewFanoutKey({ ...base, slotLevel: null })).not.toBe(buildSpellPreviewFanoutKey(base));
  });
});

const ANCHOR_CELL = { x: 10, y: 5 };

describe("area spatial validation", () => {
  it("buildAreaSpatialValidationFromPreview: no_line_of_sight → hasLineOfSight false", () => {
    const result = buildAreaSpatialValidationFromPreview({
      diagnostics: { isValid: false, failureReasons: ["no_line_of_sight"], checks: { in_range: true }, metadata: {} },
      originCell: ANCHOR_CELL,
    });
    expect(result).toMatchObject({ originCell: ANCHOR_CELL, inRange: true, hasLineOfSight: false, hasLineOfEffect: null, unavailableReason: null });
  });

  it("buildAreaSpatialValidationFromPreview: no_line_of_effect → hasLineOfEffect false, hasLineOfSight true", () => {
    const result = buildAreaSpatialValidationFromPreview({
      diagnostics: { isValid: false, failureReasons: ["no_line_of_effect"], checks: { in_range: true }, metadata: {} },
      originCell: ANCHOR_CELL,
    });
    expect(result).toMatchObject({ hasLineOfSight: true, hasLineOfEffect: false });
  });

  it("buildAreaSpatialValidationFromPreview: full_cover → hasLineOfEffect false (não LoS)", () => {
    const result = buildAreaSpatialValidationFromPreview({
      diagnostics: { isValid: false, failureReasons: ["full_cover"], checks: { in_range: true }, metadata: {} },
      originCell: ANCHOR_CELL,
    });
    expect(result).toMatchObject({ hasLineOfSight: true, hasLineOfEffect: false });
  });

  it("buildAreaSpatialValidationFromPreview: unavailableReason passa através e originCell preservado", () => {
    const result = buildAreaSpatialValidationFromPreview({
      diagnostics: null,
      originCell: ANCHOR_CELL,
      unavailableReason: "missing_map_data",
    });
    expect(result).toMatchObject({ originCell: ANCHOR_CELL, unavailableReason: "missing_map_data", inRange: null });
  });

  it("fetchAreaSpatialValidation: preview válido retorna inRange true com originCell correto", async () => {
    const previewAction = vi.fn().mockResolvedValue({
      diagnostics: { isValid: true, failureReasons: [], checks: { in_range: true }, metadata: {} },
      effectiveReachCells: 24,
      aoeCells: [],
    });
    const result = await fetchAreaSpatialValidation({
      actorRefId: "player:1",
      anchorCell: ANCHOR_CELL,
      previewAction,
      rangeMeters: 36,
      sessionId: "session-1",
    });
    expect(result).toMatchObject({ originCell: ANCHOR_CELL, inRange: true, unavailableReason: null });
  });

  it("fetchAreaSpatialValidation: LoS bloqueada → hasLineOfSight false", async () => {
    const previewAction = vi.fn().mockResolvedValue({
      diagnostics: { isValid: false, failureReasons: ["no_line_of_sight"], checks: { in_range: true }, metadata: {} },
      effectiveReachCells: 24,
      aoeCells: [],
    });
    const result = await fetchAreaSpatialValidation({ actorRefId: "player:1", anchorCell: ANCHOR_CELL, previewAction, rangeMeters: 36, sessionId: "s1" });
    expect(result).toMatchObject({ hasLineOfSight: false, unavailableReason: null });
  });

  it("fetchAreaSpatialValidation: erro de network → unavailableReason missing_map_data, sem throw", async () => {
    const previewAction = vi.fn().mockRejectedValue(new Error("network error"));
    const result = await fetchAreaSpatialValidation({ actorRefId: "player:1", anchorCell: ANCHOR_CELL, previewAction, rangeMeters: 36, sessionId: "s1" });
    expect(result).toMatchObject({ originCell: ANCHOR_CELL, unavailableReason: "missing_map_data", inRange: null });
  });
});

describe("buildSpellCoverPreviewFromDiagnostics", () => {
  it("half cover → rank half, bonus 2", () => {
    expect(buildSpellCoverPreviewFromDiagnostics({
      isValid: true, failureReasons: [], checks: {}, metadata: { cover: "half" },
    })).toEqual({ rank: "half", bonus: 2 });
  });

  it("three_quarters cover → rank three_quarters, bonus 5", () => {
    expect(buildSpellCoverPreviewFromDiagnostics({
      isValid: true, failureReasons: [], checks: {}, metadata: { cover: "three_quarters" },
    })).toEqual({ rank: "three_quarters", bonus: 5 });
  });

  it("none cover → null (não exibir cover)", () => {
    expect(buildSpellCoverPreviewFromDiagnostics({
      isValid: true, failureReasons: [], checks: {}, metadata: { cover: "none" },
    })).toBeNull();
  });

  it("ausência de cover → null", () => {
    expect(buildSpellCoverPreviewFromDiagnostics({ isValid: true, failureReasons: [], checks: {}, metadata: {} })).toBeNull();
  });

  it("diagnostics null → null", () => {
    expect(buildSpellCoverPreviewFromDiagnostics(null)).toBeNull();
  });

  it("buildTargetSpatialValidationFromPreview inclui cover quando presente", () => {
    const result = buildTargetSpatialValidationFromPreview({
      diagnostics: { isValid: true, failureReasons: [], checks: { in_range: true }, metadata: { cover: "half" } },
      targetRefId: "enemy-1",
    });
    expect(result.cover).toEqual({ rank: "half", bonus: 2 });
  });

  it("failureReasons continuam mapeando LoS mesmo com cover presente", () => {
    const result = buildTargetSpatialValidationFromPreview({
      diagnostics: { isValid: false, failureReasons: ["no_line_of_sight"], checks: { in_range: true }, metadata: { cover: "half" } },
      targetRefId: "enemy-1",
    });
    expect(result.hasLineOfSight).toBe(false);
    expect(result.cover).toEqual({ rank: "half", bonus: 2 });
  });
});
