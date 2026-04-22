import { useLocale } from "../../../shared/hooks/useLocale";
import type { RangeStatus, TargetingPreviewState } from "../hooks/useTargetingPreview";

type Props = {
  preview: TargetingPreviewState;
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

const formatDistance = (meters: number): string => {
  const rounded = Math.round(meters * 10) / 10;
  return rounded % 1 === 0 ? `${rounded.toFixed(0)}m` : `${rounded.toFixed(1).replace(".", ",")}m`;
};

export const RangeStatusBadge = ({ preview }: Props) => {
  const { t } = useLocale();
  const {
    loading,
    rangeStatus,
    distanceMeters,
    normalRangeMeters,
    maxRangeMeters,
    hasDisadvantage,
  } = preview;

  if (loading) {
    return (
      <div className="rounded-2xl border border-slate-700 bg-slate-900/40 px-3 py-2 text-xs text-slate-400">
        {t("combatUi.rangeChecking")}
      </div>
    );
  }

  const label = statusLabel(t, rangeStatus);
  const distanceLabel = distanceMeters != null ? formatDistance(distanceMeters) : null;
  const normalRangeLabel = normalRangeMeters != null ? formatDistance(normalRangeMeters) : null;
  const maxRangeLabel =
    maxRangeMeters != null && maxRangeMeters !== normalRangeMeters
      ? formatDistance(maxRangeMeters)
      : null;
  const neededLabel = maxRangeMeters != null ? formatDistance(maxRangeMeters) : null;

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
      {normalRangeLabel ? (
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
