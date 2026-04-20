import type { ObstaclePresetId } from "../../../entities/campaign";
import { CAMPAIGN_OBSTACLE_PRESETS } from "../../../entities/campaign";
import { useLocale } from "../../../shared/hooks/useLocale";
import type {
  CalibrationPreviewBounds,
  CalibrationPreviewState,
  HoveredGridCell,
} from "./types";
import {
  formatCalibrationBounds,
  formatHoveredCell,
  getHoveredCellObstaclePreset,
  summarizeObstacleMap,
} from "./utils";

type Props = {
  calibrationPreview: CalibrationPreviewState;
  gridWidth: number | null;
  gridHeight: number | null;
  obstacleMap: ReadonlyMap<string, ObstaclePresetId>;
  hoveredCell?: HoveredGridCell | null;
  className?: string;
};

const cardClassName =
  "rounded-2xl border border-slate-800 bg-slate-950/70 px-4 py-4";

function resolveCalibrationModeLabel(
  t: ReturnType<typeof useLocale>["t"],
  calibrationPreview: CalibrationPreviewState,
) {
  switch (calibrationPreview.status) {
    case "full-image":
      return t("campaignHome.mapPreviewReviewModeFull");
    case "custom":
      return t("campaignHome.mapPreviewReviewModeCustom");
    default:
      return t("campaignHome.mapPreviewReviewModeInvalid");
  }
}

function renderBounds(bounds: CalibrationPreviewBounds | null) {
  if (bounds == null) {
    return "X - | Y - | W - | H -";
  }
  return formatCalibrationBounds(bounds);
}

export const MapPreviewReviewPanel = ({
  calibrationPreview,
  gridWidth,
  gridHeight,
  obstacleMap,
  hoveredCell = null,
  className = "",
}: Props) => {
  const { t } = useLocale();
  const obstacleSummary = summarizeObstacleMap(obstacleMap);
  const hoveredPresetId = getHoveredCellObstaclePreset(obstacleMap, hoveredCell);
  const hoveredPreset =
    hoveredPresetId == null
      ? null
      : CAMPAIGN_OBSTACLE_PRESETS.find((preset) => preset.id === hoveredPresetId) ?? null;
  const totalCells =
    gridWidth != null && gridHeight != null ? gridWidth * gridHeight : null;

  return (
    <div className={`space-y-3 ${className}`}>
      <div className={cardClassName}>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
          {t("campaignHome.mapPreviewReviewGrid")}
        </p>
        <div className="mt-3 grid gap-3 sm:grid-cols-3">
          <div>
            <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">
              {t("campaignHome.mapPreviewReviewColumns")}
            </p>
            <p className="mt-1 text-lg font-semibold text-white">
              {gridWidth ?? "-"}
            </p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">
              {t("campaignHome.mapPreviewReviewRows")}
            </p>
            <p className="mt-1 text-lg font-semibold text-white">
              {gridHeight ?? "-"}
            </p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">
              {t("campaignHome.mapPreviewReviewCells")}
            </p>
            <p className="mt-1 text-lg font-semibold text-white">
              {totalCells ?? "-"}
            </p>
          </div>
        </div>
      </div>

      <div className={cardClassName}>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
          {t("campaignHome.mapPreviewReviewCalibration")}
        </p>
        <div className="mt-3 grid gap-3">
          <div>
            <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">
              {t("campaignHome.mapPreviewReviewMode")}
            </p>
            <p className="mt-1 text-sm font-semibold text-white">
              {resolveCalibrationModeLabel(t, calibrationPreview)}
            </p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">
              {t("campaignHome.mapPreviewReviewBounds")}
            </p>
            <p className="mt-1 font-mono text-xs text-slate-200">
              {renderBounds(calibrationPreview.bounds)}
            </p>
          </div>
        </div>
      </div>

      <div className={cardClassName}>
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
            {t("campaignHome.mapPreviewReviewObstacles")}
          </p>
          <span className="rounded-full border border-slate-700 bg-slate-900/70 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-200">
            {obstacleMap.size}
          </span>
        </div>
        {obstacleMap.size === 0 ? (
          <p className="mt-3 text-sm text-slate-400">
            {t("campaignHome.mapPreviewReviewObstacleEmpty")}
          </p>
        ) : (
          <div className="mt-3 space-y-2">
            {obstacleSummary.map((preset) => (
              <div
                key={preset.id}
                className="flex items-center justify-between gap-3 rounded-xl border border-slate-800/80 bg-slate-950/80 px-3 py-2"
              >
                <div className="flex items-center gap-2 text-sm text-slate-200">
                  <span
                    className="inline-block h-2.5 w-2.5 shrink-0 rounded-sm"
                    style={{ backgroundColor: preset.color }}
                  />
                  <span>{preset.label}</span>
                </div>
                <span className="text-sm font-semibold text-white">{preset.count}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className={cardClassName}>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
          {t("campaignHome.mapPreviewReviewInspection")}
        </p>
        {hoveredCell == null ? (
          <p className="mt-3 text-sm text-slate-400">
            {t("campaignHome.mapPreviewReviewNoHover")}
          </p>
        ) : (
          <div className="mt-3 space-y-3">
            <div>
              <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">
                {t("campaignHome.mapPreviewReviewHoveredCell")}
              </p>
              <p className="mt-1 text-sm font-semibold text-white">
                {formatHoveredCell(hoveredCell, {
                  columnLabel: t("campaignHome.mapPreviewHoverColumn"),
                  rowLabel: t("campaignHome.mapPreviewHoverRow"),
                })}
              </p>
            </div>
            <div>
              <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">
                {t("campaignHome.mapPreviewReviewHoveredObstacle")}
              </p>
              {hoveredPreset == null ? (
                <p className="mt-1 text-sm text-slate-400">
                  {t("campaignHome.mapPreviewReviewNoObstacle")}
                </p>
              ) : (
                <div className="mt-2 rounded-xl border border-slate-800/80 bg-slate-950/80 px-3 py-3">
                  <div className="flex items-center gap-2 text-sm font-semibold text-white">
                    <span
                      className="inline-block h-2.5 w-2.5 shrink-0 rounded-sm"
                      style={{ backgroundColor: hoveredPreset.color }}
                    />
                    {hoveredPreset.label}
                  </div>
                  <p className="mt-2 text-sm leading-6 text-slate-400">
                    {hoveredPreset.description}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
