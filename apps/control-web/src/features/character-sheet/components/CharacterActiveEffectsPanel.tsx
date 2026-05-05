import type { ActiveEffect } from "../../../shared/api/combatRepo";
import { useLocale } from "../../../shared/hooks/useLocale";
import {
  formatActiveEffectLabel,
  getActiveEffectLifecycleBadges,
} from "../../../features/active-effects";

type Props = {
  activeEffects: ActiveEffect[];
  removingEffectId?: string | null;
  onRemoveEffect?: (effectId: string) => void;
};

export const CharacterActiveEffectsPanel = ({
  activeEffects,
  removingEffectId,
  onRemoveEffect,
}: Props) => {
  const { t } = useLocale();

  if (activeEffects.length === 0) {
    return null;
  }

  return (
    <section className="rounded-3xl border border-white/8 bg-white/4 px-4 py-4">
      <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-400">
        {t("playerBoard.activeEffectsLabel")}
      </p>
      <ul className="mt-3 space-y-2">
        {activeEffects.map((effect) => {
          const label =
            formatActiveEffectLabel(effect) ??
            t("playerBoard.activeEffectFallback");
          const badges = getActiveEffectLifecycleBadges(effect);
          const isRemoving = removingEffectId === effect.id;
          return (
            <li
              key={effect.id}
              className="flex items-center justify-between gap-3"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-white">
                  {label}
                </p>
                {badges.length > 0 ? (
                  <p className="mt-0.5 flex flex-wrap gap-x-1.5 gap-y-0.5">
                    {badges.map((badge, index) => (
                      <span
                        key={badge.key}
                        className="inline-flex items-center gap-x-1.5"
                      >
                        {index > 0 ? (
                          <span className="text-[10px] text-slate-600">
                            {"\u00B7"}
                          </span>
                        ) : null}
                        <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-violet-400">
                          {badge.params
                            ? t(badge.i18nKey).replace(
                                "{count}",
                                String(badge.params.count),
                              )
                            : t(badge.i18nKey)}
                        </span>
                      </span>
                    ))}
                  </p>
                ) : null}
              </div>
              {onRemoveEffect ? (
                <button
                  type="button"
                  onClick={() => onRemoveEffect(effect.id)}
                  disabled={isRemoving}
                  className="shrink-0 rounded-full bg-white/8 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.22em] text-slate-300 transition hover:bg-red-500/20 hover:text-red-300 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isRemoving
                    ? t("playerBoard.removingEffect")
                    : t("playerBoard.removeEffect")}
                </button>
              ) : null}
            </li>
          );
        })}
      </ul>
    </section>
  );
};
