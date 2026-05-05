import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { CharacterActiveEffectsPanel } from "./CharacterActiveEffectsPanel";

vi.mock("../../../shared/hooks/useLocale", () => ({
  useLocale: () => ({
    t: (key: string) =>
      ({
        "playerBoard.activeEffectsLabel": "Efeitos ativos",
        "playerBoard.activeEffectFallback": "Efeito",
        "playerBoard.removeEffect": "Remover",
        "playerBoard.removingEffect": "Removendo...",
        "playerBoard.lifecycleConcentration": "Concentração",
        "playerBoard.lifecycleManual": "Manual",
        "playerBoard.lifecycleRounds": "{count} rodadas",
        "playerBoard.lifecycleRoundsUnknown": "Por rodadas",
        "playerBoard.lifecycleUntilTurnStart": "Até início do turno",
        "playerBoard.lifecycleUntilTurnEnd": "Até fim do turno",
        "playerBoard.lifecycleUntilLongRest": "Até descanso longo",
        "playerBoard.lifecycleUntilShortRest": "Até descanso curto",
        "playerBoard.lifecycleUntilRemoved": "Até remover",
        "playerBoard.lifecycleLongRest": "Limpa no descanso longo",
      }[key] ?? key),
  }),
}));

describe("CharacterActiveEffectsPanel", () => {
  it("renderiza painel quando há efeitos ativos", () => {
    const markup = renderToStaticMarkup(
      <CharacterActiveEffectsPanel
        activeEffects={[
          {
            id: "eff-1",
            kind: "spell_effect",
            duration_type: "manual",
            created_at: "2026-01-01T00:00:00Z",
            display_label: "Owl's Wisdom",
            metadata: {
              source_spell_name: "Owl's Wisdom",
              concentration: true,
              concentration_group: "grp-1",
            },
          },
        ] as any}
        onRemoveEffect={() => undefined}
      />,
    );

    expect(markup).toContain("Efeitos ativos");
    expect(markup).toContain("Owl&#x27;s Wisdom");
    expect(markup).toContain("Concentração");
    expect(markup).toContain("Manual");
    expect(markup).toContain("Limpa no descanso longo");
    expect(markup).toContain("Remover");
  });

  it("não renderiza quando a lista está vazia", () => {
    const markup = renderToStaticMarkup(
      <CharacterActiveEffectsPanel
        activeEffects={[]}
        onRemoveEffect={() => undefined}
      />,
    );

    expect(markup).not.toContain("Efeitos ativos");
    expect(markup).toBe("");
  });

  it("não renderiza botão Remover quando onRemoveEffect não é passado", () => {
    const markup = renderToStaticMarkup(
      <CharacterActiveEffectsPanel
        activeEffects={[
          {
            id: "eff-1",
            kind: "spell_effect",
            duration_type: "manual",
            created_at: "2026-01-01T00:00:00Z",
            display_label: "Bless",
            metadata: {},
          },
        ] as any}
      />,
    );

    expect(markup).toContain("Efeitos ativos");
    expect(markup).toContain("Bless");
    expect(markup).not.toContain("Remover");
  });

  it("desabilita botão e mostra 'Removendo...' quando removingEffectId corresponde", () => {
    const markup = renderToStaticMarkup(
      <CharacterActiveEffectsPanel
        activeEffects={[
          {
            id: "eff-1",
            kind: "spell_effect",
            duration_type: "manual",
            created_at: "2026-01-01T00:00:00Z",
            display_label: "Bless",
            metadata: {},
          },
        ] as any}
        removingEffectId="eff-1"
        onRemoveEffect={() => undefined}
      />,
    );

    expect(markup).toContain("disabled");
    expect(markup).toContain("Removendo...");
    expect(markup).not.toContain(">Remover<");
  });

  it("renderiza badge de rodadas com contagem", () => {
    const markup = renderToStaticMarkup(
      <CharacterActiveEffectsPanel
        activeEffects={[
          {
            id: "eff-1",
            kind: "spell_effect",
            duration_type: "rounds",
            remaining_rounds: 5,
            created_at: "2026-01-01T00:00:00Z",
            display_label: "Haste",
            metadata: {},
          },
        ] as any}
        onRemoveEffect={() => undefined}
      />,
    );

    expect(markup).toContain("Haste");
    expect(markup).toContain("5 rodadas");
  });

  it("renderiza badge de until-turn-start", () => {
    const markup = renderToStaticMarkup(
      <CharacterActiveEffectsPanel
        activeEffects={[
          {
            id: "eff-1",
            kind: "condition",
            condition_type: "restrained",
            duration_type: "until_turn_start",
            expires_on: "turn_start",
            created_at: "2026-01-01T00:00:00Z",
            metadata: {},
          },
        ] as any}
        onRemoveEffect={() => undefined}
      />,
    );

    expect(markup).toContain("Até início do turno");
  });
});
