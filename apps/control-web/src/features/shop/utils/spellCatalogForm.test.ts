import { describe, expect, it } from "vitest";
import { SpellSchool, type BaseSpell } from "../../../entities/base-spell";
import {
  buildSpellCreatePayload,
  buildSpellUpdatePayload,
  createEmptySpellEditorState,
  createSpellEditorState,
  getUnsupportedSpellEditorValues,
  normalizeSpellCanonicalKey,
} from "./spellCatalogForm";

const createSpell = (overrides: Partial<BaseSpell> = {}): BaseSpell => ({
  id: "spell-1",
  system: "DND5E",
  canonicalKey: "magic_missile",
  nameEn: "Magic Missile",
  namePt: "Missil Magico",
  descriptionEn: "Three glowing darts of magical force.",
  descriptionPt: "Tres dardos de energia magica.",
  level: 1,
  school: SpellSchool.EVOCATION,
  classesJson: ["Wizard", "Sorcerer"],
  castingTime: "1 action",
  rangeMeters: 36,
  rangeText: "36 m",
  duration: "Instantaneous",
  componentsJson: ["V", "S", "M"],
  materialComponentText: "A bit of phosphorus.",
  concentration: false,
  ritual: false,
  damageType: null,
  savingThrow: null,
  saveSuccessOutcome: null,
  source: "seed_json_bootstrap",
  sourceRef: null,
  isSrd: true,
  isActive: true,
  aliases: [],
  ...overrides,
});

describe("spellCatalogForm", () => {
  it("filters unsupported legacy values from the editor state", () => {
    const state = createSpellEditorState(
      createSpell({
        classesJson: ["Wizard", "Psion"],
        componentsJson: ["V", "X"],
        damageType: "Void" as any,
        savingThrow: "LCK" as any,
        saveSuccessOutcome: "quarter_damage" as any,
      }),
    );

    expect(state.classesJson).toEqual(["Wizard"]);
    expect(state.componentsJson).toEqual(["V"]);
    expect(state.damageType).toBe("");
    expect(state.savingThrow).toBe("");
    expect(state.saveSuccessOutcome).toBe("");
  });

  it("reports unsupported legacy values", () => {
    expect(
      getUnsupportedSpellEditorValues(
        createSpell({
          classesJson: ["Wizard", "Psion"],
          componentsJson: ["V", "X"],
          damageType: "Void" as any,
          saveSuccessOutcome: "quarter_damage" as any,
        }),
      ),
    ).toEqual(["Psion", "X", "Void", "quarter_damage"]);
  });

  it("clears material component text when M is not selected", () => {
    const payload = buildSpellUpdatePayload({
      ...createSpellEditorState(createSpell()),
      componentsJson: ["V", "S"],
      materialComponentText: "A bit of phosphorus.",
    });

    expect(payload.componentsJson).toEqual(["V", "S"]);
    expect(payload.materialComponentText).toBeNull();
    expect(payload.rangeMeters).toBe(36);
    expect(payload).not.toHaveProperty("canonicalKey");
  });

  it("builds campaign spell create payload with normalized canonical key", () => {
    const payload = buildSpellCreatePayload({
      ...createEmptySpellEditorState(),
      canonicalKey: "  Relampago do Cão  ",
      nameEn: "  Hound Lightning  ",
      descriptionEn: "  Strikes a spectral hound with lightning.  ",
      descriptionPt: "  Atinge um cao espectral com relampago.  ",
      level: 2,
      school: SpellSchool.EVOCATION,
      classesJson: ["Wizard"],
    });

    expect(payload).toEqual(
      expect.objectContaining({
        canonicalKey: "relampago_do_cao",
        nameEn: "Hound Lightning",
        descriptionEn: "Strikes a spectral hound with lightning.",
        descriptionPt: "Atinge um cao espectral com relampago.",
        level: 2,
        school: SpellSchool.EVOCATION,
        classesJson: ["Wizard"],
      }),
    );
  });

  it("keeps canonical key normalization deterministic", () => {
    expect(normalizeSpellCanonicalKey(" Détect Magic!!! ")).toBe("detect_magic");
  });
});
