import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { SpellCastDialogHeader } from "./SpellCastDialogHeader";
import type { SpellMapPreviewModel } from "./spellMapPreviewModel";
import type { SpellPreviewModel } from "./spellPreviewModel";
import type { CombatSpellOption } from "./types";

vi.mock("../../../features/combat-ui/components/ConcentrationSaveControl", () => ({
  ConcentrationSaveControl: () => <div>concentration</div>,
}));

vi.mock("../../../features/combat-ui/components/RangeStatusBadge", () => ({
  RangeStatusBadge: () => <div>range badge</div>,
}));

const baseSpell: CombatSpellOption = {
  id: "spell-1",
  name: "Magic Missile",
  canonicalKey: "magic_missile",
  campaignSpellId: null,
  level: 1,
  prepared: true,
  actionCost: "action",
  suggestedMode: "direct_damage",
  damageType: "Force",
  savingThrow: null,
  availableSlotLevels: [1, 2, 3],
};

const baseTargetingPreview = {
  loading: false,
  error: null,
  diagnostics: null,
  distanceMeters: null,
  normalRangeMeters: null,
  maxRangeMeters: null,
  rangeStatus: "unknown" as const,
  hasDisadvantage: false,
  failureReasons: [],
};

const baseProps = {
  actionCostLabel: "Action",
  actorDisplayName: "Mage",
  anchorCell: null,
  concentrationManualRoll: "",
  concentrationRollMode: "system" as const,
  error: null,
  isAreaSpell: false,
  loading: false,
  mapPreviewModel: null,
  onConcentrationManualRollChange: () => undefined,
  onConcentrationRollModeChange: () => undefined,
  selectedSlotLevel: 3,
  setSelectedSlotLevel: () => undefined,
  shouldShowConcentrationControl: false,
  slotOptions: [1, 2, 3],
  spell: baseSpell,
  spellMode: "direct_damage" as const,
  targetDisplayName: "Goblin",
  targetPreview: baseTargetingPreview,
};

const buildPreviewModel = (overrides: Partial<SpellPreviewModel>): SpellPreviewModel => ({
  resolutionType: "direct_damage",
  damagePreview: null,
  damageType: null,
  effectInstanceCount: 1,
  effectInstanceDice: null,
  targetType: null,
  selectionType: null,
  areaShape: null,
  areaSizeMeters: null,
  rangeMeters: null,
  requiresAttackRoll: false,
  requiresSavingThrow: false,
  saveAbility: null,
  coverAppliesToSave: null,
  source: "resolved",
  ...overrides,
});

const buildMapPreviewModel = (
  overrides: Partial<SpellMapPreviewModel>,
): SpellMapPreviewModel => ({
  status: "unknown",
  reason: null,
  affectedTargetCount: undefined,
  affectedTargetNames: undefined,
  affectedTargetSpatialMetadata: undefined,
  rangeMeters: 36,
  areaShape: null,
  areaSizeMeters: null,
  effectInstanceCount: 1,
  instanceStatuses: undefined,
  ...overrides,
});

