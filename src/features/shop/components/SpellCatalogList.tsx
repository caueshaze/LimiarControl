import type { BaseSpell } from "../../../entities/base-spell";
import type { BaseSpellUpdatePayload } from "../../../shared/api/baseSpellsRepo";
import { useLocale } from "../../../shared/hooks/useLocale";
import { SpellCatalogCard } from "./SpellCatalogCard";

type Props = {
  spells: BaseSpell[];
  onUpdate?: (
    spellId: string,
    payload: BaseSpellUpdatePayload,
  ) => boolean | Promise<boolean>;
};

export const SpellCatalogList = ({ spells, onUpdate }: Props) => {
  const { t } = useLocale();

  if (spells.length === 0) {
    return (
      <div className="rounded-[28px] border border-white/8 bg-[linear-gradient(180deg,rgba(8,12,28,0.92),rgba(2,6,23,0.95))] p-6 text-center">
        <p className="text-sm text-slate-500">{t("catalog.spells.empty")}</p>
      </div>
    );
  }

  return (
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {spells.map((spell) => (
        <SpellCatalogCard key={spell.id} spell={spell} onUpdate={onUpdate} />
      ))}
    </div>
  );
};
