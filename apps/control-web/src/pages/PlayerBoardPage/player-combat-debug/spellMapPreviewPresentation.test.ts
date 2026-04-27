import { describe, expect, it } from "vitest";
import type { AreaTargetSpatialMetadata } from "./spellMapPreviewModel";
import {
  formatAreaOriginPreviewLabel,
  formatAreaTargetCoverRank,
  formatAreaTargetEffectiveDcLine,
  formatSpellCoverPreview,
  formatSpellMapPreviewReason,
  formatSpellMapPreviewStatus,
  resolveCoverContext,
} from "./spellMapPreviewPresentation";

describe("spellMapPreviewPresentation", () => {
  it("formata valid/invalid/partial/unknown", () => {
    expect(formatSpellMapPreviewStatus("valid")).toBe("válido");
    expect(formatSpellMapPreviewStatus("invalid")).toBe("inválido");
    expect(formatSpellMapPreviewStatus("partial")).toBe("parcial");
    expect(formatSpellMapPreviewStatus("unknown")).toBe("indisponível");
  });

  it("reason out_of_range vira fora do alcance", () => {
    expect(formatSpellMapPreviewReason("out_of_range", "invalid")).toBe("fora do alcance");
  });

  it("reason blocked_line_of_sight vira linha de visão bloqueada", () => {
    expect(formatSpellMapPreviewReason("blocked_line_of_sight", "invalid")).toBe(
      "linha de visão bloqueada",
    );
  });

  it("reason blocked_line_of_effect vira linha de efeito bloqueada", () => {
    expect(formatSpellMapPreviewReason("blocked_line_of_effect", "invalid")).toBe(
      "linha de efeito bloqueada",
    );
  });

  it("unknown vira mensagem amigável", () => {
    expect(formatSpellMapPreviewReason(null, "unknown")).toBe(
      "Dados de posição insuficientes para validar o preview no mapa",
    );
  });

  it("reason missing_position vira dados de posição insuficientes", () => {
    expect(formatSpellMapPreviewReason("missing_position", "unknown")).toBe(
      "dados de posição insuficientes",
    );
  });

  it("reason missing_map_data vira dados do mapa insuficientes", () => {
    expect(formatSpellMapPreviewReason("missing_map_data", "unknown")).toBe(
      "dados do mapa insuficientes",
    );
  });

  it("preserva reason humana quando já vier formatada", () => {
    expect(formatSpellMapPreviewReason("Fora do alcance", "invalid")).toBe("Fora do alcance");
  });
});

describe("formatSpellCoverPreview", () => {
  it("half cover + attack → Cobertura: meia (+2 AC)", () => {
    expect(formatSpellCoverPreview({ rank: "half", bonus: 2 }, "attack")).toBe("Cobertura: meia (+2 AC)");
  });

  it("three_quarters cover + attack → Cobertura: três-quartos (+5 AC)", () => {
    expect(formatSpellCoverPreview({ rank: "three_quarters", bonus: 5 }, "attack")).toBe("Cobertura: três-quartos (+5 AC)");
  });

  it("half cover + save → Cobertura: meia (-2 DC efetiva)", () => {
    expect(formatSpellCoverPreview({ rank: "half", bonus: 2 }, "save")).toBe("Cobertura: meia (-2 DC efetiva)");
  });

  it("three_quarters cover + save → Cobertura: três-quartos (-5 DC efetiva)", () => {
    expect(formatSpellCoverPreview({ rank: "three_quarters", bonus: 5 }, "save")).toBe("Cobertura: três-quartos (-5 DC efetiva)");
  });

  it("half cover + other (direct damage) → null", () => {
    expect(formatSpellCoverPreview({ rank: "half", bonus: 2 }, "other")).toBeNull();
  });

  it("none cover → null", () => {
    expect(formatSpellCoverPreview({ rank: "none", bonus: null }, "attack")).toBeNull();
  });

  it("unknown cover → null", () => {
    expect(formatSpellCoverPreview({ rank: "unknown", bonus: null }, "attack")).toBeNull();
  });

  it("null cover → null", () => {
    expect(formatSpellCoverPreview(null, "attack")).toBeNull();
  });
});

describe("resolveCoverContext", () => {
  it("spell_attack → attack", () => { expect(resolveCoverContext("spell_attack")).toBe("attack"); });
  it("saving_throw + coverAppliesToSave true → save", () => { expect(resolveCoverContext("saving_throw", true)).toBe("save"); });
  it("saving_throw + coverAppliesToSave false → other", () => { expect(resolveCoverContext("saving_throw", false)).toBe("other"); });
  it("saving_throw + coverAppliesToSave null → other", () => { expect(resolveCoverContext("saving_throw", null)).toBe("other"); });
  it("saving_throw + coverAppliesToSave undefined → other", () => { expect(resolveCoverContext("saving_throw")).toBe("other"); });
  it("direct_damage → other", () => { expect(resolveCoverContext("direct_damage")).toBe("other"); });
  it("null → other", () => { expect(resolveCoverContext(null)).toBe("other"); });
});

