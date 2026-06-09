import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { GmDashboardPlayerInventoryCard } from "./GmDashboardPlayerInventoryCard";

type CastCardCapture = {
  onCast: (
    spellId: string,
    slotLevel: number | null,
    variantKey: string | null,
    targetPlayerUserId: string | null,
  ) => Promise<void> | void;
};

type EffectsPanelCapture = {
  onRemoveEffect: (effectId: string) => Promise<void> | void;
};

const requireCastCardCapture = (value: CastCardCapture | null): CastCardCapture => {
  if (!value) {
    throw new Error("Expected cast card props to be captured");
  }
  return value;
};

const requireEffectsPanelCapture = (
  value: EffectsPanelCapture | null,
): EffectsPanelCapture => {
  if (!value) {
    throw new Error("Expected active effects panel props to be captured");
  }
  return value;
};

const testState = vi.hoisted(() => ({
  sessionStatesRepoMock: {
    getByPlayer: vi.fn(async () => ({
      id: "ss-1",
      sessionId: "session-1",
      playerUserId: "ally-a",
      state: {},
      createdAt: "2026-01-01T00:00:00Z",
      updatedAt: null,
      activeSpellEffects: [],
    })),
    listCastableOutOfCombatForPlayer: vi.fn(async () => []),
    castSpellOutOfCombatForPlayer: vi.fn(async () => ({
      id: "ss-1",
      sessionId: "session-1",
      playerUserId: "ally-a",
      state: {},
      createdAt: "2026-01-01T00:00:00Z",
      updatedAt: null,
      activeSpellEffects: [],
    })),
    removePersistedEffectForPlayer: vi.fn(async () => ({
      id: "ss-1",
      sessionId: "session-1",
      playerUserId: "ally-a",
      state: {},
      createdAt: "2026-01-01T00:00:00Z",
      updatedAt: null,
      activeSpellEffects: [],
    })),
  },
  lastCastCardProps: null as CastCardCapture | null,
  lastEffectsPanelProps: null as EffectsPanelCapture | null,
}));

