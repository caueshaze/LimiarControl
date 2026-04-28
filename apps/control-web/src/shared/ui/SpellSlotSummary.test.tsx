import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { SpellSlotSummary, buildSpellSlotSummaryEntries } from "./SpellSlotSummary";

describe("buildSpellSlotSummaryEntries", () => {
  it("ignora slots com max 0 e calcula remaining corretamente", () => {
    expect(
      buildSpellSlotSummaryEntries({
        1: { max: 4, used: 2 },
        2: { max: 0, used: 0 },
        3: { max: 2, used: 3 },
      }),
    ).toEqual([
      { level: 1, max: 4, used: 2, remaining: 2 },
      { level: 3, max: 2, used: 3, remaining: 0 },
    ]);
  });
});

describe("SpellSlotSummary", () => {
  it("renderiza slots restantes e esgotados", () => {
    const markup = renderToStaticMarkup(
      <SpellSlotSummary
        slots={{
          1: { max: 4, used: 2 },
          2: { max: 0, used: 0 },
          3: { max: 2, used: 2 },
        }}
      />,
    );

    expect(markup).toContain("1º círculo");
    expect(markup).toContain("2/4 restantes");
    expect(markup).not.toContain("2º círculo");
    expect(markup).toContain("3º círculo");
    expect(markup).toContain("0/2 restantes");
  });

  it("renderiza formato compacto", () => {
    const markup = renderToStaticMarkup(
      <SpellSlotSummary
        compact
        entries={[
          { level: 1, max: 4, used: 2, remaining: 2 },
          { level: 2, max: 3, used: 3, remaining: 0 },
        ]}
      />,
    );

    expect(markup).toContain("1º: 2/4");
    expect(markup).toContain("2º: 0/3");
  });
});
