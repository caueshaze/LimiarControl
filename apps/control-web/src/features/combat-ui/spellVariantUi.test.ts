import { describe, expect, it } from "vitest";
import {
  buildPendingSaveReason,
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
});
