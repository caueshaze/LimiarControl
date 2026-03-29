import { routes } from "../../app/routes/routes";
import type { PartyMemberSummary } from "../../shared/api/partiesRepo";
import type { CurrencyWallet } from "../../shared/api/inventoryRepo";
import type { InventoryItem } from "../../entities/inventory";
import type { Item } from "../../entities/item";
import type { CharacterSheet } from "../../features/character-sheet/model/characterSheet.types";
import type { SessionInventoryFilterGroup } from "../../features/inventory/components/sessionInventoryPanel.utils";
import type { CurrencyDraft, GrantFeedback, HpActionState, ItemDraft } from "./gmDashboard.types";
import { GmDashboardPlayerProgressBlock } from "./GmDashboardPlayerProgressBlock";
import { GmDashboardInventoryFilters } from "./GmDashboardInventoryFilters";
import { GmDashboardInventoryItemList } from "./GmDashboardInventoryItemList";
import { GmDashboardGrantPanels } from "./GmDashboardGrantPanels";

type Props = {
  activeSessionPartyId: string | null;
  catalogItems: Record<string, Item>;
  currencyDraft: CurrencyDraft | undefined;
  effectiveCampaignId: string | null;
  equippedOnly: boolean;
  grantFeedback: GrantFeedback | undefined;
  grantingCurrencyForUserId: string | null;
  grantingItemForUserId: string | null;
  grantingXpForUserId: string | null;
  hpActionState: HpActionState | null;
  hpDraft: string;
  inventoryGroup: SessionInventoryFilterGroup;
  inventorySearch: string;
  isOnline: boolean;
  isOpen: boolean;
  itemDraft: ItemDraft | undefined;
  levelUpActionState: { action: "approve" | "deny"; userId: string } | null;
  locale: string;
  navigate: (to: string) => void;
  player: PartyMemberSummary;
  playerItems: InventoryItem[] | undefined;
  sheet: CharacterSheet | undefined;
  sortedCatalogItems: Item[];
  wallet: CurrencyWallet | undefined;
  xpDraft: string;
  onApproveLevelUp: () => void;
  onDamagePlayer: () => void;
  onDenyLevelUp: () => void;
  onGrantCurrency: () => void;
  onGrantItem: () => void;
  onGrantXp: () => void;
  onHealPlayer: () => void;
  onOpenInventory: () => void;
  onGroupChange: (group: SessionInventoryFilterGroup) => void;
  onSearchChange: (value: string) => void;
  onToggleEquippedOnly: () => void;
  setCurrencyDraft: (updater: (current: CurrencyDraft | undefined) => CurrencyDraft) => void;
  setHpDraftByUserId: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  setItemDraft: (updater: (current: ItemDraft | undefined) => ItemDraft) => void;
  setXpDraftByUserId: React.Dispatch<React.SetStateAction<Record<string, string>>>;
};

