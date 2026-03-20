import { useLocale } from "../../shared/hooks/useLocale";
import type { LocaleKey } from "../../shared/i18n";

const SPELL_LEVELS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9] as const;
const SPELL_SCHOOLS = [
  "abjuration", "conjuration", "divination", "enchantment",
  "evocation", "illusion", "necromancy", "transmutation",
] as const;
const CASTER_CLASSES = [
  "Bard", "Cleric", "Druid", "Paladin",
  "Ranger", "Sorcerer", "Warlock", "Wizard",
] as const;

type Props = {
  search: string;
  levelFilter: number | null;
  schoolFilter: string | null;
  classFilter: string | null;
  totalCount: number;
  filteredCount: number;
  onSearchChange: (value: string) => void;
  onLevelChange: (value: number | null) => void;
  onSchoolChange: (value: string | null) => void;
  onClassChange: (value: string | null) => void;
  onClear: () => void;
};

export const SpellCatalogFilters = ({
  search, levelFilter, schoolFilter, classFilter,
  totalCount, filteredCount,
  onSearchChange, onLevelChange, onSchoolChange, onClassChange, onClear,
}: Props) => {
  const { t } = useLocale();
  const hasActiveFilters = search.trim().length > 0 || levelFilter !== null || schoolFilter !== null || classFilter !== null;

  return (
    <div className="rounded-[30px] border border-white/8 bg-[linear-gradient(180deg,rgba(8,12,28,0.92),rgba(2,6,23,0.95))] p-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.26em] text-slate-500">
            {t("catalog.spells.filtersTitle")}
          </p>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            {filteredCount} {t("catalog.spells.filtersResults")}
            {filteredCount !== totalCount ? ` / ${totalCount}` : ""}
          </p>
        </div>

        {hasActiveFilters && (
          <button
            type="button"
            onClick={onClear}
            className="rounded-full border border-white/10 bg-white/[0.05] px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-200 transition hover:border-white/20 hover:bg-white/[0.09]"
          >
            {t("catalog.clearFilters")}
          </button>
        )}
      </div>

      <div className="mt-4">
        <input
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder={t("catalog.spells.searchPlaceholder")}
          className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-violet-400/60 focus:outline-none"
        />
      </div>

      {/* Level filter */}
      <div className="mt-4">
        <p className="mb-2 text-[9px] font-semibold uppercase tracking-[0.24em] text-slate-600">{t("catalog.spells.levelFilterLabel")}</p>
        <div className="flex flex-wrap gap-1.5">
          <FilterChip
            active={levelFilter === null}
            label={t("shop.panel.all")}
            onClick={() => onLevelChange(null)}
          />
          {SPELL_LEVELS.map((lvl) => (
            <FilterChip
              key={lvl}
              active={levelFilter === lvl}
              label={lvl === 0 ? t("catalog.spells.cantrip") : String(lvl)}
              onClick={() => onLevelChange(lvl)}
              activeClass="border-violet-300/25 bg-violet-400/12 text-violet-100"
            />
          ))}
        </div>
      </div>

      {/* School filter */}
      <div className="mt-3">
        <p className="mb-2 text-[9px] font-semibold uppercase tracking-[0.24em] text-slate-600">{t("catalog.spells.schoolFilterLabel")}</p>
        <div className="flex flex-wrap gap-1.5">
          <FilterChip
            active={schoolFilter === null}
            label={t("shop.panel.all")}
            onClick={() => onSchoolChange(null)}
          />
          {SPELL_SCHOOLS.map((school) => (
            <FilterChip
              key={school}
              active={schoolFilter === school}
              label={t(`catalog.spells.school.${school}` as LocaleKey)}
              onClick={() => onSchoolChange(school)}
              activeClass="border-violet-300/25 bg-violet-400/12 text-violet-100"
            />
          ))}
        </div>
      </div>

      {/* Class filter */}
      <div className="mt-3">
        <p className="mb-2 text-[9px] font-semibold uppercase tracking-[0.24em] text-slate-600">{t("catalog.spells.classFilterLabel")}</p>
        <div className="flex flex-wrap gap-1.5">
          <FilterChip
            active={classFilter === null}
            label={t("shop.panel.all")}
            onClick={() => onClassChange(null)}
          />
          {CASTER_CLASSES.map((cls) => (
            <FilterChip
              key={cls}
              active={classFilter === cls}
              label={cls}
              onClick={() => onClassChange(cls)}
              activeClass="border-violet-300/25 bg-violet-400/12 text-violet-100"
            />
          ))}
        </div>
      </div>
    </div>
  );
};

const FilterChip = ({
  active, label, onClick, activeClass,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
  activeClass?: string;
}) => (
  <button
    type="button"
    onClick={onClick}
    className={`rounded-full border px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] transition ${
      active
        ? activeClass ?? "border-limiar-300/25 bg-limiar-400/12 text-limiar-100"
        : "border-white/8 bg-white/[0.04] text-slate-400 hover:border-white/16 hover:bg-white/[0.08]"
    }`}
  >
    {label}
  </button>
);
