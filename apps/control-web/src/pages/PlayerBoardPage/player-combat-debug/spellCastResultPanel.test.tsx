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
});
