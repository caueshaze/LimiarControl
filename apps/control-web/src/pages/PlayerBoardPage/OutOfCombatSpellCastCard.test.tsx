import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { OutOfCombatSpellCastCard } from "./OutOfCombatSpellCastCard";
import type { OutOfCombatCastableSpell } from "../../entities/character";

const mockState = {
  overrides: null as Array<unknown> | null,
};

vi.mock("react", async () => {
  const actual = await vi.importActual<typeof import("react")>("react");
  return {
    ...actual,
    useState: vi.fn((init: unknown) => {
      if (mockState.overrides && mockState.overrides.length > 0) {
        return [mockState.overrides.shift(), vi.fn()];
      }
      return [init, vi.fn()];
    }),
  };
});

vi.mock("../../shared/hooks/useLocale", () => ({
  useLocale: () => ({
    t: (key: string) =>
      ({
        "playerBoard.castSpells": "Conjurar magia",
        "playerBoard.concentration": "Concentração",
        "playerBoard.notPrepared": "Não preparado",
        "playerBoard.selectVariant": "Variante",
        "playerBoard.selectSlotLevel": "Slot",
        "playerBoard.selectTarget": "Alvo",
        "playerBoard.targetSelf": "Você mesmo",
        "playerBoard.castSpellLoading": "Conjurando...",
        "playerBoard.castSpellConfirm": "Conjurar",
        "playerBoard.healingPreview": "Cura prevista",
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

const findCastButton = (node: unknown): { props?: { onClick?: () => void } } | null => {
  if (!node || typeof node !== "object") return null;
  const element = node as { type?: unknown; props?: Record<string, unknown> };

  if (element.type === "button") {
    const children = element.props?.children;
    if (children === "Conjurar") {
      return element;
    }
  }

  const children = element.props?.children;
  if (Array.isArray(children)) {
    for (const child of children) {
      const found = findCastButton(child);
      if (found) return found;
    }
  } else if (children && typeof children === "object") {
    const found = findCastButton(children);
    if (found) return found;
  }

  return null;
};

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

  describe("target selector", () => {
    const targetOptions = [
      { playerUserId: "ally-1", label: "Ally One" },
      { playerUserId: "ally-2", label: "Ally Two" },
    ];

    it("shows target selector for self_or_ally spell when allies exist", () => {
      mockState.overrides = ["spell-1", {}, {}, {}];
      const markup = renderToStaticMarkup(
        <OutOfCombatSpellCastCard
          spells={[makeSpell({ outOfCombatTarget: "self_or_ally" })]}
          casting={false}
          onCast={() => undefined}
          targetOptions={targetOptions}
        />,
      );
      expect(markup).toContain("Alvo");
      expect(markup).toContain("Você mesmo");
    });

    it("hides target selector for self spell even when allies exist", () => {
      mockState.overrides = ["spell-1", {}, {}, {}];
      const markup = renderToStaticMarkup(
        <OutOfCombatSpellCastCard
          spells={[makeSpell({ outOfCombatTarget: "self" })]}
          casting={false}
          onCast={() => undefined}
          targetOptions={targetOptions}
        />,
      );
      expect(markup).not.toContain("Alvo");
      expect(markup).not.toContain("Você mesmo");
    });

    it("hides target selector when no allies are available", () => {
      mockState.overrides = ["spell-1", {}, {}, {}];
      const markup = renderToStaticMarkup(
        <OutOfCombatSpellCastCard
          spells={[makeSpell({ outOfCombatTarget: "self_or_ally" })]}
          casting={false}
          onCast={() => undefined}
          targetOptions={[]}
        />,
      );
      expect(markup).not.toContain("Alvo");
    });

    it("target selector shows self and ally options", () => {
      mockState.overrides = ["spell-1", {}, {}, {}];
      const markup = renderToStaticMarkup(
        <OutOfCombatSpellCastCard
          spells={[makeSpell({ outOfCombatTarget: "self_or_ally" })]}
          casting={false}
          onCast={() => undefined}
          targetOptions={targetOptions}
        />,
      );
      expect(markup).toContain("Você mesmo");
      expect(markup).toContain("Ally One");
      expect(markup).toContain("Ally Two");
    });

    it("shows target selector for ally-only spell when allies exist", () => {
      mockState.overrides = ["spell-1", {}, {}, {}];
      const markup = renderToStaticMarkup(
        <OutOfCombatSpellCastCard
          spells={[makeSpell({ outOfCombatTarget: "ally" })]}
          casting={false}
          onCast={() => undefined}
          targetOptions={targetOptions}
        />,
      );
      expect(markup).toContain("Alvo");
      expect(markup).toContain("Ally One");
      expect(markup).toContain("Ally Two");
    });
  });

  describe("cast callback", () => {
    const targetOptions = [{ playerUserId: "ally-1", label: "Ally One" }];

    it("cast with ally target sends correct targetPlayerUserId", () => {
      const onCast = vi.fn();
      const expandedSpellId = "spell-1";
      const selectedTargetsWithAlly = { "spell-1": "ally-1" };
      mockState.overrides = [expandedSpellId, {}, {}, selectedTargetsWithAlly];

      const tree = OutOfCombatSpellCastCard({
        spells: [makeSpell({ outOfCombatTarget: "self_or_ally" })],
        casting: false,
        onCast,
        targetOptions,
      });

      const button = findCastButton(tree);
      expect(button).not.toBeNull();
      button?.props?.onClick?.();

      expect(onCast).toHaveBeenCalledTimes(1);
      expect(onCast).toHaveBeenCalledWith("spell-1", 1, null, "ally-1");
    });

    it("cast with self target sends null targetPlayerUserId", () => {
      const onCast = vi.fn();
      const expandedSpellId = "spell-1";
      const emptySelectedTargets = {};
      mockState.overrides = [expandedSpellId, {}, {}, emptySelectedTargets];

      const tree = OutOfCombatSpellCastCard({
        spells: [makeSpell({ outOfCombatTarget: "self_or_ally" })],
        casting: false,
        onCast,
        targetOptions,
      });

      const button = findCastButton(tree);
      expect(button).not.toBeNull();
      button?.props?.onClick?.();

      expect(onCast).toHaveBeenCalledTimes(1);
      expect(onCast).toHaveBeenCalledWith("spell-1", 1, null, null);
    });

    it("cast without targetOptions sends null targetPlayerUserId", () => {
      const onCast = vi.fn();
      const expandedSpellId = "spell-1";
      mockState.overrides = [expandedSpellId, {}, {}, {}];

      const tree = OutOfCombatSpellCastCard({
        spells: [makeSpell()],
        casting: false,
        onCast,
      });

      const button = findCastButton(tree);
      expect(button).not.toBeNull();
      button?.props?.onClick?.();

      expect(onCast).toHaveBeenCalledTimes(1);
      expect(onCast).toHaveBeenCalledWith("spell-1", 1, null, null);
    });

    it("cast with ally-only spell sends selected targetPlayerUserId", () => {
      const onCast = vi.fn();
      const expandedSpellId = "spell-1";
      const selectedTargetsWithAlly = { "spell-1": "ally-1" };
      mockState.overrides = [expandedSpellId, {}, {}, selectedTargetsWithAlly];

      const tree = OutOfCombatSpellCastCard({
        spells: [makeSpell({ outOfCombatTarget: "ally" })],
        casting: false,
        onCast,
        targetOptions,
      });

      const button = findCastButton(tree);
      expect(button).not.toBeNull();
      button?.props?.onClick?.();

      expect(onCast).toHaveBeenCalledTimes(1);
      expect(onCast).toHaveBeenCalledWith("spell-1", 1, null, "ally-1");
    });
  });

  describe("healing preview", () => {
    const basePreview = {
      baseFormula: "1d8 + 3",
      baseDice: "1d8",
      baseCount: 1,
      dieSides: 8,
      modifier: 3,
      upcastPerLevel: 1,
    };

    it("shows healing preview when healingPreview is provided and spell is expanded", () => {
      mockState.overrides = ["spell-1", {}, {}, {}];
      const markup = renderToStaticMarkup(
        <OutOfCombatSpellCastCard
          spells={[makeSpell({ healingPreview: basePreview })]}
          casting={false}
          onCast={() => undefined}
        />,
      );
      expect(markup).toContain("Cura prevista");
      expect(markup).toContain("1d8 + 3");
    });

    it("does not show healing preview section when healingPreview is null", () => {
      mockState.overrides = ["spell-1", {}, {}, {}];
      const markup = renderToStaticMarkup(
        <OutOfCombatSpellCastCard
          spells={[makeSpell({ healingPreview: null })]}
          casting={false}
          onCast={() => undefined}
        />,
      );
      expect(markup).not.toContain("Cura prevista");
    });

    it("does not show healing preview section when healingPreview is absent", () => {
      mockState.overrides = ["spell-1", {}, {}, {}];
      const markup = renderToStaticMarkup(
        <OutOfCombatSpellCastCard
          spells={[makeSpell()]}
          casting={false}
          onCast={() => undefined}
        />,
      );
      expect(markup).not.toContain("Cura prevista");
    });

    it("shows upcast formula when slot level 2 is selected", () => {
      // expandedId="spell-1", variants={}, levels={"spell-1": 2}, targets={}
      mockState.overrides = ["spell-1", {}, { "spell-1": 2 }, {}];
      const markup = renderToStaticMarkup(
        <OutOfCombatSpellCastCard
          spells={[makeSpell({ healingPreview: basePreview })]}
          casting={false}
          onCast={() => undefined}
        />,
      );
      expect(markup).toContain("2d8 + 3");
    });

    it("shows upcast formula when slot level 3 is selected", () => {
      mockState.overrides = ["spell-1", {}, { "spell-1": 3 }, {}];
      const markup = renderToStaticMarkup(
        <OutOfCombatSpellCastCard
          spells={[makeSpell({ healingPreview: basePreview })]}
          casting={false}
          onCast={() => undefined}
        />,
      );
      expect(markup).toContain("3d8 + 3");
    });

    it("shows base formula for 1d4 spell (Healing Word style)", () => {
      const hwPreview = { baseFormula: "1d4 + 4", baseDice: "1d4", baseCount: 1, dieSides: 4, modifier: 4, upcastPerLevel: 1 };
      mockState.overrides = ["spell-1", {}, {}, {}];
      const markup = renderToStaticMarkup(
        <OutOfCombatSpellCastCard
          spells={[makeSpell({ healingPreview: hwPreview })]}
          casting={false}
          onCast={() => undefined}
        />,
      );
      expect(markup).toContain("1d4 + 4");
    });

    it("shows dice without modifier when modifier is zero", () => {
      const zeroModPreview = { baseFormula: "1d8", baseDice: "1d8", baseCount: 1, dieSides: 8, modifier: 0, upcastPerLevel: 1 };
      mockState.overrides = ["spell-1", {}, {}, {}];
      const markup = renderToStaticMarkup(
        <OutOfCombatSpellCastCard
          spells={[makeSpell({ healingPreview: zeroModPreview })]}
          casting={false}
          onCast={() => undefined}
        />,
      );
      expect(markup).toContain("1d8");
      expect(markup).not.toContain("+ 0");
    });
  });
});
