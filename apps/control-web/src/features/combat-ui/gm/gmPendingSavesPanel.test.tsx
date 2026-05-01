import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { GmPendingSavesPanel } from "./GmPendingSavesPanel";

vi.mock("../../../shared/hooks/useLocale", () => ({
  useLocale: () => ({
    t: (key: string) => key,
  }),
}));

describe("GmPendingSavesPanel", () => {
  it("exibe a variante e as notas manuais do alvo correto", () => {
    const markup = renderToStaticMarkup(
      <GmPendingSavesPanel
        pendingSaves={[
          {
            id: "enemy-1",
            kind: "session_entity",
            ref_id: "session_entity:goblin-a",
            display_name: "Goblin A",
            initiative: 12,
            status: "active",
            team: "enemies",
            visible: true,
            actor_user_id: null,
            pending_save: {
              id: "pending-save-1",
              status: "pending",
              spell_name: "Modal Save Test Spell",
              save_ability: "wisdom",
              save_dc: 14,
              attacker_display_name: "Mage",
              selected_variant_key: "foxs_cunning",
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
                  manual_notes: [
                    {
                      key: "fox-note",
                      label: "Manual A",
                      description: "Descricao A",
                    },
                  ],
                },
                {
                  target_participant_id: "enemy-2",
                  target_display_name: "Goblin B",
                  variant_key: "owls_wisdom",
                  variant_label: "Sabedoria da Coruja",
                  manual_notes: [
                    {
                      key: "owl-note",
                      label: "Manual B",
                      description: "Descricao B",
                    },
                  ],
                },
              ],
            },
          },
        ]}
        submitting={false}
        onResolveSave={vi.fn()}
      />,
    );

    expect(markup).toContain("Variante: Esperteza da Raposa");
    expect(markup).toContain("Manual A - Descricao A");
    expect(markup).not.toContain("Manual B - Descricao B");
  });
});
