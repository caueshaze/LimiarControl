import type { BaseSpell } from "../../entities/base-spell";
import { useLocale } from "../../shared/hooks/useLocale";
import { localizeSpellSchool } from "../../shared/i18n/domainLabels";
import {
  type ActiveFilter,
  type LevelFilter,
  LEVEL_OPTIONS,
  SCHOOL_COLORS,
  SCHOOL_OPTIONS,
  type SchoolFilter,
  inputClassName,
  panelClassName,
} from "./systemSpellCatalog.types";

type Props = {
  spells: BaseSpell[];
  loading: boolean;
  search: string;
  setSearch: (value: string) => void;
  levelFilter: LevelFilter;
  setLevelFilter: (value: LevelFilter) => void;
  schoolFilter: SchoolFilter;
  setSchoolFilter: (value: SchoolFilter) => void;
  activeFilter: ActiveFilter;
  setActiveFilter: (value: ActiveFilter) => void;
  selectedSpellId: string | null;
  onSelectSpell: (spell: BaseSpell) => void;
};

export const SystemSpellCatalogSidebar = ({
  spells,
  loading,
  search,
  setSearch,
  levelFilter,
  setLevelFilter,
  schoolFilter,
  setSchoolFilter,
  activeFilter,
  setActiveFilter,
  selectedSpellId,
  onSelectSpell,
}: Props) => {
  const { locale, t } = useLocale();

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
            placeholder={t("catalog.admin.filters.searchSpellsPlaceholder")}
          />
        </label>

        <div className="grid grid-cols-2 gap-3">
          <label className="block">
            <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              {t("catalog.admin.filters.level")}
            </span>
            <select
              value={String(levelFilter)}
              onChange={(event) =>
                setLevelFilter(
                  event.target.value === "ALL" ? "ALL" : Number(event.target.value),
                )
              }
              className={`${inputClassName} mt-2`}
            >
              <option value="ALL">{t("catalog.admin.filters.allLevels")}</option>
              {LEVEL_OPTIONS.map((level) => (
                <option key={level} value={level}>
                  {level === 0
                    ? t("catalog.spells.cantrip")
                    : `${t("catalog.spells.levelLabel")} ${level}`}
                </option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              {t("catalog.spells.schoolFilterLabel")}
            </span>
            <select
              value={schoolFilter}
              onChange={(event) =>
                setSchoolFilter(event.target.value as SchoolFilter)
              }
              className={`${inputClassName} mt-2`}
            >
              <option value="ALL">{t("catalog.admin.filters.allCategories")}</option>
              {SCHOOL_OPTIONS.map((school) => (
                <option key={school} value={school}>
                  {localizeSpellSchool(school, locale)}
                </option>
              ))}
            </select>
          </label>
        </div>

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

      <div className="rounded-3xl border border-white/8 bg-black/20 px-4 py-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
          {t("catalog.filtersTitle")}
        </p>
        <p className="mt-2 text-2xl font-black text-white">{spells.length}</p>
        <p className="text-sm text-slate-400">{t("catalog.spells.filtersResults")}</p>
      </div>

      {loading && (
        <div className="rounded-3xl border border-white/8 bg-black/20 px-4 py-6 text-sm text-slate-400">
          {t("catalog.spells.loading")}
        </div>
      )}

      {!loading && (
        <div className="max-h-[70vh] space-y-3 overflow-y-auto pr-1">
          {spells.map((spell) => (
            <button
              key={spell.id}
              type="button"
              onClick={() => onSelectSpell(spell)}
              className={`w-full rounded-[24px] border px-4 py-4 text-left transition ${
                selectedSpellId === spell.id
                  ? "border-violet-300/40 bg-violet-300/10"
                  : "border-white/8 bg-black/20 hover:border-white/15 hover:bg-white/5"
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-white">
                    {spell.namePt || spell.nameEn}
                  </p>
                  <p className="mt-1 text-[11px] uppercase tracking-[0.22em] text-slate-500">
                    {spell.canonicalKey}
                  </p>
                </div>
                <span
                  className={`rounded-full px-2 py-1 text-[10px] font-bold uppercase tracking-[0.2em] ${
                    spell.isActive
                      ? "bg-emerald-400/12 text-emerald-200"
                      : "bg-rose-400/12 text-rose-200"
                  }`}
                >
                  {spell.isActive
                    ? t("catalog.admin.table.active")
                    : t("catalog.admin.table.inactive")}
                </span>
              </div>
              <div className="mt-3 flex flex-wrap gap-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400">
                <span
                  className={`rounded-full border px-2 py-1 ${
                    SCHOOL_COLORS[spell.school] ?? "border-white/10"
                  }`}
                >
                  {localizeSpellSchool(spell.school, locale)}
                </span>
                <span className="rounded-full border border-white/10 px-2 py-1">
                  {spell.level === 0
                    ? t("catalog.spells.cantrip")
                    : `${t("catalog.spells.levelLabel")} ${spell.level}`}
                </span>
                {spell.concentration && (
                  <span className="rounded-full border border-amber-400/30 bg-amber-400/10 px-2 py-1 text-amber-200">
                    C
                  </span>
                )}
                {spell.ritual && (
                  <span className="rounded-full border border-teal-400/30 bg-teal-400/10 px-2 py-1 text-teal-200">
                    R
                  </span>
                )}
              </div>
            </button>
          ))}
          {spells.length === 0 && (
            <div className="rounded-[24px] border border-dashed border-white/10 px-4 py-8 text-sm text-slate-400">
              {t("catalog.spells.empty")}
            </div>
          )}
        </div>
      )}
    </aside>
  );
};
