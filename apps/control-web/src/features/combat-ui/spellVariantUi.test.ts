import { describe, expect, it } from "vitest";
import {
  buildPendingSaveReason,
  formatEffectContextDebug,
  formatManualNotesByTarget,
  formatVariantAssignmentDebug,
  resolveTargetVariantLabel,
} from "./spellVariantUi";

describe("spellVariantUi", () => {
  it("resolve a variante correta por alvo mesmo fora de ordem", () => {
    const targetVariantAssignments = [
      {
        target_participant_id: "enemy-b",
        variant_key: "owls_wisdom",
        variant_label: "Sabedoria da Coruja",
      },
      {
        target_participant_id: "enemy-a",
        variant_key: "foxs_cunning",
        variant_label: "Esperteza da Raposa",
      },
    ];

    expect(
      resolveTargetVariantLabel({
        targetVariantAssignments,
        selectedVariantKey: null,
        targetParticipantId: "enemy-a",
      }),
    ).toBe("Esperteza da Raposa");

    expect(
      resolveTargetVariantLabel({
        targetVariantAssignments,
        selectedVariantKey: null,
        targetParticipantId: "enemy-b",
      }),
    ).toBe("Sabedoria da Coruja");
  });

  it("monta o reason do pending save com a variante reidratada", () => {
    expect(
      buildPendingSaveReason({
        spellName: "Modal Save Test Spell",
        saveAbility: "wisdom",
        variantLabel: "Esperteza da Raposa",
      }),
    ).toBe("Modal Save Test Spell - save de wisdom - variante: Esperteza da Raposa");
  });

  it("faz fallback visual seguro quando a chave da variante e desconhecida", () => {
    expect(
      resolveTargetVariantLabel({
        selectedVariantKey: "mystery_mode",
      }),
    ).toBe("Variante desconhecida (Mystery Mode)");
  });

  it("formata assignments e notas manuais por alvo", () => {
    expect(
      formatVariantAssignmentDebug(
        [
          {
            target_participant_id: "enemy-a",
            variant_key: "foxs_cunning",
            variant_label: "Esperteza da Raposa",
          },
        ],
        [
          {
            target_participant_id: "enemy-a",
            target_display_name: "Goblin A",
            variant_key: "foxs_cunning",
            variant_label: "Esperteza da Raposa",
            manual_notes: [{ key: "a", label: "Manual A", description: "Descricao A" }],
          },
        ],
      ),
    ).toEqual(["Goblin A: Esperteza da Raposa"]);

    expect(
      formatManualNotesByTarget([
        {
          target_participant_id: "enemy-a",
          target_display_name: "Goblin A",
          variant_key: "foxs_cunning",
          variant_label: "Esperteza da Raposa",
          manual_notes: [{ key: "a", label: "Manual A", description: "Descricao A" }],
        },
      ]),
    ).toEqual(["Goblin A: Manual A - Descricao A"]);
  });

  it("formata contexto debug de active effect declarativo", () => {
    const lines = formatEffectContextDebug(
      {
        id: "effect-1",
        kind: "spell_effect",
        duration_type: "manual",
        created_at: "2026-05-01T00:00:00Z",
        metadata: {
          source_spell_name: "Friends",
          selected_variant_label: "Esplendor da Aguia",
          effect_target_display_name: "Caster",
          selected_target_display_name: "Guard Captain",
          against: "selected_target",
          context_origin: "initial_cast",
          concentration: true,
          concentration_group: "group-1",
          declarative_effect: {
            type: "advantage_on_checks",
            params: { ability: "charisma" },
          },
        },
      },
      { targetDisplayName: "Caster" },
    );

    expect(lines).toContain("Source: Friends");
    expect(lines).toContain("Variant: Esplendor da Aguia");
    expect(lines).toContain("Selected target: Guard Captain");
    expect(lines).toContain("Against: selected target");
    expect(lines).toContain("Concentration: group-1");
    expect(lines).toContain("Advantage: charisma checks");
  });
});
