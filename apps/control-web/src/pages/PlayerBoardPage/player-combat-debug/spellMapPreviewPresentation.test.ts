import { describe, expect, it } from "vitest";
import {
  formatAreaOriginPreviewLabel,
  formatSpellMapPreviewReason,
  formatSpellMapPreviewStatus,
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
