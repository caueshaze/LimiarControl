import { useLocale } from "../../../shared/hooks/useLocale";
import { ExpandedPreviewDialog } from "./ExpandedPreviewDialog";
import { MapEditorForm } from "./MapEditorForm";
import { MapListWidget } from "./MapListWidget";
import { MapPreviewPanel } from "./MapPreviewPanel";
import type { Props } from "./types";
import { ACCEPTED_IMAGE_TYPES } from "./useCampaignMapImageUpload";
import {
  calibrationFieldClassName,
  useCampaignMapConfigController,
} from "./useCampaignMapConfigController";

export const CampaignMapConfigCard = ({
  campaignId,
  initialMaps,
  onSaved,
}: Props) => {
  const { t } = useLocale();
  const controller = useCampaignMapConfigController({
    campaignId,
    initialMaps,
    onSaved,
  });

  return (
    <>
      <div className="rounded-3xl border border-slate-800 bg-slate-950/35 p-5">
        <div className="flex flex-col gap-3 border-b border-white/8 pb-5 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-400">
              {t("campaignHome.mapConfigTitle")}
            </p>
            <h3 className="mt-3 text-xl font-semibold text-white">
              {t("campaignHome.mapConfigHeading")}
            </h3>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-300">
              {t("campaignHome.mapConfigDescription")}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full border border-slate-700 bg-slate-900/70 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-200">
              {`${controller.readyMaps}/${controller.sortedMaps.length} ${t("campaignHome.mapStatusReady")}`}
            </span>
            <button
              type="button"
              onClick={controller.handleCreateNew}
              className="rounded-full border border-limiar-500/30 bg-limiar-500/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-limiar-100 hover:border-limiar-400/60"
            >
              {t("campaignHome.mapNew")}
            </button>
          </div>
        </div>

        <div className="mt-5 grid gap-3 xl:grid-cols-3">
          <MapListWidget
            maps={controller.sortedMaps}
            selectedMapId={controller.selectedMapId}
            isCreatingNew={controller.isCreatingNew}
            onEditMap={controller.handleEditMap}
          />
        </div>

        <div className="mt-6 grid gap-5 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,1.4fr)]">
          <MapPreviewPanel
            imageUrl={controller.form.imageUrl}
            mapName={controller.form.mapName}
            hasMapImage={controller.hasMapImage}
            gridSummary={controller.gridSummary}
            calibrationSummary={controller.calibrationSummary}
            calibrationPreview={controller.calibrationPreview}
            previewGridWidth={controller.previewGridWidth}
            previewGridHeight={controller.previewGridHeight}
            obstacleMap={controller.obstacleMap}
            edgeObstacleMap={controller.edgeObstacleMap}
            isObstacleEditMode={controller.isObstacleEditMode}
            obstacleEditTarget={controller.obstacleEditTarget}
            selectedPresetId={controller.selectedPresetId}
            selectedEdgePresetId={controller.selectedEdgePresetId}
            edgeDirection={controller.edgeDirection}
            onSelectPreset={controller.setSelectedPresetId}
            onSelectEdgePreset={controller.setSelectedEdgePresetId}
            onSelectEdgeDirection={controller.setEdgeDirection}
            onSelectObstacleTarget={controller.setObstacleEditTarget}
            onToggleObstacleEditMode={() =>
              controller.setIsObstacleEditMode((value) => !value)
            }
            onOpenPreview={() => controller.setIsPreviewOpen(true)}
            onCellToggle={controller.toggleCell}
            onEdgeToggle={controller.toggleEdge}
          />

          <MapEditorForm
            form={controller.form}
            isCreatingNew={controller.isCreatingNew}
            isConfigured={controller.isConfigured}
            uploading={controller.uploading}
            deleting={controller.deleting}
            saving={controller.saving}
            error={controller.error}
            success={controller.success}
            imageInputRef={controller.imageInputRef}
            acceptedImageTypes={ACCEPTED_IMAGE_TYPES}
            calibrationFieldClassName={calibrationFieldClassName}
            onUpdateField={controller.updateField}
            onChooseImage={controller.handleChooseImage}
            onImageSelected={controller.handleImageSelected}
            onResetCalibration={controller.handleResetCalibration}
            onClear={controller.handleClear}
            onDelete={() => void controller.handleDelete()}
            onSave={() => void controller.handleSave()}
          />
        </div>
      </div>

      <ExpandedPreviewDialog
        isOpen={controller.isPreviewOpen && controller.hasMapImage}
        imageUrl={controller.form.imageUrl}
        mapName={controller.form.mapName}
        gridSummary={controller.gridSummary}
        calibrationPreview={controller.calibrationPreview}
        previewGridWidth={controller.previewGridWidth}
        previewGridHeight={controller.previewGridHeight}
        obstacleMap={controller.obstacleMap}
        edgeObstacleMap={controller.edgeObstacleMap}
        isObstacleEditMode={controller.isObstacleEditMode}
        obstacleEditTarget={controller.obstacleEditTarget}
        selectedPresetId={controller.selectedPresetId}
        selectedEdgePresetId={controller.selectedEdgePresetId}
        edgeDirection={controller.edgeDirection}
        saving={controller.saving}
        uploading={controller.uploading}
        deleting={controller.deleting}
        onClose={() => controller.setIsPreviewOpen(false)}
        onToggleObstacleEditMode={() =>
          controller.setIsObstacleEditMode((value) => !value)
        }
        onSelectPreset={controller.setSelectedPresetId}
        onSelectEdgePreset={controller.setSelectedEdgePresetId}
        onSelectEdgeDirection={controller.setEdgeDirection}
        onSelectObstacleTarget={controller.setObstacleEditTarget}
        onCellToggle={controller.toggleCell}
        onEdgeToggle={controller.toggleEdge}
        onSave={() => void controller.handleSave()}
      />
    </>
  );
};
