import type { ItemType } from "../../../entities/item";
import { useLocale } from "../../../shared/hooks/useLocale";
import { getShopItemTypeLabelKey, SHOP_ITEM_TYPES } from "../utils/shopItemTypes";

type ShopFilterBarProps = {
  filteredCount: number;
  ownedCount: number;
  ownedOnly: boolean;
  onClear: () => void;
  onOwnedOnlyChange: (value: boolean) => void;
  onSearchChange: (value: string) => void;
  onTypeFilterChange: (value: "ALL" | ItemType) => void;
  search: string;
  totalCount: number;
  typeCounts: Record<ItemType, number>;
  typeFilter: "ALL" | ItemType;
};

export const ShopFilterBar = ({
  filteredCount,
  ownedCount,
  ownedOnly,
  onClear,
  onOwnedOnlyChange,
  onSearchChange,
  onTypeFilterChange,
  search,
  totalCount,
  typeCounts,
  typeFilter,
}: ShopFilterBarProps) => {
  const { t } = useLocale();
  const hasActiveFilters = search.trim().length > 0 || typeFilter !== "ALL" || ownedOnly;

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-[11px] uppercase tracking-[0.3em] text-slate-500">
            {t("shop.panel.filters")}
          </p>
          <p className="mt-1 text-sm text-slate-400">
            {filteredCount} {t("shop.panel.results")}
            {filteredCount !== totalCount ? ` / ${totalCount}` : ""}
          </p>
        </div>
        {hasActiveFilters && (
          <button
            type="button"
            onClick={onClear}
            className="rounded-full border border-slate-700 bg-slate-900/70 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-300 transition hover:border-slate-500"
          >
            {t("shop.panel.clear")}
          </button>
        )}
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto]">
        <input
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder={t("shop.panel.search")}
          className="w-full rounded-2xl border border-slate-800 bg-slate-900/80 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-limiar-500 focus:outline-none"
        />
        <button
          type="button"
          onClick={() => onOwnedOnlyChange(!ownedOnly)}
          className={`rounded-2xl border px-4 py-3 text-xs font-semibold uppercase tracking-[0.18em] transition ${
            ownedOnly
              ? "border-limiar-500/40 bg-limiar-500/15 text-limiar-300"
              : "border-slate-700 bg-slate-900/70 text-slate-400 hover:border-slate-500"
          }`}
        >
          {t("shop.panel.ownedOnly")} ({ownedCount})
        </button>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        <FilterChip
          active={typeFilter === "ALL"}
          count={totalCount}
          label={t("shop.panel.all")}
          onClick={() => onTypeFilterChange("ALL")}
        />
        {SHOP_ITEM_TYPES.map((type) => (
          <FilterChip
            key={type}
            active={typeFilter === type}
            count={typeCounts[type]}
            label={t(getShopItemTypeLabelKey(type))}
            onClick={() => onTypeFilterChange(type)}
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
}: {
  active: boolean;
  count: number;
  label: string;
  onClick: () => void;
}) => (
  <button
    type="button"
    onClick={onClick}
    className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] transition ${
      active
        ? "border-limiar-500/40 bg-limiar-500/15 text-limiar-300"
        : "border-slate-700 bg-slate-900/70 text-slate-400 hover:border-slate-500"
    }`}
  >
    <span>{label}</span>
    <span
      className={`rounded-full px-2 py-0.5 text-[10px] ${
        active ? "bg-limiar-500/15 text-limiar-200" : "bg-slate-800 text-slate-300"
      }`}
    >
      {count}
    </span>
  </button>
);
