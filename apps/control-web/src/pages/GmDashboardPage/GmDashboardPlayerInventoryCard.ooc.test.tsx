import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { GmDashboardPlayerInventoryCard } from "./GmDashboardPlayerInventoryCard";

const testState = vi.hoisted(() => ({
  sessionStatesRepoMock: {
    listCastableOutOfCombatForPlayer: vi.fn(async () => []),
    castSpellOutOfCombatForPlayer: vi.fn(async () => ({
      id: "ss-1",
      sessionId: "session-1",
      playerUserId: "ally-a",
      state: {},
      createdAt: "2026-01-01T00:00:00Z",
      updatedAt: null,
    })),
  },
  lastCastCardProps: null as Record<string, unknown> | null,
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

vi.mock("../PlayerBoardPage/OutOfCombatSpellCastCard", () => ({
  OutOfCombatSpellCastCard: (props: Record<string, unknown>) => {
    testState.lastCastCardProps = props;
    return null;
  },
}));

describe("GmDashboardPlayerInventoryCard OOC cast", () => {
  it("dispatches GM cast endpoint with player_user_id and payload", async () => {
    testState.lastCastCardProps = null;
    testState.sessionStatesRepoMock.castSpellOutOfCombatForPlayer.mockClear();

    renderToStaticMarkup(
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
      />,
    );

    expect(testState.lastCastCardProps).not.toBeNull();
    const onCast = testState.lastCastCardProps?.onCast as
      | ((spellId: string, slotLevel: number | null, variantKey: string | null, targetPlayerUserId: string | null) => Promise<void> | void)
      | undefined;
    expect(onCast).toBeTypeOf("function");

    await onCast?.("spell-1", 2, "owls_wisdom", "ally-b");

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
});
