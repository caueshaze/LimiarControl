import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockState = vi.hoisted(() => ({
  dialogProps: null as Record<string, unknown> | null,
  pendingSpellPreparation: {
    source: "long_rest",
    classKey: "cleric",
    preparedLimit: 8,
    currentPreparedSpellIds: ["s1"],
    createdAt: "2026-01-01T00:00:00+00:00",
    availableDuringRest: true,
  },
  restState: "long_rest" as "exploration" | "short_rest" | "long_rest",
}));

vi.mock("../../shared/hooks/useLocale", () => ({
  useLocale: () => ({
    locale: "pt",
    t: (key: string) =>
      ({
        "playerBoard.prepareSpellsPrompt": "Preparar magias",
        "playerBoard.prepareSpellsDescription": "Você concluiu um descanso longo. Revise suas magias preparadas.",
        "playerBoard.prepareSpellsDuringLongRestPrompt": "Preparar magias durante o descanso",
        "playerBoard.prepareSpellsDuringLongRestDescription": "O descanso longo ainda está em andamento. Revise suas magias preparadas agora.",
        "playerBoard.prepareSpellsButton": "Preparar magias",
        "playerBoard.speedLabel": "Velocidade",
        "playerBoard.speedPenaltyHint": "Penalidade de carga",
      }[key] ?? key),
  }),
}));

vi.mock("../../features/auth", () => ({
  useAuth: () => ({
    user: { userId: "player-1" },
  }),
}));

vi.mock("../../features/campaign-select", () => ({
  useCampaigns: () => ({
    selectedCampaign: { name: "Campanha" },
    selectedCampaignId: "campaign-1",
    setSelectedCampaignLocal: vi.fn(),
  }),
}));

vi.mock("../../shared/hooks/useToast", () => ({
  useToast: () => ({
    toast: null,
    showToast: vi.fn(),
    clearToast: vi.fn(),
  }),
}));

vi.mock("../../features/sessions", () => ({
  useSession: () => ({
    collapseCombatUi: vi.fn(),
    combatModeVisible: false,
    combatUiExpanded: false,
    toggleCombatUiExpanded: vi.fn(),
  }),
  SessionActivityToggle: () => <div data-testid="activity-toggle" />,
}));

vi.mock("./usePlayerBoardResources", () => ({
  usePlayerBoardResources: () => ({
    activeConcentration: null,
    activeSession: {
      id: "session-1",
      status: "ACTIVE",
      title: "Sessao",
      number: 1,
      startedAt: "2026-01-01T00:00:00+00:00",
      campaignId: "campaign-1",
    },
    activeSpellEffects: null,
    catalogItems: {},
    clearCommand: vi.fn(),
    clearSessionEnded: vi.fn(),
    combatActive: false,
    effectiveCampaignId: "campaign-1",
    lastCommand: null,
    lastEvent: null,
    myInventory: [],
    partyPlayers: [],
    pendingSpellPreparation: mockState.pendingSpellPreparation,
    playerSheet: {
      abilities: {
        strength: 10,
      },
      spellcasting: {
        ability: "wisdom",
        mode: "prepared",
        slots: {},
        spells: [],
      },
    },
    playerWallet: null,
    refresh: vi.fn(),
    refreshInventoryData: vi.fn(),
    refreshPlayerWallet: vi.fn(),
    restState: mockState.restState,
    roll: vi.fn(),
    rollEvents: [],
    sessionEndedAt: null,
    setActiveConcentration: vi.fn(),
    setActiveSpellEffects: vi.fn(),
    setMyInventory: vi.fn(),
    setPendingSpellPreparation: vi.fn(),
    setPlayerSheet: vi.fn(),
    setPlayerWallet: vi.fn(),
    setSelectedSessionId: vi.fn(),
    shopAvailable: false,
  }),
}));

vi.mock("./usePlayerBoardRealtime", () => ({
  usePlayerBoardRealtime: () => ({
    clearPendingRoll: vi.fn(),
    handleAuthoritativeRollResolved: vi.fn(),
    handleManualRoll: vi.fn(),
    handleOpenShop: vi.fn(),
    handleRoll: vi.fn(),
    handleShopClose: vi.fn(),
    inventoryFlash: false,
    inventoryOpen: false,
    manualValue: "",
    pendingRoll: null,
    rollMode: "normal",
    setInventoryFlash: vi.fn(),
    setInventoryOpen: vi.fn(),
    setManualValue: vi.fn(),
    setRollMode: vi.fn(),
    shopOpen: false,
  }),
}));

vi.mock("./usePlayerBoardSummary", () => ({
  usePlayerBoardSummary: () => ({
    boardDescription: "Resumo",
    campaignTitle: "Campanha",
    inventoryTotal: 0,
    playerStatus: null,
    sessionStatusLabel: "Ativa",
    sessionStatusTone: "active",
  }),
}));

