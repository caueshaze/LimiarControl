import { describe, expect, it } from "vitest";
import {
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
