import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { SpellCatalogResolutionFields } from "./SpellCatalogResolutionFields";
import { createEmptySpellEditorState } from "../utils/spellCatalogForm";

vi.mock("../../../shared/hooks/useLocale", () => ({
  useLocale: () => ({
    locale: "pt",
    t: (key: string) => key,
  }),
}));

describe("SpellCatalogResolutionFields", () => {
  it("renders coverAppliesToSave in the resolution/saving throw section", () => {
    const state = {
      ...createEmptySpellEditorState(),
      resolutionType: "damage" as const,
      savingThrow: "DEX",
    };

    const html = renderToStaticMarkup(
      <SpellCatalogResolutionFields
        state={state}
        setState={() => undefined}
        t={(key) => key}
        locale="pt"
        selectPlaceholder="Selecione"
        showSavingThrowFields
        showSaveSuccessOutcome
        showDamageFields
        showHealFields={false}
      />,
    );

    expect(html).toContain("catalog.spells.form.coverAppliesToSave");
    expect(html).toContain("catalog.spells.form.coverAppliesToSaveHelp");
    expect(html).toContain(">Física<");
    expect(html).toContain(">Nenhuma<");
  });
});
