import { useState } from "react";
import type { OutOfCombatCastableSpell, SpellHealingPreview } from "../../entities/character";
import { useLocale } from "../../shared/hooks/useLocale";

function buildHealFormula(preview: SpellHealingPreview, spellLevel: number, slotLevel: number): string {
  const extra = (slotLevel - spellLevel) * preview.upcastPerLevel;
  const count = preview.baseCount + extra;
  const diceStr = `${count}d${preview.dieSides}`;
  if (preview.modifier > 0) return `${diceStr} + ${preview.modifier}`;
  if (preview.modifier < 0) return `${diceStr} - ${Math.abs(preview.modifier)}`;
  return diceStr;
}

type TargetOption = { playerUserId: string; label: string };

type Props = {
  spells: OutOfCombatCastableSpell[];
  casting: boolean;
  onCast: (spellId: string, slotLevel: number | null, variantKey: string | null, targetPlayerUserId: string | null) => void;
  targetOptions?: TargetOption[];
};

export const OutOfCombatSpellCastCard = ({ spells, casting, onCast, targetOptions }: Props) => {
  const { t } = useLocale();
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [selectedVariants, setSelectedVariants] = useState<Record<string, string>>({});
  const [selectedLevels, setSelectedLevels] = useState<Record<string, number>>({});
  const [selectedTargets, setSelectedTargets] = useState<Record<string, string>>({});

  if (spells.length === 0) return null;

  const handleToggle = (spellId: string | null) => {
    if (!spellId) return;
    setExpandedId((cur) => (cur === spellId ? null : spellId));
  };

  const handleCast = (spell: OutOfCombatCastableSpell) => {
    if (!spell.id || casting) return;
    const variantKey =
      spell.variants.length > 0 ? (selectedVariants[spell.id] ?? null) : null;
    const slotLevel =
      spell.level > 0 ? (selectedLevels[spell.id] ?? spell.level) : null;
    const targetPlayerUserId = targetOptions?.length
      ? (selectedTargets[spell.id] ?? null)
      : null;
    onCast(spell.id, slotLevel, variantKey, targetPlayerUserId);
  };

  const isCastable = (spell: OutOfCombatCastableSpell) => {
    if (!spell.prepared) return false;
    if (spell.variants.length > 0 && !selectedVariants[spell.id ?? ""]) return false;
    return true;
  };

  return (
    <div className="rounded-xl border border-violet-700/40 bg-slate-900/70 p-4">
      <h3 className="mb-3 text-xs font-bold uppercase tracking-[0.15em] text-violet-300">
        {t("playerBoard.castSpells")}
      </h3>
      <ul className="space-y-2">
        {spells.map((spell) => {
          const id = spell.id ?? spell.canonicalKey;
          const isExpanded = expandedId === id;
          const name = spell.namePt ?? spell.nameEn;
          const canCast = isCastable(spell);

          return (
            <li key={id} className="rounded-lg border border-slate-700/50 bg-slate-800/60">
              <button
                type="button"
                disabled={!spell.prepared}
                onClick={() => handleToggle(id)}
                className="flex w-full items-center justify-between px-3 py-2 text-left disabled:opacity-40"
              >
                <span className="flex items-center gap-2">
                  <span className="text-sm font-medium text-slate-100">{name}</span>
                  {spell.level > 0 && (
                    <span className="rounded-full bg-slate-700 px-1.5 py-0.5 text-[10px] text-slate-400">
                      {`Nv ${spell.level}`}
                    </span>
                  )}
                  {spell.concentration && (
                    <span className="rounded-full bg-violet-900/60 px-1.5 py-0.5 text-[10px] text-violet-300">
                      {t("playerBoard.concentration")}
                    </span>
                  )}
                </span>
                {!spell.prepared && (
                  <span className="text-[10px] text-slate-500">{t("playerBoard.notPrepared")}</span>
                )}
                {spell.prepared && (
                  <span className="text-[10px] text-slate-400">{isExpanded ? "▲" : "▼"}</span>
                )}
              </button>

              {isExpanded && (
                <div className="border-t border-slate-700/50 px-3 pb-3 pt-2 space-y-3">
                  {spell.variants.length > 0 && (
                    <div>
                      <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                        {t("playerBoard.selectVariant")}
                      </label>
                      <select
                        value={selectedVariants[id] ?? ""}
                        onChange={(e) =>
                          setSelectedVariants((cur) => ({ ...cur, [id]: e.target.value }))
                        }
                        className="w-full rounded bg-slate-700 px-2 py-1.5 text-sm text-slate-100"
                      >
                        <option value="">—</option>
                        {spell.variants.map((v) => (
                          <option key={v.key} value={v.key}>
                            {v.labelPt ?? v.labelEn ?? v.key}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  {spell.level > 0 && (
                    <div>
                      <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                        {t("playerBoard.selectSlotLevel")}
                      </label>
                      <select
                        value={selectedLevels[id] ?? spell.level}
                        onChange={(e) =>
                          setSelectedLevels((cur) => ({ ...cur, [id]: Number(e.target.value) }))
                        }
                        className="w-full rounded bg-slate-700 px-2 py-1.5 text-sm text-slate-100"
                      >
                        {Array.from({ length: 9 - spell.level + 1 }, (_, i) => spell.level + i).map(
                          (lvl) => (
                            <option key={lvl} value={lvl}>
                              {lvl}
                            </option>
                          ),
                        )}
                      </select>
                    </div>
                  )}

                  {targetOptions && targetOptions.length > 0 && spell.outOfCombatTarget !== "self" && (
                    <div>
                      <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                        {t("playerBoard.selectTarget")}
                      </label>
                      <select
                        value={selectedTargets[id] ?? ""}
                        onChange={(e) =>
                          setSelectedTargets((cur) => ({ ...cur, [id]: e.target.value }))
                        }
                        className="w-full rounded bg-slate-700 px-2 py-1.5 text-sm text-slate-100"
                      >
                        <option value="">{t("playerBoard.targetSelf")}</option>
                        {targetOptions.map((opt) => (
                          <option key={opt.playerUserId} value={opt.playerUserId}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  {spell.healingPreview && (
                    <div className="rounded-lg bg-slate-700/50 px-3 py-2">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                        {t("playerBoard.healingPreview")}
                      </p>
                      <p className="mt-0.5 text-sm font-medium text-emerald-300">
                        {buildHealFormula(
                          spell.healingPreview,
                          spell.level,
                          selectedLevels[id] ?? spell.level,
                        )}
                      </p>
                    </div>
                  )}

                  <button
                    type="button"
                    disabled={!canCast || casting}
                    onClick={() => handleCast(spell)}
                    className="w-full rounded-lg bg-violet-700 px-4 py-2 text-sm font-bold text-white transition hover:bg-violet-600 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {casting ? t("playerBoard.castSpellLoading") : t("playerBoard.castSpellConfirm")}
                  </button>
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
};
