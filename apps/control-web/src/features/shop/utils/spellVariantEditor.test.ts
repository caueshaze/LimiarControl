import { describe, expect, it } from "vitest";
import {
  addSpellVariant,
  getSpellVariantErrors,
  normalizeSpellVariantsForPayload,
  removeSpellVariant,
  summarizeSpellVariant,
  validateSpellVariants,
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

  it("reports duplicate and blank keys as blocking errors", () => {
    const validation = validateSpellVariants([
      {
        key: "",
        labelPt: "Sem chave",
        effects: [{ type: "restrict_action", target: "selected_target", duration: { type: "manual" }, params: { action: "actions" } }],
        onEndEffects: [],
        manualNotes: [],
      },
      {
        key: "foxs_cunning",
        labelPt: "Esperteza da Raposa",
        effects: [{ type: "restrict_action", target: "selected_target", duration: { type: "manual" }, params: { action: "actions" } }],
        onEndEffects: [],
        manualNotes: [],
      },
      {
        key: "foxs_cunning",
        labelPt: "Esperteza da Raposa 2",
        effects: [{ type: "restrict_action", target: "selected_target", duration: { type: "manual" }, params: { action: "actions" } }],
        onEndEffects: [],
        manualNotes: [],
      },
    ]);

    expect(validation.errors.some((issue) => issue.message.includes("precisa de uma chave"))).toBe(true);
    expect(validation.errors.some((issue) => issue.message.includes("Chave de variante duplicada"))).toBe(true);
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

    expect(errors[0]).toContain("ao menos um efeito declarativo");
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

  it("round-trips Enlarge/Reduce declarative effects without dropping fields", () => {
    const normalized = normalizeSpellVariantsForPayload([
      {
        key: "reduce",
        labelPt: "Reduzir",
        labelEn: "Reduce",
        descriptionPt: "Reduz tamanho e dano.",
        descriptionEn: "Reduces size and damage.",
        effects: [
          {
            type: "size_modifier",
            target: "selected_target",
            duration: { type: "timed", seconds: 60 },
            params: { value: -1 },
          },
          {
            type: "disadvantage_on_saves",
            target: "selected_target",
            duration: { type: "timed", seconds: 60 },
            params: { abilities: ["strength"] },
            stacking: "replace",
          },
          {
            type: "modify_weapon_damage",
            target: "selected_target",
            duration: { type: "timed", seconds: 60 },
            params: { dice: "1d4", operation: "subtract", minimum_total_damage: 1 },
            stacking: "replace",
          },
        ],
        onEndEffects: [],
        manualNotes: [],
      },
    ]);

    expect(normalized.errors).toEqual([]);
    expect(normalized.variants?.[0]?.effects).toEqual([
      {
        type: "size_modifier",
        target: "selected_target",
        duration: { type: "timed", seconds: 60 },
        params: { value: -1 },
      },
      {
        type: "disadvantage_on_saves",
        target: "selected_target",
        duration: { type: "timed", seconds: 60 },
        params: { abilities: ["strength"] },
        stacking: "replace",
      },
      {
        type: "modify_weapon_damage",
        target: "selected_target",
        duration: { type: "timed", seconds: 60 },
        params: { dice: "1d4", operation: "subtract", minimum_total_damage: 1 },
        stacking: "replace",
      },
    ]);
  });

  it("requires a label in the current locale and warns about the secondary locale", () => {
    const ptValidation = validateSpellVariants([
      {
        key: "owls_wisdom",
        labelPt: "",
        labelEn: "Owl's Wisdom",
        descriptionPt: "",
        descriptionEn: "Advantage on Wisdom checks.",
        effects: [
          {
            type: "advantage_on_checks",
            target: "selected_target",
            duration: { type: "manual" },
            params: { ability: "wisdom", against: "any" },
          },
        ],
        onEndEffects: [],
        manualNotes: [],
      },
    ], "pt");

    expect(ptValidation.errors.some((issue) => issue.message.includes("rótulo em português"))).toBe(true);

    const enValidation = validateSpellVariants([
      {
        key: "owls_wisdom",
        labelPt: "Sabedoria da Coruja",
        labelEn: "Owl's Wisdom",
        descriptionPt: "",
        descriptionEn: "",
        effects: [
          {
            type: "advantage_on_checks",
            target: "selected_target",
            duration: { type: "manual" },
            params: { ability: "wisdom", against: "any" },
          },
        ],
        onEndEffects: [],
        manualNotes: [],
      },
    ], "en");

    expect(enValidation.warnings.some((issue) => issue.message.includes("missing an English description"))).toBe(true);
    expect(enValidation.warnings.some((issue) => issue.message.includes("incomplete in PT localization"))).toBe(true);
  });
});