vi.mock("../../shared/hooks/useLocale", () => ({
  useLocale: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock("../../shared/api/sessionStatesRepo", () => ({
  sessionStatesRepo: testState.sessionStatesRepoMock,
}));

vi.mock("./GmDashboardPlayerProgressBlock", () => ({
  GmDashboardPlayerProgressBlock: () => null,
}));

vi.mock("./GmDashboardInventoryFilters", () => ({
  GmDashboardInventoryFilters: () => null,
}));

vi.mock("./GmDashboardInventoryItemList", () => ({
  GmDashboardInventoryItemList: () => null,
}));

vi.mock("./GmDashboardGrantPanels", () => ({
  GmDashboardGrantPanels: () => null,
}));

vi.mock("../../features/character-sheet/components/CharacterActiveEffectsPanel", () => ({
  CharacterActiveEffectsPanel: (props: EffectsPanelCapture) => {
    testState.lastEffectsPanelProps = props;
    return null;
  },
}));

vi.mock("../PlayerBoardPage/OutOfCombatSpellCastCard", () => ({
  OutOfCombatSpellCastCard: (props: CastCardCapture) => {
    testState.lastCastCardProps = props;
    return null;
  },
}));

describe("GmDashboardPlayerInventoryCard OOC cast", () => {
  it("dispatches GM cast endpoint with player_user_id and payload", async () => {
    testState.lastCastCardProps = null;
    testState.sessionStatesRepoMock.castSpellOutOfCombatForPlayer.mockClear();

    renderToStaticMarkup(
      <MemoryRouter>
        <GmDashboardPlayerInventoryCard
        activeSessionId="session-1"
        activeSessionPartyId="party-1"
        catalogItems={{}}
        currencyDraft={undefined}
        effectiveCampaignId={null}
        equippedOnly={false}
        grantFeedback={undefined}
        grantingCurrencyForUserId={null}
        grantingItemForUserId={null}
        grantingXpForUserId={null}
        hpActionState={null}
        hpDraft=""
        inventoryGroup="all"
        inventorySearch=""
        isOnline
        isOpen
        itemDraft={undefined}
        levelUpActionState={null}
        locale="pt-BR"
        navigate={() => undefined}
        player={{
          userId: "ally-a",
          role: "PLAYER",
          status: "joined",
          createdAt: "2026-01-01T00:00:00Z",
          displayName: "Aelar",
          username: "aelar",
        }}
        playerItems={[]}
        sheet={undefined}
        sortedCatalogItems={[]}
        wallet={undefined}
        xpDraft=""
        targetOptions={[
          { playerUserId: "ally-a", label: "Aelar" },
          { playerUserId: "ally-b", label: "Luna" },
        ]}
        onApproveLevelUp={() => undefined}
        onDamagePlayer={() => undefined}
        onDenyLevelUp={() => undefined}
        onGrantCurrency={() => undefined}
        onGrantItem={() => undefined}
        onGrantXp={() => undefined}
        onHealPlayer={() => undefined}
        onOpenInventory={() => undefined}
        onGroupChange={() => undefined}
        onSearchChange={() => undefined}
        onToggleEquippedOnly={() => undefined}
        setCurrencyDraft={() => ({ amount: "", coin: "gp" })}
        setHpDraftByUserId={() => ({})}
        setItemDraft={() => ({ itemId: "", quantity: "" })}
        setXpDraftByUserId={() => ({})}
        />
      </MemoryRouter>,
    );

    const onCast = requireCastCardCapture(testState.lastCastCardProps).onCast;
    expect(onCast).toBeTypeOf("function");

    await onCast("spell-1", 2, "owls_wisdom", "ally-b");

    expect(testState.sessionStatesRepoMock.castSpellOutOfCombatForPlayer).toHaveBeenCalledWith(
      "session-1",
      "ally-a",
      {
        spellId: "spell-1",
        slotLevel: 2,
        variantKey: "owls_wisdom",
        targetPlayerUserId: "ally-b",
      },
    );
  });

  it("dispatches GM remove endpoint with player_user_id and effect_id", async () => {
    testState.lastEffectsPanelProps = null;
    testState.sessionStatesRepoMock.removePersistedEffectForPlayer.mockClear();

    renderToStaticMarkup(
      <MemoryRouter>
        <GmDashboardPlayerInventoryCard
        activeSessionId="session-1"
        activeSessionPartyId="party-1"
        catalogItems={{}}
        currencyDraft={undefined}
        effectiveCampaignId={null}
        equippedOnly={false}
        grantFeedback={undefined}
        grantingCurrencyForUserId={null}
        grantingItemForUserId={null}
        grantingXpForUserId={null}
        hpActionState={null}
        hpDraft=""
        inventoryGroup="all"
        inventorySearch=""
        isOnline
        isOpen
        itemDraft={undefined}
        levelUpActionState={null}
        locale="pt-BR"
        navigate={() => undefined}
        player={{
          userId: "ally-a",
          role: "PLAYER",
          status: "joined",
          createdAt: "2026-01-01T00:00:00Z",
          displayName: "Aelar",
          username: "aelar",
        }}
        playerItems={[]}
        sheet={undefined}
        sortedCatalogItems={[]}
        wallet={undefined}
        xpDraft=""
        targetOptions={[
          { playerUserId: "ally-a", label: "Aelar" },
          { playerUserId: "ally-b", label: "Luna" },
        ]}
        onApproveLevelUp={() => undefined}
        onDamagePlayer={() => undefined}
        onDenyLevelUp={() => undefined}
        onGrantCurrency={() => undefined}
        onGrantItem={() => undefined}
        onGrantXp={() => undefined}
        onHealPlayer={() => undefined}
        onOpenInventory={() => undefined}
        onGroupChange={() => undefined}
        onSearchChange={() => undefined}
        onToggleEquippedOnly={() => undefined}
        setCurrencyDraft={() => ({ amount: "", coin: "gp" })}
        setHpDraftByUserId={() => ({})}
        setItemDraft={() => ({ itemId: "", quantity: "" })}
        setXpDraftByUserId={() => ({})}
        />
      </MemoryRouter>,
    );

    const onRemoveEffect = requireEffectsPanelCapture(testState.lastEffectsPanelProps).onRemoveEffect;
    expect(onRemoveEffect).toBeTypeOf("function");

    await onRemoveEffect("eff-1");

    expect(testState.sessionStatesRepoMock.removePersistedEffectForPlayer).toHaveBeenCalledWith(
      "session-1",
      "ally-a",
      "eff-1",
    );
  });
});
