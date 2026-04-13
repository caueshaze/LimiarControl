import { useLocale } from "../../../shared/hooks/useLocale";
import type { CombatPhase, TurnResources } from "../../../shared/api/combatRepo";
import { getTurnResourceLabel } from "../combatUi.helpers";

type Props = {
  currentParticipantName?: string | null;
  expanded: boolean;
  isMyTurn?: boolean;
  onToggleExpanded: () => void;
  phase?: CombatPhase | null;
  round?: number | null;
  turnResources?: TurnResources | null;
};

export const CombatModeBar = ({
  currentParticipantName,
  expanded,
  isMyTurn = false,
  onToggleExpanded,
  phase = null,
  round = null,
  turnResources = null,
}: Props) => {
  const { t } = useLocale();

  return (
    <section className="sticky top-20 z-20 rounded-4xl border border-rose-500/20 bg-[linear-gradient(135deg,rgba(69,10,10,0.92),rgba(15,23,42,0.96))] p-4 shadow-[0_24px_80px_rgba(2,6,23,0.35)] backdrop-blur">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full border border-rose-400/30 bg-rose-500/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.28em] text-rose-200">
              {t("combatUi.mode")}
            </span>
            {isMyTurn ? (
              <span className="rounded-full border border-emerald-400/30 bg-emerald-500/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.24em] text-emerald-200">
                {t("combatUi.yourTurn")}
              </span>
            ) : null}
          </div>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-slate-200">
            <span>
              {t("combatUi.round")}:{" "}
              <strong className="text-white">{round ?? "-"}</strong>
            </span>
            <span>
              {t("combatUi.phase")}:{" "}
              <strong className="text-white">{phase ?? "-"}</strong>
            </span>
            <span>
              {t("combatUi.activeTurn")}:{" "}
              <strong className="text-white">{currentParticipantName ?? "-"}</strong>
            </span>
          </div>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          {turnResources ? (
            <div className="flex flex-wrap items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-200">
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">
                {getTurnResourceLabel(t, "action", turnResources.action_used)}
              </span>
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">
                {getTurnResourceLabel(t, "bonus", turnResources.bonus_action_used)}
              </span>
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">
                {getTurnResourceLabel(t, "reaction", turnResources.reaction_used)}
              </span>
            </div>
          ) : null}
          <button
            type="button"
            onClick={onToggleExpanded}
            className="rounded-full border border-white/15 bg-white/6 px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-white transition-colors hover:bg-white/10"
          >
            {expanded ? t("combatUi.returnToFocus") : t("combatUi.fullBoard")}
          </button>
        </div>
      </div>
    </section>
  );
};
