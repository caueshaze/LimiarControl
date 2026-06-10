import { useLocale } from "../../../shared/hooks/useLocale";
import type { CreatureSize } from "@limiarmap/shared-contracts";
import type { RangeStatus, TargetingPreviewState } from "../hooks/useTargetingPreview";
import { formatSizeMeleeReachBonusSource, formatMetersCompact } from "../utils/formatSizeMeleeReachBonus";

type Props = {
  preview: TargetingPreviewState;
  effectiveSize?: CreatureSize;
  /**
   * Spells whose targeting is resolved per instance/target (e.g. Magic Missile)
   * have no single target to measure against, so the per-target distance check
   * is meaningless. Show an informational "range per die" badge instead of the
   * default "range unavailable" fallback.
   */
  perTargetRange?: boolean;
};

const STATUS_STYLES: Record<RangeStatus, string> = {
  normal: "border-emerald-500/40 bg-emerald-500/10 text-emerald-200",
  long: "border-amber-500/40 bg-amber-500/10 text-amber-200",
  out: "border-rose-500/40 bg-rose-500/10 text-rose-200",
  unknown: "border-slate-600/50 bg-slate-800/40 text-slate-300",
};

const statusLabel = (
  t: (key: "combatUi.rangeNormal" | "combatUi.rangeLong" | "combatUi.rangeOut" | "combatUi.rangeUnknown") => string,
  status: RangeStatus,
): string => {
  switch (status) {
    case "normal":
      return t("combatUi.rangeNormal");
    case "long":
      return t("combatUi.rangeLong");
    case "out":
      return t("combatUi.rangeOut");
    default:
      return t("combatUi.rangeUnknown");
  }
};

export const RangeStatusBadge = ({ preview, effectiveSize, perTargetRange = false }: Props) => {
  const { t } = useLocale();
  const {
    loading,
    rangeStatus,
    distanceMeters,
    normalRangeMeters,
    maxRangeMeters,
    effectiveReachMeters,
    hasDisadvantage,
  } = preview;

  const sizeBonusSource = effectiveSize
    ? formatSizeMeleeReachBonusSource(effectiveSize, t)
    : null;

  if (perTargetRange) {
    return (
      <div className={`rounded-2xl border px-3 py-2 text-xs font-semibold ${STATUS_STYLES.unknown}`}>
        {t("combatUi.rangePerDie")}
      </div>
    );
  }

  if (loading) {
    return (
      <div className="rounded-2xl border border-slate-700 bg-slate-900/40 px-3 py-2 text-xs text-slate-400">
        {t("combatUi.rangeChecking")}
      </div>
    );
  }

  const label = statusLabel(t, rangeStatus);
  const distanceLabel = distanceMeters != null ? formatMetersCompact(distanceMeters) : null;
  const normalRangeLabel = normalRangeMeters != null ? formatMetersCompact(normalRangeMeters) : null;
  const maxRangeLabel =
    maxRangeMeters != null && maxRangeMeters !== normalRangeMeters
      ? formatMetersCompact(maxRangeMeters)
      : null;
  const effectiveReachLabel = effectiveReachMeters != null ? formatMetersCompact(effectiveReachMeters) : null;
  const neededLabel = effectiveReachLabel ?? (maxRangeMeters != null ? formatMetersCompact(maxRangeMeters) : null);

  return (
    <div
      className={`rounded-2xl border px-3 py-2 text-xs font-semibold ${STATUS_STYLES[rangeStatus]}`}
    >
      <div className="flex items-center justify-between gap-2">
        <span>{label}</span>
        {distanceLabel ? <span className="opacity-80">{distanceLabel}</span> : null}
      </div>
      {distanceLabel || neededLabel ? (
        <p className="mt-1 text-[11px] font-normal opacity-90">
          {distanceLabel ? `Distancia atual: ${distanceLabel}` : "Distancia atual: -"}
          {neededLabel ? ` · precisa <= ${neededLabel}` : ""}
        </p>
      ) : null}
      {sizeBonusSource && effectiveReachLabel ? (
        <p className="mt-1 text-[11px] font-normal opacity-90">
          {t("combatUi.meleeReachEffective")}: {effectiveReachLabel}
          {normalRangeLabel ? ` (${t("combatUi.meleeReachBase")}: ${normalRangeLabel} · ${sizeBonusSource.label})` : ` (${sizeBonusSource.label})`}
        </p>
      ) : normalRangeLabel ? (
        <p className="mt-1 text-[11px] font-normal opacity-80">
          Alcance normal: {normalRangeLabel}
          {maxRangeLabel ? ` · longo: ${maxRangeLabel}` : ""}
        </p>
      ) : null}
      {hasDisadvantage ? (
        <p className="mt-1 text-[11px] font-normal text-amber-100">
          {t("combatUi.disadvantageRange")}
        </p>
      ) : null}
    </div>
  );
};
