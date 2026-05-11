import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import type { ActiveEffect } from "../../../shared/api/combatRepo";
import { ActiveEffectDebugPanel } from "./ActiveEffectDebugPanel";

vi.mock("../../../shared/hooks/useLocale", () => ({
  useLocale: () => ({
    t: (key: string) => key,
  }),
}));

describe("ActiveEffectDebugPanel", () => {
  it("renderiza metadados contextuais do efeito ativo", () => {
    const markup = renderToStaticMarkup(
      <ActiveEffectDebugPanel
        targetDisplayName="Caster"
        effects={[
          {
            id: "effect-1",
            kind: "spell_effect",
            duration_type: "manual",
            created_at: "2026-05-01T00:00:00Z",
            display_label: "Friends",
            metadata: {
              source_spell_name: "Friends",
              selected_target_display_name: "Guard Captain",
              against: "selected_target",
              concentration: false,
              context_origin: "initial_cast",
              declarative_effect: {
                type: "advantage_on_checks",
                params: { ability: "charisma" },
              },
            },
          },
        ]}
      />,
    );

    expect(markup).toContain("Friends");
    expect(markup).toContain("Vantagem em testes de Carisma");
  });

  it("exibe PV temporários concedidos com valor final e aviso de não expiração", () => {
    const markup = renderToStaticMarkup(
      <ActiveEffectDebugPanel
        targetDisplayName="Goblin A"
        effects={[
          {
            id: "effect-2",
            kind: "temp_hp_granted" as ActiveEffect["kind"],
            duration_type: "manual",
            created_at: "2026-05-01T00:00:00Z",
            display_label: "Enhance Ability",
            metadata: {
              source_spell_name: "Enhance Ability",
              rolled_temp_hp: 9,
              applied_temp_hp: true,
              previous_temp_hp: 3,
              final_temp_hp: 9,
              does_not_expire_temp_hp: true,
              declarative_effect: {
                type: "grant_temp_hp",
                params: { dice: "2d6" },
              },
            },
          },
        ]}
      />,
    );

    expect(markup).toContain("PV temporários: +9 (final: 9).");
    expect(markup).toContain("Não expiram com a concentração");
  });

  it("exibe PV temporários pendentes quando não aplicado ainda", () => {
    const markup = renderToStaticMarkup(
      <ActiveEffectDebugPanel
        targetDisplayName="Goblin A"
        effects={[
          {
            id: "effect-3",
            kind: "temp_hp_granted" as ActiveEffect["kind"],
            duration_type: "manual",
            created_at: "2026-05-01T00:00:00Z",
            display_label: "Enhance Ability",
            metadata: {
              source_spell_name: "Enhance Ability",
              rolled_temp_hp: 7,
              applied_temp_hp: false,
              does_not_expire_temp_hp: true,
              declarative_effect: {
                type: "grant_temp_hp",
                params: { dice: "2d6" },
              },
            },
          },
        ]}
      />,
    );

    expect(markup).toContain("PV temporários: 7");
    expect(markup).toContain("aguardando aplicação");
  });

  it("exibe bônus de perícia passiva", () => {
    const markup = renderToStaticMarkup(
      <ActiveEffectDebugPanel
        targetDisplayName="Ranger"
        effects={[
          {
            id: "effect-4",
            kind: "spell_effect",
            duration_type: "manual",
            created_at: "2026-05-01T00:00:00Z",
            display_label: "Enhance Ability",
            metadata: {
              source_spell_name: "Enhance Ability",
              declarative_effect: {
                type: "passive_skill_bonus",
                params: { skill: "perception", bonus: 5 },
              },
            },
          },
        ]}
      />,
    );

    expect(markup).toContain("Bônus passivo: +5 em perception");
  });

  it("exibe multiplicador de capacidade de carga", () => {
    const markup = renderToStaticMarkup(
      <ActiveEffectDebugPanel
        targetDisplayName="Fighter"
        effects={[
          {
            id: "effect-5",
            kind: "spell_effect",
            duration_type: "manual",
            created_at: "2026-05-01T00:00:00Z",
            display_label: "Enhance Ability",
            metadata: {
              source_spell_name: "Enhance Ability",
              declarative_effect: {
                type: "carrying_capacity_multiplier",
                params: { multiplier: 2 },
              },
            },
          },
        ]}
      />,
    );

    expect(markup).toContain("Capacidade de carga: x2");
  });

  it("exibe limiar de imunidade a queda", () => {
    const markup = renderToStaticMarkup(
      <ActiveEffectDebugPanel
        targetDisplayName="Rogue"
        effects={[
          {
            id: "effect-6",
            kind: "spell_effect",
            duration_type: "manual",
            created_at: "2026-05-01T00:00:00Z",
            display_label: "Enhance Ability",
            metadata: {
              source_spell_name: "Enhance Ability",
              declarative_effect: {
                type: "fall_damage_immunity_threshold",
                params: { max_distance_meters: 6 },
              },
            },
          },
        ]}
      />,
    );

    expect(markup).toContain("Imunidade a queda: até 6m");
  });

  it("não explode com metadata vazia ou ausente", () => {
    const markup = renderToStaticMarkup(
      <ActiveEffectDebugPanel
        effects={[
          {
            id: "old-effect",
            kind: "spell_effect",
            duration_type: "manual",
            created_at: "2024-01-01T00:00:00Z",
            display_label: "Old Spell",
            metadata: null,
          },
          {
            id: "partial-effect",
            kind: "temp_hp_granted" as ActiveEffect["kind"],
            duration_type: "manual",
            created_at: "2024-01-01T00:00:00Z",
            display_label: "Bear's Endurance",
            metadata: {},
          },
        ]}
      />,
    );

    expect(markup).not.toContain("undefined");
    expect(markup).not.toContain("NaN");
  });
});
