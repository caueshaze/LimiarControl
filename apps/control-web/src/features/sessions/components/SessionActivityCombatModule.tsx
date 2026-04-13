import { useMemo, useState } from "react";
import type { ActivityEvent } from "../../../shared/api/sessionsRepo";
import { useLocale } from "../../../shared/hooks/useLocale";
import { CombatLogEntries } from "../../combat-ui/components/CombatLogEntries";
import { useCombatUiState } from "../../combat-ui/useCombatUiState";
import { SessionActivityRow } from "./SessionActivityRow";
import { formatSessionActivityOffset } from "./sessionActivity.utils";

type Props = {
  events: ActivityEvent[];
  isGm?: boolean;
  isLatest: boolean;
  sessionId: string;
};

export const SessionActivityCombatModule = ({
  events,
  isGm = false,
  isLatest,
  sessionId,
}: Props) => {
  const { t } = useLocale();
  const [open, setOpen] = useState(false);
  const combatState = useCombatUiState({
    enabled: open && isLatest,
    historyLimit: 18,
    pollMs: 10_000,
    sessionId,
  });

  const fallbackEvents = useMemo(() => [...events].reverse(), [events]);
  const startOffset = events[0]?.sessionOffsetSeconds ?? null;
  const endOffset = events[events.length - 1]?.sessionOffsetSeconds ?? null;
  const offsetLabel =
    startOffset == null
      ? null
      : endOffset == null || startOffset === endOffset
        ? formatSessionActivityOffset(startOffset)
        : `${formatSessionActivityOffset(startOffset)} - ${formatSessionActivityOffset(endOffset)}`;
  const shouldShowCombatLog = isLatest && combatState.logs.length > 0;

  return (
    <article className="overflow-hidden rounded-3xl border border-amber-500/20 bg-amber-500/8">
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        className="flex w-full items-center justify-between gap-4 px-4 py-4 text-left transition hover:bg-amber-500/6"
        aria-expanded={open}
      >
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-amber-200/80">
            {t("sessionActivity.combatModuleEyebrow")}
          </p>
          <p className="mt-1 text-sm font-semibold text-white">{t("sessionActivity.combatModuleTitle")}</p>
          <p className="mt-1 text-xs text-slate-300">
            {`${events.length} ${t("sessionActivity.combatEventsCount")}`}
            {offsetLabel ? ` · ${offsetLabel}` : ""}
          </p>
        </div>
        <span className={`shrink-0 text-xs text-slate-400 transition-transform ${open ? "rotate-180" : ""}`}>
          ▼
        </span>
      </button>

      {open ? (
        <div className="border-t border-amber-500/15 px-4 py-4">
          {combatState.loading && isLatest ? (
            <p className="text-sm text-slate-400">{t("combatUi.loadingState")}</p>
          ) : shouldShowCombatLog ? (
            <CombatLogEntries compact emptyLabel={t("combatUi.logEmpty")} logs={combatState.logs} />
          ) : fallbackEvents.length > 0 ? (
            <div className="space-y-2">
              {fallbackEvents.map((event, index) => (
                <SessionActivityRow key={`${event.type}-${event.timestamp}-${index}`} event={event} isGm={isGm} />
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-400">{t("combatUi.logEmpty")}</p>
          )}
        </div>
      ) : null}
    </article>
  );
};
