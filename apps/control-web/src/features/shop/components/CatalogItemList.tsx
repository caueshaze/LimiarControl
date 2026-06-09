import type { Item, ItemInput, ItemType } from "../../../entities/item";
import type { BaseSpell } from "../../../entities/base-spell";
import { CatalogItemCard } from "./CatalogItemCard";
import { useLocale } from "../../../shared/hooks/useLocale";

type CatalogItemListProps = {
  items: Item[];
  itemTypes: ItemType[];
  spells: BaseSpell[];
  onUpdate?: (itemId: string, payload: ItemInput) => boolean | Promise<boolean>;
  onDelete?: (itemId: string) => void | Promise<void>;
};

export const CatalogItemList = ({
  items,
  itemTypes,
  spells,
  onUpdate,
  onDelete,
}: CatalogItemListProps) => {
  const { t } = useLocale();
  if (items.length === 0) {
    return (
      <div className="rounded-[28px] border border-white/8 bg-[linear-gradient(180deg,rgba(8,12,28,0.92),rgba(2,6,23,0.95))] p-5 text-sm text-slate-300">
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
          spells={spells}
          onUpdate={onUpdate}
          onDelete={onDelete}
        />
      ))}
    </div>
  );
};
