import { describe, expect, it } from "vitest";
import {
  composeCreationPersonalityFields,
  parseCreationPersonalityFields,
} from "./creationPersonality";

describe("creationPersonality", () => {
  it("parses structured portuguese sections", () => {
    const parsed = parseCreationPersonalityFields(
      "Traços de personalidade: Curioso.\n\nIdeais: Liberdade.\n\nLigações: Minha guilda.\n\nDefeitos: Teimoso.",
    );

    expect(parsed).toEqual({
      personalityTraits: "Curioso.",
      ideals: "Liberdade.",
      bonds: "Minha guilda.",
      flaws: "Teimoso.",
    });
  });

  it("falls back to the first field for legacy freeform text", () => {
    const parsed = parseCreationPersonalityFields("Texto antigo sem estrutura.");

    expect(parsed).toEqual({
      personalityTraits: "Texto antigo sem estrutura.",
      ideals: "",
      bonds: "",
      flaws: "",
    });
  });

  it("composes only filled sections", () => {
    expect(
      composeCreationPersonalityFields({
        personalityTraits: "Observador",
        ideals: "",
        bonds: "Minha cidade",
        flaws: "",
      }),
    ).toBe("Traços de personalidade: Observador\n\nLigações: Minha cidade");
  });
});
