import { useMemo, useState } from "react";
import type { ItemType } from "../../entities/item";
import { formatDamageLabel } from "../../shared/i18n/domainLabels";
import { useLocale } from "../../shared/hooks/useLocale";
import {
  buildInventoryGroupsFromResolved,
  filterInventoryEntries,
  type SessionInventoryFilterGroup,
  type SessionInventoryResolvedEntry,
} from "../../features/inventory/components/sessionInventoryPanel.utils";
import type { PartyDetailsPlayerResource } from "./usePartyDetailsResources";

type InventoryCardProps = {
  loadError: string | null;
  loading: boolean;
  players: PartyDetailsPlayerResource[];
};

export const PartyDetailsInventoryCard = ({
  loadError,
  loading,
  players,
}: InventoryCardProps) => {
  const { locale, t } = useLocale();
  const [search, setSearch] = useState("");
  const [group, setGroup] = useState<SessionInventoryFilterGroup>("all");
  const [equippedOnly, setEquippedOnly] = useState(false);
  const [selectedPlayerId, setSelectedPlayerId] = useState("all");
  const hasEntryFilters = Boolean(search.trim()) || group !== "all" || equippedOnly;
  const visiblePlayers = useMemo(
    () =>
      players
        .filter((player) => selectedPlayerId === "all" || player.userId === selectedPlayerId)
        .map((player) => {
          const filteredEntries = filterInventoryEntries(player.resolvedInventory, {
            equippedOnly,
            group,
            search,
          });
          return {
            ...player,
            entriesToRender: hasEntryFilters ? filteredEntries : player.resolvedInventory,
          };
        })
        .filter((player) => !hasEntryFilters || player.entriesToRender.length > 0),
    [equippedOnly, group, hasEntryFilters, players, search, selectedPlayerId],
  );
  const visibleSummary = useMemo(
    () => ({
      equippedCount: visiblePlayers.reduce(
        (sum, player) => sum + player.entriesToRender.filter((entry) => entry.entry.isEquipped).length,
        0,
      ),
      playerCount: visiblePlayers.length,
      totalItems: visiblePlayers.reduce(
        (sum, player) => sum + player.entriesToRender.reduce((playerSum, entry) => playerSum + entry.entry.quantity, 0),
        0,
      ),
    }),
    [visiblePlayers],
  );

  return (
    <div className="rounded-[30px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.95))] p-6">
      <div className="border-b border-white/8 pb-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-amber-300">
          {t("gm.party.inventoryTitle")}
        </p>
        <p className="mt-3 text-sm leading-7 text-slate-300">
          {t("gm.party.inventoryDescription")}
        </p>
      </div>

      <div className="mt-5 space-y-3">
        {loadError ? (
          <p className="text-sm text-rose-300">{loadError}</p>
        ) : loading ? (
          <p className="text-sm text-slate-400">{t("gm.party.loadingResources")}</p>
        ) : players.length === 0 ? (
          <p className="text-sm text-slate-500">{t("gm.party.noPlayersYet")}</p>
        ) : (
          <div className="space-y-5">
            <div className="grid gap-3 sm:grid-cols-3">
              <PartyInventorySummaryPill
                label={t("inventory.playersTitle")}
                value={String(visibleSummary.playerCount)}
              />
              <PartyInventorySummaryPill
                label={t("gm.party.inventoryItems")}
                value={String(visibleSummary.totalItems)}
              />
              <PartyInventorySummaryPill
                label={t("inventory.equipped")}
                value={String(visibleSummary.equippedCount)}
              />
            </div>

            <div className="space-y-3 rounded-[26px] border border-white/8 bg-white/3 p-4">
              <div className="space-y-3">
                <input
                  type="text"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder={t("inventory.searchPlaceholder")}
                  className="min-w-0 rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-amber-400/60 focus:outline-none"
                />

                <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto]">
                  <select
                    value={selectedPlayerId}
                    onChange={(event) => setSelectedPlayerId(event.target.value)}
                    className="min-w-0 rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-amber-400/60 focus:outline-none"
                  >
                    <option value="all">
                      {t("inventory.playersTitle")} · {t("inventory.filterAll")}
                    </option>
                    {players.map((player) => (
                      <option key={player.userId} value={player.userId}>
                        {player.displayName}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={() => setEquippedOnly((current) => !current)}
                    className={`w-full rounded-2xl border px-4 py-3 text-xs font-semibold uppercase tracking-[0.18em] transition md:w-auto ${
                      equippedOnly
                        ? "border-emerald-400/40 bg-emerald-400/10 text-emerald-200"
                        : "border-white/10 bg-white/4 text-slate-300 hover:border-white/20"
                    }`}
                  >
                    {t("inventory.equippedOnly")}
                  </button>
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                {(["all", "weapon", "armor", "magic", "consumable", "misc"] as const).map((entryGroup) => (
                  <button
                    key={entryGroup}
                    type="button"
                    onClick={() => setGroup(entryGroup)}
                    className={`rounded-full border px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] transition ${
                      group === entryGroup
                        ? "border-amber-400/40 bg-amber-400/10 text-amber-200"
                        : "border-white/10 bg-white/3 text-slate-400 hover:border-white/20"
                    }`}
                  >
                    {entryGroup === "all" ? t("inventory.filterAll") : getPartyInventoryGroupLabel(entryGroup, t)}
                  </button>
                ))}
              </div>
            </div>

            {visiblePlayers.length === 0 ? (
              <p className="text-sm text-slate-400">{t("inventory.emptyFiltered")}</p>
            ) : (
              <div className="space-y-4">
                {visiblePlayers.map((player) => (
                  <PartyPlayerInventorySection
                    key={player.userId}
                    entries={player.entriesToRender}
                    locale={locale}
                    player={player}
                    t={t}
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

const PartyInventorySummaryPill = ({ label, value }: { label: string; value: string }) => (
  <div className="rounded-[22px] border border-white/8 bg-white/3 px-4 py-3">
    <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
    <p className="mt-2 text-lg font-semibold text-white">{value}</p>
  </div>
);

const PartyPlayerInventorySection = ({
  entries,
  locale,
  player,
  t,
}: {
  entries: SessionInventoryResolvedEntry[];
  locale: "en" | "pt" | string;
  player: PartyDetailsPlayerResource & { entriesToRender: SessionInventoryResolvedEntry[] };
  t: ReturnType<typeof useLocale>["t"];
}) => {
  const groupedEntries = buildInventoryGroupsFromResolved(entries);
  const totalItems = entries.reduce((sum, entry) => sum + entry.entry.quantity, 0);
  const equippedCount = entries.filter((entry) => entry.entry.isEquipped).length;

  return (
    <article className="rounded-3xl border border-white/8 bg-white/3 p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-base font-semibold text-white">{player.displayName}</p>
          <p className="mt-2 text-xs text-slate-400">
            {t("gm.party.inventoryItemsCount").replace("{n}", String(totalItems))}
            {" · "}
            {t("gm.party.inventoryTypesCount").replace("{n}", String(entries.length))}
            {" · "}
            {t("gm.party.inventoryEquippedCount").replace("{n}", String(equippedCount))}
          </p>
        </div>
        <span className="rounded-full border border-white/10 bg-white/4 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-300">
          {player.totalItems}
        </span>
      </div>

      {entries.length === 0 ? (
        <p className="mt-4 text-sm text-slate-500">{t("gm.party.inventoryPreviewEmpty")}</p>
      ) : (
        <div className="mt-4 space-y-4">
          {groupedEntries.map((section) => (
            <div key={section.group} className="space-y-3">
              <div className="flex items-center gap-3">
                <span className="h-px flex-1 bg-white/8" />
                <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                  {getPartyInventoryGroupLabel(section.group, t)}
                </p>
                <span className="h-px flex-1 bg-white/8" />
              </div>

              <div className="space-y-3">
                {section.entries.map((resolved) => {
                  const meta = getPartyInventoryEntryMeta(resolved.item, locale, t);

                  return (
                    <div
                      key={resolved.entry.id}
                      className="flex items-start justify-between gap-4 rounded-[22px] border border-white/8 bg-slate-950/60 px-4 py-3"
                    >
                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold text-white">
                          {resolved.name}
                        </p>
                        <p className="mt-1 truncate text-xs text-slate-500">
                          {getPartyInventoryItemTypeLabel(resolved.item?.type, t)}
                        </p>
                        {meta ? (
                          <p className="mt-2 truncate text-xs text-slate-300">{meta}</p>
                        ) : null}
                      </div>

                      <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
                        <span className="rounded-full border border-white/10 bg-white/4 px-2.5 py-1 text-xs font-semibold text-slate-200">
                          x{resolved.entry.quantity}
                        </span>
                        {resolved.entry.isEquipped ? (
                          <span className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.22em] text-emerald-200">
                            {t("inventory.equipped")}
                          </span>
                        ) : null}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </article>
  );
};

const getPartyInventoryGroupLabel = (
  group: "weapon" | "armor" | "magic" | "consumable" | "misc",
  t: ReturnType<typeof useLocale>["t"],
) => {
  switch (group) {
    case "weapon":
      return t("playerParty.itemTypeWeapon");
    case "armor":
      return t("playerParty.itemTypeArmor");
    case "magic":
      return t("playerParty.itemTypeMagic");
    case "consumable":
      return t("playerParty.itemTypeConsumable");
    default:
      return t("playerParty.itemTypeMisc");
  }
};

const getPartyInventoryItemTypeLabel = (
  type: ItemType | null | undefined,
  t: ReturnType<typeof useLocale>["t"],
) => {
  switch (type) {
    case "WEAPON":
      return t("playerParty.itemTypeWeapon");
    case "ARMOR":
      return t("playerParty.itemTypeArmor");
    case "CONSUMABLE":
      return t("playerParty.itemTypeConsumable");
    case "MAGIC":
      return t("playerParty.itemTypeMagic");
    case "MISC":
      return t("playerParty.itemTypeMisc");
    default:
      return t("inventory.unknownType");
  }
};

const getPartyInventoryEntryMeta = (
  item: SessionInventoryResolvedEntry["item"],
  locale: "en" | "pt" | string,
  t: ReturnType<typeof useLocale>["t"],
) => {
  if (!item) {
    return null;
  }
  if (item.damageDice) {
    return formatDamageLabel(item.damageDice, item.damageType, locale) ?? item.damageDice;
  }
  if (item.healDice || typeof item.healBonus === "number") {
    if (!item.healDice) {
      return `${t("inventory.healing")} ${item.healBonus ?? 0}`;
    }
    return `${t("inventory.healing")} ${item.healDice}${typeof item.healBonus === "number" && item.healBonus !== 0 ? ` + ${item.healBonus}` : ""}`;
  }
  if (item.armorClassBase != null) {
    return `CA ${item.armorClassBase}`;
  }
  if (item.weight != null) {
    return `${t("inventory.weight")} ${item.weight}`;
  }
  return item.description || null;
};
