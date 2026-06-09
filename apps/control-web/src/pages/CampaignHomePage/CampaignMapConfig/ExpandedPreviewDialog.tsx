import { useEffect, useState } from "react";
import type {
  EdgeObstaclePresetId,
  ObstaclePresetId,
} from "../../../entities/campaign";
import { useLocale } from "../../../shared/hooks/useLocale";
import { MapPreviewReviewPanel } from "./MapPreviewReviewPanel";
import { MapPreviewSurface } from "./MapPreviewSurface";
import { MapZoomControls } from "./MapZoomControls";
import { useMapZoom } from "./useMapZoom";
import type {
  CalibrationPreviewBounds,
  CalibrationPreviewState,
  FormState,
  HoveredGridCell,
} from "./types";

type Props = {
  isOpen: boolean;
  imageUrl: string;
  mapName: string;
  gridSummary: string;
  calibrationPreview: CalibrationPreviewState;
  calibrationCell: CalibrationPreviewBounds | null;
  /** When false the dialog is view-only (no cell/grid editing controls). */
  editable: boolean;
  previewGridWidth: number | null;
  previewGridHeight: number | null;
  gridWidthValue: string;
  gridHeightValue: string;
  obstacleMap: ReadonlyMap<string, ObstaclePresetId>;
  edgeObstacleMap: ReadonlyMap<string, EdgeObstaclePresetId>;
  onUpdateField: (field: keyof FormState, value: string) => void;
  onCalibrationChange: (cell: CalibrationPreviewBounds) => void;
  onClose: () => void;
};

