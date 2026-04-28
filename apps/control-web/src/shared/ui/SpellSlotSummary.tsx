import type { SpellSlots } from "../../features/character-sheet/model/characterSheet.types";

export type SpellSlotSummaryEntry = {
  level: number;
  max: number;
  used: number;
  remaining: number;
};

type Props = {
  slots?: Record<number, SpellSlots> | null;
  entries?: SpellSlotSummaryEntry[] | null;
  compact?: boolean;
  emptyLabel?: string;
  highlightLevel?: number | null;
  title?: string | null;
};

export const buildSpellSlotSummaryEntries = (
  slots?: Record<number, SpellSlots> | null,
): SpellSlotSummaryEntry[] =>
  Object.entries(slots ?? {})
    .map(([level, slot]) => ({
      level: Number(level),
      max: Math.max(0, Number(slot?.max ?? 0)),
      used: Math.max(0, Number(slot?.used ?? 0)),
    }))
    .filter(({ level, max }) => Number.isInteger(level) && level > 0 && max > 0)
    .sort((left, right) => left.level - right.level)
    .map(({ level, max, used }) => ({
      level,
      max,
      used,
      remaining: Math.max(0, max - used),
    }));

const formatSlotLabel = (entry: SpellSlotSummaryEntry) =>
  `${entry.level}º: ${entry.remaining}/${entry.max}`;

export const SpellSlotSummary = ({
  slots,
  entries,
  compact = false,
  emptyLabel = "Sem slots de magia",
  highlightLevel = null,
  title = null,
}: Props) => {
  const resolvedEntries = entries?.length ? entries : buildSpellSlotSummaryEntries(slots);

  if (resolvedEntries.length === 0) {
    return <p className="text-sm text-slate-400">{emptyLabel}</p>;
  }

  return (
    <div className="space-y-2" data-testid="spell-slot-summary">
      {title ? (
        <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
          {title}
        </p>
      ) : null}
      <div className={compact ? "flex flex-wrap gap-2" : "space-y-2"}>
        {resolvedEntries.map((entry) => {
          const isHighlighted = highlightLevel === entry.level;
          const isExhausted = entry.remaining <= 0;
          return (
            <div
              key={entry.level}
              className={
                compact
                  ? `rounded-full border px-3 py-1 text-xs font-semibold ${
                      isHighlighted
                        ? "border-fuchsia-400/40 bg-fuchsia-500/15 text-fuchsia-100"
                        : isExhausted
                          ? "border-rose-500/30 bg-rose-500/10 text-rose-100"
                          : "border-emerald-500/25 bg-emerald-500/10 text-emerald-100"
                    }`
                  : "rounded-2xl border border-white/8 bg-white/4 px-3 py-3"
              }
            >
              {compact ? (
                <span>{formatSlotLabel(entry)}</span>
              ) : (
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-white">{entry.level}º círculo</p>
                    <p className="mt-1 text-xs text-slate-400">
                      {entry.remaining}/{entry.max} restantes
                    </p>
                  </div>
                  <div className="flex items-center gap-1.5" aria-label={`${entry.level}º círculo: ${entry.remaining}/${entry.max}`}>
                    {Array.from({ length: entry.max }, (_, index) => (
                      <span
                        key={`${entry.level}-${index}`}
                        className={`h-2.5 w-2.5 rounded-full ${
                          index < entry.remaining ? "bg-emerald-300" : "bg-slate-700"
                        }`}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
