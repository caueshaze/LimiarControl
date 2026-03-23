import { routes } from "../../app/routes/routes";
import type { PartyMemberSummary } from "../../shared/api/partiesRepo";
import type { CurrencyWallet } from "../../shared/api/inventoryRepo";
import type { InventoryItem } from "../../entities/inventory";
import type { Item } from "../../entities/item";
import type { CharacterSheet } from "../../features/character-sheet/model/characterSheet.types";
import { EMPTY_WALLET, buildWalletDisplay } from "../../features/shop/utils/shopCurrency";
import { localizedItemName } from "../../features/shop/utils/localizedItemName";
import { useLocale } from "../../shared/hooks/useLocale";
import type { CurrencyUnit } from "../../shared/utils/money";
import {
  filterInventoryEntries,
  resolveInventoryEntries,
  type SessionInventoryFilterGroup,
} from "../../features/inventory/components/sessionInventoryPanel.utils";
import type { CurrencyDraft, GrantFeedback, HpActionState, ItemDraft } from "./gmDashboard.types";
import { GmDashboardPlayerProgressBlock } from "./GmDashboardPlayerProgressBlock";
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
          const items = memberId ? inventoryByMemberId[memberId] : undefined;
          const sheet = playerSheetByUserId[player.userId];
          const isOpen = inventoryOpenForUserId === player.userId;
          const isOnline = Boolean(onlineUsers[player.userId]);
          const isApproving =
            levelUpActionState?.userId === player.userId && levelUpActionState.action === "approve";
          const isDenying =
            levelUpActionState?.userId === player.userId && levelUpActionState.action === "deny";
          const isDamaging =
            hpActionState?.userId === player.userId && hpActionState.action === "damage";
          const isHealing =
            hpActionState?.userId === player.userId && hpActionState.action === "heal";
          const resolvedItems = resolveInventoryEntries(items ?? [], catalogItems, locale);
          const filteredItems = filterInventoryEntries(resolvedItems, {
            equippedOnly: equippedOnlyByUserId[player.userId] ?? false,
            group: inventoryGroupByUserId[player.userId] ?? "all",
            search: inventorySearchByUserId[player.userId] ?? "",
          });
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
            <div key={player.userId} className="overflow-hidden rounded-2xl border border-slate-800">
              <div
                onClick={() => onOpenInventory(player.userId)}
                className="flex w-full cursor-pointer items-center justify-between px-4 py-3 transition-colors hover:bg-slate-900/40"
              >
                <div className="flex items-center gap-3">
                  <div className="relative">
                    <div className="flex h-8 w-8 items-center justify-center rounded-full border border-slate-700 bg-slate-800 text-sm font-bold text-limiar-400">
                      {(player.displayName || player.username || "?").charAt(0).toUpperCase()}
                    </div>
                    <span className={`absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-slate-900 ${isOnline ? "bg-emerald-400" : "bg-slate-600"}`} />
                  </div>
                  <div>
                    <span className="text-sm font-medium text-white">{player.displayName || player.username || "Player"}</span>
                    <span className={`block text-[10px] ${isOnline ? "text-emerald-500" : "text-slate-600"}`}>
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
                  <span className={`text-xs text-slate-500 transition-transform ${isOpen ? "rotate-180" : ""}`}>▼</span>
                </div>
              </div>

              {isOpen && (
                <div className="border-t border-slate-800/60 px-4 pb-4">
                  <GmDashboardPlayerProgressBlock
                    grantingHpAction={isDamaging || isHealing}
                    grantingXp={grantingXpForUserId === player.userId}
                    hpActionState={hpActionState?.userId === player.userId ? hpActionState : null}
                    hpDraft={hpDraftByUserId[player.userId] ?? ""}
                    isApproving={isApproving}
                    isDamaging={isDamaging}
                    isDenying={isDenying}
                    isHealing={isHealing}
                    onDamagePlayer={() => onDamagePlayer(player.userId)}
                    onApproveLevelUp={() => onApproveLevelUp(player.userId)}
                    onDenyLevelUp={() => onDenyLevelUp(player.userId)}
                    onGrantXp={() => onGrantXp(player.userId)}
                    onHealPlayer={() => onHealPlayer(player.userId)}
                    setHpDraftByUserId={setHpDraftByUserId}
                    setXpDraftByUserId={setXpDraftByUserId}
                    sheet={sheet}
                    userId={player.userId}
                    xpDraft={xpDraftByUserId[player.userId] ?? ""}
                  />

                  {!items ? (
                    <p className="py-2 text-xs text-slate-500">Loading...</p>
                  ) : items.length === 0 ? (
                    <p className="py-2 text-xs text-slate-500">No items yet.</p>
                  ) : (
                    <div className="mt-3 space-y-3">
                      <div className="space-y-3 rounded-2xl border border-slate-800 bg-slate-950/60 p-3">
                        <div className="flex flex-col gap-3 lg:flex-row">
                          <input
                            type="text"
                            value={inventorySearchByUserId[player.userId] ?? ""}
                            onChange={(event) =>
                              setInventorySearchByUserId((current) => ({
                                ...current,
                                [player.userId]: event.target.value,
                              }))
                            }
                            placeholder="Search inventory"
                            className="flex-1 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white placeholder:text-slate-500 focus:border-limiar-500 focus:outline-none"
                          />
                          <button
                            type="button"
                            onClick={() =>
                              setEquippedOnlyByUserId((current) => ({
                                ...current,
                                [player.userId]: !(current[player.userId] ?? false),
                              }))
                            }
                            className={`rounded-xl border px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.18em] ${
                              equippedOnlyByUserId[player.userId]
                                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                                : "border-slate-700 bg-slate-900 text-slate-300"
                            }`}
                          >
                            Equipped only
                          </button>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {(["all", "weapon", "armor", "magic", "consumable", "misc"] as const).map((entryGroup) => (
                            <button
                              key={entryGroup}
                              type="button"
                              onClick={() =>
                                setInventoryGroupByUserId((current) => ({
                                  ...current,
                                  [player.userId]: entryGroup,
                                }))
                              }
                              className={`rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] ${
                                (inventoryGroupByUserId[player.userId] ?? "all") === entryGroup
                                  ? "border-limiar-500/30 bg-limiar-500/10 text-limiar-200"
                                  : "border-slate-700 bg-slate-900 text-slate-400"
                              }`}
                            >
                              {entryGroup === "all"
                                ? "All"
                                : entryGroup === "weapon"
                                  ? "Weapon"
                                  : entryGroup === "armor"
                                    ? "Armor"
                                    : entryGroup === "magic"
                                      ? "Magic"
                                      : entryGroup === "consumable"
                                        ? "Consumable"
                                        : "Misc"}
                            </button>
                          ))}
                        </div>
                      </div>

                      {filteredItems.length === 0 ? (
                        <p className="py-2 text-xs text-slate-500">No items match the current filters.</p>
                      ) : null}

                      {filteredItems.map(({ entry, item }) => (
                        <div key={entry.id} className="flex items-center justify-between rounded-xl bg-slate-900/60 px-3 py-2">
                          <span className="text-sm text-white">
                            {item ? localizedItemName(item, locale) : entry.itemId}
                          </span>
                          <div className="flex items-center gap-2 text-xs text-slate-400">
                            <span>×{entry.quantity}</span>
                            {entry.isEquipped && (
                              <span className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2 py-0.5 text-emerald-400">
                                Equipped
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="mt-4 grid gap-3 lg:grid-cols-2">
                    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-3">
                      <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-500">
                        Give Currency
                      </p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {buildWalletDisplay(walletByUserId[player.userId] ?? EMPTY_WALLET).map((coin) => (
                          <span key={coin.coin} className={coin.className} title={coin.longLabel}>
                            {coin.amount} {coin.shortLabel}
                          </span>
                        ))}
                      </div>
                      <div className="mt-3 flex gap-2">
                        <input
                          type="number"
                          min={1}
                          value={currencyDraftByUserId[player.userId]?.amount ?? ""}
                          onChange={(event) =>
                            setCurrencyDraftByUserId((current) => ({
                              ...current,
                              [player.userId]: {
                                amount: event.target.value,
                                coin: current[player.userId]?.coin ?? "gp",
                              },
                            }))
                          }
                          placeholder="10"
                          className="w-24 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-limiar-500 focus:outline-none"
                        />
                        <select
                          value={currencyDraftByUserId[player.userId]?.coin ?? "gp"}
                          onChange={(event) =>
                            setCurrencyDraftByUserId((current) => ({
                              ...current,
                              [player.userId]: {
                                amount: current[player.userId]?.amount ?? "",
                                coin: event.target.value as CurrencyUnit,
                              },
                            }))
                          }
                          className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs uppercase text-white focus:border-limiar-500 focus:outline-none"
                        >
                          {(["cp", "sp", "ep", "gp", "pp"] as CurrencyUnit[]).map((coin) => (
                            <option key={coin} value={coin}>
                              {coin}
                            </option>
                          ))}
                        </select>
                        <button
                          type="button"
                          onClick={() => onGrantCurrency(player.userId)}
                          disabled={grantingCurrencyForUserId === player.userId}
                          className="rounded-xl bg-emerald-500/80 px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-white hover:bg-emerald-500 disabled:opacity-60"
                        >
                          {grantingCurrencyForUserId === player.userId ? "Sending..." : "Give"}
                        </button>
                      </div>
                    </div>

                    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-3">
                      <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-500">Give Item</p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        <select
                          value={itemDraftByUserId[player.userId]?.itemId ?? sortedCatalogItems[0]?.id ?? ""}
                          onChange={(event) =>
                            setItemDraftByUserId((current) => ({
                              ...current,
                              [player.userId]: {
                                itemId: event.target.value,
                                quantity: current[player.userId]?.quantity ?? "1",
                              },
                            }))
                          }
                          className="min-w-48 flex-1 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-limiar-500 focus:outline-none"
                        >
                          {sortedCatalogItems.length === 0 ? (
                            <option value="">No items</option>
                          ) : (
                            sortedCatalogItems.map((item) => (
                              <option key={item.id} value={item.id}>
                                {localizedItemName(item, locale)}
                              </option>
                            ))
                          )}
                        </select>
                        <input
                          type="number"
                          min={1}
                          value={itemDraftByUserId[player.userId]?.quantity ?? "1"}
                          onChange={(event) =>
                            setItemDraftByUserId((current) => ({
                              ...current,
                              [player.userId]: {
                                itemId: current[player.userId]?.itemId ?? sortedCatalogItems[0]?.id ?? "",
                                quantity: event.target.value,
                              },
                            }))
                          }
                          className="w-20 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-limiar-500 focus:outline-none"
                        />
                        <button
                          type="button"
                          onClick={() => onGrantItem(player.userId)}
                          disabled={grantingItemForUserId === player.userId || sortedCatalogItems.length === 0}
                          className="rounded-xl bg-limiar-500/80 px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-white hover:bg-limiar-500 disabled:opacity-60"
                        >
                          {grantingItemForUserId === player.userId ? "Sending..." : "Give"}
                        </button>
                      </div>
                    </div>
                  </div>

                  {grantFeedbackByUserId[player.userId] && (
                    <div className={`mt-3 rounded-2xl border px-3 py-2 text-[11px] ${grantFeedbackByUserId[player.userId].tone === "success" ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-300" : "border-rose-500/20 bg-rose-500/10 text-rose-200"}`}>
                      {grantFeedbackByUserId[player.userId].message}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
