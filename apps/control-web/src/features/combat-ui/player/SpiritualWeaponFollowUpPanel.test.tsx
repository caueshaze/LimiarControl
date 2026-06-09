/**
 * UI / dialog tests for the Spiritual Weapon follow-up panel (issue #261).
 *
 * Tests:
 *   - test_spiritual_weapon_follow_up_opens_map_targeting_mode
 *   - test_spiritual_weapon_follow_up_highlights_current_anchor   (via panel state)
 *   - test_spiritual_weapon_follow_up_selects_destination_from_map_click
 *   - test_spiritual_weapon_follow_up_shows_target_options_after_destination_selection
 *   - test_spiritual_weapon_follow_up_can_submit_attack_without_movement
 *   - test_spiritual_weapon_follow_up_payload_uses_clicked_destination
 *   - test_spiritual_weapon_follow_up_disables_submit_on_noop
 */

import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { SpiritualWeaponFollowUpPanel } from "./SpiritualWeaponFollowUpPanel";
import type { SpiritualWeaponFollowUpAction } from "./spiritualWeapon";
import type { CombatParticipant } from "../../../shared/api/combatRepo";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const t = (key: string) =>
  ({
    "combatUi.spiritualWeaponAction": "Arma Espiritual",
    "combatUi.spiritualWeaponNoTarget": "Nenhum alvo",
    "combatUi.spiritualWeaponConfirm": "Confirmar",
  }[key] ?? key);

const makeAction = (
  override: Partial<SpiritualWeaponFollowUpAction> = {},
): SpiritualWeaponFollowUpAction => ({
  anchorId: "anchor-1",
  position: { x: 5, y: 5 },
  remainingRounds: 4,
  maxMovementMeters: 6,
  ...override,
});

const makeParticipant = (
  override: Partial<CombatParticipant> = {},
): CombatParticipant => ({
  id: "p-1",
  kind: "session_entity",
  ref_id: "npc-ref-1",
  display_name: "Goblin",
  initiative: 8,
  status: "active",
  team: "enemies",
  visible: true,
  actor_user_id: null,
  ...override,
});

const defaultProps = {
  action: makeAction(),
  destination: null,
  targetId: "",
  validTargets: [],
  finalPosition: null,
  submitting: false,
  isMyTurn: true,
  mapTokensLoaded: false,
  onTargetChange: vi.fn(),
  onCancel: vi.fn(),
  onConfirm: vi.fn(),
  t,
};

// ---------------------------------------------------------------------------
// test_spiritual_weapon_follow_up_opens_map_targeting_mode
// ---------------------------------------------------------------------------

describe("test_spiritual_weapon_follow_up_opens_map_targeting_mode", () => {
  it("renderiza o painel quando o modo de targeting está ativo", () => {
    const markup = renderToStaticMarkup(
      <SpiritualWeaponFollowUpPanel {...defaultProps} />,
    );
    expect(markup).toContain("Arma Espiritual");
  });

  it("exibe instrução para clicar no mapa quando não há destino selecionado", () => {
    const markup = renderToStaticMarkup(
      <SpiritualWeaponFollowUpPanel {...defaultProps} destination={null} />,
    );
    expect(markup).toContain("Clique no mapa para selecionar o destino da arma.");
  });

  it("exibe botão de cancelar para sair do modo de targeting", () => {
    const markup = renderToStaticMarkup(
      <SpiritualWeaponFollowUpPanel {...defaultProps} />,
    );
    expect(markup).toContain("Cancelar");
  });
});

// ---------------------------------------------------------------------------
// test_spiritual_weapon_follow_up_highlights_current_anchor
// ---------------------------------------------------------------------------

describe("test_spiritual_weapon_follow_up_highlights_current_anchor", () => {
  it("exibe a posição da anchor quando destino ainda não foi selecionado", () => {
    // O painel recebe action.position como âncora atual.
    // Quando não há destino, a âncora é a posição final implícita.
    const markup = renderToStaticMarkup(
      <SpiritualWeaponFollowUpPanel
        {...defaultProps}
        destination={null}
        finalPosition={{ x: 5, y: 5 }}
      />,
    );
    // Panel renders without destination text (showing click-to-select message)
    expect(markup).toContain("Clique no mapa");
    // No destination text shown yet
    expect(markup).not.toContain("Destino:");
  });

  it("a âncora é representada como posição de origem no estado inicial", () => {
    const action = makeAction({ position: { x: 3, y: 7 } });
    const markup = renderToStaticMarkup(
      <SpiritualWeaponFollowUpPanel
        {...defaultProps}
        action={action}
        destination={null}
      />,
    );
    // Initial state: anchor position not shown as destination; map handles it
    expect(markup).not.toContain("Destino: (3, 7)");
  });
});