export const ExpandedPreviewDialog = ({
  isOpen,
  imageUrl,
  mapName,
  gridSummary,
  calibrationPreview,
  calibrationCell,
  editable,
  previewGridWidth,
  previewGridHeight,
  gridWidthValue,
  gridHeightValue,
  obstacleMap,
  edgeObstacleMap,
  onUpdateField,
  onCalibrationChange,
  onClose,
}: Props) => {
  const { t } = useLocale();
  const [hoveredCell, setHoveredCell] = useState<HoveredGridCell | null>(null);
  const [showGrid, setShowGrid] = useState(true);
  const [cellEditing, setCellEditing] = useState(false);
  const zoomControls = useMapZoom();
  const hasGrid = previewGridWidth != null && previewGridHeight != null;
  const isCalibrating = editable && cellEditing && hasGrid;

  useEffect(() => {
    if (!isOpen) {
      setHoveredCell(null);
      setCellEditing(false);
      zoomControls.reset();
    }
  }, [isOpen]);

  if (!isOpen) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 px-4 py-6 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={t("campaignHome.mapPreviewDialogTitle")}
        onClick={(event) => event.stopPropagation()}
        className="flex h-[88vh] w-full max-w-7xl flex-col overflow-hidden rounded-[2rem] border border-slate-800 bg-slate-950/95 shadow-2xl shadow-black/40"
      >
        <div className="shrink-0 border-b border-white/8 px-5 py-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
                {t("campaignHome.mapPreviewDialogTitle")}
              </p>
              <h4 className="mt-2 text-lg font-semibold text-white">
                {mapName.trim() || t("campaignHome.mapUntitled")}
              </h4>
              <p className="mt-2 max-w-3xl text-sm text-slate-300">
                {t("campaignHome.mapPreviewHint")}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-slate-700 bg-slate-900/70 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-200">
                {gridSummary}
              </span>
              <button
                type="button"
                onClick={() => setShowGrid((value) => !value)}
                className={`rounded-full border px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] ${
                  showGrid
                    ? "border-slate-700 text-slate-200 hover:border-slate-500"
                    : "border-limiar-500/50 bg-limiar-500/15 text-limiar-100"
                }`}
              >
                {showGrid
                  ? t("campaignHome.mapPreviewHideGrid")
                  : t("campaignHome.mapPreviewShowGrid")}
              </button>
              <MapZoomControls
                zoom={zoomControls.zoom}
                canZoomIn={zoomControls.canZoomIn}
                canZoomOut={zoomControls.canZoomOut}
                onZoomIn={zoomControls.zoomIn}
                onZoomOut={zoomControls.zoomOut}
                onReset={zoomControls.reset}
              />
              <button
                type="button"
                onClick={onClose}
                className="rounded-full border border-slate-700 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-200 hover:border-slate-500"
              >
                {t("campaignHome.mapPreviewClose")}
              </button>
            </div>
          </div>
        </div>

        <div className="grid min-h-0 flex-1 gap-4 overflow-hidden px-5 py-5 xl:grid-cols-[minmax(0,1.65fr)_minmax(320px,0.95fr)]">
          <div className="flex min-h-0 flex-col overflow-hidden rounded-3xl border border-slate-800 bg-slate-950/70">
            <div className="shrink-0 border-b border-slate-800 px-4 py-3">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                {t("campaignHome.mapPreviewTitle")}
              </p>
              <p className="mt-2 text-sm text-slate-300">
                {t("campaignHome.mapPreviewScrollableHint")}
              </p>
            </div>
            <div
              className="min-h-0 flex-1 overflow-auto p-4"
              onWheel={zoomControls.handleWheelZoom}
            >
              <div
                className="mx-auto overflow-hidden border border-slate-800 bg-slate-950 shadow-2xl shadow-black/30"
                style={{ width: `${zoomControls.zoom * 100}%` }}
              >
                <MapPreviewSurface
                    imageUrl={imageUrl}
                    alt={mapName || t("campaignHome.mapPreviewAlt")}
                    bounds={calibrationPreview.bounds}
                    gridWidth={previewGridWidth}
                    gridHeight={previewGridHeight}
                    imageClassName="block h-auto w-full"
                    invalidMessage={t("campaignHome.mapPreviewInvalid")}
                    showGridLines={showGrid}
                    calibrationEditing={isCalibrating}
                    calibrationCell={calibrationCell}
                    onCalibrationChange={onCalibrationChange}
                    hoverHint={t("campaignHome.mapPreviewHoverHint")}
                    hoverMissingGrid={t("campaignHome.mapPreviewHoverMissingGrid")}
                    hoverCellLabel={t("campaignHome.mapPreviewHoverCell")}
                    hoverColumnLabel={t("campaignHome.mapPreviewHoverColumn")}
                    hoverRowLabel={t("campaignHome.mapPreviewHoverRow")}
                    obstacleMap={obstacleMap}
                    edgeObstacleMap={edgeObstacleMap}
                    onHoveredCellChange={setHoveredCell}
                  />
              </div>
            </div>
          </div>

          <div className="min-h-0 space-y-4 overflow-y-auto pr-1">
            {editable && (
            <div className="space-y-3 rounded-2xl border border-slate-800 bg-slate-950/70 px-4 py-4">
              <div className="grid grid-cols-2 gap-3">
                <label className="block space-y-2">
                  <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                    {t("campaignHome.mapGridWidth")}
                  </span>
                  <input
                    value={gridWidthValue}
                    onChange={(event) => onUpdateField("gridWidth", event.target.value)}
                    type="number"
                    min={1}
                    max={150}
                    className="w-full rounded-2xl border border-slate-700 bg-slate-950/70 px-3 py-2 text-sm text-slate-100 focus:border-limiar-500 focus:outline-none"
                  />
                </label>
                <label className="block space-y-2">
                  <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                    {t("campaignHome.mapGridHeight")}
                  </span>
                  <input
                    value={gridHeightValue}
                    onChange={(event) => onUpdateField("gridHeight", event.target.value)}
                    type="number"
                    min={1}
                    max={150}
                    className="w-full rounded-2xl border border-slate-700 bg-slate-950/70 px-3 py-2 text-sm text-slate-100 focus:border-limiar-500 focus:outline-none"
                  />
                </label>
              </div>
              <button
                type="button"
                onClick={() => setCellEditing((value) => !value)}
                disabled={!hasGrid}
                className={`w-full rounded-full border px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
                  isCalibrating
                    ? "border-emerald-400/60 bg-emerald-400/15 text-emerald-100"
                    : "border-slate-700 text-slate-200 hover:border-emerald-400/40"
                }`}
              >
                {isCalibrating
                  ? t("campaignHome.mapCellEditDone")
                  : t("campaignHome.mapCellEditStart")}
              </button>
              {cellEditing && !hasGrid && (
                <p className="text-sm text-amber-200">
                  {t("campaignHome.mapCalibrationNeedsGridError")}
                </p>
              )}
              {isCalibrating && (
                <p className="text-sm text-emerald-100">
                  {t("campaignHome.mapCalibrationDragHint")}
                </p>
              )}
            </div>
            )}

            <MapPreviewReviewPanel
              calibrationPreview={calibrationPreview}
              gridWidth={previewGridWidth}
              gridHeight={previewGridHeight}
              obstacleMap={obstacleMap}
              edgeObstacleMap={edgeObstacleMap}
              hoveredCell={hoveredCell}
            />
          </div>
        </div>
      </div>
    </div>
  );
};
