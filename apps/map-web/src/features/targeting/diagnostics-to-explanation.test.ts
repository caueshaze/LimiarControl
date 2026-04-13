import { describe, expect, it } from "vitest";
import {
  buildFailureExplanation,
  type FailureExplanation,
} from "./diagnostics-to-explanation";
import type { TacticalDiagnostics } from "../battle-map/battle-map-store";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function diag(
  failureReasons: string[],
  metadata: Record<string, number | string | boolean> = {}
): TacticalDiagnostics {
  return {
    isValid: failureReasons.length === 0,
    failureReasons,
    checks: {},
    metadata,
  };
}

function invalidDiag(
  reasons: string[],
  meta: Record<string, number | string | boolean> = {}
): TacticalDiagnostics {
  return { isValid: false, failureReasons: reasons, checks: {}, metadata: meta };
}

// ─── Null / valid cases ───────────────────────────────────────────────────────

describe("buildFailureExplanation — valid / null cases", () => {
  it("returns null for a valid diagnostics", () => {
    expect(buildFailureExplanation(diag([]))).toBeNull();
  });

  it("returns null when isValid=true even with stale reasons list", () => {
    const d: TacticalDiagnostics = {
      isValid: true,
      failureReasons: ["target_out_of_reach"],
      checks: {},
      metadata: {},
    };
    expect(buildFailureExplanation(d)).toBeNull();
  });

  it("returns null when isValid=false but failureReasons is empty", () => {
    const d: TacticalDiagnostics = {
      isValid: false,
      failureReasons: [],
      checks: {},
      metadata: {},
    };
    expect(buildFailureExplanation(d)).toBeNull();
  });
});

// ─── Primary label mapping ────────────────────────────────────────────────────

describe("buildFailureExplanation — primary label per failure reason", () => {
  const cases: [string, string][] = [
    ["target_not_found", "Alvo não encontrado"],
    ["invalid_target_type", "Tipo de alvo inválido"],
    ["target_out_of_reach", "Fora do alcance"],
    ["no_line_of_sight", "Sem linha de visão"],
    ["no_line_of_effect", "Bloqueado"],
    ["not_visible", "Não visível"],
    ["blocked_by_condition", "Condição bloqueante"],
    ["self_target_not_allowed", "Não pode alvejar a si"],
    ["map_unreachable", "Mapa indisponível"],
  ];

  for (const [reason, expectedLabel] of cases) {
    it(`maps ${reason} → "${expectedLabel}"`, () => {
      const result = buildFailureExplanation(invalidDiag([reason]));
      expect(result).not.toBeNull();
      expect(result!.primary).toBe(expectedLabel);
    });
  }

  it("falls back gracefully for unknown reason codes", () => {
    const result = buildFailureExplanation(invalidDiag(["future_reason"]));
    expect(result).not.toBeNull();
    expect(result!.primary).toBe("future_reason"); // raw code fallback
    expect(result!.details).toEqual([]);
    expect(result!.severity).toBe("gray");
  });
});

// ─── Detail builders ──────────────────────────────────────────────────────────

describe("buildFailureExplanation — details from metadata", () => {
  it("target_out_of_reach with full metadata → 2 detail lines", () => {
    const result = buildFailureExplanation(
      invalidDiag(["target_out_of_reach"], { distance_cells: 3, reach_cells: 1 })
    );
    expect(result!.details).toEqual(["Distância: 3 células", "Alcance: 1 célula"]);
    expect(result!.context).toEqual({ distance: 3, range: 1 });
  });

  it("target_out_of_reach with distance=1 → singular 'célula'", () => {
    const result = buildFailureExplanation(
      invalidDiag(["target_out_of_reach"], { distance_cells: 1, reach_cells: 1 })
    );
    expect(result!.details[0]).toBe("Distância: 1 célula");
    expect(result!.details[1]).toBe("Alcance: 1 célula");
  });

  it("target_out_of_reach with only distance_cells → 1 detail line", () => {
    const result = buildFailureExplanation(
      invalidDiag(["target_out_of_reach"], { distance_cells: 5 })
    );
    expect(result!.details).toEqual(["Distância: 5 células"]);
    expect(result!.context).toEqual({ distance: 5 });
  });

  it("target_out_of_reach with no metadata → empty details", () => {
    const result = buildFailureExplanation(invalidDiag(["target_out_of_reach"]));
    expect(result!.details).toEqual([]);
    expect(result!.context).toEqual({});
  });

  it("no_line_of_sight → fixed detail string", () => {
    const result = buildFailureExplanation(invalidDiag(["no_line_of_sight"]));
    expect(result!.details).toEqual(["Visão bloqueada por obstáculo"]);
  });

  it("no_line_of_effect → fixed detail string", () => {
    const result = buildFailureExplanation(invalidDiag(["no_line_of_effect"]));
    expect(result!.details).toEqual(["Efeito bloqueado por obstáculo"]);
  });

  it("not_visible → fixed detail string", () => {
    const result = buildFailureExplanation(invalidDiag(["not_visible"]));
    expect(result!.details).toEqual(["Alvo não pode ser visto"]);
  });

  it("blocked_by_condition without condition metadata → generic message", () => {
    const result = buildFailureExplanation(invalidDiag(["blocked_by_condition"]));
    expect(result!.details).toEqual(["Você está incapacitado"]);
    expect(result!.context).toEqual({});
  });

  it("blocked_by_condition with condition metadata → named condition", () => {
    const result = buildFailureExplanation(
      invalidDiag(["blocked_by_condition"], { condition: "stunned" })
    );
    expect(result!.details).toEqual(["Condição: stunned"]);
    expect(result!.context).toEqual({ condition: "stunned" });
  });

  it("map_unreachable → reconnect hint", () => {
    const result = buildFailureExplanation(invalidDiag(["map_unreachable"]));
    expect(result!.details).toEqual(["Reconecte ao mapa"]);
  });

  it("target_not_found → no detail lines", () => {
    const result = buildFailureExplanation(invalidDiag(["target_not_found"]));
    expect(result!.details).toEqual([]);
  });

  it("self_target_not_allowed → no detail lines", () => {
    const result = buildFailureExplanation(invalidDiag(["self_target_not_allowed"]));
    expect(result!.details).toEqual([]);
  });
});

