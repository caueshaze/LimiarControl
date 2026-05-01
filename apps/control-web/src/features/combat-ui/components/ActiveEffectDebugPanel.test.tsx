import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
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

    expect(markup).toContain("Source: Friends");
    expect(markup).toContain("Selected target: Guard Captain");
    expect(markup).toContain("Against: selected target");
    expect(markup).toContain("Advantage: charisma checks");
  });
});
