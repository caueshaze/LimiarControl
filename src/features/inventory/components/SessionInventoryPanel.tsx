import { useState } from "react";
import type { InventoryItem } from "../../../entities/inventory";
import type { Item } from "../../../entities/item";
import { getItemPropertyLabels } from "../../../entities/item";
import { useLocale } from "../../../shared/hooks/useLocale";
import type { CurrencyWallet } from "../../../shared/api/inventoryRepo";

type SessionInventoryPanelProps = {
  flash?: boolean;
  inventory: InventoryItem[] | null;
  itemsById: Record<string, Item>;
  wallet?: CurrencyWallet | null;
  open: boolean;
  onToggleOpen: () => void;
};

export const SessionInventoryPanel = ({
  flash = false,
  inventory,
  itemsById,
  wallet = null,
  open,
  onToggleOpen,
}: SessionInventoryPanelProps) => {
  const { t } = useLocale();
  const totalItems = inventory?.reduce((sum, item) => sum + item.quantity, 0) ?? 0;

  return (
    <div
      className={`overflow-hidden rounded-[32px] border bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] shadow-[0_18px_60px_rgba(2,6,23,0.2)] transition-all ${
        flash
          ? "border-emerald-500/35 shadow-[0_0_40px_rgba(16,185,129,0.12)]"
          : "border-white/8"
      }`}
    >
      <button
        type="button"
        onClick={onToggleOpen}
        className="flex w-full items-center justify-between gap-4 px-6 py-5 text-left transition-colors hover:bg-white/[0.03]"
      >
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-slate-400">
            {t("playerBoard.inventoryStateLabel")}
          </p>
          <h2 className="mt-2 flex items-center gap-3 text-sm font-bold uppercase tracking-[0.24em] text-slate-100">
            <span className="h-4 w-1 rounded-full bg-amber-500" />
            {t("playerBoard.inventoryTitle")}
          </h2>
          {inventory !== null && (
            <p className="mt-1 text-sm text-slate-400">
              {totalItems} · {t("playerBoard.inventoryLoadedState")}
            </p>
          )}
          <p className="mt-2 text-xs text-amber-200">
            {t("shop.panel.wallet")}: {formatInventoryWallet(wallet)}
          </p>
        </div>
        <span className={`text-xs text-slate-500 transition-transform ${open ? "rotate-180" : ""}`}>
          ▼
        </span>
      </button>
      {open && (
        <div className="border-t border-white/8 px-6 pb-6">
          {inventory === null ? (
            <p className="py-4 text-sm text-slate-400">{t("inventory.loading")}</p>
          ) : inventory.length === 0 ? (
            <p className="py-4 text-sm text-slate-400">{t("inventory.empty")}</p>
          ) : (
            <div className="mt-4 space-y-2">
              {inventory.map((entry) => (
                <SessionInventoryItem
                  key={entry.id}
                  entry={entry}
                  item={itemsById[entry.itemId]}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const formatInventoryWallet = (wallet: CurrencyWallet | null | undefined) => {
  const current = wallet ?? { cp: 0, sp: 0, ep: 0, gp: 0, pp: 0 };
  const parts = ([
    ["pp", current.pp],
    ["gp", current.gp],
    ["ep", current.ep],
    ["sp", current.sp],
    ["cp", current.cp],
  ] as const)
    .filter(([, amount]) => amount > 0)
    .map(([coin, amount]) => `${amount} ${coin}`);

  return parts.length > 0 ? parts.join(" · ") : "0 gp";
};

const SessionInventoryItem = ({
  entry,
  item,
}: {
  entry: InventoryItem;
  item?: Item;
}) => {
  const { t, locale } = useLocale();
  const [expanded, setExpanded] = useState(false);
  const propertyLabels = getItemPropertyLabels(item?.properties, locale);

  const detailRows = [
    item?.priceLabel ?? item?.price
      ? { label: t("inventory.price"), value: item?.priceLabel ?? String(item?.price) }
      : null,
    item?.damageDice ? { label: t("inventory.damage"), value: item.damageDice } : null,
    item?.rangeMeters !== undefined && item?.rangeMeters !== null
      ? { label: t("inventory.range"), value: `${item.rangeMeters}m` }
      : null,
    item?.weight !== undefined && item?.weight !== null
      ? { label: t("inventory.weight"), value: String(item.weight) }
      : null,
    propertyLabels.length > 0
      ? { label: t("inventory.properties"), value: propertyLabels.join(", ") }
      : null,
    entry.notes ? { label: t("inventory.notes"), value: entry.notes } : null,
  ].filter(Boolean) as Array<{ label: string; value: string }>;

  const hasDetails = Boolean(item?.description || detailRows.length > 0);

  return (
    <div className="rounded-[24px] border border-white/8 bg-white/[0.04]">
      <button
        type="button"
        onClick={() => hasDetails && setExpanded((current) => !current)}
        className={`flex w-full items-center justify-between gap-4 px-4 py-3 text-left ${
          hasDetails ? "hover:bg-white/[0.03]" : ""
        }`}
      >
        <div className="min-w-0">
          <p className="text-sm font-medium text-white">
            {item?.name ?? t("inventory.unknownItem")}
          </p>
          <p className="text-xs text-slate-500">
            {item?.type ?? t("inventory.unknownType")}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2 text-xs">
          <span className="rounded-full border border-slate-700 px-3 py-1 text-slate-300">
            x{entry.quantity}
          </span>
          {entry.isEquipped && (
            <span className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2 py-1 text-emerald-400">
              {t("inventory.equipped")}
            </span>
          )}
          {hasDetails && (
            <span className={`text-slate-500 transition-transform ${expanded ? "rotate-180" : ""}`}>
              ▼
            </span>
          )}
        </div>
      </button>
      {expanded && hasDetails && (
        <div className="space-y-3 border-t border-white/8 px-4 py-4 text-xs text-slate-300">
          {item?.description && <p className="text-slate-400">{item.description}</p>}
          <div className="grid gap-2 sm:grid-cols-2">
            {detailRows.map((detail) => (
              <p key={`${detail.label}-${detail.value}`} className="rounded-xl bg-slate-950/50 px-3 py-2">
                <span className="text-slate-500">{detail.label}</span> {detail.value}
              </p>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
