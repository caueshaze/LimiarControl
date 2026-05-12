import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { AuthoritativeRollDialog } from "./AuthoritativeRollDialog";

const useRollResolutionMock = vi.hoisted(() => vi.fn());

vi.mock("../../../shared/hooks/useLocale", () => ({
  useLocale: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock("../hooks/useRollResolution", () => ({
  useRollResolution: () => useRollResolutionMock(),
}));

vi.mock("./RollResultCard", () => ({
  RollResultCard: () => <div>result</div>,
}));

describe("AuthoritativeRollDialog", () => {
  it("exibe vantagem contextual vinda do backend", () => {
    useRollResolutionMock.mockReturnValue({
      result: {
        event_id: "roll-1",
        roll_type: "ability",
        actor_kind: "player",
        actor_ref_id: "player-1",
        actor_display_name: "Hero",
        rolls: [12, 19],
        selected_roll: 19,
        advantage_mode: "advantage",
        modifier_used: 2,
        override_used: false,
        formula: "1d20 + 2",
        total: 21,
        check_modifier_sources: [
          {
            source_label: "Sabedoria da Coruja",
            modifier_type: "advantage",
            roll_type: "ability",
            ability: "wisdom",
            against: "any",
            applied: true,
            skip_reason: null,
          },
        ],
        is_gm_roll: false,
        roll_source: "system",
        timestamp: "2026-05-01T00:00:00Z",
      },
      loading: false,
      error: null,
      submitRoll: vi.fn(),
      clearResult: vi.fn(),
    });

    const markup = renderToStaticMarkup(
      <AuthoritativeRollDialog
        request={{
          rollType: "ability",
          ability: "wisdom",
          advantageMode: "normal",
          reason: "Wisdom check",
        }}
        sessionId="session-1"
        actorKind="player"
        actorRefId="player-1"
        onClose={() => undefined}
      />,
    );

    expect(markup).toContain("Vantagem automática");
    expect(markup).toContain("Vantagem por Sabedoria da Coruja em wisdom");
  });

  it("renderiza explicacoes debug aplicadas e puladas", () => {
    useRollResolutionMock.mockReturnValue({
      result: null,
      loading: false,
      error: null,
      submitRoll: vi.fn(),
      clearResult: vi.fn(),
    });

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

    expect(markup).toContain("Contexto do efeito");
    expect(markup).toContain("Vantagem por Friends em charisma");
    expect(markup).toContain("Não aplicado: Friends só vale contra Other Guard");
  });

  it("exibe bônus de Bênção +1d4 quando backend envia roll_bonus_dice", () => {
    useRollResolutionMock.mockReturnValue({
      result: {
        event_id: "roll-2",
        roll_type: "attack",
        actor_kind: "player",
        actor_ref_id: "player-1",
        actor_display_name: "Hero",
        rolls: [12, 12],
        selected_roll: 12,
        advantage_mode: "normal",
        modifier_used: 5,
        override_used: false,
        formula: "1d20 + 5",
        total: 20,
        check_modifier_sources: [
          {
            source_label: "Bênção",
            modifier_type: "roll_bonus_dice",
            roll_type: "attack",
            dice: "1d4",
            rolls: [3],
            signed_total: 3,
            applied: true,
            skip_reason: null,
          },
        ],
        is_gm_roll: false,
        roll_source: "system",
        timestamp: "2026-05-01T00:00:00Z",
      },
      loading: false,
      error: null,
      submitRoll: vi.fn(),
      clearResult: vi.fn(),
    });

    const markup = renderToStaticMarkup(
      <AuthoritativeRollDialog
        request={{
          rollType: "attack",
          advantageMode: "normal",
          reason: "Attack roll",
        }}
        sessionId="session-1"
        actorKind="player"
        actorRefId="player-1"
        onClose={() => undefined}
      />,
    );

    expect(markup).toContain("Contexto do efeito");
    expect(markup).toContain("Bênção: +1d4");
  });

  it("exibe penalidade de Perdição -1d4 quando backend envia roll_dice_modifier", () => {
    useRollResolutionMock.mockReturnValue({
      result: {
        event_id: "roll-3",
        roll_type: "save",
        actor_kind: "player",
        actor_ref_id: "player-1",
        actor_display_name: "Hero",
        rolls: [13, 13],
        selected_roll: 13,
        advantage_mode: "normal",
        modifier_used: 2,
        override_used: false,
        formula: "1d20 + 2",
        total: 12,
        check_modifier_sources: [
          {
            source_label: "Perdição",
            modifier_type: "roll_dice_modifier",
            mode: "penalty",
            roll_type: "save",
            dice: "1d4",
            rolls: [3],
            signed_total: -3,
            display_label: "Perdição: -1d4",
            applied: true,
            skip_reason: null,
          },
        ],
        is_gm_roll: false,
        roll_source: "system",
        timestamp: "2026-05-01T00:00:00Z",
      },
      loading: false,
      error: null,
      submitRoll: vi.fn(),
      clearResult: vi.fn(),
    });

    const markup = renderToStaticMarkup(
      <AuthoritativeRollDialog
        request={{ rollType: "save", advantageMode: "normal", reason: "Saving throw" }}
        sessionId="session-1"
        actorKind="player"
        actorRefId="player-1"
        onClose={() => undefined}
      />,
    );
    expect(markup).toContain("Perdição: -1d4");
  });

  it("exibe bônus de Orientação +1d4 em teste de atributo", () => {
    useRollResolutionMock.mockReturnValue({
      result: {
        event_id: "roll-4",
        roll_type: "ability",
        actor_kind: "player",
        actor_ref_id: "player-1",
        actor_display_name: "Hero",
        rolls: [12, 12],
        selected_roll: 12,
        advantage_mode: "normal",
        modifier_used: 1,
        override_used: false,
        formula: "1d20 + 1",
        total: 16,
        check_modifier_sources: [
          {
            source_label: "Orientação",
            modifier_type: "roll_dice_modifier",
            mode: "bonus",
            roll_type: "ability",
            dice: "1d4",
            rolls: [3],
            signed_total: 3,
            display_label: "Orientação: +1d4",
            applied: true,
            skip_reason: null,
          },
        ],
        is_gm_roll: false,
        roll_source: "system",
        timestamp: "2026-05-01T00:00:00Z",
      },
      loading: false,
      error: null,
      submitRoll: vi.fn(),
      clearResult: vi.fn(),
    });

    const markup = renderToStaticMarkup(
      <AuthoritativeRollDialog
        request={{ rollType: "ability", advantageMode: "normal", reason: "Ability check" }}
        sessionId="session-1"
        actorKind="player"
        actorRefId="player-1"
        onClose={() => undefined}
      />,
    );
    expect(markup).toContain("Orientação: +1d4");
  });
});