export const GmDashboardPlayerInventoryCard = ({
  activeSessionPartyId,
  catalogItems,
  currencyDraft,
  effectiveCampaignId,
  equippedOnly,
  grantFeedback,
  grantingCurrencyForUserId,
  grantingItemForUserId,
  grantingXpForUserId,
  hpActionState,
  hpDraft,
  inventoryGroup,
  inventorySearch,
  isOnline,
  isOpen,
  itemDraft,
  levelUpActionState,
  locale,
  navigate,
  player,
  playerItems,
  sheet,
  sortedCatalogItems,
  wallet,
  xpDraft,
  onApproveLevelUp,
  onDamagePlayer,
  onDenyLevelUp,
  onGrantCurrency,
  onGrantItem,
  onGrantXp,
  onHealPlayer,
  onOpenInventory,
  onGroupChange,
  onSearchChange,
  onToggleEquippedOnly,
  setCurrencyDraft,
  setHpDraftByUserId,
  setItemDraft,
  setXpDraftByUserId,
}: Props) => {
  const isApproving =
    levelUpActionState?.userId === player.userId && levelUpActionState.action === "approve";
  const isDenying =
    levelUpActionState?.userId === player.userId && levelUpActionState.action === "deny";
  const isDamaging =
    hpActionState?.userId === player.userId && hpActionState.action === "damage";
  const isHealing =
    hpActionState?.userId === player.userId && hpActionState.action === "heal";

  const playSheetRoute = activeSessionPartyId
    ? `${routes.characterSheetParty.replace(":partyId", activeSessionPartyId)}?${new URLSearchParams({
        mode: "play",
        playerId: player.userId,
        playerName: player.displayName || player.username || "Player",
        ...(effectiveCampaignId ? { campaignId: effectiveCampaignId } : {}),
        from: "gm-dashboard",
      }).toString()}`
    : null;

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-800">
      <div
        onClick={onOpenInventory}
        className="flex w-full cursor-pointer items-center justify-between px-4 py-3 transition-colors hover:bg-slate-900/40"
      >
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="flex h-8 w-8 items-center justify-center rounded-full border border-slate-700 bg-slate-800 text-sm font-bold text-limiar-400">
              {(player.displayName || player.username || "?").charAt(0).toUpperCase()}
            </div>
            <span
              className={`absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-slate-900 ${isOnline ? "bg-emerald-400" : "bg-slate-600"}`}
            />
          </div>
          <div>
            <span className="text-sm font-medium text-white">
              {player.displayName || player.username || "Player"}
            </span>
            <span
              className={`block text-[10px] ${isOnline ? "text-emerald-500" : "text-slate-600"}`}
            >
              {isOnline ? "Online" : "Offline"}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {sheet?.pendingLevelUp && (
            <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-amber-200">
              Level-Up Pending
            </span>
          )}
          {playSheetRoute && (
            <button
              type="button"
              onClick={(event) => {
                event.stopPropagation();
                navigate(playSheetRoute);
              }}
              className="rounded-full border border-limiar-500/30 bg-limiar-500/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-limiar-300 hover:bg-limiar-500/20"
            >
              Play Sheet
            </button>
          )}
          <span
            className={`text-xs text-slate-500 transition-transform ${isOpen ? "rotate-180" : ""}`}
          >
            ▼
          </span>
        </div>
      </div>

      {isOpen && (
        <div className="border-t border-slate-800/60 px-4 pb-4">
          <GmDashboardPlayerProgressBlock
            grantingHpAction={isDamaging || isHealing}
            grantingXp={grantingXpForUserId === player.userId}
            hpActionState={hpActionState?.userId === player.userId ? hpActionState : null}
            hpDraft={hpDraft}
            isApproving={isApproving}
            isDamaging={isDamaging}
            isDenying={isDenying}
            isHealing={isHealing}
            onDamagePlayer={onDamagePlayer}
            onApproveLevelUp={onApproveLevelUp}
            onDenyLevelUp={onDenyLevelUp}
            onGrantXp={onGrantXp}
            onHealPlayer={onHealPlayer}
            setHpDraftByUserId={setHpDraftByUserId}
            setXpDraftByUserId={setXpDraftByUserId}
            sheet={sheet}
            userId={player.userId}
            xpDraft={xpDraft}
          />

          <div className="mt-3 space-y-3">
            <GmDashboardInventoryFilters
              userId={player.userId}
              searchValue={inventorySearch}
              equippedOnly={equippedOnly}
              activeGroup={inventoryGroup}
              onSearchChange={onSearchChange}
              onToggleEquippedOnly={onToggleEquippedOnly}
              onGroupChange={onGroupChange}
            />

            <GmDashboardInventoryItemList
              items={playerItems}
              catalogItems={catalogItems}
              locale={locale}
              equippedOnly={equippedOnly}
              group={inventoryGroup}
              search={inventorySearch}
            />
          </div>

          <GmDashboardGrantPanels
            userId={player.userId}
            locale={locale}
            wallet={wallet}
            currencyDraft={currencyDraft}
            itemDraft={itemDraft}
            sortedCatalogItems={sortedCatalogItems}
            grantingCurrencyForUserId={grantingCurrencyForUserId}
            grantingItemForUserId={grantingItemForUserId}
            grantFeedback={grantFeedback}
            onGrantCurrency={onGrantCurrency}
            onGrantItem={onGrantItem}
            setCurrencyDraft={setCurrencyDraft}
            setItemDraft={setItemDraft}
          />
        </div>
      )}
    </div>
  );
};
