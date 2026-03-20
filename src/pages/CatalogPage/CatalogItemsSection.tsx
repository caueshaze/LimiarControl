import type { ReactNode } from "react";
import type { Item, ItemInput, ItemType } from "../../entities/item";
import { CatalogItemList } from "../../features/shop";
import { useLocale } from "../../shared/hooks/useLocale";
import { CatalogFilters } from "./CatalogFilters";

type Props = {
  filteredItemsCount: number;
  itemsCount: number;
  itemsLoading: boolean;
  itemTypes: ItemType[];
  items: Item[];
  search: string;
  showEmptyFiltered: boolean;
  typeCounts: Record<ItemType, number>;
  typeFilter: "ALL" | ItemType;
  onClear: () => void;
  onDelete: (itemId: string) => void | Promise<void>;
  onSearchChange: (value: string) => void;
  onTypeFilterChange: (value: "ALL" | ItemType) => void;
  onUpdate: (itemId: string, payload: ItemInput) => boolean | Promise<boolean>;
};

export const CatalogItemsSection = ({
  filteredItemsCount,
  itemsCount,
  itemsLoading,
  itemTypes,
  items,
  search,
  showEmptyFiltered,
  typeCounts,
  typeFilter,
  onClear,
  onDelete,
  onSearchChange,
  onTypeFilterChange,
  onUpdate,
}: Props) => {
  const { t } = useLocale();

  return (
    <div className="space-y-5">
      <CatalogFilters
        filteredCount={filteredItemsCount}
        search={search}
        totalCount={itemsCount}
        typeCounts={typeCounts}
        typeFilter={typeFilter}
        itemTypes={itemTypes}
        onClear={onClear}
        onSearchChange={onSearchChange}
        onTypeFilterChange={onTypeFilterChange}
      />

      {itemsLoading ? (
        <StatusCard>{t("catalog.loading")}</StatusCard>
      ) : showEmptyFiltered ? (
        <div className="rounded-[28px] border border-white/8 bg-[linear-gradient(180deg,rgba(8,12,28,0.92),rgba(2,6,23,0.95))] p-6 shadow-[0_20px_60px_rgba(2,6,23,0.18)]">
          <p className="text-[10px] font-semibold uppercase tracking-[0.26em] text-slate-500">
            {t("catalog.filtersTitle")}
          </p>
          <h2 className="mt-3 font-display text-2xl font-bold text-white">
            {t("catalog.emptyFilteredTitle")}
          </h2>
          <p className="mt-3 max-w-xl text-sm leading-7 text-slate-400">
            {t("catalog.emptyFilteredDescription")}
          </p>
        </div>
      ) : (
        <CatalogItemList
          items={items}
          itemTypes={itemTypes}
          onUpdate={onUpdate}
          onDelete={onDelete}
        />
      )}
    </div>
  );
};

const StatusCard = ({ children }: { children: ReactNode }) => (
  <div className="rounded-[28px] border border-white/8 bg-[linear-gradient(180deg,rgba(8,12,28,0.92),rgba(2,6,23,0.95))] p-5 text-sm text-slate-300">
    {children}
  </div>
);
