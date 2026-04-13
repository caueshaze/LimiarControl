import type { ItemType } from "../../entities/item";
import { useLocale } from "../../shared/hooks/useLocale";
import { getShopItemTypeLabelKey } from "../../features/shop/utils/shopItemTypes";
import { CATALOG_TYPE_META } from "../../features/shop/utils/catalogTypeMeta";

type CatalogFiltersProps = {
  filteredCount: number;
  search: string;
  totalCount: number;
  typeCounts: Record<ItemType, number>;
  typeFilter: "ALL" | ItemType;
  itemTypes: ItemType[];
  onClear: () => void;
  onSearchChange: (value: string) => void;
  onTypeFilterChange: (value: "ALL" | ItemType) => void;
};

export const CatalogFilters = ({
  filteredCount,
  search,
  totalCount,
  typeCounts,
  typeFilter,
  itemTypes,
  onClear,
  onSearchChange,
  onTypeFilterChange,
}: CatalogFiltersProps) => {
  const { t } = useLocale();
  const hasActiveFilters = search.trim().length > 0 || typeFilter !== "ALL";

  return (
    <div className="rounded-[30px] border border-white/8 bg-[linear-gradient(180deg,rgba(8,12,28,0.92),rgba(2,6,23,0.95))] p-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.26em] text-slate-500">
            {t("catalog.filtersTitle")}
          </p>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            {filteredCount} {t("catalog.filtersResults")}
            {filteredCount !== totalCount ? ` / ${totalCount}` : ""}
          </p>
        </div>

        {hasActiveFilters && (
          <button
            type="button"
            onClick={onClear}
            className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-200 transition hover:border-white/20 hover:bg-white/9"
          >
            {t("catalog.clearFilters")}
          </button>
        )}
      </div>

      <div className="mt-4">
        <input
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder={t("catalog.searchPlaceholder")}
          className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-limiar-400/60 focus:outline-none"
        />
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <FilterChip
          active={typeFilter === "ALL"}
          count={totalCount}
          label={t("shop.panel.all")}
          onClick={() => onTypeFilterChange("ALL")}
        />
        {itemTypes.map((type) => (
          <FilterChip
            key={type}
            active={typeFilter === type}
            count={typeCounts[type]}
            label={t(getShopItemTypeLabelKey(type))}
            onClick={() => onTypeFilterChange(type)}
            className={CATALOG_TYPE_META[type].chipClass}
          />
        ))}
      </div>
    </div>
  );
};

const FilterChip = ({
  active,
  count,
  label,
  onClick,
  className,
}: {
  active: boolean;
  count: number;
  label: string;
  onClick: () => void;
  className?: string;
}) => (
  <button
    type="button"
    onClick={onClick}
    className={`inline-flex items-center gap-2 rounded-full border px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] transition ${
      active
        ? className ?? "border-limiar-300/25 bg-limiar-400/12 text-limiar-100"
        : "border-white/8 bg-white/4 text-slate-300 hover:border-white/16 hover:bg-white/8"
    }`}
  >
    <span>{label}</span>
    <span className={`rounded-full px-2 py-0.5 text-[10px] ${active ? "bg-black/20 text-white" : "bg-slate-900 text-slate-300"}`}>
      {count}
    </span>
  </button>
);