vi.mock("./usePlayerBoardLoadout", () => ({
  usePlayerBoardLoadout: () => ({
    armorOptions: [],
    handleArmorChange: vi.fn(),
    handleWeaponChange: vi.fn(),
    isSavingLoadout: false,
    loadoutStatus: null,
    selectedArmorId: null,
    selectedWeaponId: null,
    weaponOptions: [],
  }),
}));

vi.mock("./usePlayerBoardRestActions", () => ({
  usePlayerBoardRestActions: () => ({
    handleUseHitDie: vi.fn(),
    usingHitDie: false,
  }),
}));

vi.mock("../../features/combat-ui/useCombatUiState", () => ({
  useCombatUiState: () => ({
    currentParticipant: null,
    isMyTurn: false,
    myParticipant: null,
    state: null,
  }),
}));

vi.mock("./PlayerBoardHero", () => ({
  PlayerBoardHero: () => <div data-testid="hero" />,
}));

vi.mock("./PlayerBoardRestBanner", () => ({
  PlayerBoardRestBanner: () => <div data-testid="rest-banner" />,
}));

vi.mock("./PlayerBoardStatusPanel", () => ({
  PlayerBoardStatusPanel: () => <div data-testid="status-panel" />,
}));

vi.mock("../../features/inventory", () => ({
  SessionInventoryPanel: () => <div data-testid="inventory-panel" />,
}));

vi.mock("../../features/shop", () => ({
  ShopPanel: () => <div data-testid="shop-panel" />,
}));

vi.mock("../../features/session-entities", () => ({
  PlayerEntityList: () => <div data-testid="player-entities" />,
}));

vi.mock("../../features/dice-roller/components/DiceVisualizer", () => ({
  DiceVisualizer: () => <div data-testid="dice-visualizer" />,
}));

vi.mock("../../features/rolls/components/AuthoritativeRollDialog", () => ({
  AuthoritativeRollDialog: () => <div data-testid="authoritative-roll" />,
}));

vi.mock("./PlayerBoardRollDialog", () => ({
  PlayerBoardRollDialog: () => <div data-testid="manual-roll" />,
}));

vi.mock("./SpellPreparationDialog", () => ({
  SpellPreparationDialog: (props: Record<string, unknown>) => {
    mockState.dialogProps = props;
    return <div data-testid="spell-prep-dialog">{String(props.copyMode ?? "fallback")}</div>;
  },
}));

vi.mock("../../shared/ui/Toast", () => ({
  Toast: () => null,
}));

vi.mock("../../features/combat-ui/components/CombatModeBar", () => ({
  CombatModeBar: () => <div data-testid="combat-mode-bar" />,
}));

vi.mock("../../features/combat-ui/player/PlayerCombatModeShell", () => ({
  PlayerCombatModeShell: () => <div data-testid="combat-shell" />,
}));

vi.mock("react-router-dom", () => ({
  useNavigate: () => vi.fn(),
  useParams: () => ({ partyId: "party-1" }),
}));

vi.mock("../../shared/lib/navigation", () => ({
  navigateBackOrFallback: vi.fn(),
}));

import { PlayerBoardPage } from "./PlayerBoardPage";

describe("PlayerBoardPage spell preparation wiring", () => {
  beforeEach(() => {
    mockState.dialogProps = null;
    mockState.pendingSpellPreparation = {
      source: "long_rest",
      classKey: "cleric",
      preparedLimit: 8,
      currentPreparedSpellIds: ["s1"],
      createdAt: "2026-01-01T00:00:00+00:00",
      availableDuringRest: true,
    };
    mockState.restState = "long_rest";
  });

  it("shows long-rest copy and passes during-long-rest mode to the dialog", () => {
    const markup = renderToStaticMarkup(<PlayerBoardPage />);

    expect(markup).toContain("Preparar magias durante o descanso");
    expect(markup).toContain("O descanso longo ainda está em andamento");
    expect(markup).toContain("during_long_rest");
    expect(mockState.dialogProps?.copyMode).toBe("during_long_rest");
  });

  it("falls back to the post-rest copy when the pending prompt was created after the rest", () => {
    mockState.pendingSpellPreparation = {
      source: "long_rest",
      classKey: "cleric",
      preparedLimit: 8,
      currentPreparedSpellIds: ["s1"],
      createdAt: "2026-01-01T00:00:00+00:00",
      availableDuringRest: false,
    };
    mockState.restState = "exploration";

    const markup = renderToStaticMarkup(<PlayerBoardPage />);

    expect(markup).toContain("Você concluiu um descanso longo");
    expect(markup).toContain("fallback");
    expect(mockState.dialogProps?.copyMode).toBe("fallback");
  });
});
