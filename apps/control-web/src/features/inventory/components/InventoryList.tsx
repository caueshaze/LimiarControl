import type { Item } from "../../../entities/item";
import type { InventoryItem } from "../../../entities/inventory";
import { InventoryItemRow } from "./InventoryItemRow";
import { useLocale } from "../../../shared/hooks/useLocale";

type InventoryListProps = {
  inventory: InventoryItem[];
  itemsById: Record<string, Item>;
  onToggleEquipped: (id: string) => void;
};

export const InventoryList = ({
  inventory,
  itemsById,
  onToggleEquipped,
}: InventoryListProps) => {
  const { t } = useLocale();
  if (inventory.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-300">
        {t("inventory.empty")}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {inventory.map((entry) => (
        <InventoryItemRow
          key={entry.id}
          entry={entry}
          item={itemsById[entry.itemId]}
          onToggleEquipped={() => onToggleEquipped(entry.id)}
        />
      ))}
    </div>
  );
};
