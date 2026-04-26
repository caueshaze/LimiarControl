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

  it("unknown vira mensagem amigável", () => {
    expect(formatSpellMapPreviewReason(null, "unknown")).toBe(
      "Dados de posição insuficientes para validar o preview no mapa",
    );
  });

  it("preserva reason humana quando já vier formatada", () => {
    expect(formatSpellMapPreviewReason("Fora do alcance", "invalid")).toBe("Fora do alcance");
  });
});
