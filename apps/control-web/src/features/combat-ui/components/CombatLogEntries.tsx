import { useLocale } from "../../../shared/hooks/useLocale";
import { localizeCombatLogMessage } from "../combatLogLocalization";
import type { CombatLogEntry } from "../types";

type Props = {
  compact?: boolean;
  emptyLabel: string;
  logs: CombatLogEntry[];
};

export const CombatLogEntries = ({
  compact = false,
  emptyLabel,
  logs,
}: Props) => {
  if (logs.length === 0) {
    return (
      <div
        className={
          compact
            ? "rounded-3xl border border-dashed border-white/10 bg-white/3 px-4 py-4 text-sm text-slate-400"
            : "rounded-3xl border border-dashed border-white/10 bg-white/3 px-4 py-5 text-sm text-slate-400"
        }
      >
        {emptyLabel}
      </div>
    );
  }

  return (
    <div className={compact ? "space-y-2" : "space-y-2"}>
      {logs.map((entry) => (
        <CombatLogEntryRow compact={compact} entry={entry} key={entry.id} />
      ))}
    </div>
  );
};

const CombatLogEntryRow = ({
  compact,
  entry,
}: {
  compact: boolean;
  entry: CombatLogEntry;
}) => {
  const { locale } = useLocale();

  return (
    <article
      className={
        compact
          ? "rounded-3xl border border-white/6 bg-white/4 px-4 py-3 text-sm leading-6 text-slate-200"
          : "rounded-3xl border border-white/6 bg-white/4 px-4 py-3 text-sm leading-6 text-slate-200"
      }
    >
      {localizeCombatLogMessage(entry.message, locale)}
    </article>
  );
};