describe("SpellCastDialogHeader tactical preview", () => {
  it("renderiza status válido", () => {
    const markup = renderToStaticMarkup(
      <SpellCastDialogHeader
        {...baseProps}
        mapPreviewModel={buildMapPreviewModel({ status: "valid" })}
        previewModel={buildPreviewModel({})}
      />,
    );

    expect(markup).toContain("Preview tático: válido");
  });

  it("renderiza status inválido com reason", () => {
    const markup = renderToStaticMarkup(
      <SpellCastDialogHeader
        {...baseProps}
        mapPreviewModel={buildMapPreviewModel({ status: "invalid", reason: "out_of_range" })}
        previewModel={buildPreviewModel({})}
      />,
    );

    expect(markup).toContain("Preview tático: inválido");
    expect(markup).toContain("Motivo: fora do alcance");
  });

  it("renderiza linha de visão bloqueada", () => {
    const markup = renderToStaticMarkup(
      <SpellCastDialogHeader
        {...baseProps}
        mapPreviewModel={buildMapPreviewModel({ status: "invalid", reason: "blocked_line_of_sight" })}
        previewModel={buildPreviewModel({})}
      />,
    );

    expect(markup).toContain("Motivo: linha de visão bloqueada");
  });

  it("renderiza linha de efeito bloqueada", () => {
    const markup = renderToStaticMarkup(
      <SpellCastDialogHeader
        {...baseProps}
        mapPreviewModel={buildMapPreviewModel({ status: "invalid", reason: "blocked_line_of_effect" })}
        previewModel={buildPreviewModel({})}
      />,
    );

    expect(markup).toContain("Motivo: linha de efeito bloqueada");
  });

  it("renderiza status unknown como indisponível e não como erro", () => {
    const markup = renderToStaticMarkup(
      <SpellCastDialogHeader
        {...baseProps}
        mapPreviewModel={buildMapPreviewModel({ status: "unknown" })}
        previewModel={buildPreviewModel({})}
      />,
    );

    expect(markup).toContain("Preview tático: indisponível");
    expect(markup).toContain("Dados de posição insuficientes para validar o preview no mapa");
  });

  it("renders Magic Missile slot 3 preview from resolved context (5 instâncias, 5d4+5)", () => {
    const markup = renderToStaticMarkup(
      <SpellCastDialogHeader
        {...baseProps}
        mapPreviewModel={buildMapPreviewModel({
          status: "valid",
          effectInstanceCount: 5,
          instanceStatuses: Array.from({ length: 5 }, (_, offset) => ({
            instanceIndex: offset + 1,
            targetRefId: "enemy-1",
            status: "valid",
            reason: null,
          })),
        })}
        previewModel={buildPreviewModel({
          damagePreview: "5d4+5",
          damageType: "force",
          effectInstanceCount: 5,
          effectInstanceDice: "1d4+1",
          rangeMeters: 36,
          source: "resolved",
        })}
      />,
    );

    expect(markup).toContain("Dano 5d4+5");
    expect(markup).toContain("5 instâncias");
    expect(markup).toContain("(1d4+1)");
    expect(markup).toContain("alcance 36m");
    expect(markup).toContain("Míssil 1: válido");
    expect(markup).toContain("Míssil 5: válido");
    expect(markup).toContain('data-preview-source="resolved"');
  });

  it("renders Eldritch Blast caster level 5 with 2 feixes from resolved context", () => {
    const markup = renderToStaticMarkup(
      <SpellCastDialogHeader
        {...baseProps}
        spell={{ ...baseSpell, name: "Eldritch Blast", canonicalKey: "eldritch_blast", level: 0 }}
        spellMode="spell_attack"
        mapPreviewModel={buildMapPreviewModel({
          status: "partial",
          effectInstanceCount: 2,
          instanceStatuses: [
            { instanceIndex: 1, targetRefId: "enemy-1", status: "valid", reason: null },
            { instanceIndex: 2, targetRefId: "enemy-2", status: "invalid", reason: "out_of_range" },
          ],
        })}
        previewModel={buildPreviewModel({
          resolutionType: "spell_attack",
          requiresAttackRoll: true,
          damagePreview: "2d10",
          damageType: "force",
          effectInstanceCount: 2,
          effectInstanceDice: "1d10",
        })}
      />,
    );

    expect(markup).toContain("Dano 2d10");
    expect(markup).toContain("2 instâncias");
    expect(markup).toContain("(1d10)");
    expect(markup).toContain("ataque");
    expect(markup).toContain("Feixe 1: válido");
    expect(markup).toContain("Feixe 2: inválido · fora do alcance");
    expect(markup).toContain("Preview tático: parcial");
  });

  it("renderiza reason por instância em multi-instância", () => {
    const markup = renderToStaticMarkup(
      <SpellCastDialogHeader
        {...baseProps}
        spell={{ ...baseSpell, name: "Eldritch Blast", canonicalKey: "eldritch_blast", level: 0 }}
        spellMode="spell_attack"
        mapPreviewModel={buildMapPreviewModel({
          status: "partial",
          effectInstanceCount: 2,
          instanceStatuses: [
            { instanceIndex: 1, targetRefId: "enemy-1", status: "valid", reason: null },
            { instanceIndex: 2, targetRefId: "enemy-2", status: "invalid", reason: "blocked_line_of_sight" },
          ],
        })}
        previewModel={buildPreviewModel({
          resolutionType: "spell_attack",
          requiresAttackRoll: true,
          effectInstanceCount: 2,
          effectInstanceDice: "1d10",
        })}
      />,
    );

    expect(markup).toContain("Feixe 2: inválido · linha de visão bloqueada");
  });

  it("renders Acid Splash as saving throw without instâncias", () => {
    const markup = renderToStaticMarkup(
      <SpellCastDialogHeader
        {...baseProps}
        spell={{ ...baseSpell, name: "Acid Splash", canonicalKey: "acid_splash", level: 0 }}
        spellMode="saving_throw"
        mapPreviewModel={buildMapPreviewModel({ status: "valid", rangeMeters: 18 })}
        previewModel={buildPreviewModel({
          resolutionType: "saving_throw",
          requiresSavingThrow: true,
          saveAbility: "dexterity",
          damagePreview: "2d6",
          damageType: "acid",
          effectInstanceCount: 1,
        })}
      />,
    );

    expect(markup).toContain("saving throw");
    expect(markup).toContain("save dexterity");
    expect(markup).toContain("Dano 2d6");
    expect(markup).not.toContain("instâncias");
  });

  it("renders Fireball area shape and area size from resolved context", () => {
    const markup = renderToStaticMarkup(
      <SpellCastDialogHeader
        {...baseProps}
        isAreaSpell
        spell={{ ...baseSpell, name: "Fireball", canonicalKey: "fireball", level: 3, areaShape: "sphere", selectionType: "point" }}
        spellMode="saving_throw"
        mapPreviewModel={buildMapPreviewModel({
          status: "valid",
          rangeMeters: 45,
          areaShape: "sphere",
          areaSizeMeters: 6,
          affectedTargetCount: 3,
          affectedTargetNames: ["Goblin A", "Goblin B", "Orc C"],
        })}
        previewModel={buildPreviewModel({
          resolutionType: "saving_throw",
          requiresSavingThrow: true,
          saveAbility: "dexterity",
          damagePreview: "8d6",
          damageType: "fire",
          areaShape: "sphere",
          areaSizeMeters: 6,
          rangeMeters: 45,
        })}
      />,
    );

    expect(markup).toContain("sphere");
    expect(markup).toContain("raio 6m");
    expect(markup).toContain("Dano 8d6");
    expect(markup).toContain("Afetados: 3");
    expect(markup).toContain("Alvos: Goblin A, Goblin B, Orc C");
  });

  it("Fireball válida mostra Origem da área: válida", () => {
    const markup = renderToStaticMarkup(
      <SpellCastDialogHeader
        {...baseProps}
        isAreaSpell
        spell={{ ...baseSpell, name: "Fireball", canonicalKey: "fireball", level: 3, areaShape: "sphere", selectionType: "point" }}
        spellMode="saving_throw"
        mapPreviewModel={buildMapPreviewModel({ status: "valid", areaShape: "sphere", areaSizeMeters: 6 })}
        previewModel={buildPreviewModel({ areaShape: "sphere", areaSizeMeters: 6 })}
      />,
    );

    expect(markup).toContain("Origem da área: válida");
    expect(markup).not.toContain("Preview tático:");
  });

  it("Fireball fora de alcance mostra Origem da área: fora do alcance", () => {
    const markup = renderToStaticMarkup(
      <SpellCastDialogHeader
        {...baseProps}
        isAreaSpell
        spell={{ ...baseSpell, name: "Fireball", canonicalKey: "fireball", level: 3, areaShape: "sphere", selectionType: "point" }}
        spellMode="saving_throw"
        mapPreviewModel={buildMapPreviewModel({ status: "invalid", reason: "out_of_range", areaShape: "sphere" })}
        previewModel={buildPreviewModel({ areaShape: "sphere", areaSizeMeters: 6 })}
      />,
    );

    expect(markup).toContain("Origem da área: fora do alcance");
    expect(markup).not.toContain("Motivo:");
  });

  it("Fireball com LoS bloqueada mostra Origem da área: linha de visão bloqueada", () => {
    const markup = renderToStaticMarkup(
      <SpellCastDialogHeader
        {...baseProps}
        isAreaSpell
        spell={{ ...baseSpell, name: "Fireball", canonicalKey: "fireball", level: 3, areaShape: "sphere", selectionType: "point" }}
        spellMode="saving_throw"
        mapPreviewModel={buildMapPreviewModel({ status: "invalid", reason: "blocked_line_of_sight", areaShape: "sphere" })}
        previewModel={buildPreviewModel({ areaShape: "sphere" })}
      />,
    );

    expect(markup).toContain("Origem da área: linha de visão bloqueada");
  });

  it("Fireball com LoE bloqueada mostra Origem da área: linha de efeito bloqueada", () => {
    const markup = renderToStaticMarkup(
      <SpellCastDialogHeader
        {...baseProps}
        isAreaSpell
        spell={{ ...baseSpell, name: "Fireball", canonicalKey: "fireball", level: 3, areaShape: "sphere", selectionType: "point" }}
        spellMode="saving_throw"
        mapPreviewModel={buildMapPreviewModel({ status: "invalid", reason: "blocked_line_of_effect", areaShape: "sphere" })}
        previewModel={buildPreviewModel({ areaShape: "sphere" })}
      />,
    );

    expect(markup).toContain("Origem da área: linha de efeito bloqueada");
  });

  it("Fireball unknown mostra Origem da área: dados insuficientes", () => {
    const markup = renderToStaticMarkup(
      <SpellCastDialogHeader
        {...baseProps}
        isAreaSpell
        spell={{ ...baseSpell, name: "Fireball", canonicalKey: "fireball", level: 3, areaShape: "sphere", selectionType: "point" }}
        spellMode="saving_throw"
        mapPreviewModel={buildMapPreviewModel({ status: "unknown", reason: "missing_map_data", areaShape: "sphere" })}
        previewModel={buildPreviewModel({ areaShape: "sphere" })}
      />,
    );

    expect(markup).toContain("Origem da área: dados do mapa insuficientes");
    expect(markup).not.toContain("Preview tático:");
  });

  it("Fireball inválida com affected targets mostra reason da origem e lista de alvos", () => {
    const markup = renderToStaticMarkup(
      <SpellCastDialogHeader
        {...baseProps}
        isAreaSpell
        spell={{ ...baseSpell, name: "Fireball", canonicalKey: "fireball", level: 3, areaShape: "sphere", selectionType: "point" }}
        spellMode="saving_throw"
        mapPreviewModel={buildMapPreviewModel({
          status: "invalid",
          reason: "blocked_line_of_sight",
          areaShape: "sphere",
          affectedTargetCount: 3,
          affectedTargetNames: ["Goblin A", "Goblin B", "Orc C"],
        })}
        previewModel={buildPreviewModel({ areaShape: "sphere" })}
      />,
    );

    expect(markup).toContain("Origem da área: linha de visão bloqueada");
    expect(markup).toContain("Afetados: 3");
    expect(markup).toContain("Alvos: Goblin A, Goblin B, Orc C");
  });

  it("Eldritch Blast single-target com half cover mostra +2 AC", () => {
    const markup = renderToStaticMarkup(
      <SpellCastDialogHeader
        {...baseProps}
        spell={{ ...baseSpell, name: "Eldritch Blast", canonicalKey: "eldritch_blast", level: 0 }}
        spellMode="spell_attack"
        mapPreviewModel={buildMapPreviewModel({
          status: "valid",
          cover: { rank: "half", bonus: 2 },
        })}
        previewModel={buildPreviewModel({ resolutionType: "spell_attack", requiresAttackRoll: true })}
      />,
    );

    expect(markup).toContain("Cobertura: meia cobertura (+2 AC)");
  });

  it("Eldritch Blast single-target com three_quarters cover mostra +5 AC", () => {
    const markup = renderToStaticMarkup(
      <SpellCastDialogHeader
        {...baseProps}
        spell={{ ...baseSpell, name: "Eldritch Blast", canonicalKey: "eldritch_blast", level: 0 }}
        spellMode="spell_attack"
        mapPreviewModel={buildMapPreviewModel({
          status: "valid",
          cover: { rank: "three_quarters", bonus: 5 },
        })}
        previewModel={buildPreviewModel({ resolutionType: "spell_attack", requiresAttackRoll: true })}
      />,
    );

    expect(markup).toContain("Cobertura: três-quartos (+5 AC)");
  });

  it("Eldritch Blast multi-instância mostra cover por feixe", () => {
    const markup = renderToStaticMarkup(
      <SpellCastDialogHeader
        {...baseProps}
        spell={{ ...baseSpell, name: "Eldritch Blast", canonicalKey: "eldritch_blast", level: 0 }}
        spellMode="spell_attack"
        mapPreviewModel={buildMapPreviewModel({
          status: "valid",
          effectInstanceCount: 2,
          instanceStatuses: [
            { instanceIndex: 1, targetRefId: "enemy-1", status: "valid", reason: null, cover: { rank: "half", bonus: 2 } },
            { instanceIndex: 2, targetRefId: "enemy-2", status: "valid", reason: null, cover: null },
          ],
        })}
        previewModel={buildPreviewModel({ resolutionType: "spell_attack", effectInstanceCount: 2, source: "resolved" })}
      />,
    );

    expect(markup).toContain("Feixe 1: válido · Cobertura: meia cobertura (+2 AC)");
    expect(markup).not.toContain("Feixe 2: válido · Cobertura");
  });

  it("spell inválida por LoS mantém reason e não transforma cover em reason", () => {
    const markup = renderToStaticMarkup(
      <SpellCastDialogHeader
        {...baseProps}
        spell={{ ...baseSpell, name: "Eldritch Blast", canonicalKey: "eldritch_blast", level: 0 }}
        spellMode="spell_attack"
        mapPreviewModel={buildMapPreviewModel({
          status: "invalid",
          reason: "blocked_line_of_sight",
          cover: { rank: "half", bonus: 2 },
        })}
        previewModel={buildPreviewModel({ resolutionType: "spell_attack" })}
      />,
    );

    expect(markup).toContain("Motivo: linha de visão bloqueada");
    // cover is shown even when invalid (it's metadata, not a reason)
    expect(markup).toContain("Cobertura: meia cobertura (+2 AC)");
  });

  it("Magic Missile não mostra cover como modificador AC/DC (direct_damage)", () => {
    const markup = renderToStaticMarkup(
      <SpellCastDialogHeader
        {...baseProps}
        spellMode="direct_damage"
        mapPreviewModel={buildMapPreviewModel({
          status: "valid",
          cover: { rank: "half", bonus: 2 },
        })}
        previewModel={buildPreviewModel({ resolutionType: "direct_damage" })}
      />,
    );

    expect(markup).not.toContain("Cobertura:");
  });

  it("saving throw com coverAppliesToSave true e half cover mostra -2 DC efetiva", () => {
    const markup = renderToStaticMarkup(
      <SpellCastDialogHeader
        {...baseProps}
        spell={{ ...baseSpell, name: "Ice Knife Shards", canonicalKey: "ice_knife_shards", level: 1 }}
        spellMode="saving_throw"
        mapPreviewModel={buildMapPreviewModel({
          status: "valid",
          cover: { rank: "half", bonus: 2 },
        })}
        previewModel={buildPreviewModel({
          resolutionType: "saving_throw",
          requiresSavingThrow: true,
          saveAbility: "dexterity",
          coverAppliesToSave: true,
        })}
      />,
    );

    expect(markup).toContain("Cobertura: meia cobertura (-2 DC efetiva)");
  });

  it("saving throw com coverAppliesToSave true e three_quarters cover mostra -5 DC efetiva", () => {
    const markup = renderToStaticMarkup(
      <SpellCastDialogHeader
        {...baseProps}
        spell={{ ...baseSpell, name: "Ice Knife Shards", canonicalKey: "ice_knife_shards", level: 1 }}
        spellMode="saving_throw"
        mapPreviewModel={buildMapPreviewModel({
          status: "valid",
          cover: { rank: "three_quarters", bonus: 5 },
        })}
        previewModel={buildPreviewModel({
          resolutionType: "saving_throw",
          requiresSavingThrow: true,
          saveAbility: "dexterity",
          coverAppliesToSave: true,
        })}
      />,
    );

    expect(markup).toContain("Cobertura: três-quartos (-5 DC efetiva)");
  });

  it("saving throw com coverAppliesToSave false não mostra cover", () => {
    const markup = renderToStaticMarkup(
      <SpellCastDialogHeader
        {...baseProps}
        spell={{ ...baseSpell, name: "Acid Splash", canonicalKey: "acid_splash", level: 0 }}
        spellMode="saving_throw"
        mapPreviewModel={buildMapPreviewModel({
          status: "valid",
          cover: { rank: "half", bonus: 2 },
        })}
        previewModel={buildPreviewModel({
          resolutionType: "saving_throw",
          requiresSavingThrow: true,
          saveAbility: "dexterity",
          coverAppliesToSave: false,
        })}
      />,
    );

    expect(markup).not.toContain("Cobertura:");
  });

  it("Acid Splash sem coverAppliesToSave true não mostra cover", () => {
    const markup = renderToStaticMarkup(
      <SpellCastDialogHeader
        {...baseProps}
        spell={{ ...baseSpell, name: "Acid Splash", canonicalKey: "acid_splash", level: 0 }}
        spellMode="saving_throw"
        mapPreviewModel={buildMapPreviewModel({
          status: "valid",
          cover: { rank: "half", bonus: 2 },
        })}
        previewModel={buildPreviewModel({
          resolutionType: "saving_throw",
          requiresSavingThrow: true,
          saveAbility: "dexterity",
          coverAppliesToSave: null,
        })}
      />,
    );

    expect(markup).not.toContain("Cobertura:");
  });

  it("falls back gracefully when resolve-context is unavailable (preview-source=fallback)", () => {
    const markup = renderToStaticMarkup(
      <SpellCastDialogHeader
        {...baseProps}
        mapPreviewModel={null}
        previewModel={buildPreviewModel({
          source: "fallback",
          damagePreview: "1d10",
          damageType: "Force",
          effectInstanceCount: 1,
        })}
      />,
    );

    expect(markup).toContain('data-preview-source="fallback"');
    expect(markup).toContain("Dano 1d10");
    // multi-instance preview must NOT show in fallback mode — fallback path
    // would otherwise re-derive scaling we explicitly want to avoid.
    expect(markup).not.toContain("instâncias");
  });
});

