import { useMemo, useState } from "react";
import type { InventoryItem } from "../../../entities/inventory";
import type { Item } from "../../../entities/item";
import { localizedItemName } from "../../../features/shop/utils/localizedItemName";
import {
  buildInventoryGroupsFromResolved,
  buildInventorySummary,
  filterInventoryEntries,
  resolveInventoryEntries,
  type SessionInventoryFilterGroup,
} from "../../../features/inventory/components/sessionInventoryPanel.utils";
import { useLocale } from "../../../shared/hooks/useLocale";
import { formatDamageLabel } from "../../../shared/i18n/domainLabels";
import type { PlayerPartySelectedItem } from "../playerParty.types";
import { getItemTypeLabel } from "../playerParty.utils";

type Props = {
  inventory: InventoryItem[] | null;
  catalogItems: Record<string, Item>;
  onSelectItem: (item: PlayerPartySelectedItem) => void;
};

export const PlayerPartyInventoryCard = ({
  inventory,
  catalogItems,
  onSelectItem,
}: Props) => {
  const { locale, t } = useLocale();
  const [search, setSearch] = useState("");
  const [group, setGroup] = useState<SessionInventoryFilterGroup>("all");
  const [equippedOnly, setEquippedOnly] = useState(false);
  const inventorySummary = useMemo(
    () => buildInventorySummary(inventory, catalogItems, locale),
    [catalogItems, inventory, locale],
  );
  const resolvedEntries = useMemo(
    () => resolveInventoryEntries(inventory, catalogItems, locale),
    [catalogItems, inventory, locale],
  );
  const filteredEntries = useMemo(
    () =>
      filterInventoryEntries(resolvedEntries, {
        equippedOnly,
        group,
        search,
      }),
    [equippedOnly, group, resolvedEntries, search],
  );
  const groups = useMemo(
    () => buildInventoryGroupsFromResolved(filteredEntries),
    [filteredEntries],
  );

  return (
    <section className="rounded-4xl border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] px-6 py-5 shadow-[0_18px_60px_rgba(2,6,23,0.2)]">
      <div className="flex items-start justify-between gap-4 border-b border-white/8 pb-4">
        <div className="space-y-1">
          <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-500">
            {t("playerParty.inventoryTitle")}
          </p>
          <h2 className="text-xl font-semibold text-white">
            {t("playerParty.inventoryHeading")}
          </h2>
          <p className="text-sm leading-7 text-slate-400">
            {t("playerParty.inventoryDescription")}
          </p>
        </div>
        <span className="rounded-full border border-white/8 bg-white/4 px-3 py-1.5 text-xs font-semibold text-slate-200">
          {inventorySummary.totalItems}
        </span>
      </div>

      {inventory === null ? (
        <p className="py-5 text-sm text-slate-400">{t("playerParty.inventoryLoading")}</p>
      ) : inventory.length === 0 ? (
        <p className="py-5 text-sm leading-7 text-slate-400">
          {t("playerParty.inventoryEmpty")}
        </p>
      ) : (
        <div className="mt-4 space-y-5">
          <div className="grid gap-3 sm:grid-cols-3">
            <SummaryPill
              label={t("playerBoard.inventoryTotalLabel")}
              value={String(inventorySummary.totalItems)}
            />
            <SummaryPill
              label={t("playerBoard.inventoryDistinctLabel")}
              value={String(inventorySummary.distinctItems)}
            />
            <SummaryPill
              label={t("playerBoard.inventoryEquippedLabel")}
              value={String(inventorySummary.equippedCount)}
            />
          </div>

          <div className="space-y-3 rounded-[26px] border border-white/8 bg-white/3 p-4">
            <div className="flex flex-col gap-3 lg:flex-row">
              <input
                type="text"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder={t("inventory.searchPlaceholder")}
                className="flex-1 rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-amber-400/60 focus:outline-none"
              />
              <button
                type="button"
                onClick={() => setEquippedOnly((current) => !current)}
                className={`rounded-2xl border px-4 py-3 text-xs font-semibold uppercase tracking-[0.18em] transition ${
                  equippedOnly
                    ? "border-emerald-400/40 bg-emerald-400/10 text-emerald-200"
                    : "border-white/10 bg-white/4 text-slate-300 hover:border-white/20"
                }`}
              >
                {t("inventory.equippedOnly")}
              </button>
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
                  {entryGroup === "all" ? t("inventory.filterAll") : getItemTypeLabelLabel(entryGroup, t)}
                </button>
              ))}
            </div>
          </div>

          {filteredEntries.length === 0 ? (
            <p className="text-sm text-slate-400">{t("inventory.emptyFiltered")}</p>
          ) : (
            <div className="space-y-4">
              {groups.map((section) => (
                <div key={section.group} className="space-y-3">
                  <div className="flex items-center gap-3">
                    <span className="h-px flex-1 bg-white/8" />
                    <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                      {getItemTypeLabelLabel(section.group, t)}
                    </p>
                    <span className="h-px flex-1 bg-white/8" />
                  </div>

                  <div className="space-y-3">
                    {section.entries.map(({ entry, item }) => {
                      const meta = getInventoryEntryMeta(item, locale, t);

                      return (
                        <button
                          key={entry.id}
                          type="button"
                          onClick={() =>
                            item
                              ? onSelectItem({ item, inv: entry })
                              : undefined
                          }
                          className={`flex w-full items-start justify-between gap-4 rounded-[22px] border px-4 py-3 text-left transition ${
                            item
                              ? "border-white/8 bg-white/3 hover:border-white/14 hover:bg-white/5"
                              : "cursor-default border-white/8 bg-white/3"
                          }`}
                        >
                          <div className="min-w-0">
                            <p className="truncate text-sm font-semibold text-white">
                              {item ? localizedItemName(item, locale) : t("inventory.unknownItem")}
                            </p>
                            <p className="mt-1 truncate text-xs text-slate-500">
                              {getItemTypeLabel(item?.type, t)}
                            </p>
                            {meta ? (
                              <p className="mt-2 truncate text-xs text-slate-300">{meta}</p>
                            ) : null}
                          </div>

                          <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
                            <span className="rounded-full border border-white/10 bg-white/4 px-2.5 py-1 text-xs font-semibold text-slate-200">
                              x{entry.quantity}
                            </span>
                            {entry.isEquipped ? (
                              <span className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.22em] text-emerald-200">
                                {t("playerParty.equipped")}
                              </span>
                            ) : null}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
};

const SummaryPill = ({ label, value }: { label: string; value: string }) => (
  <div className="rounded-[22px] border border-white/8 bg-white/3 px-4 py-3">
    <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
    <p className="mt-2 text-lg font-semibold text-white">{value}</p>
  </div>
);

const getItemTypeLabelLabel = (
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

const getInventoryEntryMeta = (
  item: Item | null | undefined,
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
