import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { SpellPreparationDialog } from "./SpellPreparationDialog";

vi.mock("../../entities/dnd-base", () => ({
  loadSpellCatalog: vi.fn(() => Promise.resolve()),
  resolveSpellByAuthority: vi.fn((catalog: Array<{ canonicalKey?: string | null; namePt?: string | null; name: string }>, spell: { canonicalKey?: string | null }) =>
    catalog.find((entry) => entry.canonicalKey === spell.canonicalKey) ?? null),
}));

vi.mock("../../features/character-sheet/utils/creationSpells", () => ({
  getCatalogSpellOptions: vi.fn(() => [
    {
      canonicalKey: "light",
      name: "Light",
      namePt: "Luz",
    },
  ]),
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
        "playerBoard.prepareSpellsCantrips": "Truques",
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

  it("falls back to post-rest copy by default", () => {
    const markup = renderToStaticMarkup(
      <SpellPreparationDialog
        open
        spells={[]}
        preparedLimit={3}
        currentPreparedIds={[]}
        onClose={() => undefined}
        onSubmit={() => undefined}
      />,
    );

    expect(markup).toContain("Preparar magias");
    expect(markup).toContain("Você concluiu um descanso longo");
  });

  it("marks cantrips as always prepared", () => {
    const markup = renderToStaticMarkup(
      <SpellPreparationDialog
        open
        spells={[
          {
            id: "spell-1",
            name: "Light",
            canonicalKey: "light",
            level: 0,
            school: "Evocation",
            prepared: true,
            notes: "",
            campaignSpellId: null,
          },
        ]}
        preparedLimit={3}
        currentPreparedIds={["spell-1"]}
        onClose={() => undefined}
        onSubmit={() => undefined}
      />,
    );

    expect(markup).toContain("Truques (sempre preparados)");
    expect(markup).toContain("Preparado");
    expect(markup).toContain("Luz");
  });
});
