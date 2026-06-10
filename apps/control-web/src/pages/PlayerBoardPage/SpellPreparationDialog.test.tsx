import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { SpellPreparationDialog } from "./SpellPreparationDialog";
import {
  buildSpellPreparationCatalog,
  resolveSpellPreparationDisplayName,
} from "./spellPreparationDialogModel";

const getBaseSpellsMock = vi.fn();
const isSpellCatalogLoadedMock = vi.fn();
const loadSpellCatalogMock = vi.fn(() => Promise.resolve());
const resolveSpellByAuthorityMock = vi.fn();
const getCatalogSpellOptionsMock = vi.fn();

vi.mock("../../entities/dnd-base", () => ({
  getBaseSpells: (...args: unknown[]) => getBaseSpellsMock(...args),
  isSpellCatalogLoaded: (...args: unknown[]) => isSpellCatalogLoadedMock(...args),
  loadSpellCatalog: (...args: unknown[]) => loadSpellCatalogMock(...args),
  resolveSpellByAuthority: (...args: unknown[]) => resolveSpellByAuthorityMock(...args),
}));

vi.mock("../../features/character-sheet/utils/creationSpells", () => ({
  getCatalogSpellOptions: (...args: unknown[]) => getCatalogSpellOptionsMock(...args),
}));

vi.mock("../../shared/hooks/useLocale", () => ({
  useLocale: () => ({
    locale: "pt",
    t: (key: string) =>
      ({
        "playerBoard.prepareSpellsPrompt": "Preparar magias",
        "playerBoard.prepareSpellsDescription": "Você concluiu um descanso longo. Revise suas magias preparadas.",
        "playerBoard.prepareSpellsDuringLongRestPrompt": "Preparar magias durante o descanso",
        "playerBoard.prepareSpellsDuringLongRestDescription": "O descanso longo ainda está em andamento. Revise suas magias preparadas agora.",
        "playerBoard.prepareSpellsButton": "Preparar magias",
        "playerBoard.prepareSpellsSelected": "Selecionadas: {count} / {limit}",
        "playerBoard.prepareSpellsOverLimit": "Limite excedido",
        "playerBoard.prepareSpellsCantripsAlwaysPrepared": "Truques (sempre preparados)",
        "playerBoard.prepareSpellsPrepared": "Preparado",
        "playerBoard.prepareSpellsLevel": "Nível {level}",
        "common.cancel": "Cancelar",
        "common.saving": "Salvando...",
      }[key] ?? key),
  }),
}));

describe("SpellPreparationDialog", () => {
  it("shows during-long-rest copy when availableDuringRest is true", () => {
    const markup = renderToStaticMarkup(
      <SpellPreparationDialog
        open
        spells={[]}
        preparedLimit={3}
        currentPreparedIds={[]}
        onClose={() => undefined}
        onSubmit={() => undefined}
        copyMode="during_long_rest"
      />,
    );

    expect(markup).toContain("Preparar magias durante o descanso");
    expect(markup).toContain("O descanso longo ainda está em andamento");
    expect(markup).toContain("Preparar magias");
  });

  it("keeps english on the initial unresolved pass and uses localized names after catalog resolution", () => {
    const spell = {
      id: "spell-1",
      name: "Light",
      canonicalKey: "light",
      level: 0,
      school: "Evocation",
      prepared: true,
      notes: "",
      campaignSpellId: null,
    };

    getCatalogSpellOptionsMock.mockReturnValue([
      { canonicalKey: "light", name: "Light", namePt: "Luz" },
    ]);
    resolveSpellByAuthorityMock.mockImplementation((catalog, candidate) =>
      catalog.find((entry: { canonicalKey?: string | null }) => entry.canonicalKey === candidate.canonicalKey) ?? null,
    );

    const unresolvedCatalog = buildSpellPreparationCatalog(false, "cleric", "campaign-1");
    const resolvedCatalog = buildSpellPreparationCatalog(true, "cleric", "campaign-1");

    expect(resolveSpellPreparationDisplayName(unresolvedCatalog, spell, "pt")).toBe("Light");
    expect(resolveSpellPreparationDisplayName(resolvedCatalog, spell, "pt")).toBe("Luz");
  });

  it("falls back to base-scope catalog when class-scoped catalog is empty", () => {
    const spell = {
      id: "spell-1",
      name: "Light",
      canonicalKey: "light",
      level: 0,
      school: "Evocation",
      prepared: true,
      notes: "",
      campaignSpellId: "camp-spell-1",
    };

    getCatalogSpellOptionsMock.mockReturnValue([]);
    getBaseSpellsMock.mockReturnValue([
      { campaignSpellId: "camp-spell-1", canonicalKey: "light", name: "Light", namePt: "Luz" },
    ]);
    resolveSpellByAuthorityMock.mockImplementation((catalog, candidate) =>
      catalog.find((entry: { campaignSpellId?: string | null }) => entry.campaignSpellId === candidate.campaignSpellId) ?? null,
    );

    const catalog = buildSpellPreparationCatalog(true, "unknown_class", "campaign-1");
    expect(resolveSpellPreparationDisplayName(catalog, spell, "pt")).toBe("Luz");
  });

  it("keeps the english fallback when no catalog entry resolves", () => {
    const spell = {
      id: "spell-1",
      name: "Light",
      canonicalKey: "light",
      level: 0,
      school: "Evocation",
      prepared: true,
      notes: "",
      campaignSpellId: null,
    };

    getCatalogSpellOptionsMock.mockReturnValue([]);
    getBaseSpellsMock.mockReturnValue([]);
    resolveSpellByAuthorityMock.mockReturnValue(null);

    const catalog = buildSpellPreparationCatalog(true, "cleric", "campaign-1");
    expect(resolveSpellPreparationDisplayName(catalog, spell, "pt")).toBe("Light");
  });
});