describe("SpellCastDialogHeader – DC por alvo (area spatial metadata)", () => {
  const areaMetadata = [
    { targetRefId: "goblin-a", targetDisplayName: "Goblin A", cover: null, baseSaveDc: 15, effectiveSaveDc: 15, coverModifier: 0 },
    { targetRefId: "goblin-b", targetDisplayName: "Goblin B", cover: "half", baseSaveDc: 15, effectiveSaveDc: 13, coverModifier: 2 },
    { targetRefId: "orc-c", targetDisplayName: "Orc C", cover: "three_quarters", baseSaveDc: 15, effectiveSaveDc: 10, coverModifier: 5 },
  ];

  const renderAreaWithMetadata = (metadata: typeof areaMetadata | undefined, overrides?: Partial<typeof baseProps>) =>
    renderToStaticMarkup(
      <SpellCastDialogHeader
        {...baseProps}
        isAreaSpell
        spell={{ ...baseSpell, name: "Fireball", canonicalKey: "fireball", level: 3, areaShape: "sphere", selectionType: "point" }}
        spellMode="saving_throw"
        mapPreviewModel={buildMapPreviewModel({
          status: "valid",
          areaShape: "sphere",
          areaSizeMeters: 6,
          affectedTargetCount: 3,
          affectedTargetNames: ["Goblin A", "Goblin B", "Orc C"],
          affectedTargetSpatialMetadata: metadata,
        })}
        previewModel={buildPreviewModel({
          resolutionType: "saving_throw",
          requiresSavingThrow: true,
          saveAbility: "dexterity",
          areaShape: "sphere",
          areaSizeMeters: 6,
          rangeMeters: 45,
        })}
        {...overrides}
      />,
    );

  it("renders DC por alvo section with metadata", () => {
    const markup = renderAreaWithMetadata(areaMetadata);

    expect(markup).toContain("DC por alvo:");
    expect(markup).toContain("Goblin A: DC 15");
    expect(markup).toContain("Goblin B: meia cobertura, DC efetiva 13");
    expect(markup).toContain("Orc C: três-quartos, DC efetiva 10");
  });

  it("target without cover renders plain DC", () => {
    const markup = renderAreaWithMetadata([
      { targetRefId: "goblin-a", targetDisplayName: "Goblin A", cover: null, baseSaveDc: 15, effectiveSaveDc: 15, coverModifier: 0 },
    ]);

    expect(markup).toContain("Goblin A: DC 15");
    expect(markup).not.toContain("DC efetiva");
  });

  it("target with half cover renders cover label and effective DC", () => {
    const markup = renderAreaWithMetadata([
      { targetRefId: "goblin-b", targetDisplayName: "Goblin B", cover: "half", baseSaveDc: 15, effectiveSaveDc: 13, coverModifier: 2 },
    ]);

    expect(markup).toContain("Goblin B: meia cobertura, DC efetiva 13");
  });

  it("affectedTargetCount and affectedTargetNames still visible alongside metadata", () => {
    const markup = renderAreaWithMetadata(areaMetadata);

    expect(markup).toContain("Afetados: 3");
    expect(markup).toContain("Alvos: Goblin A, Goblin B, Orc C");
  });

  it("no DC por alvo section when metadata is undefined", () => {
    const markup = renderAreaWithMetadata(undefined);

    expect(markup).not.toContain("DC por alvo:");
  });

  it("no DC por alvo section when metadata is empty array", () => {
    const markup = renderAreaWithMetadata([]);

    expect(markup).not.toContain("DC por alvo:");
  });

  it("invalid origin still shows DC per target if metadata exists", () => {
    const markup = renderToStaticMarkup(
      <SpellCastDialogHeader
        {...baseProps}
        isAreaSpell
        spell={{ ...baseSpell, name: "Fireball", canonicalKey: "fireball", level: 3, areaShape: "sphere", selectionType: "point" }}
        spellMode="saving_throw"
        mapPreviewModel={buildMapPreviewModel({
          status: "invalid",
          reason: "blocked_line_of_sight",
          areaShape: "sphere",
          areaSizeMeters: 6,
          affectedTargetCount: 2,
          affectedTargetNames: ["Goblin A", "Goblin B"],
          affectedTargetSpatialMetadata: [
            { targetRefId: "goblin-a", targetDisplayName: "Goblin A", cover: null, baseSaveDc: 15, effectiveSaveDc: 15, coverModifier: 0 },
            { targetRefId: "goblin-b", targetDisplayName: "Goblin B", cover: "half", baseSaveDc: 15, effectiveSaveDc: 13, coverModifier: 2 },
          ],
        })}
        previewModel={buildPreviewModel({ areaShape: "sphere" })}
      />,
    );

    expect(markup).toContain("Origem da área: linha de visão bloqueada");
    expect(markup).toContain("DC por alvo:");
    expect(markup).toContain("Goblin A: DC 15");
  });
});
