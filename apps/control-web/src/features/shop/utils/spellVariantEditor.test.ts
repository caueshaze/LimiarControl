import { describe, expect, it } from "vitest";
import {
  addSpellVariant,
  getSpellVariantWarnings,
  getSpellVariantErrors,
  normalizeSpellVariantsForPayload,
  removeSpellVariant,
  summarizeSpellVariant,
} from "./spellVariantEditor";

describe("spellVariantEditor", () => {
  it("allows adding and removing variants", () => {
    const added = addSpellVariant([]);
    expect(added).toHaveLength(1);
    expect(added[0]?.key).toBe("");

    const removed = removeSpellVariant(
      [
        { ...added[0], key: "bulls_strength", labelPt: "Força do Touro" },
        { ...added[0], key: "owls_wisdom", labelPt: "Sabedoria da Coruja" },
      ],
      0,
    );

    expect(removed).toEqual([
      expect.objectContaining({ key: "owls_wisdom", labelPt: "Sabedoria da Coruja" }),
    ]);
  });

  it("warns about duplicate and blank keys", () => {
    const warnings = getSpellVariantWarnings([
      {
        key: "",
        labelPt: "",
        effects: [],
        onEndEffects: [],
        manualNotes: [],
      },
      {
        key: "foxs_cunning",
        labelPt: "Esperteza da Raposa",
        effects: [],
        onEndEffects: [],
        manualNotes: [],
      },
      {
        key: "foxs_cunning",
        labelPt: "Esperteza da Raposa 2",
        effects: [],
        onEndEffects: [],
        manualNotes: [],
      },
    ]);

    expect(warnings.some((warning) => warning.includes("sem chave"))).toBe(true);
    expect(warnings.some((warning) => warning.includes("Chaves duplicadas"))).toBe(true);
  });

  it("blocks a variant that has neither effects nor manual notes", () => {
    const errors = getSpellVariantErrors([
      {
        key: "empty_variant",
        labelPt: "Variante vazia",
        effects: [],
        onEndEffects: [],
        manualNotes: [],
      },
    ]);

    expect(errors[0]).toContain("ao menos um efeito declarativo ou nota manual");
  });

  it("serializes manual notes and trims optional fields", () => {
    const normalized = normalizeSpellVariantsForPayload([
      {
        key: " bears_endurance ",
        labelPt: " Resistência do Urso ",
        labelEn: " Bear's Endurance ",
        descriptionPt: " ",
        descriptionEn: " Temporary hit points. ",
        effects: [],
        onEndEffects: [],
        manualNotes: [
          {
            key: " grant_temp_hp ",
            label: " PV temporários ",
            description: " Remover quando a magia terminar. ",
          },
        ],
      },
    ]);

    expect(normalized.errors).toEqual([]);
    expect(normalized.variants).toEqual([
      {
        key: "bears_endurance",
        labelPt: "Resistência do Urso",
        labelEn: "Bear's Endurance",
        descriptionPt: null,
        descriptionEn: "Temporary hit points.",
        effects: null,
        onEndEffects: null,
        manualNotes: [
          {
            key: "grant_temp_hp",
            label: "PV temporários",
            description: "Remover quando a magia terminar.",
          },
        ],
      },
    ]);
  });

  it("builds a compact summary for quick scanning", () => {
    expect(
      summarizeSpellVariant({
        key: "bears_endurance",
        labelPt: "Resistência do Urso",
        effects: [
          {
            type: "advantage_on_checks",
            target: "selected_target",
            duration: { type: "manual" },
            params: { ability: "constitution", against: "any" },
          },
        ],
        onEndEffects: [],
        manualNotes: [
          {
            key: "grant_temp_hp",
            label: "2d6 HP",
            description: "Aplicar manualmente.",
          },
        ],
      }),
    ).toBe("advantage_on_checks (CON) + manual (2d6 HP)");
  });
});
