import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { AuthoritativeRollDialog } from "./AuthoritativeRollDialog";

vi.mock("../../../shared/hooks/useLocale", () => ({
  useLocale: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock("../hooks/useRollResolution", () => ({
  useRollResolution: () => ({
    result: null,
    loading: false,
    error: null,
    submitRoll: vi.fn(),
    clearResult: vi.fn(),
  }),
}));

vi.mock("./RollResultCard", () => ({
  RollResultCard: () => <div>result</div>,
}));

describe("AuthoritativeRollDialog", () => {
  it("renderiza explicacoes debug aplicadas e puladas", () => {
    const markup = renderToStaticMarkup(
      <AuthoritativeRollDialog
        request={{
          rollType: "ability",
          ability: "charisma",
          advantageMode: "advantage",
          targetParticipantId: "guard-1",
          reason: "Persuasion check",
          debugModifiers: [
            {
              source_label: "Friends",
              modifier_type: "advantage",
              roll_type: "ability",
              ability: "charisma",
              against: "selected_target",
              selected_target_participant_id: "guard-1",
              selected_target_display_name: "Guard Captain",
              applied: true,
              skip_reason: null,
            },
            {
              source_label: "Friends",
              modifier_type: "advantage",
              roll_type: "ability",
              ability: "charisma",
              against: "selected_target",
              selected_target_participant_id: "guard-2",
              selected_target_display_name: "Other Guard",
              applied: false,
              skip_reason: "target_mismatch",
            },
          ],
        }}
        sessionId="session-1"
        actorKind="player"
        actorRefId="player-1"
        onClose={() => undefined}
      />,
    );

    expect(markup).toContain("Effect Context");
    expect(markup).toContain("Friends: advantage em charisma contra Guard Captain");
    expect(markup).toContain("Não aplicado: Friends só vale contra Other Guard");
  });
});
