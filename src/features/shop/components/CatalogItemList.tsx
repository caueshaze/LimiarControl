import type { Item, ItemInput, ItemType } from "../../../entities/item";
import { CatalogItemCard } from "./CatalogItemCard";
import { useLocale } from "../../../shared/hooks/useLocale";

type CatalogItemListProps = {
  items: Item[];
  itemTypes: ItemType[];
  onUpdate?: (itemId: string, payload: ItemInput) => void;
  onDelete?: (itemId: string) => void;
};

export const CatalogItemList = ({
  items,
  itemTypes,
  onUpdate,
  onDelete,
}: CatalogItemListProps) => {
  const { t } = useLocale();
  if (items.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-300">
        {t("catalog.empty")}
      </div>
    );
  }

  return (
    <div className="grid gap-4">
      {items.map((item) => (
        <CatalogItemCard
          key={item.id}
          item={item}
          itemTypes={itemTypes}
          onUpdate={onUpdate}
          onDelete={onDelete}
        />
      ))}
    </div>
  );
};
