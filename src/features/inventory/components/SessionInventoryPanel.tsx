import { useState } from "react";
import type { InventoryItem } from "../../../entities/inventory";
import type { Item } from "../../../entities/item";
import { getItemPropertyLabels } from "../../../entities/item";
import { useLocale } from "../../../shared/hooks/useLocale";

type SessionInventoryPanelProps = {
  flash?: boolean;
  inventory: InventoryItem[] | null;
  itemsById: Record<string, Item>;
  open: boolean;
  onToggleOpen: () => void;
};

export const SessionInventoryPanel = ({
  flash = false,
  inventory,
  itemsById,
  open,
  onToggleOpen,
}: SessionInventoryPanelProps) => {
  const { t } = useLocale();
  const totalItems = inventory?.reduce((sum, item) => sum + item.quantity, 0) ?? 0;

  return (
    <div
      className={`rounded-3xl border bg-slate-950/60 overflow-hidden transition-all ${
        flash
          ? "border-emerald-500/40 shadow-[0_0_30px_rgba(16,185,129,0.12)]"
          : "border-slate-800"
      }`}
    >
      <button
        type="button"
        onClick={onToggleOpen}
        className="flex w-full items-center justify-between p-6 transition-colors hover:bg-slate-900/20"
      >
        <h2 className="flex items-center gap-3 text-sm font-bold uppercase tracking-[0.3em] text-slate-400">
          <span className="h-4 w-1 rounded-full bg-amber-500" />
          {t("playerBoard.inventoryTitle") || "My Inventory"}
          {inventory !== null && (
            <span className="text-xs font-normal text-slate-500 normal-case tracking-normal">
              ({totalItems})
            </span>
          )}
        </h2>
        <span className={`text-xs text-slate-500 transition-transform ${open ? "rotate-180" : ""}`}>
          ▼
        </span>
      </button>
      {open && (
        <div className="border-t border-slate-800/60 px-6 pb-6">
          {inventory === null ? (
            <p className="py-4 text-sm text-slate-500">Loading inventory...</p>
          ) : inventory.length === 0 ? (
            <p className="py-4 text-sm text-slate-500">
              No items yet. Buy from the shop during a session.
            </p>
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
    <div className="rounded-2xl border border-slate-800/40 bg-slate-900/40">
      <button
        type="button"
        onClick={() => hasDetails && setExpanded((current) => !current)}
        className={`flex w-full items-center justify-between gap-4 px-4 py-3 text-left ${
          hasDetails ? "hover:bg-slate-900/40" : ""
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
        <div className="space-y-3 border-t border-slate-800/60 px-4 py-4 text-xs text-slate-300">
          {item?.description && <p className="text-slate-400">{item.description}</p>}
          <div className="grid gap-2 sm:grid-cols-2">
            {detailRows.map((detail) => (
              <p key={`${detail.label}-${detail.value}`} className="rounded-xl bg-slate-950/60 px-3 py-2">
                <span className="text-slate-500">{detail.label}</span> {detail.value}
              </p>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
