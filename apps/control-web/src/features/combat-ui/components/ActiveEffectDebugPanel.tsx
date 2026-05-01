import { formatEffectContextDebug } from "../spellVariantUi";
import { getCombatEffectLabel } from "../combatUi.helpers";
import type { ActiveEffect } from "../../../shared/api/combatRepo";
import { useLocale } from "../../../shared/hooks/useLocale";

type Props = {
  effects: ActiveEffect[];
  targetDisplayName?: string | null;
};

export const ActiveEffectDebugPanel = ({
  effects,
  targetDisplayName = null,
}: Props) => {
  const { t } = useLocale();
  const debugEntries = effects
    .map((effect) => ({
      effect,
      lines: formatEffectContextDebug(effect, { targetDisplayName }),
    }))
    .filter((entry) => entry.lines.length > 0);

  if (!debugEntries.length) {
    return null;
  }

  return (
    <div className="mt-3 space-y-2">
      {debugEntries.map(({ effect, lines }) => (
        <details
          key={effect.id}
          className="rounded-2xl border border-sky-500/20 bg-sky-500/8 px-3 py-2"
        >
          <summary className="cursor-pointer text-xs font-semibold uppercase tracking-[0.16em] text-sky-100">
            {getCombatEffectLabel(t, effect)}
          </summary>
          <div className="mt-2 space-y-1 text-xs text-slate-200">
            {lines.map((line, index) => (
              <p key={`${effect.id}:${index}`}>{line}</p>
            ))}
          </div>
        </details>
      ))}
    </div>
  );
};
