import { useEffect, useState } from "react";
import type { ObstaclePresetId } from "../../../entities/campaign";
import { useLocale } from "../../../shared/hooks/useLocale";
import { MapPreviewReviewPanel } from "./MapPreviewReviewPanel";
import { MapPreviewSurface } from "./MapPreviewSurface";
import { ObstaclePresetPicker } from "./ObstaclePresetPicker";
import type {
  CalibrationPreviewState,
  HoveredGridCell,
} from "./types";

type Props = {
  isOpen: boolean;
  imageUrl: string;
  mapName: string;
  gridSummary: string;
  calibrationPreview: CalibrationPreviewState;
  previewGridWidth: number | null;
  previewGridHeight: number | null;
  obstacleMap: ReadonlyMap<string, ObstaclePresetId>;
  isObstacleEditMode: boolean;
  selectedPresetId: ObstaclePresetId;
  saving: boolean;
  uploading: boolean;
  deleting: boolean;
  onClose: () => void;
  onToggleObstacleEditMode: () => void;
  onSelectPreset: (presetId: ObstaclePresetId) => void;
  onCellToggle: (x: number, y: number) => void;
  onSave: () => void;
};

export const ExpandedPreviewDialog = ({
  isOpen,
  imageUrl,
  mapName,
  gridSummary,
  calibrationPreview,
  previewGridWidth,
  previewGridHeight,
  obstacleMap,
  isObstacleEditMode,
  selectedPresetId,
  saving,
  uploading,
  deleting,
  onClose,
  onToggleObstacleEditMode,
  onSelectPreset,
  onCellToggle,
  onSave,
}: Props) => {
  const { t } = useLocale();
  const [hoveredCell, setHoveredCell] = useState<HoveredGridCell | null>(null);

  useEffect(() => {
    if (!isOpen) {
      setHoveredCell(null);
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
        className="flex max-h-[92vh] w-full max-w-7xl flex-col overflow-hidden rounded-[2rem] border border-slate-800 bg-slate-950/95 shadow-2xl shadow-black/40"
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
                {isObstacleEditMode
                  ? t("campaignHome.mapPreviewEditHint")
                  : t("campaignHome.mapPreviewHint")}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-slate-700 bg-slate-900/70 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-200">
                {gridSummary}
              </span>
              {previewGridWidth != null && previewGridHeight != null && (
                <button
                  type="button"
                  onClick={onToggleObstacleEditMode}
                  className={`rounded-full border px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] ${
                    isObstacleEditMode
                      ? "border-rose-500/50 bg-rose-500/15 text-rose-200"
                      : "border-slate-700 text-slate-300 hover:border-rose-500/30"
                  }`}
                >
                  {isObstacleEditMode
                    ? t("campaignHome.mapObstacleEditDone")
                    : t("campaignHome.mapObstacleEditStart")}
                </button>
              )}
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
            <div className="min-h-0 flex-1 overflow-auto p-4">
              <div className="flex min-h-full items-center justify-center">
                <div className="max-w-full overflow-hidden rounded-2xl border border-slate-800 bg-slate-950 shadow-2xl shadow-black/30">
                  <MapPreviewSurface
                    imageUrl={imageUrl}
                    alt={mapName || t("campaignHome.mapPreviewAlt")}
                    bounds={calibrationPreview.bounds}
                    gridWidth={previewGridWidth}
                    gridHeight={previewGridHeight}
                    imageClassName="block h-auto max-h-[62vh] w-auto max-w-full"
                    invalidMessage={t("campaignHome.mapPreviewInvalid")}
                    hoverHint={
                      isObstacleEditMode
                        ? t("campaignHome.mapPreviewEditHint")
                        : t("campaignHome.mapPreviewHoverHint")
                    }
                    hoverMissingGrid={t("campaignHome.mapPreviewHoverMissingGrid")}
                    hoverCellLabel={t("campaignHome.mapPreviewHoverCell")}
                    hoverColumnLabel={t("campaignHome.mapPreviewHoverColumn")}
                    hoverRowLabel={t("campaignHome.mapPreviewHoverRow")}
                    obstacleMap={obstacleMap}
                    onCellToggle={isObstacleEditMode ? onCellToggle : undefined}
                    onHoveredCellChange={setHoveredCell}
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="min-h-0 space-y-4 overflow-y-auto pr-1">
            {isObstacleEditMode && (
              <ObstaclePresetPicker
                selectedPresetId={selectedPresetId}
                onSelectPreset={onSelectPreset}
                obstacleMap={obstacleMap}
              />
            )}

            <MapPreviewReviewPanel
              calibrationPreview={calibrationPreview}
              gridWidth={previewGridWidth}
              gridHeight={previewGridHeight}
              obstacleMap={obstacleMap}
              hoveredCell={hoveredCell}
            />
          </div>
        </div>

        <div className="shrink-0 border-t border-white/8 px-5 py-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-slate-400">
              {t("campaignHome.mapPreviewSaveHint")}
            </p>
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={onClose}
                className="rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-300 hover:border-slate-500"
              >
                {t("campaignHome.mapPreviewClose")}
              </button>
              <button
                type="button"
                onClick={onSave}
                disabled={saving || uploading || deleting}
                className="rounded-full bg-limiar-500 px-5 py-2 text-xs font-bold uppercase tracking-[0.2em] text-white hover:bg-limiar-400 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {saving ? t("campaignHome.mapSaving") : t("campaignHome.mapSave")}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
