import type { CommandFeedback } from "./gmDashboard.types";
import { useLocale } from "../../shared/hooks/useLocale";

type Props = {
  combatUiActive: boolean;
  commandFeedback: CommandFeedback | null;
  commandSending: boolean;
  restState: "exploration" | "short_rest" | "long_rest";
  onCommand: (
    type: "start_short_rest" | "start_long_rest" | "end_rest",
    payload?: Record<string, unknown>,
  ) => void;
};

const getRestBadgeClasses = (restState: Props["restState"]) => {
  if (restState === "short_rest") {
    return "border-amber-500/40 text-amber-300";
  }
  if (restState === "long_rest") {
    return "border-sky-500/40 text-sky-300";
  }
  return "border-slate-700 text-slate-400";
};

const getRestLabel = (restState: Props["restState"]) => {
  if (restState === "short_rest") return "gm.dashboard.rest.short";
  if (restState === "long_rest") return "gm.dashboard.rest.long";
  return "gm.dashboard.rest.exploration";
};

export const GmDashboardRestControlCard = ({
  combatUiActive,
  commandFeedback,
  commandSending,
  restState,
  onCommand,
}: Props) => {
  const { t } = useLocale();
  const restActive = restState !== "exploration";
  const isRestFeedback =
    commandFeedback?.type === "start_short_rest" ||
    commandFeedback?.type === "start_long_rest" ||
    commandFeedback?.type === "end_rest";

  return (
    <div className="rounded-2xl border border-slate-800 bg-linear-to-br from-slate-950/60 to-slate-900/40 p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <label className="text-[10px] font-semibold uppercase tracking-[0.35em] text-slate-500">
            {t("gm.dashboard.restControl")}
          </label>
          <p className="mt-1 text-xs text-slate-400">
            {t("gm.dashboard.restControlDescription")}
          </p>
        </div>
        <span
          className={`rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] ${getRestBadgeClasses(restState)}`}
        >
          {t(getRestLabel(restState))}
        </span>
      </div>

      {!restActive ? (
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <button
            type="button"
            onClick={() => onCommand("start_short_rest")}
            disabled={commandSending || combatUiActive}
            className="rounded-2xl bg-amber-900/50 px-4 py-3 text-xs font-semibold uppercase tracking-[0.25em] text-amber-100 transition-colors hover:bg-amber-900/70 disabled:opacity-50"
          >
            {t("gm.dashboard.startShortRest")}
          </button>
          <button
            type="button"
            onClick={() => onCommand("start_long_rest")}
            disabled={commandSending || combatUiActive}
            className="rounded-2xl bg-sky-900/50 px-4 py-3 text-xs font-semibold uppercase tracking-[0.25em] text-sky-100 transition-colors hover:bg-sky-900/70 disabled:opacity-50"
          >
            {t("gm.dashboard.startLongRest")}
          </button>
        </div>
      ) : (
        <div className="mt-4 space-y-3">
          <p className="text-xs text-slate-400">
            {restState === "short_rest"
              ? t("gm.dashboard.shortRestDescription")
              : t("gm.dashboard.longRestDescription")}
          </p>
          <button
            type="button"
            onClick={() => onCommand("end_rest")}
            disabled={commandSending}
            className="w-full rounded-2xl bg-slate-800 px-4 py-3 text-xs font-semibold uppercase tracking-[0.25em] text-slate-200 transition-colors hover:bg-slate-700 disabled:opacity-50"
          >
            {t("gm.dashboard.endRest")}
          </button>
        </div>
      )}

      {combatUiActive && !restActive ? (
        <p className="mt-3 text-[11px] text-rose-300">{t("gm.dashboard.endCombatBeforeRest")}</p>
      ) : null}

      {isRestFeedback && commandFeedback ? (
        <div
          className={`mt-3 rounded-2xl border px-3 py-2 text-[11px] ${
            commandFeedback.tone === "success"
              ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-300"
              : "border-rose-500/20 bg-rose-500/10 text-rose-200"
          }`}
        >
          {commandFeedback.message}
        </div>
      ) : null}
    </div>
  );
};
