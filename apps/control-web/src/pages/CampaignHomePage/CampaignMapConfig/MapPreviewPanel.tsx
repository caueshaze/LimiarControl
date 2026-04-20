import type {
  CampaignEdgeDirection,
  EdgeObstaclePresetId,
  ObstaclePresetId,
} from "../../../entities/campaign";
import { useLocale } from "../../../shared/hooks/useLocale";
import { ObstacleEditorControls } from "./ObstacleEditorControls";
import { MapPreviewSurface } from "./MapPreviewSurface";
import { MapPreviewReviewPanel } from "./MapPreviewReviewPanel";
import type { CalibrationPreviewState, ObstacleEditTarget } from "./types";

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
  isObstacleEditMode: boolean;
  obstacleEditTarget: ObstacleEditTarget;
  selectedPresetId: ObstaclePresetId;
  selectedEdgePresetId: EdgeObstaclePresetId;
  edgeDirection: CampaignEdgeDirection;
  onSelectPreset: (presetId: ObstaclePresetId) => void;
  onSelectEdgePreset: (presetId: EdgeObstaclePresetId) => void;
  onSelectEdgeDirection: (direction: CampaignEdgeDirection) => void;
  onSelectObstacleTarget: (target: ObstacleEditTarget) => void;
  onToggleObstacleEditMode: () => void;
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
  isObstacleEditMode,
  obstacleEditTarget,
  selectedPresetId,
  selectedEdgePresetId,
  edgeDirection,
  onSelectPreset,
  onSelectEdgePreset,
  onSelectEdgeDirection,
  onSelectObstacleTarget,
  onToggleObstacleEditMode,
  onOpenPreview,
  onCellToggle,
  onEdgeToggle,
}: Props) => {
  const { t } = useLocale();

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
          <div className="flex gap-2">
            {hasMapImage && previewGridWidth != null && previewGridHeight != null && (
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
              onClick={onOpenPreview}
              disabled={!hasMapImage}
              className="rounded-full border border-slate-700 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-200 hover:border-limiar-500/50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {t("campaignHome.mapOpenPreview")}
            </button>
          </div>
        </div>
      </div>

      <div className="mt-4 overflow-hidden rounded-3xl border border-slate-800 bg-slate-950">
        {hasMapImage ? (
          <MapPreviewSurface
            imageUrl={imageUrl}
            alt={mapName || t("campaignHome.mapPreviewAlt")}
            bounds={calibrationPreview.bounds}
            gridWidth={previewGridWidth}
            gridHeight={previewGridHeight}
            imageClassName="block w-full"
            invalidMessage={t("campaignHome.mapPreviewInvalid")}
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