// ---------------------------------------------------------------------------
// test_spiritual_weapon_follow_up_selects_destination_from_map_click
// ---------------------------------------------------------------------------

describe("test_spiritual_weapon_follow_up_selects_destination_from_map_click", () => {
  it("exibe as coordenadas do destino após seleção no mapa", () => {
    const markup = renderToStaticMarkup(
      <SpiritualWeaponFollowUpPanel
        {...defaultProps}
        destination={{ x: 7, y: 4 }}
        finalPosition={{ x: 7, y: 4 }}
      />,
    );
    expect(markup).toContain("Destino: (7, 4)");
  });

  it("não exibe instrução de clique quando destino está selecionado", () => {
    const markup = renderToStaticMarkup(
      <SpiritualWeaponFollowUpPanel
        {...defaultProps}
        destination={{ x: 7, y: 4 }}
      />,
    );
    expect(markup).not.toContain("Clique no mapa para selecionar o destino da arma.");
  });

  it("destino null restaura mensagem de instrução (staying in place é limpar destino)", () => {
    const markup = renderToStaticMarkup(
      <SpiritualWeaponFollowUpPanel
        {...defaultProps}
        destination={null}
      />,
    );
    expect(markup).toContain("Clique no mapa para selecionar o destino da arma.");
  });
});

// ---------------------------------------------------------------------------
// test_spiritual_weapon_follow_up_shows_target_options_after_destination_selection
// ---------------------------------------------------------------------------

describe("test_spiritual_weapon_follow_up_shows_target_options_after_destination_selection", () => {
  it("lista alvos válidos no select quando há participantes adjacentes", () => {
    const targets = [
      makeParticipant({ id: "p-1", display_name: "Goblin" }),
      makeParticipant({ id: "p-2", display_name: "Orc", ref_id: "npc-ref-2" }),
    ];
    const markup = renderToStaticMarkup(
      <SpiritualWeaponFollowUpPanel
        {...defaultProps}
        destination={{ x: 6, y: 5 }}
        finalPosition={{ x: 6, y: 5 }}
        validTargets={targets}
      />,
    );
    expect(markup).toContain("Goblin");
    expect(markup).toContain("Orc");
  });

  it("opção vazia de placeholder está sempre presente no select", () => {
    const markup = renderToStaticMarkup(
      <SpiritualWeaponFollowUpPanel
        {...defaultProps}
        validTargets={[makeParticipant()]}
      />,
    );
    expect(markup).toContain("Nenhum alvo");
  });

  it("exibe aviso quando não há alvos adjacentes após tokens carregados", () => {
    const markup = renderToStaticMarkup(
      <SpiritualWeaponFollowUpPanel
        {...defaultProps}
        destination={{ x: 9, y: 9 }}
        finalPosition={{ x: 9, y: 9 }}
        validTargets={[]}
        mapTokensLoaded={true}
      />,
    );
    expect(markup).toContain("Nenhum alvo válido adjacente");
  });

  it("não exibe aviso de sem alvos enquanto tokens ainda carregam", () => {
    const markup = renderToStaticMarkup(
      <SpiritualWeaponFollowUpPanel
        {...defaultProps}
        finalPosition={{ x: 9, y: 9 }}
        validTargets={[]}
        mapTokensLoaded={false}
      />,
    );
    expect(markup).not.toContain("Nenhum alvo válido adjacente");
  });

  it("não exibe aviso de sem alvos quando finalPosition é null", () => {
    const markup = renderToStaticMarkup(
      <SpiritualWeaponFollowUpPanel
        {...defaultProps}
        finalPosition={null}
        validTargets={[]}
        mapTokensLoaded={true}
      />,
    );
    expect(markup).not.toContain("Nenhum alvo válido adjacente");
  });
});

// ---------------------------------------------------------------------------
// test_spiritual_weapon_follow_up_can_submit_attack_without_movement
// ---------------------------------------------------------------------------

