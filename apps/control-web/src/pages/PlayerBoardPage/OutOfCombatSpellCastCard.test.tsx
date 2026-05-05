import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { OutOfCombatSpellCastCard } from "./OutOfCombatSpellCastCard";
import type { OutOfCombatCastableSpell } from "../../entities/character";

vi.mock("../../shared/hooks/useLocale", () => ({
  useLocale: () => ({
    t: (key: string) =>
      ({
        "playerBoard.castSpells": "Conjurar magia",
        "playerBoard.concentration": "Concentração",
        "playerBoard.notPrepared": "Não preparado",
        "playerBoard.selectVariant": "Variante",
        "playerBoard.selectSlotLevel": "Slot",
        "playerBoard.castSpellLoading": "Conjurando...",
        "playerBoard.castSpellConfirm": "Conjurar",
      }[key] ?? key),
  }),
}));

const makeSpell = (
  overrides: Partial<OutOfCombatCastableSpell> = {},
): OutOfCombatCastableSpell => ({
  id: "spell-1",
  canonicalKey: "shield_of_faith",
  nameEn: "Shield of Faith",
  namePt: "Escudo da Fé",
  level: 1,
  concentration: true,
  prepared: true,
  variants: [],
  effects: [],
  ...overrides,
});

describe("OutOfCombatSpellCastCard", () => {
  it("returns null when spell list is empty", () => {
    const markup = renderToStaticMarkup(
      <OutOfCombatSpellCastCard spells={[]} casting={false} onCast={() => undefined} />,
    );
    expect(markup).toBe("");
  });

  it("renders spell name for each eligible spell", () => {
    const markup = renderToStaticMarkup(
      <OutOfCombatSpellCastCard
        spells={[makeSpell({ namePt: "Escudo da Fé" })]}
        casting={false}
        onCast={() => undefined}
      />,
    );
    expect(markup).toContain("Escudo da Fé");
  });

  it("shows level badge for leveled spells", () => {
    const markup = renderToStaticMarkup(
      <OutOfCombatSpellCastCard
        spells={[makeSpell({ level: 2 })]}
        casting={false}
        onCast={() => undefined}
      />,
    );
    expect(markup).toContain("Nv 2");
  });

  it("shows concentration badge for concentration spells", () => {
    const markup = renderToStaticMarkup(
      <OutOfCombatSpellCastCard
        spells={[makeSpell({ concentration: true })]}
        casting={false}
        onCast={() => undefined}
      />,
    );
    expect(markup).toContain("Concentração");
  });

  it("shows not-prepared badge for unprepared spells", () => {
    const markup = renderToStaticMarkup(
      <OutOfCombatSpellCastCard
        spells={[makeSpell({ prepared: false })]}
        casting={false}
        onCast={() => undefined}
      />,
    );
    expect(markup).toContain("Não preparado");
  });

  it("does not show expand arrow for unprepared spells", () => {
    const markup = renderToStaticMarkup(
      <OutOfCombatSpellCastCard
        spells={[makeSpell({ prepared: false })]}
        casting={false}
        onCast={() => undefined}
      />,
    );
    expect(markup).not.toContain("▼");
  });

  it("shows expand arrow for prepared spells", () => {
    const markup = renderToStaticMarkup(
      <OutOfCombatSpellCastCard
        spells={[makeSpell({ prepared: true })]}
        casting={false}
        onCast={() => undefined}
      />,
    );
    expect(markup).toContain("▼");
  });

  it("renders multiple spells", () => {
    const markup = renderToStaticMarkup(
      <OutOfCombatSpellCastCard
        spells={[
          makeSpell({ id: "s1", nameEn: "Bless", namePt: "Benção" }),
          makeSpell({ id: "s2", nameEn: "Shield of Faith", namePt: "Escudo da Fé" }),
        ]}
        casting={false}
        onCast={() => undefined}
      />,
    );
    expect(markup).toContain("Benção");
    expect(markup).toContain("Escudo da Fé");
  });

  it("does not crash with casting=true", () => {
    expect(() =>
      renderToStaticMarkup(
        <OutOfCombatSpellCastCard
          spells={[makeSpell()]}
          casting={true}
          onCast={() => undefined}
        />,
      ),
    ).not.toThrow();
  });

  it("falls back to nameEn when namePt is absent", () => {
    const markup = renderToStaticMarkup(
      <OutOfCombatSpellCastCard
        spells={[makeSpell({ namePt: undefined, nameEn: "Guidance" })]}
        casting={false}
        onCast={() => undefined}
      />,
    );
    expect(markup).toContain("Guidance");
  });
});
