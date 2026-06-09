import type {
  CampaignEdgeDirection,
  EdgeObstaclePresetId,
  ObstaclePresetId,
} from "../../../entities/campaign";
import { useLocale } from "../../../shared/hooks/useLocale";
import { MapEditorModeSwitcher } from "./MapEditorModeSwitcher";
import { MapZoomControls } from "./MapZoomControls";
import { ObstacleEditorControls } from "./ObstacleEditorControls";
import { MapPreviewSurface } from "./MapPreviewSurface";
import { MapPreviewReviewPanel } from "./MapPreviewReviewPanel";
import { useMapZoom } from "./useMapZoom";
import type {
  CalibrationPreviewBounds,
  CalibrationPreviewState,
  EditorMode,
  ObstacleEditTarget,
} from "./types";

type Props = {
  imageUrl: string;
  mapName: string;
  hasMapImage: boolean;
  gridSummary: string;
  calibrationSummary: string;
  calibrationPreview: CalibrationPreviewState;
  previewGridWidth: number | null;
  previewGridHeight: number | null;
  obstacleMap: ReadonlyMap<string, ObstaclePresetId>;
  edgeObstacleMap: ReadonlyMap<string, EdgeObstaclePresetId>;
  editorMode: EditorMode;
  isObstacleEditMode: boolean;
  isCalibrating: boolean;
  calibrationCell: CalibrationPreviewBounds | null;
  obstacleEditTarget: ObstacleEditTarget;
  selectedPresetId: ObstaclePresetId;
  selectedEdgePresetId: EdgeObstaclePresetId;
  edgeDirection: CampaignEdgeDirection;
  onSelectMode: (mode: EditorMode) => void;
  onSelectPreset: (presetId: ObstaclePresetId) => void;
  onSelectEdgePreset: (presetId: EdgeObstaclePresetId) => void;
  onSelectEdgeDirection: (direction: CampaignEdgeDirection) => void;
  onSelectObstacleTarget: (target: ObstacleEditTarget) => void;
  onCalibrationChange: (bounds: CalibrationPreviewBounds) => void;
  onOpenPreview: () => void;
  onCellToggle: (x: number, y: number) => void;
  onEdgeToggle: (x: number, y: number, direction: CampaignEdgeDirection) => void;
};