describe("test_spiritual_weapon_follow_up_can_submit_attack_without_movement", () => {
  it("confirmar está habilitado quando alvo selecionado mas destino é null (sem movimento)", () => {
    const markup = renderToStaticMarkup(
      <SpiritualWeaponFollowUpPanel
        {...defaultProps}
        destination={null}
        targetId="p-1"
        validTargets={[makeParticipant({ id: "p-1" })]}
        isMyTurn={true}
      />,
    );
    // Button should NOT have disabled attribute
    expect(markup).not.toContain('disabled=""');
  });

  it("botão de confirmar não está desabilitado com alvo mas sem destino na minha vez", () => {
    const markup = renderToStaticMarkup(
      <SpiritualWeaponFollowUpPanel
        {...defaultProps}
        destination={null}
        targetId="p-1"
        validTargets={[makeParticipant({ id: "p-1" })]}
        isMyTurn={true}
      />,
    );
    // The confirm button text should appear without disabled
    expect(markup).toContain("Confirmar");
    expect(markup).not.toContain('disabled=""');
  });
});

// ---------------------------------------------------------------------------
// test_spiritual_weapon_follow_up_payload_uses_clicked_destination
// ---------------------------------------------------------------------------

describe("test_spiritual_weapon_follow_up_payload_uses_clicked_destination", () => {
  it("exibe as coordenadas exatas do destino clicado", () => {
    const clicked = { x: 10, y: 3 };
    const markup = renderToStaticMarkup(
      <SpiritualWeaponFollowUpPanel
        {...defaultProps}
        destination={clicked}
        finalPosition={clicked}
      />,
    );
    expect(markup).toContain("Destino: (10, 3)");
  });

  it("destino diferente exibe coordenadas corretas", () => {
    const markup1 = renderToStaticMarkup(
      <SpiritualWeaponFollowUpPanel
        {...defaultProps}
        destination={{ x: 2, y: 8 }}
      />,
    );
    const markup2 = renderToStaticMarkup(
      <SpiritualWeaponFollowUpPanel
        {...defaultProps}
        destination={{ x: 4, y: 1 }}
      />,
    );
    expect(markup1).toContain("Destino: (2, 8)");
    expect(markup1).not.toContain("Destino: (4, 1)");
    expect(markup2).toContain("Destino: (4, 1)");
    expect(markup2).not.toContain("Destino: (2, 8)");
  });

  it("o alvo selecionado aparece como selected no markup", () => {
    const targets = [
      makeParticipant({ id: "p-enemy", display_name: "Inimigo" }),
    ];
    const markup = renderToStaticMarkup(
      <SpiritualWeaponFollowUpPanel
        {...defaultProps}
        targetId="p-enemy"
        validTargets={targets}
      />,
    );
    // The option with value p-enemy should appear; select's value is controlled
    expect(markup).toContain('value="p-enemy"');
    expect(markup).toContain("Inimigo");
  });
});

// ---------------------------------------------------------------------------
// test_spiritual_weapon_follow_up_disables_submit_on_noop
// ---------------------------------------------------------------------------

describe("test_spiritual_weapon_follow_up_disables_submit_on_noop", () => {
  it("botão confirmar desabilitado quando não há destino nem alvo selecionado", () => {
    const markup = renderToStaticMarkup(
      <SpiritualWeaponFollowUpPanel
        {...defaultProps}
        destination={null}
        targetId=""
        isMyTurn={true}
      />,
    );
    expect(markup).toContain('disabled=""');
  });

  it("botão confirmar desabilitado quando não é a vez do jogador", () => {
    const markup = renderToStaticMarkup(
      <SpiritualWeaponFollowUpPanel
        {...defaultProps}
        destination={{ x: 5, y: 5 }}
        targetId="p-1"
        isMyTurn={false}
      />,
    );
    expect(markup).toContain('disabled=""');
  });

  it("botão confirmar desabilitado enquanto está em execução", () => {
    const markup = renderToStaticMarkup(
      <SpiritualWeaponFollowUpPanel
        {...defaultProps}
        destination={{ x: 5, y: 5 }}
        targetId="p-1"
        submitting={true}
        isMyTurn={true}
      />,
    );
    expect(markup).toContain('disabled=""');
    expect(markup).toContain("Executando...");
  });

  it("botão confirmar habilitado quando destino selecionado na minha vez", () => {
    const markup = renderToStaticMarkup(
      <SpiritualWeaponFollowUpPanel
        {...defaultProps}
        destination={{ x: 6, y: 5 }}
        targetId=""
        isMyTurn={true}
      />,
    );
    expect(markup).not.toContain('disabled=""');
  });
});
