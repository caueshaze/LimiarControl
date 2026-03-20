import type { BaseSpell } from "../../entities/base-spell";
import type { BaseSpellUpdatePayload } from "../../shared/api/baseSpellsRepo";
import { useLocale } from "../../shared/hooks/useLocale";
import { SpellCatalogList } from "../../features/shop/components/SpellCatalogList";
import { SpellCatalogFilters } from "./SpellCatalogFilters";

type Props = {
  allSpellsCount: number;
  classFilter: string | null;
  filteredSpells: BaseSpell[];
  levelFilter: number | null;
  schoolFilter: string | null;
  search: string;
  spellsLoading: boolean;
  onClassChange: (value: string | null) => void;
  onClear: () => void;
  onLevelChange: (value: number | null) => void;
  onSchoolChange: (value: string | null) => void;
  onSearchChange: (value: string) => void;
  onUpdate: (
    spellId: string,
    payload: BaseSpellUpdatePayload,
  ) => boolean | Promise<boolean>;
};

export const CatalogSpellsSection = ({
  allSpellsCount,
  classFilter,
  filteredSpells,
  levelFilter,
  schoolFilter,
  search,
  spellsLoading,
  onClassChange,
  onClear,
  onLevelChange,
  onSchoolChange,
  onSearchChange,
  onUpdate,
}: Props) => {
  const { t } = useLocale();

  return (
    <div className="space-y-5">
      <SpellCatalogFilters
        search={search}
        levelFilter={levelFilter}
        schoolFilter={schoolFilter}
        classFilter={classFilter}
        totalCount={allSpellsCount}
        filteredCount={filteredSpells.length}
        onSearchChange={onSearchChange}
        onLevelChange={onLevelChange}
        onSchoolChange={onSchoolChange}
        onClassChange={onClassChange}
        onClear={onClear}
      />

      {spellsLoading ? (
        <div className="rounded-[28px] border border-white/8 bg-[linear-gradient(180deg,rgba(8,12,28,0.92),rgba(2,6,23,0.95))] p-5 text-sm text-slate-300">
          {t("catalog.spells.loading")}
        </div>
      ) : (
        <SpellCatalogList spells={filteredSpells} onUpdate={onUpdate} />
      )}
    </div>
  );
};
