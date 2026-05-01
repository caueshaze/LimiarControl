import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { SpellCatalogVariantsFields } from "./SpellCatalogVariantsFields";

vi.mock("../../../shared/hooks/useLocale", () => ({
  useLocale: () => ({
    locale: "pt",
    t: (key: string) => key,
  }),
}));

describe("SpellCatalogVariantsFields", () => {
  it("shows inline validation for the affected variant and manual note", () => {
    const markup = renderToStaticMarkup(
      <SpellCatalogVariantsFields
        variants={[
          {
            key: "owls_wisdom",
            labelPt: "Sabedoria da Coruja",
            labelEn: "",
            descriptionPt: "",
            descriptionEn: "",
            effects: [],
            onEndEffects: [],
            manualNotes: [
              {
                key: "",
                label: "Percepção passiva",
                description: "",
              },
            ],
          },
        ]}
        onChange={vi.fn()}
      />,
    );

    expect(markup).toContain("Nota manual 1 da variante owls_wisdom precisa de uma chave.");
    expect(markup).toContain("Nota manual 1 da variante owls_wisdom precisa de rótulo e descrição.");
    expect(markup).toContain("está sem descrição em português");
    expect(markup).toContain("localização EN incompleta");
    expect(markup).toContain("depende apenas de notas manuais");
  });
});
