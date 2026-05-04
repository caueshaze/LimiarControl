import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { CharacterHeader } from "./CharacterHeader";

vi.mock("react-router-dom", () => ({
  useNavigate: () => () => {},
}));

vi.mock("../../../shared/hooks/useLocale", () => ({
  useLocale: () => ({
    t: (key: string) =>
      ({
        "sheet.header.unnamed": "Sem nome",
        "sheet.header.reset": "Resetar",
        "sheet.header.exportJson": "Exportar",
        "sheet.header.importJson": "Importar",
      }[key] ?? key),
  }),
}));

vi.mock("../../../shared/lib/navigation", () => ({
  canNavigateBack: () => false,
  navigateBackOrFallback: () => {},
}));

vi.mock("../data/classes", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../data/classes")>();
  return {
    ...actual,
    formatClassDisplayName: () => "Guerreiro",
  };
});

vi.mock("../constants", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../constants")>();
  return {
    ...actual,
    CONDITION_LABELS: {},
    CONDITION_NAMES: [],
  };
});

const BASE_SHEET: Record<string, unknown> = {
  name: "Teste",
  class: "fighter",
  subclass: null,
  subclassConfig: null,
  level: 1,
  currentHP: 10,
  maxHP: 10,
  tempHP: 0,
  inspiration: false,
  conditions: {},
};

const noop = () => {};
const importRef = { current: null };

describe("CharacterHeader", () => {
  it("renders PP chip without helper when no bonus", () => {
    const markup = renderToStaticMarkup(
      <CharacterHeader
        sheet={BASE_SHEET as any}
        mode="play"
        canSave={false}
        showResetImport={false}
        ac={12}
        initiative={1}
        profBonus={2}
        passivePerception={13}
        spellSaveDC={null}
        spellAttack={null}
        hpTextColor="text-emerald-400"
        isDirty={false}
        saving={false}
        saveError={null}
        importRef={importRef as any}
        importError={null}
        onSave={noop}
        onExport={noop}
        onImport={noop}
        onReset={noop}
      />,
    );

    expect(markup).toContain("PP");
    expect(markup).toContain(">13<");
    expect(markup).not.toContain("Sabedoria");
  });

  it("renders PP chip with helper when bonus sources provided", () => {
    const markup = renderToStaticMarkup(
      <CharacterHeader
        sheet={BASE_SHEET as any}
        mode="play"
        canSave={false}
        showResetImport={false}
        ac={12}
        initiative={1}
        profBonus={2}
        passivePerception={17}
        passivePerceptionBonus={5}
        passivePerceptionBonusSources={[
          { label: "Sabedoria da Coruja", value: 5, groupKey: "a" },
        ]}
        spellSaveDC={null}
        spellAttack={null}
        hpTextColor="text-emerald-400"
        isDirty={false}
        saving={false}
        saveError={null}
        importRef={importRef as any}
        importError={null}
        onSave={noop}
        onExport={noop}
        onImport={noop}
        onReset={noop}
      />,
    );

    expect(markup).toContain(">17<");
    expect(markup).toContain("Base 12 + Sabedoria da Coruja +5");
  });

  it("includes aria-label with breakdown when bonus exists", () => {
    const markup = renderToStaticMarkup(
      <CharacterHeader
        sheet={BASE_SHEET as any}
        mode="play"
        canSave={false}
        showResetImport={false}
        ac={12}
        initiative={1}
        profBonus={2}
        passivePerception={17}
        passivePerceptionBonus={5}
        passivePerceptionBonusSources={[
          { label: "Sabedoria da Coruja", value: 5, groupKey: "a" },
        ]}
        spellSaveDC={null}
        spellAttack={null}
        hpTextColor="text-emerald-400"
        isDirty={false}
        saving={false}
        saveError={null}
        importRef={importRef as any}
        importError={null}
        onSave={noop}
        onExport={noop}
        onImport={noop}
        onReset={noop}
      />,
    );

    expect(markup).toContain("aria-label");
    expect(markup).toContain("PP 17. Base 12 + Sabedoria da Coruja +5");
  });
});
