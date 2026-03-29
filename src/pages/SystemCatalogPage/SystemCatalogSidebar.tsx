import type { BaseItem } from "../../entities/base-item";
import { useLocale } from "../../shared/hooks/useLocale";
import {
  localizeBaseItemAdminValue,
  localizeBaseItemCostUnit,
} from "../../shared/i18n/domainLabels";
import { currencyLabel } from "./systemCatalog.helpers";
import {
  type ActiveFilter,
  type EquipmentCategoryFilter,
  EQUIPMENT_CATEGORY_OPTIONS,
  ITEM_KIND_OPTIONS,
  type ItemKindFilter,
  inputClassName,
  panelClassName,
} from "./systemCatalog.types";

type Props = {
  items: BaseItem[];
  loading: boolean;
  search: string;
  setSearch: (value: string) => void;
  itemKindFilter: ItemKindFilter;
  setItemKindFilter: (value: ItemKindFilter) => void;
  equipmentCategoryFilter: EquipmentCategoryFilter;
  setEquipmentCategoryFilter: (value: EquipmentCategoryFilter) => void;
  activeFilter: ActiveFilter;
  setActiveFilter: (value: ActiveFilter) => void;
  selectedItemId: string | null;
  onSelectItem: (item: BaseItem) => void;
};

export const SystemCatalogSidebar = ({
  items,
  loading,
  search,
  setSearch,
  itemKindFilter,
  setItemKindFilter,
  equipmentCategoryFilter,
  setEquipmentCategoryFilter,
  activeFilter,
  setActiveFilter,
  selectedItemId,
  onSelectItem,
}: Props) => {
  const { locale, t } = useLocale();

  const formatItemChoiceLabel = (value: string) =>
    value === "DND5E" ? "D&D 5e" : localizeBaseItemAdminValue(value, locale);

  return (
    <aside className={`${panelClassName} space-y-5`}>
      <div className="grid gap-3">
        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            {t("catalog.admin.filters.search")}
          </span>
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className={`${inputClassName} mt-2`}
            placeholder={t("catalog.admin.filters.searchItemsPlaceholder")}
          />
        </label>

        <div className="grid gap-3">
          <label className="block">
            <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              {t("catalog.admin.filters.kind")}
            </span>
            <select
              value={itemKindFilter}
              onChange={(event) =>
                setItemKindFilter(event.target.value as ItemKindFilter)
              }
              className={`${inputClassName} mt-2`}
            >
              <option value="ALL">{t("catalog.admin.filters.allKinds")}</option>
              {ITEM_KIND_OPTIONS.map((itemKind) => (
                <option key={itemKind} value={itemKind}>
                  {formatItemChoiceLabel(itemKind)}
                </option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              {t("catalog.admin.filters.category")}
            </span>
            <select
              value={equipmentCategoryFilter}
              onChange={(event) =>
                setEquipmentCategoryFilter(
                  event.target.value as EquipmentCategoryFilter,
                )
              }
              className={`${inputClassName} mt-2`}
            >
              <option value="ALL">{t("catalog.admin.filters.allCategories")}</option>
              {EQUIPMENT_CATEGORY_OPTIONS.map((category) => (
                <option key={category} value={category}>
                  {formatItemChoiceLabel(category)}
                </option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              {t("catalog.admin.filters.status")}
            </span>
            <select
              value={activeFilter}
              onChange={(event) =>
                setActiveFilter(event.target.value as ActiveFilter)
              }
              className={`${inputClassName} mt-2`}
            >
              <option value="all">{t("catalog.admin.filters.allStatuses")}</option>
              <option value="active">{t("catalog.admin.table.active")}</option>
              <option value="inactive">{t("catalog.admin.table.inactive")}</option>
            </select>
          </label>
        </div>
      </div>

      <div className="rounded-3xl border border-white/8 bg-black/20 px-4 py-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
          {t("catalog.filtersTitle")}
        </p>
        <p className="mt-2 text-2xl font-black text-white">{items.length}</p>
        <p className="text-sm text-slate-400">{t("catalog.filtersResults")}</p>
      </div>

      {loading && (
        <div className="rounded-3xl border border-white/8 bg-black/20 px-4 py-6 text-sm text-slate-400">
          {t("catalog.loading")}
        </div>
      )}

      {!loading && (
        <div className="max-h-[70vh] space-y-3 overflow-y-auto pr-1">
          {items.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onSelectItem(item)}
              className={`w-full rounded-[24px] border px-4 py-4 text-left transition ${
                selectedItemId === item.id
                  ? "border-amber-300/40 bg-amber-300/10"
                  : "border-white/8 bg-black/20 hover:border-white/15 hover:bg-white/5"
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-white">
                    {item.namePt || item.nameEn}
                  </p>
                  <p className="mt-1 text-[11px] uppercase tracking-[0.22em] text-slate-500">
                    {item.canonicalKey}
                  </p>
                </div>
                <span
                  className={`rounded-full px-2 py-1 text-[10px] font-bold uppercase tracking-[0.2em] ${
                    item.isActive
                      ? "bg-emerald-400/12 text-emerald-200"
                      : "bg-rose-400/12 text-rose-200"
                  }`}
                >
                  {item.isActive
                    ? t("catalog.admin.table.active")
                    : t("catalog.admin.table.inactive")}
                </span>
              </div>
              <div className="mt-3 flex flex-wrap gap-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400">
                <span className="rounded-full border border-white/10 px-2 py-1">
                  {formatItemChoiceLabel(item.itemKind)}
                </span>
                <span className="rounded-full border border-white/10 px-2 py-1">
                  {item.costUnit
                    ? localizeBaseItemCostUnit(item.costUnit, locale)
                    : currencyLabel(item.costUnit)}
                </span>
                {item.equipmentCategory && (
                  <span className="rounded-full border border-white/10 px-2 py-1">
                    {formatItemChoiceLabel(item.equipmentCategory)}
                  </span>
                )}
              </div>
            </button>
          ))}
          {items.length === 0 && (
            <div className="rounded-[24px] border border-dashed border-white/10 px-4 py-8 text-sm text-slate-400">
              {t("catalog.emptyFilteredTitle")}
            </div>
          )}
        </div>
      )}
    </aside>
  );
};
