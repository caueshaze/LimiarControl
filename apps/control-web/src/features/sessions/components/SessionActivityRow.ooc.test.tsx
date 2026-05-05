import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import type { ActivityEvent } from "../../../shared/api/sessionsRepo";
import { SessionActivityRow } from "./SessionActivityRow";

vi.mock("../../../shared/hooks/useLocale", () => ({
  useLocale: () => ({
    t: (key: string) =>
      ({
        "sessionActivity.unknownActor": "desconhecido",
        "sessionActivity.unknownTarget": "alvo desconhecido",
        "sessionActivity.onTarget": "em",
        "sessionActivity.castVerb": "lançou",
        "sessionActivity.castByGmDid": "fez",
        "sessionActivity.castByGmCastVerb": "lançar",
        "sessionActivity.usingSlotLevel": "usando espaço de",
        "sessionActivity.slotLevelSuffix": "º nível.",
        "sessionActivity.removedEffectVerb": "removeu",
        "sessionActivity.concentrationEndedSentence": "A concentração foi encerrada.",
        "sessionActivity.previousConcentrationEndedPrefix": "A concentração anterior em",
      }[key] ?? key),
  }),
}));

const castBase: ActivityEvent = {
  type: "out_of_combat_spell_cast",
  actorDisplayName: "Caue",
  actorPlayerUserId: "caster-1",
  createdEffectIds: ["eff-1"],
  displayName: "Caue",
  newConcentrationGroup: "grp-new",
  previousConcentrationGroup: "grp-old",
  replacedConcentration: false,
  sessionOffsetSeconds: 42,
  spellKey: "shield_of_faith",
  spellName: "Escudo da Fé",
  targetDisplayName: "Ally B",
  targetPlayerUserId: "ally-b",
  timestamp: "2026-05-05T10:00:00Z",
  userId: "caster-1",
};

describe("SessionActivityRow out-of-combat events", () => {
  it("renders cast line with slot level", () => {
    const markup = renderToStaticMarkup(
      <SessionActivityRow
        event={{
          ...castBase,
          slotLevel: 2,
          variantLabel: "Sabedoria da Coruja",
        }}
      />,
    );
    expect(markup).toContain("Caue");
    expect(markup).toContain("lançou");
    expect(markup).toContain("Escudo da Fé — Sabedoria da Coruja");
    expect(markup).toContain("em");
    expect(markup).toContain("Ally B");
    expect(markup).toContain("usando espaço de");
    expect(markup).toContain("2");
    expect(markup).toContain("º nível.");
  });

  it("renders cast line without slot level", () => {
    const markup = renderToStaticMarkup(
      <SessionActivityRow
        event={{
          ...castBase,
          slotLevel: null,
          variantLabel: null,
        }}
      />,
    );
    expect(markup).toContain("Caue");
    expect(markup).toContain("lançou");
    expect(markup).toContain("Escudo da Fé");
    expect(markup).toContain("em");
    expect(markup).toContain("Ally B");
    expect(markup).toContain("Escudo da Fé</span> em");
  });

  it("renders GM cast line with actor and caster when cast_by_gm is true", () => {
    const markup = renderToStaticMarkup(
      <SessionActivityRow
        event={{
          ...castBase,
          castByGm: true,
          actorDisplayName: "GM",
          casterDisplayName: "Aelar",
          targetDisplayName: "Luna",
          spellName: "Melhorar Habilidade",
          variantLabel: "Sabedoria da Coruja",
        }}
      />,
    );
    expect(markup).toContain("GM");
    expect(markup).toContain("fez");
    expect(markup).toContain("Aelar");
    expect(markup).toContain("lançar");
    expect(markup).toContain("Melhorar Habilidade — Sabedoria da Coruja");
    expect(markup).toContain("Luna");
  });

  it("renders previous concentration context when replacement metadata exists", () => {
    const markup = renderToStaticMarkup(
      <SessionActivityRow
        event={{
          ...castBase,
          replacedConcentration: true,
          previousSpellName: "Melhorar Habilidade",
          previousVariantLabel: "Sabedoria da Coruja",
        }}
      />,
    );
    expect(markup).toContain("A concentração anterior em");
    expect(markup).toContain("Melhorar Habilidade — Sabedoria da Coruja");
  });

  it("renders effect removal line with concentration ended note", () => {
    const event: ActivityEvent = {
      type: "out_of_combat_effect_removed",
      actorDisplayName: "Caue",
      actorPlayerUserId: "caster-1",
      brokeConcentrationGroup: true,
      concentrationGroup: "grp-1",
      displayName: "Caue",
      effectLabel: "Escudo da Fé",
      removedEffectId: "eff-1",
      sessionOffsetSeconds: 5,
      sourceSpellName: "Escudo da Fé",
      timestamp: "2026-05-05T10:01:00Z",
      userId: "caster-1",
      variantLabel: null,
    };
    const markup = renderToStaticMarkup(<SessionActivityRow event={event} />);
    expect(markup).toContain("Caue");
    expect(markup).toContain("removeu");
    expect(markup).toContain("Escudo da Fé");
    expect(markup).toContain("A concentração foi encerrada.");
  });

  it("renders effect removal line without concentration note when unrelated", () => {
    const event: ActivityEvent = {
      type: "out_of_combat_effect_removed",
      actorDisplayName: "Caue",
      actorPlayerUserId: "caster-1",
      brokeConcentrationGroup: false,
      concentrationGroup: null,
      displayName: "Caue",
      effectLabel: "Armadura Arcana",
      removedEffectId: "eff-2",
      sessionOffsetSeconds: 5,
      sourceSpellName: "Armadura Arcana",
      timestamp: "2026-05-05T10:01:30Z",
      userId: "caster-1",
      variantLabel: null,
    };
    const markup = renderToStaticMarkup(<SessionActivityRow event={event} />);
    expect(markup).toContain("Caue");
    expect(markup).toContain("removeu");
    expect(markup).toContain("Armadura Arcana");
    expect(markup).not.toContain("A concentração foi encerrada.");
  });
});
