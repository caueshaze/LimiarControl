import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { Skills } from "./Skills";

vi.mock("../../../shared/hooks/useLocale", () => ({
  useLocale: () => ({
    t: (key: string) =>
      ({
        "sheet.skills.title": "Perícias",
        "sheet.skills.passivePerception": "Percepção Passiva",
        "sheet.skills.cycleProficiency": "Alternar proficiência",
      }[key] ?? key),
  }),
}));

vi.mock("./Section", () => ({
  Section: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

const BASE_ABILITIES = {
  strength: 10,
  dexterity: 10,
  constitution: 10,
  intelligence: 10,
  wisdom: 14,
  charisma: 10,
};

const BASE_PROFS: Record<string, number> = {
  acrobatics: 0,
  animalHandling: 0,
  arcana: 0,
  athletics: 0,
  deception: 0,
  history: 0,
  insight: 0,
  intimidation: 0,
  investigation: 0,
  medicine: 0,
  nature: 0,
  perception: 1,
  performance: 0,
  persuasion: 0,
  religion: 0,
  sleightOfHand: 0,
  stealth: 0,
  survival: 0,
};

const noop = () => {};

describe("Skills", () => {
  it("renders base passive perception with no bonus", () => {
    const markup = renderToStaticMarkup(
      <Skills
        abilities={BASE_ABILITIES as any}
        skillProficiencies={BASE_PROFS as any}
        level={1}
        onCycleProf={noop}
      />,
    );

    expect(markup).toContain("Percepção Passiva:");
    expect(markup).toContain(">14<");
    expect(markup).not.toContain("Sabedoria");
  });

  it("renders bonus breakdown when sources provided", () => {
    const markup = renderToStaticMarkup(
      <Skills
        abilities={BASE_ABILITIES as any}
        skillProficiencies={BASE_PROFS as any}
        level={1}
        onCycleProf={noop}
        passivePerceptionBonus={5}
        passivePerceptionBonusSources={[
          { label: "Sabedoria da Coruja", value: 5, groupKey: "a" },
        ]}
      />,
    );

    expect(markup).toContain("Percepção Passiva:");
    expect(markup).toContain(">19<");
    expect(markup).toContain("Base 14 + Sabedoria da Coruja +5");
  });

  it("does not show bonus text when bonus is 0", () => {
    const markup = renderToStaticMarkup(
      <Skills
        abilities={BASE_ABILITIES as any}
        skillProficiencies={BASE_PROFS as any}
        level={1}
        onCycleProf={noop}
        passivePerceptionBonus={0}
        passivePerceptionBonusSources={[]}
      />,
    );

    expect(markup).toContain("Percepção Passiva:");
    expect(markup).toContain(">14<");
    expect(markup).not.toContain("Base 14 +");
  });
});
