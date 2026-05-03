import { describe, expect, it } from "vitest";
import { deriveCheckModifierPreviewSources } from "./checkModifierSources";

describe("deriveCheckModifierPreviewSources", () => {
  const owlsWisdomEffect = {
    id: "effect-1",
    kind: "spell_effect" as const,
    duration_type: "manual" as const,
    created_at: "2026-05-02T00:00:00Z",
    metadata: {
      source_spell_name: "Sabedoria da Coruja",
      declarative_effect: {
        type: "advantage_on_checks",
        params: {
          ability: "wisdom",
          against: "any",
        },
      },
    },
  };

  it("aplica vantagem em teste de habilidade compatível", () => {
    const preview = deriveCheckModifierPreviewSources([owlsWisdomEffect], {
      rollType: "ability",
      ability: "wisdom",
    });

    expect(preview).toHaveLength(1);
    expect(preview[0]?.applied).toBe(true);
    expect(preview[0]?.source_label).toBe("Sabedoria da Coruja");
  });

  it("aplica vantagem em perícia baseada na habilidade compatível", () => {
    const preview = deriveCheckModifierPreviewSources([owlsWisdomEffect], {
      rollType: "skill",
      skill: "perception",
    });

    expect(preview).toHaveLength(1);
    expect(preview[0]?.applied).toBe(true);
    expect(preview[0]?.skill).toBe("perception");
  });

  it("não aplica vantagem em habilidade diferente", () => {
    const preview = deriveCheckModifierPreviewSources([owlsWisdomEffect], {
      rollType: "ability",
      ability: "strength",
    });

    expect(preview).toHaveLength(1);
    expect(preview[0]?.applied).toBe(false);
    expect(preview[0]?.skip_reason).toBe("ability_mismatch");
  });
});
