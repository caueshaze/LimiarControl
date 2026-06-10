import { useEffect, useMemo, useState } from "react";
import {
  isSpellCatalogLoaded,
  loadSpellCatalog,
} from "../../entities/dnd-base";
import { useLocale } from "../../shared/hooks/useLocale";
import type { Spell } from "../../features/character-sheet/model/characterSheet.types";
import { getSpellPreparationCopyKeys, type SpellPreparationCopyMode } from "./spellPreparationCopy";
import {
  buildSpellPreparationCatalog,
  resolveSpellPreparationDisplayName,
} from "./spellPreparationDialogModel";

type Props = {
  open: boolean;
  onClose: () => void;
  spells: Spell[];
  preparedLimit: number;
  currentPreparedIds: string[];
  onSubmit: (preparedIds: string[]) => void;
  isSubmitting?: boolean;
  copyMode?: SpellPreparationCopyMode;
  campaignId?: string | null;
  characterClass?: string | null;
};

export const SpellPreparationDialog = ({
  open,
  onClose,
  spells,
  preparedLimit,
  currentPreparedIds,
  onSubmit,
  isSubmitting,
  copyMode = "fallback",
  campaignId = null,
  characterClass = null,
}: Props) => {
  const { t, locale } = useLocale();
  const copyKeys = getSpellPreparationCopyKeys(copyMode);
  const currentPreparedKey = currentPreparedIds.join("|");
  const [catalogReady, setCatalogReady] = useState(() => isSpellCatalogLoaded(campaignId));
  const [selectedIds, setSelectedIds] = useState<Set<string>>(
    () => new Set(currentPreparedIds),
  );

  useEffect(() => {
    if (!open) return;
    setSelectedIds(new Set(currentPreparedIds));
  }, [currentPreparedIds, currentPreparedKey, open]);

  useEffect(() => {
    if (!open) return;
    if (isSpellCatalogLoaded(campaignId)) {
      setCatalogReady(true);
      return;
    }

    let active = true;
    setCatalogReady(false);
    void loadSpellCatalog(campaignId)
      .catch(() => undefined)
      .finally(() => {
        if (active) {
          setCatalogReady(true);
        }
      });

    return () => {
      active = false;
    };
  }, [campaignId, characterClass, open]);

  const grouped = useMemo(() => {
    const byLevel: Record<number, Spell[]> = {};
    for (const spell of spells) {
      const level = spell.level ?? 0;
      if (!byLevel[level]) byLevel[level] = [];
      byLevel[level].push(spell);
    }
    return Object.entries(byLevel)
      .map(([level, list]) => ({
        level: Number(level),
        spells: list.sort((a, b) => a.name.localeCompare(b.name)),
      }))
      .sort((a, b) => a.level - b.level);
  }, [spells]);

  const spellCatalog = useMemo(() => {
    return buildSpellPreparationCatalog(catalogReady, characterClass, campaignId);
  }, [campaignId, catalogReady, characterClass]);

  const getSpellDisplayName = (spell: Spell) => {
    return resolveSpellPreparationDisplayName(spellCatalog, spell, locale);
  };

  const leveledCount = useMemo(() => {
    return spells.filter(
      (s) => (s.level ?? 0) > 0 && selectedIds.has(s.id),
    ).length;
  }, [spells, selectedIds]);

  const overLimit = leveledCount > preparedLimit;

  const toggle = (id: string, level: number) => {
    if (level === 0) return; // cantrips are always prepared
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="max-h-[80vh] w-full max-w-md overflow-y-auto rounded-3xl border border-white/10 bg-[#0f172a] p-6 shadow-2xl">
        <h2 className="text-lg font-bold text-white">
          {t(copyKeys.title)}
        </h2>
        <p className="mt-1 text-sm text-slate-400">
          {t(copyKeys.description)}
        </p>

        <div className="mt-4 flex items-center justify-between">
          <p
            className={`text-sm font-semibold ${
              overLimit ? "text-red-400" : "text-slate-300"
            }`}
          >
            {t("playerBoard.prepareSpellsSelected")
              .replace("{count}", String(leveledCount))
              .replace("{limit}", String(preparedLimit))}
          </p>
          {overLimit ? (
            <span className="text-xs font-bold uppercase tracking-wider text-red-400">
              {t("playerBoard.prepareSpellsOverLimit")}
            </span>
          ) : null}
        </div>

        <div className="mt-4 space-y-4">
          {grouped.map(({ level, spells: levelSpells }) => (
            <div key={level}>
              <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">
                {level === 0
                  ? t("playerBoard.prepareSpellsCantripsAlwaysPrepared")
                  : t("playerBoard.prepareSpellsLevel").replace(
                      "{level}",
                      String(level),
                    )}
              </p>
              <ul className="mt-2 space-y-1.5">
                {levelSpells.map((spell) => {
                  const isCantrip = (spell.level ?? 0) === 0;
                  const isSelected = selectedIds.has(spell.id);
                  return (
                    <li key={spell.id}>
                      <label
                        className={`flex cursor-pointer items-center gap-3 rounded-xl border px-3 py-2 transition ${
                          isCantrip
                            ? "border-white/5 bg-white/3 opacity-60"
                            : isSelected
                              ? "border-violet-500/30 bg-violet-500/10"
                              : "border-white/5 bg-white/3 hover:bg-white/6"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={isSelected}
                          disabled={isCantrip || isSubmitting}
                          onChange={() => toggle(spell.id, spell.level ?? 0)}
                          className="h-4 w-4 accent-violet-500"
                        />
                        <span className="text-sm text-slate-200">
                          {getSpellDisplayName(spell)}
                        </span>
                        {isCantrip ? (
                          <span className="ml-auto text-[10px] uppercase tracking-wider text-slate-500">
                            {t("playerBoard.prepareSpellsPrepared")}
                          </span>
                        ) : null}
                      </label>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-6 flex gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="flex-1 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold text-slate-300 transition hover:bg-white/10 disabled:opacity-50"
          >
            {t("common.cancel")}
          </button>
          <button
            type="button"
            onClick={() => onSubmit(Array.from(selectedIds))}
            disabled={overLimit || isSubmitting}
            className="flex-1 rounded-full bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isSubmitting
              ? t("common.saving")
              : t("playerBoard.prepareSpellsButton")}
          </button>
        </div>
      </div>
    </div>
  );
};