export const MapPreviewPanel = ({
  imageUrl,
  mapName,
  hasMapImage,
  gridSummary,
  calibrationSummary,
  calibrationPreview,
  previewGridWidth,
  previewGridHeight,
  obstacleMap,
  edgeObstacleMap,
  editorMode,
  isObstacleEditMode,
  isCalibrating,
  calibrationCell,
  obstacleEditTarget,
  selectedPresetId,
  selectedEdgePresetId,
  edgeDirection,
  onSelectMode,
  onSelectPreset,
  onSelectEdgePreset,
  onSelectEdgeDirection,
  onSelectObstacleTarget,
  onCalibrationChange,
  onOpenPreview,
  onCellToggle,
  onEdgeToggle,
}: Props) => {
  const { t } = useLocale();
  const zoomControls = useMapZoom();
  const hasGrid = previewGridWidth != null && previewGridHeight != null;
  const gridOverflows =
    calibrationPreview.bounds != null &&
    (calibrationPreview.bounds.x + calibrationPreview.bounds.width > 1.0001 ||
      calibrationPreview.bounds.y + calibrationPreview.bounds.height > 1.0001);

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-950/70 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
            {t("campaignHome.mapPreviewTitle")}
          </p>
          <p className="mt-2 text-sm text-slate-300">
            {t("campaignHome.mapPreviewHint")}
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <span className="rounded-full border border-slate-700 bg-slate-900/70 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-200">
            {gridSummary}
          </span>
          <button
            type="button"
            onClick={onOpenPreview}
            disabled={!hasMapImage}
            className="rounded-full border border-slate-700 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-200 hover:border-limiar-500/50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {t("campaignHome.mapOpenPreview")}
          </button>
        </div>
      </div>

      {hasMapImage && (
        <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
          <MapEditorModeSwitcher
            editorMode={editorMode}
            obstaclesDisabled={!hasGrid}
            onSelectMode={onSelectMode}
          />
          <MapZoomControls
            zoom={zoomControls.zoom}
            canZoomIn={zoomControls.canZoomIn}
            canZoomOut={zoomControls.canZoomOut}
            onZoomIn={zoomControls.zoomIn}
            onZoomOut={zoomControls.zoomOut}
            onReset={zoomControls.reset}
          />
        </div>
      )}

      <div
        className="mt-4 max-h-[70vh] overflow-auto border border-slate-800 bg-slate-950"
        onWheel={zoomControls.handleWheelZoom}
      >
        {hasMapImage ? (
          <div className="mx-auto" style={{ width: `${zoomControls.zoom * 100}%` }}>
          <MapPreviewSurface
            imageUrl={imageUrl}
            alt={mapName || t("campaignHome.mapPreviewAlt")}
            bounds={calibrationPreview.bounds}
            gridWidth={previewGridWidth}
            gridHeight={previewGridHeight}
            imageClassName="block w-full"
            invalidMessage={t("campaignHome.mapPreviewInvalid")}
            calibrationEditing={isCalibrating && hasGrid}
            calibrationCell={calibrationCell}
            onCalibrationChange={onCalibrationChange}
            hoverHint={
              isObstacleEditMode
                ? obstacleEditTarget === "edge"
                  ? t("campaignHome.mapPreviewEdgeEditHint").replace(
                      "{direction}",
                      edgeDirection,
                    )
                  : t("campaignHome.mapPreviewEditHint")
                : t("campaignHome.mapPreviewHoverHint")
            }
            hoverMissingGrid={t("campaignHome.mapPreviewHoverMissingGrid")}
            hoverCellLabel={t("campaignHome.mapPreviewHoverCell")}
            hoverColumnLabel={t("campaignHome.mapPreviewHoverColumn")}
            hoverRowLabel={t("campaignHome.mapPreviewHoverRow")}
            obstacleMap={obstacleMap}
            edgeObstacleMap={edgeObstacleMap}
            obstacleEditTarget={obstacleEditTarget}
            edgeDirection={edgeDirection}
            onCellToggle={
              isObstacleEditMode && obstacleEditTarget === "cell"
                ? onCellToggle
                : undefined
            }
            onEdgeToggle={
              isObstacleEditMode && obstacleEditTarget === "edge"
                ? onEdgeToggle
                : undefined
            }
          />
          </div>
        ) : (
          <div className="flex h-72 items-center justify-center px-6 text-center text-sm text-slate-500">
            {t("campaignHome.mapPreviewEmpty")}
          </div>
        )}
      </div>

      {isObstacleEditMode && (
        <div className="mt-3">
          <ObstacleEditorControls
            obstacleEditTarget={obstacleEditTarget}
            selectedPresetId={selectedPresetId}
            selectedEdgePresetId={selectedEdgePresetId}
            edgeDirection={edgeDirection}
            obstacleMap={obstacleMap}
            edgeObstacleMap={edgeObstacleMap}
            onSelectTarget={onSelectObstacleTarget}
            onSelectPreset={onSelectPreset}
            onSelectEdgePreset={onSelectEdgePreset}
            onSelectEdgeDirection={onSelectEdgeDirection}
          />
        </div>
      )}

      <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
          {t("campaignHome.mapPreviewLegend")}
        </p>
        {isCalibrating &&
          (hasGrid ? (
            <p className="mt-2 text-sm text-limiar-100">
              {t("campaignHome.mapCalibrationDragHint")}
            </p>
          ) : (
            <p className="mt-2 text-sm text-amber-200">
              {t("campaignHome.mapCalibrationNeedsGridError")}
            </p>
          ))}
        {gridOverflows && (
          <p className="mt-2 text-sm text-amber-200">
            {t("campaignHome.mapCalibrationOverflowError")}
          </p>
        )}
        <p className="mt-2 text-sm text-slate-200">{calibrationSummary}</p>
      </div>

      <MapPreviewReviewPanel
        calibrationPreview={calibrationPreview}
        gridWidth={previewGridWidth}
        gridHeight={previewGridHeight}
        obstacleMap={obstacleMap}
        edgeObstacleMap={edgeObstacleMap}
        className="mt-4"
      />
    </div>
  );
};
