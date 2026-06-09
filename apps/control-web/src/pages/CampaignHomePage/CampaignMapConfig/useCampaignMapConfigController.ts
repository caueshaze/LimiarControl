import { useEffect, useMemo, useState } from "react";
import type { CampaignMapConfig } from "../../../entities/campaign";
import { campaignsRepo } from "../../../shared/api/campaignsRepo";
import { useLocale } from "../../../shared/hooks/useLocale";
import type {
  CalibrationPreviewBounds,
  EditorMode,
  FormState,
  Props,
} from "./types";
import { useCampaignMapObstacleEditor } from "./useCampaignMapObstacleEditor";
import { useCampaignMapImageUpload } from "./useCampaignMapImageUpload";
import {
  EMPTY_FORM,
  buildEdgeObstacleMap,
  buildObstacleMap,
  configToForm,
  getCalibrationPreview,
  isMapReady,
  normalizeOptionalFloat,
  normalizeOptionalInt,
  parsePreviewFloat,
  parsePreviewInt,
  serializeEdgeObstacleMap,
  serializeObstacleMap,
  sortMaps,
} from "./utils";

const presetMapsEqual = (
  left: ReadonlyMap<string, string>,
  right: ReadonlyMap<string, string>,
) => {
  if (left.size !== right.size) return false;
  for (const [key, value] of left) {
    if (right.get(key) !== value) return false;
  }
  return true;
};
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
  const [isCreatingNew, setIsCreatingNew] = useState(false);
  // True while editing an existing map in the full editor view. When both this
  // and isCreatingNew are false we show only the catalog (the list of maps).
  const [isEditing, setIsEditing] = useState(false);
  const [form, setForm] = useState(() => configToForm(sortedMaps[0] ?? null));
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [editorMode, setEditorMode] = useState<EditorMode>("calibrate");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const obstacleEditor = useCampaignMapObstacleEditor(sortedMaps[0] ?? null);
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
  const previewCellWidth = parsePreviewFloat(form.cellWidth);
  const previewCellHeight = parsePreviewFloat(form.cellHeight);
  const calibrationSummary =
    calibrationPreview.status === "full-image"
      ? t("campaignHome.mapPreviewUsingFullImage")
      : calibrationPreview.status === "custom" &&
          previewBounds != null &&
          previewCellWidth != null &&
          previewCellHeight != null
        ? t("campaignHome.mapPreviewCellSummary")
            .replace("{cellW}", `${(previewCellWidth * 100).toFixed(1)}%`)
            .replace("{cellH}", `${(previewCellHeight * 100).toFixed(1)}%`)
            .replace("{extentW}", `${(previewBounds.width * 100).toFixed(0)}%`)
            .replace("{extentH}", `${(previewBounds.height * 100).toFixed(0)}%`)
        : t("campaignHome.mapPreviewInvalid");
  const gridSummary =
    previewGridWidth != null && previewGridHeight != null
      ? t("campaignHome.mapPreviewGridSummary")
          .replace("{cols}", String(previewGridWidth))
          .replace("{rows}", String(previewGridHeight))
      : t("campaignHome.mapPreviewGridMissing");

  const isCalibrating = editorMode === "calibrate";
  const isObstacleEditMode = editorMode === "obstacles";

  const baselineConfig = isCreatingNew ? null : selectedMap;
  const baselineForm = useMemo(() => configToForm(baselineConfig), [baselineConfig]);
  const isDirty = useMemo(() => {
    const formChanged = (Object.keys(form) as (keyof FormState)[]).some(
      (key) => form[key] !== baselineForm[key],
    );
    if (formChanged) return true;
    return (
      !presetMapsEqual(obstacleEditor.obstacleMap, buildObstacleMap(baselineConfig)) ||
      !presetMapsEqual(
        obstacleEditor.edgeObstacleMap,
        buildEdgeObstacleMap(baselineConfig),
      )
    );
  }, [form, baselineForm, baselineConfig, obstacleEditor.obstacleMap, obstacleEditor.edgeObstacleMap]);

  // The reference (top-left) cell the user manipulates while calibrating. Derived
  // from the previewed grid extent ÷ count so it always reflects the current cell
  // size (including the full-image default).
  const calibrationCell =
    previewBounds != null && previewGridWidth != null && previewGridHeight != null
      ? {
          x: previewBounds.x,
          y: previewBounds.y,
          width: previewBounds.width / previewGridWidth,
          height: previewBounds.height / previewGridHeight,
        }
      : null;

  const setCalibrationBounds = (cell: CalibrationPreviewBounds) => {
    // The dragged rectangle IS one cell; the grid replicates it by the count.
    setForm((current) => ({
      ...current,
      calibrationX: String(cell.x),
      calibrationY: String(cell.y),
      cellWidth: String(cell.width),
      cellHeight: String(cell.height),
    }));
  };

  useEffect(() => {
    const nextSelected = sortedMaps[0] ?? null;
    setSelectedMapId(nextSelected?.id ?? null);
    setIsCreatingNew(false);
    setIsEditing(false);
    setForm(configToForm(nextSelected));
    obstacleEditor.resetFromConfig(nextSelected);
    setError(null);
    setSuccess(null);
  }, [campaignId]);

  useEffect(() => {
    if (isCreatingNew || !isEditing) {
      return;
    }

    if (selectedMap != null) {
      setForm(configToForm(selectedMap));
      obstacleEditor.resetFromConfig(selectedMap);
      return;
    }

    const fallback = sortedMaps[0] ?? null;
    setSelectedMapId(fallback?.id ?? null);
    setForm(configToForm(fallback));
    obstacleEditor.resetFromConfig(fallback);
  }, [isCreatingNew, isEditing, selectedMap, sortedMaps]);

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
    obstacleEditor.resetFromConfig(config);
    setError(null);
    setSuccess(null);
  };

  const updateField = (field: keyof typeof form, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const handleEditMap = (map: CampaignMapConfig) => {
    setSelectedMapId(map.id);
    setIsCreatingNew(false);
    setIsEditing(true);
    resetEditorState(map);
  };

  // Open the expanded preview for a catalog map without entering the editor.
  const handlePreviewMap = (map: CampaignMapConfig) => {
    setSelectedMapId(map.id);
    resetEditorState(map);
    setIsPreviewOpen(true);
  };

  // Back to the catalog: show only the list, no editor.
  const handleShowList = () => {
    setIsCreatingNew(false);
    setIsEditing(false);
    resetEditorState(selectedMap);
  };

  const handleCreateNew = () => {
    setSelectedMapId(null);
    setIsCreatingNew(true);
    setIsEditing(false);
    setForm(EMPTY_FORM);
    obstacleEditor.clearAll();
    setError(null);
    setSuccess(null);
  };

  const handleResetCalibration = () => {
    setForm((current) => {
      // Fill the whole image: origin at 0,0 and a cell that tiles exactly to the
      // current count (cell = 1 / count). Falls back to clearing if no count.
      const cols = parsePreviewInt(current.gridWidth);
      const rows = parsePreviewInt(current.gridHeight);
      return {
        ...current,
        calibrationX: "0",
        calibrationY: "0",
        cellWidth: cols != null ? String(1 / cols) : "",
        cellHeight: rows != null ? String(1 / rows) : "",
      };
    });
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

      // Cell size is the editor's source of truth; the persisted calibration
      // rectangle is derived as count × cell size (keeps the backend model).
      const cellRawValues = [form.cellWidth, form.cellHeight].map((value) =>
        value.trim(),
      );
      const someCellFilled = cellRawValues.some(Boolean);
      const allCellFilled = cellRawValues.every(Boolean);
      if (someCellFilled && !allCellFilled) {
        throw new Error(t("campaignHome.mapCalibrationPartialError"));
      }

      let calibration: CampaignMapConfig["calibration"] = null;
      if (allCellFilled) {
        if (gridWidth == null || gridHeight == null) {
          throw new Error(t("campaignHome.mapCalibrationNeedsGridError"));
        }
        const x = normalizeOptionalFloat(form.calibrationX, t("campaignHome.mapCalibration")) ?? 0;
        const y = normalizeOptionalFloat(form.calibrationY, t("campaignHome.mapCalibration")) ?? 0;
        const cellWidth = normalizeOptionalFloat(form.cellWidth, t("campaignHome.mapCellWidth"));
        const cellHeight = normalizeOptionalFloat(form.cellHeight, t("campaignHome.mapCellHeight"));

        if (cellWidth == null || cellHeight == null || cellWidth <= 0 || cellHeight <= 0) {
          throw new Error(t("campaignHome.mapCalibrationBoundsError"));
        }

        const width = gridWidth * cellWidth;
        const height = gridHeight * cellHeight;

        if (x < 0 || y < 0 || x + width > 1 || y + height > 1) {
          throw new Error(t("campaignHome.mapCalibrationOverflowError"));
        }

        calibration = { x, y, width, height };
      }

      const payload = {
        mapName: form.mapName.trim() || null,
        imageUrl: form.imageUrl.trim() || null,
        gridWidth,
        gridHeight,
        calibration,
        obstacles: serializeObstacleMap(obstacleEditor.obstacleMap),
        edgeObstacles: serializeEdgeObstacleMap(obstacleEditor.edgeObstacleMap),
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
      setIsEditing(true);
      setForm(configToForm(savedConfig));
      obstacleEditor.resetFromConfig(savedConfig);
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
      setIsCreatingNew(false);
      setIsEditing(false);
      setForm(configToForm(fallback));
      obstacleEditor.resetFromConfig(fallback);
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
    isEditing,
    form,
    saving,
    uploading,
    deleting,
    isPreviewOpen,
    editorMode,
    setEditorMode,
    isCalibrating,
    calibrationCell,
    setCalibrationBounds,
    isDirty,
    error,
    success,
    ...obstacleEditor,
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
    handlePreviewMap,
    handleShowList,
    handleCreateNew,
    handleChooseImage,
    handleImageSelected,
    handleResetCalibration,
    handleClear,
    handleSave,
    handleDelete,
    setIsPreviewOpen,
    updateField,
  };
}
