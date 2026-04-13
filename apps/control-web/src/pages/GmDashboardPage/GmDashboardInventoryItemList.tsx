import type { Item } from "../../entities/item";
import type { InventoryItem } from "../../entities/inventory";
import { localizedItemName } from "../../features/shop/utils/localizedItemName";
import { resolveInventoryEntries, filterInventoryEntries, type SessionInventoryFilterGroup } from "../../features/inventory/components/sessionInventoryPanel.utils";

type Props = {
  items: InventoryItem[] | undefined;
  catalogItems: Record<string, Item>;
  locale: string;
  equippedOnly: boolean;
  group: SessionInventoryFilterGroup;
  search: string;
};

export const GmDashboardInventoryItemList = ({
  items,
  catalogItems,
  locale,
  equippedOnly,
  group,
  search,
}: Props) => {
  if (!items) {
    return <p className="py-2 text-xs text-slate-500">Loading...</p>;
  }

  if (items.length === 0) {
    return <p className="py-2 text-xs text-slate-500">No items yet.</p>;
  }

  const resolvedItems = resolveInventoryEntries(items, catalogItems, locale);
  const filteredItems = filterInventoryEntries(resolvedItems, { equippedOnly, group, search });

  return (
    <div className="space-y-1">
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
  );
};
