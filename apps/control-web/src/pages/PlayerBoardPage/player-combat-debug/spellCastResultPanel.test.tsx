import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { SpellCastResultPanel } from "./SpellCastResultPanel";

const baseProps = {
  effectDiceLabel: "1d10",
  effectKindLabel: "dano",
  effectMode: "choose" as const,
  effectRollCount: 1,
  effectRollValues: [1, 2, 3],
  loading: false,
  manualEffectRolls: [],
  onClose: () => undefined,
  onEffectModeChange: () => undefined,
  onManualEffectRollsChange: () => undefined,
  onSubmitEffect: () => undefined,
};

describe("SpellCastResultPanel", () => {
  it("exibe effect_instance_outcomes quando presente", () => {
    const markup = renderToStaticMarkup(
      <SpellCastResultPanel
        {...baseProps}
        result={{
          spell_name: "Magic Missile",
          spell_canonical_key: "magic_missile",
          action_kind: "direct_damage",
          effect_kind: "damage",
          damage: 18,
          healing: 0,
          target_display_name: "Goblin A",
          target_kind: "session_entity",
          effect_instance_outcomes: [
            {
              instance_index: 1,
              target_ref_id: "session_entity:goblin-a",
              target_display_name: "Goblin A",
              target_kind: "session_entity",
              damage: 4,
            },
          ],
        }}
      />,
    );

    expect(markup).toContain("Míssil 1 -&gt; Goblin A: 4 dano");
  });

  it("exibe dano por missil para Magic Missile", () => {
    const markup = renderToStaticMarkup(
      <SpellCastResultPanel
        {...baseProps}
        result={{
          spell_name: "Magic Missile",
          spell_canonical_key: "magic_missile",
          action_kind: "direct_damage",
          effect_kind: "damage",
          damage: 9,
          healing: 0,
          target_display_name: "Goblin A",
          target_kind: "session_entity",
          effect_instance_outcomes: [
            {
              instance_index: 1,
              target_ref_id: "session_entity:goblin-a",
              target_display_name: "Goblin A",
              target_kind: "session_entity",
              damage: 4,
            },
            {
              instance_index: 2,
              target_ref_id: "session_entity:goblin-b",
              target_display_name: "Goblin B",
              target_kind: "session_entity",
              damage: 5,
            },
          ],
        }}
      />,
    );

    expect(markup).toContain("Míssil 1 -&gt; Goblin A: 4 dano");
    expect(markup).toContain("Míssil 2 -&gt; Goblin B: 5 dano");
  });

  it("exibe hit/miss e dano para Eldritch Blast", () => {
    const markup = renderToStaticMarkup(
      <SpellCastResultPanel
        {...baseProps}
        result={{
          spell_name: "Eldritch Blast",
          spell_canonical_key: "eldritch_blast",
          action_kind: "spell_attack",
          effect_kind: "damage",
          damage: 7,
          healing: 0,
          target_display_name: "Goblin A",
          target_kind: "session_entity",
          effect_instance_outcomes: [
            {
              instance_index: 1,
              target_ref_id: "session_entity:goblin-a",
              target_display_name: "Goblin A",
              target_kind: "session_entity",
              is_hit: true,
              damage: 7,
            },
            {
              instance_index: 2,
              target_ref_id: "session_entity:orc-b",
              target_display_name: "Orc B",
              target_kind: "session_entity",
              is_hit: false,
            },
          ],
        }}
      />,
    );

    expect(markup).toContain("Feixe 1 -&gt; Goblin A: acerto, 7 dano");
    expect(markup).toContain("Feixe 2 -&gt; Orc B: erro");
  });

  it("nao quebra resultados antigos sem effect_instance_outcomes", () => {
    const markup = renderToStaticMarkup(
      <SpellCastResultPanel
        {...baseProps}
        result={{
          spell_name: "Acid Splash",
          spell_canonical_key: "acid_splash",
          action_kind: "saving_throw",
          effect_kind: "damage",
          damage: 6,
          healing: 0,
          is_saved: false,
          target_display_name: "Goblin A",
          target_kind: "session_entity",
          effect_dice: "1d6",
          effect_rolls: [6],
          base_effect: 6,
          effect_bonus: 0,
        }}
      />,
    );

    expect(markup).toContain("1d6: [6] = 6");
  });

  it("exibe narrativa de metade no erro para Flecha Ácida", () => {
    const markup = renderToStaticMarkup(
      <SpellCastResultPanel
        {...baseProps}
        result={{
          spell_name: "Flecha Ácida",
          spell_canonical_key: "acid_arrow",
          action_kind: "spell_attack",
          effect_kind: "damage",
          damage: 4,
          healing: 0,
          is_hit: false,
          damage_mode: "half_on_miss",
          target_display_name: "Goblin A",
          target_kind: "session_entity",
          effect_dice: "4d4",
          effect_rolls: [2, 2, 2, 3],
          base_effect: 9,
          effect_bonus: 0,
        }}
      />,
    );

    expect(markup).toContain("errou Goblin A, mas ainda causou metade do dano: 4");
    expect(markup).toContain("metade aplicada = 4");
  });

  it("explica quando um alvo de area foi excluido por guardrail mecanico", () => {
    const markup = renderToStaticMarkup(
      <SpellCastResultPanel
        {...baseProps}
        result={{
          spell_name: "Fireball",
          spell_canonical_key: "fireball",
          action_kind: "saving_throw",
          effect_kind: "damage",
          damage: 24,
          healing: 0,
          target_display_name: "Area effect",
          target_kind: "session_entity",
          area_shape: "sphere",
          affected_target_ref_ids: ["charmer-1", "enemy-1"],
          affected_cells: [{ x: 10, y: 10 }],
          area_target_outcomes: [
            {
              target_ref_id: "charmer-1",
              target_display_name: "Charmed Noble",
              target_kind: "player",
              excluded_by_guardrail: true,
              guardrail_reason: "You cannot use a hostile spell against Charmed Noble while charmed.",
            },
            {
              target_ref_id: "enemy-1",
              target_display_name: "Goblin A",
              target_kind: "session_entity",
              is_saved: false,
              damage_applied: 24,
            },
          ],
        }}
      />,
    );

    expect(markup).toContain("Charmed Noble: excluído por regra mecânica");
    expect(markup).toContain("You cannot use a hostile spell against Charmed Noble while charmed.");
    expect(markup).toContain("1 alvo na área foi excluído por regras mecânicas.");
  });

  it("exibe variante resolvida e notas manuais agrupadas por alvo", () => {
    const markup = renderToStaticMarkup(
      <SpellCastResultPanel
        {...baseProps}
        result={{
          spell_name: "Modal Save Test Spell",
          spell_canonical_key: "modal_save_test_spell",
          selected_variant_key: "foxs_cunning",
          selected_variant_label: "Esperteza da Raposa",
          context_origin: "pending_spell",
          concentration_group: "group-1",
          action_kind: "saving_throw",
          effect_kind: "damage",
          damage: 7,
          healing: 0,
          is_saved: false,
          target_display_name: "Goblin A",
          target_kind: "session_entity",
          target_variant_assignments: [
            {
              target_participant_id: "enemy-1",
              variant_key: "foxs_cunning",
              variant_label: "Esperteza da Raposa",
            },
            {
              target_participant_id: "enemy-2",
              variant_key: "owls_wisdom",
              variant_label: "Sabedoria da Coruja",
            },
          ],
          manual_notes_by_target: [
            {
              target_participant_id: "enemy-1",
              target_display_name: "Goblin A",
              variant_key: "foxs_cunning",
              variant_label: "Esperteza da Raposa",
              manual_notes: [{ key: "a", label: "Manual A", description: "Descricao A" }],
            },
            {
              target_participant_id: "enemy-2",
              target_display_name: "Goblin B",
              variant_key: "owls_wisdom",
              variant_label: "Sabedoria da Coruja",
              manual_notes: [{ key: "b", label: "Manual B", description: "Descricao B" }],
            },
          ],
        }}
      />,
    );

    expect(markup).toContain("Origem: pending spell");
    expect(markup).toContain("Concentração: group-1");
    expect(markup).toContain("Goblin A: Esperteza da Raposa");
    expect(markup).toContain("Manual A - Descricao A");
    expect(markup).toContain("Goblin B: Sabedoria da Coruja");
    expect(markup).toContain("Manual B - Descricao B");
  });

  it("exibe efeitos declarativos aplicados por alvo sem duplicar nota manual equivalente", () => {
    const markup = renderToStaticMarkup(
      <SpellCastResultPanel
        {...baseProps}
        result={{
          spell_name: "Enhance Ability",
          spell_canonical_key: "enhance_ability",
          action_kind: "utility",
          effect_kind: "damage",
          damage: 0,
          healing: 0,
          target_display_name: "Fighter",
          target_kind: "player",
          applied_declarative_effects_by_target: [
            {
              target_display_name: "Fighter",
              target_participant_id: "ally-1",
              variant_key: "bulls_strength",
              variant_label: "Força do Touro",
              effects: [
                {
                  type: "carrying_capacity_multiplier",
                  params: { multiplier: 2 },
                },
              ],
            },
          ],
          manual_notes_by_target: [
            {
              target_participant_id: "ally-1",
              target_display_name: "Fighter",
              variant_key: "bulls_strength",
              variant_label: "Força do Touro",
              manual_notes: [
                {
                  key: "carrying_capacity_multiplier",
                  label: "Capacidade de carga",
                  description: "Duplicada",
                },
                {
                  key: "reminder",
                  label: "Lembrete",
                  description: "Conferir mochila",
                },
              ],
            },
          ],
        }}
      />,
    );

    expect(markup).toContain("Fighter");
    expect(markup).toContain("Variante: Força do Touro");
    expect(markup).toContain("Capacidade de carga: x2");
    expect(markup).toContain("Lembrete - Conferir mochila");
    expect(markup).not.toContain("Capacidade de carga - Duplicada");
  });

  it("exibe grant_temp_hp aplicado por alvo", () => {
    const markup = renderToStaticMarkup(
      <SpellCastResultPanel
        {...baseProps}
        result={{
          spell_name: "Enhance Ability",
          spell_canonical_key: "enhance_ability",
          action_kind: "utility",
          effect_kind: "damage",
          damage: 0,
          healing: 0,
          target_display_name: "Barbarian",
          target_kind: "player",
          applied_declarative_effects_by_target: [
            {
              target_display_name: "Barbarian",
              target_participant_id: "ally-2",
              variant_key: "bears_endurance",
              variant_label: "Resistência do Urso",
              effects: [
                {
                  type: "grant_temp_hp",
                  params: { dice: "2d6" },
                  observability: {
                    rolled_temp_hp: 7,
                    applied_temp_hp: true,
                    previous_temp_hp: 0,
                    final_temp_hp: 7,
                    does_not_expire_temp_hp: true,
                  },
                },
              ],
            },
          ],
        }}
      />,
    );

    expect(markup).toContain("Barbarian");
    expect(markup).toContain("Variante: Resistência do Urso");
    expect(markup).toContain("PV temporários: +7 (final: 7).");
  });

  it("exibe grant_temp_hp ignorado quando alvo ja tinha valor maior", () => {
    const markup = renderToStaticMarkup(
      <SpellCastResultPanel
        {...baseProps}
        result={{
          spell_name: "Enhance Ability",
          spell_canonical_key: "enhance_ability",
          action_kind: "utility",
          effect_kind: "damage",
          damage: 0,
          healing: 0,
          target_display_name: "Barbarian",
          target_kind: "player",
          applied_declarative_effects_by_target: [
            {
              target_display_name: "Barbarian",
              target_participant_id: "ally-2",
              variant_key: "bears_endurance",
              variant_label: "Resistência do Urso",
              effects: [
                {
                  type: "grant_temp_hp",
                  params: { dice: "2d6" },
                  observability: {
                    rolled_temp_hp: 5,
                    applied_temp_hp: true,
                    previous_temp_hp: 8,
                    final_temp_hp: 8,
                    does_not_expire_temp_hp: true,
                  },
                },
              ],
            },
          ],
        }}
      />,
    );

    expect(markup).toContain("PV temporários: 5 rolados, mantidos 8 existentes.");
  });
});
