import { useEffect, useMemo, useState } from "react";
import type { CampaignMapConfig, ObstaclePresetId } from "../../../entities/campaign";
import { campaignsRepo } from "../../../shared/api/campaignsRepo";
import { useLocale } from "../../../shared/hooks/useLocale";
import type { Props } from "./types";
import { useCampaignMapImageUpload } from "./useCampaignMapImageUpload";
import {
  EMPTY_FORM,
  buildObstacleMap,
  configToForm,
  formatCalibrationBounds,
  getCalibrationPreview,
  isMapReady,
  normalizeOptionalFloat,
  normalizeOptionalInt,
  parsePreviewInt,
  serializeObstacleMap,
  sortMaps,
} from "./utils";
export const calibrationFieldClassName =
  "block w-full rounded-2xl border border-slate-700 bg-slate-950/70 px-3 py-2 text-sm text-slate-100 focus:border-limiar-500 focus:outline-none";

export function useCampaignMapConfigController({
  campaignId,
  initialMaps,
  onSaved,
}: Props) {
  const { t } = useLocale();
  const sortedMaps = useMemo(() => sortMaps(initialMaps), [initialMaps]);
  const [selectedMapId, setSelectedMapId] = useState<string | null>(
    sortedMaps[0]?.id ?? null,
  );
  const [isCreatingNew, setIsCreatingNew] = useState(sortedMaps.length === 0);
  const [form, setForm] = useState(() => configToForm(sortedMaps[0] ?? null));
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [obstacleMap, setObstacleMap] = useState<Map<string, ObstaclePresetId>>(
    () => buildObstacleMap(sortedMaps[0]),
  );
  const [selectedPresetId, setSelectedPresetId] =
    useState<ObstaclePresetId>("solid_wall");
  const [isObstacleEditMode, setIsObstacleEditMode] = useState(false);
  const {
    imageInputRef,
    uploading,
    handleChooseImage,
    handleImageSelected,
  } = useCampaignMapImageUpload({
    campaignId,
    setForm,
    setError,
    setSuccess,
  });

  const selectedMap = sortedMaps.find((entry) => entry.id === selectedMapId) ?? null;
  const hasMapImage = Boolean(form.imageUrl.trim());
  const isConfigured =
    hasMapImage && Boolean(form.gridWidth.trim()) && Boolean(form.gridHeight.trim());
  const readyMaps = sortedMaps.filter((entry) => isMapReady(entry)).length;
  const calibrationPreview = useMemo(() => getCalibrationPreview(form), [form]);
  const previewGridWidth = parsePreviewInt(form.gridWidth);
  const previewGridHeight = parsePreviewInt(form.gridHeight);
  const previewBounds = calibrationPreview.bounds;
  const calibrationSummary =
    calibrationPreview.status === "full-image"
      ? t("campaignHome.mapPreviewUsingFullImage")
      : calibrationPreview.status === "custom" && previewBounds != null
        ? t("campaignHome.mapPreviewCustom").replace(
            "{bounds}",
            formatCalibrationBounds(previewBounds),
          )
        : t("campaignHome.mapPreviewInvalid");
  const gridSummary =
    previewGridWidth != null && previewGridHeight != null
      ? t("campaignHome.mapPreviewGridSummary")
          .replace("{cols}", String(previewGridWidth))
          .replace("{rows}", String(previewGridHeight))
      : t("campaignHome.mapPreviewGridMissing");

  useEffect(() => {
    const nextSelected = sortedMaps[0] ?? null;
    setSelectedMapId(nextSelected?.id ?? null);
    setIsCreatingNew(nextSelected == null);
    setForm(configToForm(nextSelected));
    setObstacleMap(buildObstacleMap(nextSelected));
    setIsObstacleEditMode(false);
    setError(null);
    setSuccess(null);
  }, [campaignId]);

  useEffect(() => {
    if (isCreatingNew) {
      return;
    }

    if (selectedMap != null) {
      setForm(configToForm(selectedMap));
      setObstacleMap(buildObstacleMap(selectedMap));
      return;
    }

    const fallback = sortedMaps[0] ?? null;
    setSelectedMapId(fallback?.id ?? null);
    setForm(configToForm(fallback));
    setObstacleMap(buildObstacleMap(fallback));
  }, [isCreatingNew, selectedMap, sortedMaps]);

  useEffect(() => {
    if (!isPreviewOpen) {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsPreviewOpen(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isPreviewOpen]);

  useEffect(() => {
    if (!hasMapImage && isPreviewOpen) {
      setIsPreviewOpen(false);
    }
  }, [hasMapImage, isPreviewOpen]);

  const resetEditorState = (config: CampaignMapConfig | null) => {
    setForm(configToForm(config));
    setObstacleMap(buildObstacleMap(config));
    setIsObstacleEditMode(false);
    setError(null);
    setSuccess(null);
  };

  const updateField = (field: keyof typeof form, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const handleEditMap = (map: CampaignMapConfig) => {
    setSelectedMapId(map.id);
    setIsCreatingNew(false);
    resetEditorState(map);
  };

  const handleCreateNew = () => {
    setSelectedMapId(null);
    setIsCreatingNew(true);
    setForm(EMPTY_FORM);
    setObstacleMap(new Map());
    setIsObstacleEditMode(false);
    setError(null);
    setSuccess(null);
  };

  const handleCellToggle = (x: number, y: number) => {
    const key = `${x}:${y}`;
    setObstacleMap((current) => {
      const next = new Map(current);
      if (next.get(key) === selectedPresetId) {
        next.delete(key);
      } else {
        next.set(key, selectedPresetId);
      }
      return next;
    });
  };

  const handleResetCalibration = () => {
    setForm((current) => ({
      ...current,
      calibrationX: "0",
      calibrationY: "0",
      calibrationWidth: "1",
      calibrationHeight: "1",
    }));
    setSuccess(null);
  };

  const handleClear = () => {
    resetEditorState(isCreatingNew ? null : selectedMap);
  };

  const handleSave = async () => {
    if (saving) return;

    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const gridWidth = normalizeOptionalInt(form.gridWidth, t("campaignHome.mapGridWidth"));
      const gridHeight = normalizeOptionalInt(
        form.gridHeight,
        t("campaignHome.mapGridHeight"),
      );

      const calibrationRawValues = [
        form.calibrationX,
        form.calibrationY,
        form.calibrationWidth,
        form.calibrationHeight,
      ].map((value) => value.trim());

      const someCalibrationFilled = calibrationRawValues.some(Boolean);
      const allCalibrationFilled = calibrationRawValues.every(Boolean);
      if (someCalibrationFilled && !allCalibrationFilled) {
        throw new Error(t("campaignHome.mapCalibrationPartialError"));
      }

      let calibration: CampaignMapConfig["calibration"] = null;
      if (allCalibrationFilled) {
        const x = normalizeOptionalFloat(form.calibrationX, t("campaignHome.mapCalibrationX"));
        const y = normalizeOptionalFloat(form.calibrationY, t("campaignHome.mapCalibrationY"));
        const width = normalizeOptionalFloat(
          form.calibrationWidth,
          t("campaignHome.mapCalibrationWidth"),
        );
        const height = normalizeOptionalFloat(
          form.calibrationHeight,
          t("campaignHome.mapCalibrationHeight"),
        );

        if (
          x == null ||
          y == null ||
          width == null ||
          height == null ||
          x < 0 ||
          y < 0 ||
          width <= 0 ||
          height <= 0 ||
          x + width > 1 ||
          y + height > 1
        ) {
          throw new Error(t("campaignHome.mapCalibrationBoundsError"));
        }

        calibration = { x, y, width, height };
      }

      const payload = {
        mapName: form.mapName.trim() || null,
        imageUrl: form.imageUrl.trim() || null,
        gridWidth,
        gridHeight,
        calibration,
        obstacles: serializeObstacleMap(obstacleMap),
      };

      const savedConfig = isCreatingNew
        ? await campaignsRepo.createMap(campaignId, payload)
        : await campaignsRepo.updateMap(campaignId, selectedMapId ?? "", payload);

      const nextMaps = isCreatingNew
        ? sortMaps([savedConfig, ...sortedMaps])
        : sortMaps(
            sortedMaps.map((entry) => (entry.id === savedConfig.id ? savedConfig : entry)),
          );

      onSaved(nextMaps);
      setSelectedMapId(savedConfig.id);
      setIsCreatingNew(false);
      setForm(configToForm(savedConfig));
      setObstacleMap(buildObstacleMap(savedConfig));
      setSuccess(t("campaignHome.mapSaved"));
    } catch (saveError) {
      setError(
        saveError instanceof Error ? saveError.message : t("campaignHome.mapSaveError"),
      );
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (selectedMap == null || deleting) {
      return;
    }
    if (!confirm(t("campaignHome.mapDeleteConfirm"))) {
      return;
    }

    setDeleting(true);
    setError(null);
    setSuccess(null);
    try {
      await campaignsRepo.deleteMap(campaignId, selectedMap.id);
      const nextMaps = sortMaps(sortedMaps.filter((entry) => entry.id !== selectedMap.id));
      const fallback = nextMaps[0] ?? null;
      onSaved(nextMaps);
      setSelectedMapId(fallback?.id ?? null);
      setIsCreatingNew(fallback == null);
      setForm(configToForm(fallback));
      setObstacleMap(buildObstacleMap(fallback));
      setSuccess(t("campaignHome.mapDeleted"));
    } catch (deleteError) {
      setError(
        deleteError instanceof Error
          ? deleteError.message
          : t("campaignHome.mapSaveError"),
      );
    } finally {
      setDeleting(false);
    }
  };

  return {
    imageInputRef,
    sortedMaps,
    selectedMapId,
    isCreatingNew,
    form,
    saving,
    uploading,
    deleting,
    isPreviewOpen,
    error,
    success,
    obstacleMap,
    selectedPresetId,
    isObstacleEditMode,
    hasMapImage,
    isConfigured,
    readyMaps,
    calibrationPreview,
    previewGridWidth,
    previewGridHeight,
    calibrationSummary,
    gridSummary,
    handleEditMap,
    handleCreateNew,
    handleCellToggle,
    handleChooseImage,
    handleImageSelected,
    handleResetCalibration,
    handleClear,
    handleSave,
    handleDelete,
    setIsPreviewOpen,
    setSelectedPresetId,
    setIsObstacleEditMode,
    updateField,
  };
}
