import type { PartyMemberSummary } from "../../shared/api/partiesRepo";
import type { CurrencyWallet } from "../../shared/api/inventoryRepo";
import type { InventoryItem } from "../../entities/inventory";
import type { Item } from "../../entities/item";
import type { CharacterSheet } from "../../features/character-sheet/model/characterSheet.types";
import type { SessionInventoryFilterGroup } from "../../features/inventory/components/sessionInventoryPanel.utils";
import { useLocale } from "../../shared/hooks/useLocale";
import type { CurrencyDraft, GrantFeedback, HpActionState, ItemDraft } from "./gmDashboard.types";
import { GmDashboardPlayerInventoryCard } from "./GmDashboardPlayerInventoryCard";
import { useState } from "react";

type Props = {
  activeSessionPartyId: string | null;
  catalogItems: Record<string, Item>;
  currencyDraftByUserId: Record<string, CurrencyDraft>;
  effectiveCampaignId: string | null;
  grantFeedbackByUserId: Record<string, GrantFeedback>;
  grantingCurrencyForUserId: string | null;
  grantingItemForUserId: string | null;
  grantingXpForUserId: string | null;
  hpActionState: HpActionState | null;
  hpDraftByUserId: Record<string, string>;
  inventoryByMemberId: Record<string, InventoryItem[]>;
  inventoryOpenForUserId: string | null;
  itemDraftByUserId: Record<string, ItemDraft>;
  levelUpActionState: { action: "approve" | "deny"; userId: string } | null;
  memberIdByUserId: Record<string, string>;
  navigate: (to: string) => void;
  onlineUsers: Record<string, string>;
  partyPlayers: PartyMemberSummary[];
  playerSheetByUserId: Record<string, CharacterSheet>;
  sortedCatalogItems: Item[];
  walletByUserId: Record<string, CurrencyWallet>;
  xpDraftByUserId: Record<string, string>;
  onApproveLevelUp: (userId: string) => void;
  onDamagePlayer: (userId: string) => void;
  onGrantCurrency: (userId: string) => void;
  onGrantItem: (userId: string) => void;
  onGrantXp: (userId: string) => void;
  onHealPlayer: (userId: string) => void;
  onDenyLevelUp: (userId: string) => void;
  onOpenInventory: (userId: string) => void;
  setCurrencyDraftByUserId: React.Dispatch<React.SetStateAction<Record<string, CurrencyDraft>>>;
  setHpDraftByUserId: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  setItemDraftByUserId: React.Dispatch<React.SetStateAction<Record<string, ItemDraft>>>;
  setXpDraftByUserId: React.Dispatch<React.SetStateAction<Record<string, string>>>;
};

export const GmDashboardPartyInventories = ({
  activeSessionPartyId,
  catalogItems,
  currencyDraftByUserId,
  effectiveCampaignId,
  grantFeedbackByUserId,
  grantingCurrencyForUserId,
  grantingItemForUserId,
  grantingXpForUserId,
  hpActionState,
  hpDraftByUserId,
  inventoryByMemberId,
  inventoryOpenForUserId,
  itemDraftByUserId,
  levelUpActionState,
  memberIdByUserId,
  navigate,
  onlineUsers,
  partyPlayers,
  playerSheetByUserId,
  sortedCatalogItems,
  walletByUserId,
  xpDraftByUserId,
  onApproveLevelUp,
  onDamagePlayer,
  onGrantCurrency,
  onGrantItem,
  onGrantXp,
  onHealPlayer,
  onDenyLevelUp,
  onOpenInventory,
  setCurrencyDraftByUserId,
  setHpDraftByUserId,
  setItemDraftByUserId,
  setXpDraftByUserId,
}: Props) => {
  const { locale } = useLocale();
  const [inventorySearchByUserId, setInventorySearchByUserId] = useState<Record<string, string>>({});
  const [inventoryGroupByUserId, setInventoryGroupByUserId] = useState<Record<string, SessionInventoryFilterGroup>>({});
  const [equippedOnlyByUserId, setEquippedOnlyByUserId] = useState<Record<string, boolean>>({});

  if (partyPlayers.length === 0) return null;

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6">
      <h2 className="mb-4 text-lg font-semibold text-white">Party Inventories</h2>
      <div className="space-y-3">
        {partyPlayers.map((player) => {
          const memberId = memberIdByUserId[player.userId];
          const playerItems = memberId ? inventoryByMemberId[memberId] : undefined;

          return (
            <GmDashboardPlayerInventoryCard
              key={player.userId}
              activeSessionPartyId={activeSessionPartyId}
              catalogItems={catalogItems}
              currencyDraft={currencyDraftByUserId[player.userId]}
              effectiveCampaignId={effectiveCampaignId}
              equippedOnly={equippedOnlyByUserId[player.userId] ?? false}
              grantFeedback={grantFeedbackByUserId[player.userId]}
              grantingCurrencyForUserId={grantingCurrencyForUserId}
              grantingItemForUserId={grantingItemForUserId}
              grantingXpForUserId={grantingXpForUserId}
              hpActionState={hpActionState}
              hpDraft={hpDraftByUserId[player.userId] ?? ""}
              inventoryGroup={inventoryGroupByUserId[player.userId] ?? "all"}
              inventorySearch={inventorySearchByUserId[player.userId] ?? ""}
              isOnline={Boolean(onlineUsers[player.userId])}
              isOpen={inventoryOpenForUserId === player.userId}
              itemDraft={itemDraftByUserId[player.userId]}
              levelUpActionState={levelUpActionState}
              locale={locale}
              navigate={navigate}
              player={player}
              playerItems={playerItems}
              sheet={playerSheetByUserId[player.userId]}
              sortedCatalogItems={sortedCatalogItems}
              wallet={walletByUserId[player.userId]}
              xpDraft={xpDraftByUserId[player.userId] ?? ""}
              onApproveLevelUp={() => onApproveLevelUp(player.userId)}
              onDamagePlayer={() => onDamagePlayer(player.userId)}
              onDenyLevelUp={() => onDenyLevelUp(player.userId)}
              onGrantCurrency={() => onGrantCurrency(player.userId)}
              onGrantItem={() => onGrantItem(player.userId)}
              onGrantXp={() => onGrantXp(player.userId)}
              onHealPlayer={() => onHealPlayer(player.userId)}
              onOpenInventory={() => onOpenInventory(player.userId)}
              onGroupChange={(group) =>
                setInventoryGroupByUserId((current) => ({ ...current, [player.userId]: group }))
              }
              onSearchChange={(value) =>
                setInventorySearchByUserId((current) => ({ ...current, [player.userId]: value }))
              }
              onToggleEquippedOnly={() =>
                setEquippedOnlyByUserId((current) => ({
                  ...current,
                  [player.userId]: !(current[player.userId] ?? false),
                }))
              }
              setCurrencyDraft={(updater) =>
                setCurrencyDraftByUserId((current) => ({
                  ...current,
                  [player.userId]: updater(current[player.userId]),
                }))
              }
              setHpDraftByUserId={setHpDraftByUserId}
              setItemDraft={(updater) =>
                setItemDraftByUserId((current) => ({
                  ...current,
                  [player.userId]: updater(current[player.userId]),
                }))
              }
              setXpDraftByUserId={setXpDraftByUserId}
            />
          );
        })}
      </div>
    </div>
  );
};
