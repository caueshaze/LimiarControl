import { useLocale } from "../../../shared/hooks/useLocale";
import type { CombatMapPreviewToken, CombatMovementPreviewResponse } from "../../../shared/api/combatRepo";
import {
  canConfirmMovementPreview,
  getMovementPreviewReasonLabel,
  pathCostUnitsToMeters,
} from "./useMovementPreview";

type Props = {
  active: boolean;
  actorLabel: string | null;
  actorToken: CombatMapPreviewToken | null;
  preview: CombatMovementPreviewResponse | null;
  loading: boolean;
  error: string | null;
  confirming?: boolean;
  onToggle: () => void;
  onCancel: () => void;
  onConfirm: () => void;
};

function formatMeters(value: number | null | undefined): string {
  if (value == null) return "-";
  return `${Number.isInteger(value) ? value : value.toFixed(1)} m`;
}

export const MovementPreviewPanel = ({
  active,
  actorLabel,
  actorToken,
  preview,
  loading,
  error,
  confirming = false,
  onToggle,
  onCancel,
  onConfirm,
}: Props) => {
  const { t } = useLocale();
  const currentBudgetMeters = pathCostUnitsToMeters(actorToken?.movement_budget ?? 0);
  const speedMeters = ((actorToken?.movement_speed_cells ?? 0) * 1.5);
  const costMeters = preview ? pathCostUnitsToMeters(preview.path_cost_units) : null;
  const remainingMeters = preview ? pathCostUnitsToMeters(preview.remaining_budget) : currentBudgetMeters;
  const invalidReason = !preview?.is_valid ? getMovementPreviewReasonLabel(preview?.reason) : null;

  return (
    <section className="rounded-4xl border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.85),rgba(2,6,23,0.94))] p-5 shadow-[0_18px_60px_rgba(2,6,23,0.2)]">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-slate-400">
            {t("combatUi.movementEyebrow")}
          </p>
          <h3 className="mt-2 text-lg font-semibold text-white">{t("combatUi.movementTitle")}</h3>
        </div>
        <button
          type="button"
          onClick={onToggle}
          className={`rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] transition-colors ${
            active
              ? "border border-emerald-400/30 bg-emerald-500/15 text-emerald-100 hover:bg-emerald-500/25"
              : "border border-white/12 bg-white/6 text-white hover:bg-white/10"
          }`}
        >
          {active ? t("combatUi.movementModeActive") : t("combatUi.movementMode")}
        </button>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <div className="rounded-3xl border border-white/8 bg-white/4 px-4 py-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
            {t("combatUi.activeTurn")}
          </p>
          <p className="mt-2 text-sm text-white">{actorLabel ?? "-"}</p>
          <p className="mt-2 text-xs text-slate-400">
            {actorToken?.position ? `(${actorToken.position.x}, ${actorToken.position.y})` : "-"}
          </p>
        </div>
        <div className="rounded-3xl border border-white/8 bg-white/4 px-4 py-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
            {t("combatUi.movementBudget")}
          </p>
          <p className="mt-2 text-sm text-white">
            {formatMeters(currentBudgetMeters)} / {formatMeters(speedMeters)}
          </p>
        </div>
        <div className="rounded-3xl border border-white/8 bg-white/4 px-4 py-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
            {t("combatUi.movementPreview")}
          </p>
          <p className="mt-2 text-sm text-white">
            {preview ? `${formatMeters(costMeters)} -> ${formatMeters(remainingMeters)}` : t("combatUi.movementAwaitingDestination")}
          </p>
        </div>
      </div>

      {active ? (
        <div className="mt-4 space-y-3">
          <p className="text-sm leading-7 text-slate-300">{t("combatUi.mapHintMove")}</p>

          {loading ? (
            <div className="rounded-3xl border border-sky-400/25 bg-sky-500/10 px-4 py-3 text-sm text-sky-100">
              {t("combatUi.movementChecking")}
            </div>
          ) : null}

          {error ? (
            <div className="rounded-3xl border border-rose-500/25 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
              {error}
            </div>
          ) : null}

          {invalidReason && !error ? (
            <div className="rounded-3xl border border-amber-400/25 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
              {invalidReason}
            </div>
          ) : null}

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              disabled={!canConfirmMovementPreview(preview, loading) || confirming}
              onClick={onConfirm}
              className="rounded-3xl bg-emerald-500 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-slate-950 transition-colors hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {t("combatUi.confirmMovement")}
            </button>
            <button
              type="button"
              onClick={onCancel}
              className="rounded-3xl border border-white/12 bg-white/6 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white transition-colors hover:bg-white/10"
            >
              {t("combatUi.cancelMovement")}
            </button>
          </div>
        </div>
      ) : null}
    </section>
  );
};