// ─── Severity mapping ─────────────────────────────────────────────────────────

describe("buildFailureExplanation — severity", () => {
  const severityCases: [string, FailureExplanation["severity"]][] = [
    ["target_out_of_reach", "orange"],
    ["no_line_of_sight", "red"],
    ["no_line_of_effect", "red"],
    ["blocked_by_condition", "purple"],
    ["not_visible", "gray"],
    ["target_not_found", "gray"],
    ["invalid_target_type", "gray"],
    ["self_target_not_allowed", "gray"],
    ["map_unreachable", "gray"],
  ];

  for (const [reason, expectedSeverity] of severityCases) {
    it(`${reason} → severity="${expectedSeverity}"`, () => {
      const result = buildFailureExplanation(invalidDiag([reason]));
      expect(result!.severity).toBe(expectedSeverity);
    });
  }
});

// ─── Priority ordering ────────────────────────────────────────────────────────

describe("buildFailureExplanation — priority ordering", () => {
  it("blocked_by_condition beats target_out_of_reach", () => {
    const result = buildFailureExplanation(
      invalidDiag(["target_out_of_reach", "blocked_by_condition"])
    );
    expect(result!.primary).toBe("Condição bloqueante");
    expect(result!.severity).toBe("purple");
  });

  it("target_not_found beats target_out_of_reach", () => {
    const result = buildFailureExplanation(
      invalidDiag(["target_out_of_reach", "target_not_found"])
    );
    expect(result!.primary).toBe("Alvo não encontrado");
  });

  it("target_out_of_reach beats no_line_of_sight", () => {
    const result = buildFailureExplanation(
      invalidDiag(["no_line_of_sight", "target_out_of_reach"])
    );
    expect(result!.primary).toBe("Fora do alcance");
    expect(result!.severity).toBe("orange");
  });

  it("no_line_of_sight beats no_line_of_effect", () => {
    const result = buildFailureExplanation(
      invalidDiag(["no_line_of_effect", "no_line_of_sight"])
    );
    expect(result!.primary).toBe("Sem linha de visão");
  });

  it("no_line_of_effect beats not_visible", () => {
    const result = buildFailureExplanation(
      invalidDiag(["not_visible", "no_line_of_effect"])
    );
    expect(result!.primary).toBe("Bloqueado");
  });

  it("not_visible beats self_target_not_allowed", () => {
    const result = buildFailureExplanation(
      invalidDiag(["self_target_not_allowed", "not_visible"])
    );
    expect(result!.primary).toBe("Não visível");
  });

  it("priority is independent of list order (blocked_by_condition last)", () => {
    const result = buildFailureExplanation(
      invalidDiag([
        "map_unreachable",
        "not_visible",
        "no_line_of_effect",
        "no_line_of_sight",
        "target_out_of_reach",
        "invalid_target_type",
        "target_not_found",
        "blocked_by_condition",
      ])
    );
    expect(result!.primary).toBe("Condição bloqueante");
  });

  it("single reason → that reason wins regardless of priority", () => {
    const result = buildFailureExplanation(invalidDiag(["map_unreachable"]));
    expect(result!.primary).toBe("Mapa indisponível");
  });
});

// ─── Context object ───────────────────────────────────────────────────────────

describe("buildFailureExplanation — context", () => {
  it("returns empty context for reasons with no metadata", () => {
    const result = buildFailureExplanation(invalidDiag(["no_line_of_sight"]));
    expect(result!.context).toEqual({});
  });

  it("reach metadata is reflected in context under canonical keys", () => {
    const result = buildFailureExplanation(
      invalidDiag(["target_out_of_reach"], { distance_cells: 4, reach_cells: 2 })
    );
    expect(result!.context.distance).toBe(4);
    expect(result!.context.range).toBe(2);
  });
});
