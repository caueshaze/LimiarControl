import { useLocale } from "../../../shared/hooks/useLocale";
import { ExpandedPreviewDialog } from "./ExpandedPreviewDialog";
import { MapEditorForm } from "./MapEditorForm";
import { MapListWidget } from "./MapListWidget";
import { MapPreviewPanel } from "./MapPreviewPanel";
import type { Props } from "./types";
import { ACCEPTED_IMAGE_TYPES } from "./useCampaignMapImageUpload";
import { useCampaignMapConfigController } from "./useCampaignMapConfigController";

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
        </div>

        <div className="mt-5 grid gap-2 sm:grid-cols-2">
          <button
            type="button"
            onClick={controller.handleShowList}
            className={`rounded-3xl px-5 py-5 text-left transition ${
              controller.isCreatingNew || controller.isEditing
                ? "border border-transparent bg-white/3 text-slate-300 hover:bg-white/6"
                : "border border-sky-300/20 bg-sky-400/10 text-white shadow-[0_18px_40px_rgba(56,189,248,0.08)]"
            }`}
          >
            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
              {t("campaignHome.mapSwitchListLabel")}
            </p>
            <p className="mt-2 text-lg font-semibold text-inherit">
              {t("campaignHome.mapTabList")}
            </p>
            <p className="mt-2 text-sm leading-7 text-slate-300">
              {t("campaignHome.mapSwitchListDescription")}
            </p>
          </button>
          <button
            type="button"
            onClick={controller.handleCreateNew}
            className={`rounded-3xl px-5 py-5 text-left transition ${
              controller.isCreatingNew
                ? "border border-violet-300/20 bg-violet-400/10 text-white shadow-[0_18px_40px_rgba(167,139,250,0.08)]"
                : "border border-transparent bg-white/3 text-slate-300 hover:bg-white/6"
            }`}
          >
            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
              {t("campaignHome.mapSwitchNewLabel")}
            </p>
            <p className="mt-2 text-lg font-semibold text-inherit">
              {t("campaignHome.mapNew")}
            </p>
            <p className="mt-2 text-sm leading-7 text-slate-300">
              {t("campaignHome.mapSwitchNewDescription")}
            </p>
          </button>
        </div>

        {!controller.isCreatingNew && !controller.isEditing ? (
          controller.sortedMaps.length === 0 ? (
            <div className="mt-5 flex flex-col items-center gap-4 rounded-3xl border border-dashed border-slate-700 bg-slate-950/40 px-6 py-14 text-center">
              <p className="text-base font-semibold text-white">
                {t("campaignHome.mapEmptyTitle")}
              </p>
              <p className="max-w-md text-sm leading-7 text-slate-400">
                {t("campaignHome.mapEmptyList")}
              </p>
              <button
                type="button"
                onClick={controller.handleCreateNew}
                className="rounded-full border border-violet-300/30 bg-violet-400/15 px-5 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-violet-100 transition hover:border-violet-300/50 hover:bg-violet-400/20"
              >
                {t("campaignHome.mapCreateNow")}
              </button>
            </div>
          ) : (
            <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              <MapListWidget
                maps={controller.sortedMaps}
                selectedMapId={controller.selectedMapId}
                isCreatingNew={controller.isCreatingNew}
                onEditMap={controller.handleEditMap}
                onPreviewMap={controller.handlePreviewMap}
              />
            </div>
          )
        ) : (
          <div className="mt-5">
            <button
              type="button"
              onClick={controller.handleShowList}
              className="mb-4 inline-flex items-center gap-2 rounded-full border border-slate-700 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-300 hover:border-slate-500"
            >
              <span aria-hidden>←</span>
              {t("campaignHome.mapTabList")}
            </button>

            <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)]">
            <MapEditorForm
              form={controller.form}
              isCreatingNew={controller.isCreatingNew}
              isConfigured={controller.isConfigured}
              isDirty={controller.isDirty}
              calibrationSummary={controller.calibrationSummary}
              uploading={controller.uploading}
              deleting={controller.deleting}
              saving={controller.saving}
              error={controller.error}
              success={controller.success}
              imageInputRef={controller.imageInputRef}
              acceptedImageTypes={ACCEPTED_IMAGE_TYPES}
              onUpdateField={controller.updateField}
              onChooseImage={controller.handleChooseImage}
              onImageSelected={controller.handleImageSelected}
              onResetCalibration={controller.handleResetCalibration}
              onClear={controller.handleClear}
              onDelete={() => void controller.handleDelete()}
              onSave={() => void controller.handleSave()}
            />

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
              editorMode={controller.editorMode}
              isObstacleEditMode={controller.isObstacleEditMode}
              isCalibrating={controller.isCalibrating}
              calibrationCell={controller.calibrationCell}
              obstacleEditTarget={controller.obstacleEditTarget}
              selectedPresetId={controller.selectedPresetId}
              selectedEdgePresetId={controller.selectedEdgePresetId}
              edgeDirection={controller.edgeDirection}
              onSelectMode={controller.setEditorMode}
              onSelectPreset={controller.setSelectedPresetId}
              onSelectEdgePreset={controller.setSelectedEdgePresetId}
              onSelectEdgeDirection={controller.setEdgeDirection}
              onSelectObstacleTarget={controller.setObstacleEditTarget}
              onCalibrationChange={controller.setCalibrationBounds}
              onOpenPreview={() => controller.setIsPreviewOpen(true)}
              onCellToggle={controller.toggleCell}
              onEdgeToggle={controller.toggleEdge}
            />
            </div>
          </div>
        )}
      </div>

      <ExpandedPreviewDialog
        isOpen={controller.isPreviewOpen && controller.hasMapImage}
        imageUrl={controller.form.imageUrl}
        mapName={controller.form.mapName}
        gridSummary={controller.gridSummary}
        calibrationPreview={controller.calibrationPreview}
        calibrationCell={controller.calibrationCell}
        editable={controller.isEditing || controller.isCreatingNew}
        previewGridWidth={controller.previewGridWidth}
        previewGridHeight={controller.previewGridHeight}
        gridWidthValue={controller.form.gridWidth}
        gridHeightValue={controller.form.gridHeight}
        obstacleMap={controller.obstacleMap}
        edgeObstacleMap={controller.edgeObstacleMap}
        onUpdateField={controller.updateField}
        onCalibrationChange={controller.setCalibrationBounds}
        onClose={() => controller.setIsPreviewOpen(false)}
      />
    </>
  );
};