describe("formatAreaOriginPreviewLabel", () => {
  it("valid sem reason → Origem da área: válida", () => {
    expect(formatAreaOriginPreviewLabel({ status: "valid", reason: null })).toBe("Origem da área: válida");
  });

  it("invalid + out_of_range → Origem da área: fora do alcance", () => {
    expect(formatAreaOriginPreviewLabel({ status: "invalid", reason: "out_of_range" })).toBe("Origem da área: fora do alcance");
  });

  it("invalid + blocked_line_of_sight → Origem da área: linha de visão bloqueada", () => {
    expect(formatAreaOriginPreviewLabel({ status: "invalid", reason: "blocked_line_of_sight" })).toBe("Origem da área: linha de visão bloqueada");
  });

  it("invalid + blocked_line_of_effect → Origem da área: linha de efeito bloqueada", () => {
    expect(formatAreaOriginPreviewLabel({ status: "invalid", reason: "blocked_line_of_effect" })).toBe("Origem da área: linha de efeito bloqueada");
  });

  it("unknown + missing_position → Origem da área: dados de posição insuficientes", () => {
    expect(formatAreaOriginPreviewLabel({ status: "unknown", reason: "missing_position" })).toBe("Origem da área: dados de posição insuficientes");
  });

  it("unknown + missing_map_data → Origem da área: dados do mapa insuficientes", () => {
    expect(formatAreaOriginPreviewLabel({ status: "unknown", reason: "missing_map_data" })).toBe("Origem da área: dados do mapa insuficientes");
  });

  it("unknown sem reason → Origem da área: dados insuficientes", () => {
    expect(formatAreaOriginPreviewLabel({ status: "unknown", reason: null })).toBe("Origem da área: dados insuficientes");
  });

  it("invalid sem reason conhecido → Origem da área: inválida", () => {
    expect(formatAreaOriginPreviewLabel({ status: "invalid", reason: null })).toBe("Origem da área: inválida");
  });
});

describe("formatAreaTargetCoverRank", () => {
  it("half → meia cobertura", () => {
    expect(formatAreaTargetCoverRank("half")).toBe("meia cobertura");
  });

  it("three_quarters → três-quartos", () => {
    expect(formatAreaTargetCoverRank("three_quarters")).toBe("três-quartos");
  });

  it("threeQuarters (camelCase) → três-quartos", () => {
    expect(formatAreaTargetCoverRank("threeQuarters")).toBe("três-quartos");
  });

  it("none → null", () => {
    expect(formatAreaTargetCoverRank("none")).toBeNull();
  });

  it("full → null", () => {
    expect(formatAreaTargetCoverRank("full")).toBeNull();
  });

  it("null → null", () => {
    expect(formatAreaTargetCoverRank(null)).toBeNull();
  });

  it("unknown value → null", () => {
    expect(formatAreaTargetCoverRank("unknown_value")).toBeNull();
  });
});

describe("formatAreaTargetEffectiveDcLine", () => {
  const base = (overrides: Partial<AreaTargetSpatialMetadata>): AreaTargetSpatialMetadata => ({
    targetRefId: "goblin-a",
    targetDisplayName: "Goblin A",
    cover: null,
    baseSaveDc: null,
    effectiveSaveDc: null,
    coverModifier: 0,
    ...overrides,
  });

  it("no cover, effective DC 15 → Goblin A: DC 15", () => {
    expect(formatAreaTargetEffectiveDcLine(base({ effectiveSaveDc: 15 }))).toBe("Goblin A: DC 15");
  });

  it("half cover, modifier 2, effective DC 13 → Goblin B: meia cobertura, DC efetiva 13", () => {
    expect(
      formatAreaTargetEffectiveDcLine(
        base({ targetRefId: "goblin-b", targetDisplayName: "Goblin B", cover: "half", coverModifier: 2, effectiveSaveDc: 13 }),
      ),
    ).toBe("Goblin B: meia cobertura, DC efetiva 13");
  });

  it("three_quarters cover, modifier 5, effective DC 10 → Orc C: três-quartos, DC efetiva 10", () => {
    expect(
      formatAreaTargetEffectiveDcLine(
        base({ targetRefId: "orc-c", targetDisplayName: "Orc C", cover: "three_quarters", coverModifier: 5, effectiveSaveDc: 10 }),
      ),
    ).toBe("Orc C: três-quartos, DC efetiva 10");
  });

  it("threeQuarters (camel) → same três-quartos label", () => {
    expect(
      formatAreaTargetEffectiveDcLine(
        base({ cover: "threeQuarters", coverModifier: 5, effectiveSaveDc: 10 }),
      ),
    ).toBe("Goblin A: três-quartos, DC efetiva 10");
  });

  it("full cover + modifier 0 → no cover label, plain DC", () => {
    expect(
      formatAreaTargetEffectiveDcLine(
        base({ cover: "full", coverModifier: 0, effectiveSaveDc: 15 }),
      ),
    ).toBe("Goblin A: DC 15");
  });

  it("missing effective DC, base DC 15 → Goblin A: DC 15", () => {
    expect(formatAreaTargetEffectiveDcLine(base({ baseSaveDc: 15 }))).toBe("Goblin A: DC 15");
  });

  it("both DCs null → null", () => {
    expect(formatAreaTargetEffectiveDcLine(base({}))).toBeNull();
  });

  it("missing display name → fallback to targetRefId", () => {
    expect(
      formatAreaTargetEffectiveDcLine(
        base({ targetDisplayName: null, effectiveSaveDc: 12 }),
      ),
    ).toBe("goblin-a: DC 12");
  });

  it("coverModifier 0 with cover half → no cover label", () => {
    expect(
      formatAreaTargetEffectiveDcLine(
        base({ cover: "half", coverModifier: 0, effectiveSaveDc: 13 }),
      ),
    ).toBe("Goblin A: DC 13");
  });
});
