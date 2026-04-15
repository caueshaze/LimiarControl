import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
} from "react";
import type { CampaignMapConfig } from "../../../entities/campaign";
import { campaignsRepo } from "../../../shared/api/campaignsRepo";
import { uploadRepo } from "../../../shared/api/uploadRepo";
import { useLocale } from "../../../shared/hooks/useLocale";
import { ManagedImage } from "../../../shared/ui";
import type { FormState, Props } from "./types";
import {
  EMPTY_FORM,
  configToForm,
  getCalibrationPreview,
  isMapReady,
  normalizeOptionalFloat,
  normalizeOptionalInt,
  parsePreviewInt,
  sortMaps,
} from "./utils";
import { MapPreviewSurface } from "./MapPreviewSurface";
import { MapListWidget } from "./MapListWidget";

const ACCEPTED_IMAGE_TYPES = "image/jpeg,image/png,image/webp,image/gif";
const MAX_IMAGE_MB = 30;
const MAX_IMAGE_BYTES = MAX_IMAGE_MB * 1024 * 1024;
const calibrationFieldClassName = "rounded-2xl border border-slate-700 bg-slate-950/70 px-3 py-2 text-sm text-slate-100 focus:border-limiar-500 focus:outline-none";

export const CampaignMapConfigCard = ({
  campaignId,
  initialMaps,
  onSaved,
}: Props) => {
  const { t } = useLocale();
  const imageInputRef = useRef<HTMLInputElement>(null);
  const sortedMaps = useMemo(() => sortMaps(initialMaps), [initialMaps]);
  const [selectedMapId, setSelectedMapId] = useState<string | null>(
    sortedMaps[0]?.id ?? null,
  );
  const [isCreatingNew, setIsCreatingNew] = useState(sortedMaps.length === 0);
  const [form, setForm] = useState<FormState>(() => configToForm(sortedMaps[0] ?? null));
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  // Obstacle editing state — tracks 0-based cell keys "x:y"
  const [blockedCellSet, setBlockedCellSet] = useState<Set<string>>(
    () => new Set((sortedMaps[0]?.blockedCells ?? []).map((c) => `${c.x}:${c.y}`)),
  );
  const [isObstacleEditMode, setIsObstacleEditMode] = useState(false);

  const selectedMap = sortedMaps.find((entry) => entry.id === selectedMapId) ?? null;

  useEffect(() => {
    const nextSelected = sortedMaps[0] ?? null;
    setSelectedMapId(nextSelected?.id ?? null);
    setIsCreatingNew(nextSelected == null);
    setForm(configToForm(nextSelected));
    setBlockedCellSet(new Set((nextSelected?.blockedCells ?? []).map((c) => `${c.x}:${c.y}`)));
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
      setBlockedCellSet(new Set((selectedMap.blockedCells ?? []).map((c) => `${c.x}:${c.y}`)));
      return;
    }

    const fallback = sortedMaps[0] ?? null;
    setSelectedMapId(fallback?.id ?? null);
    setForm(configToForm(fallback));
    setBlockedCellSet(new Set((fallback?.blockedCells ?? []).map((c) => `${c.x}:${c.y}`)));
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

  const handleEditMap = (map: CampaignMapConfig) => {
    setSelectedMapId(map.id);
    setIsCreatingNew(false);
    setForm(configToForm(map));
    setBlockedCellSet(new Set((map.blockedCells ?? []).map((c) => `${c.x}:${c.y}`)));
    setIsObstacleEditMode(false);
    setError(null);
    setSuccess(null);
  };

  const handleCreateNew = () => {
    setSelectedMapId(null);
    setIsCreatingNew(true);
    setForm(EMPTY_FORM);
    setBlockedCellSet(new Set());
    setIsObstacleEditMode(false);
    setError(null);
    setSuccess(null);
  };

  const handleCellToggle = (x: number, y: number) => {
    const key = `${x}:${y}`;
    setBlockedCellSet((current) => {
      const next = new Set(current);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const updateField = (field: keyof FormState, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const handleChooseImage = () => {
    imageInputRef.current?.click();
  };

  const handleImageSelected = async (event: ChangeEvent<HTMLInputElement>) => {
    const input = event.currentTarget;
    const file = input.files?.[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      setError(t("campaignHome.mapImageTypeError"));
      input.value = "";
      return;
    }

    if (file.size > MAX_IMAGE_BYTES) {
      setError(
        t("campaignHome.mapImageSizeError").replace(
          "{maxMb}",
          String(MAX_IMAGE_MB),
        ),
      );
      input.value = "";
      return;
    }

    setUploading(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await uploadRepo.uploadImage({
        file,
        kind: "campaign_map",
        campaignId,
      });
      setForm((current) => ({ ...current, imageUrl: result.url }));
    } catch (uploadError) {
      setError(
        uploadError instanceof Error
          ? uploadError.message
          : t("campaignHome.mapUploadError"),
      );
    } finally {
      setUploading(false);
      input.value = "";
    }
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
    const source = isCreatingNew ? null : selectedMap;
    setForm(configToForm(source));
    setBlockedCellSet(new Set((source?.blockedCells ?? []).map((c) => `${c.x}:${c.y}`)));
    setIsObstacleEditMode(false);
    setError(null);
    setSuccess(null);
  };

  const handleSave = async () => {
    if (saving) return;

    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const gridWidth = normalizeOptionalInt(
        form.gridWidth,
        t("campaignHome.mapGridWidth"),
      );
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
        const x = normalizeOptionalFloat(
          form.calibrationX,
          t("campaignHome.mapCalibrationX"),
        );
        const y = normalizeOptionalFloat(
          form.calibrationY,
          t("campaignHome.mapCalibrationY"),
        );
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

      const blockedCells = Array.from(blockedCellSet).map((key) => {
        const [x, y] = key.split(":").map(Number);
        return { x, y };
      });

      const payload = {
        mapName: form.mapName.trim() || null,
        imageUrl: form.imageUrl.trim() || null,
        gridWidth,
        gridHeight,
        calibration,
        blockedCells,
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
      setSuccess(t("campaignHome.mapSaved"));
    } catch (saveError) {
      setError(
        saveError instanceof Error
          ? saveError.message
          : t("campaignHome.mapSaveError"),
      );
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (selectedMap == null || deleting) {
      return;
    }
    const confirmed = confirm(t("campaignHome.mapDeleteConfirm"));
    if (!confirmed) {
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
            `X ${previewBounds.x.toFixed(3)} | Y ${previewBounds.y.toFixed(3)} | W ${previewBounds.width.toFixed(3)} | H ${previewBounds.height.toFixed(3)}`,
          )
        : t("campaignHome.mapPreviewInvalid");
  const gridSummary =
    previewGridWidth != null && previewGridHeight != null
      ? t("campaignHome.mapPreviewGridSummary")
          .replace("{cols}", String(previewGridWidth))
          .replace("{rows}", String(previewGridHeight))
      : t("campaignHome.mapPreviewGridMissing");

  useEffect(() => {
    if (!hasMapImage && isPreviewOpen) {
      setIsPreviewOpen(false);
    }
  }, [hasMapImage, isPreviewOpen]);

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
            {`${readyMaps}/${sortedMaps.length} ${t("campaignHome.mapStatusReady")}`}
          </span>
          <button
            type="button"
            onClick={handleCreateNew}
            className="rounded-full border border-limiar-500/30 bg-limiar-500/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-limiar-100 hover:border-limiar-400/60"
          >
            {t("campaignHome.mapNew")}
          </button>
        </div>
        </div>

        <div className="mt-5 grid gap-3 xl:grid-cols-3">
        <MapListWidget
          maps={sortedMaps}
          selectedMapId={selectedMapId}
          isCreatingNew={isCreatingNew}
          onEditMap={handleEditMap}
        />
        </div>

        <div className="mt-6 grid gap-5 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,1.4fr)]">
        <div className="space-y-3">
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
                      onClick={() => setIsObstacleEditMode((v) => !v)}
                      className={`rounded-full border px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] ${
                        isObstacleEditMode
                          ? "border-rose-500/50 bg-rose-500/15 text-rose-200"
                          : "border-slate-700 text-slate-300 hover:border-rose-500/30"
                      }`}
                    >
                      {isObstacleEditMode ? "Concluir edição" : "Editar obstáculos"}
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => setIsPreviewOpen(true)}
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
                  imageUrl={form.imageUrl}
                  alt={form.mapName || t("campaignHome.mapPreviewAlt")}
                  bounds={previewBounds}
                  gridWidth={previewGridWidth}
                  gridHeight={previewGridHeight}
                  imageClassName="block w-full"
                  invalidMessage={t("campaignHome.mapPreviewInvalid")}
                  hoverHint={isObstacleEditMode ? "Clique para marcar/desmarcar célula bloqueada" : t("campaignHome.mapPreviewHoverHint")}
                  hoverMissingGrid={t("campaignHome.mapPreviewHoverMissingGrid")}
                  hoverCellLabel={t("campaignHome.mapPreviewHoverCell")}
                  blockedCellSet={blockedCellSet}
                  onCellToggle={isObstacleEditMode ? handleCellToggle : undefined}
                />
              ) : (
                <div className="flex h-72 items-center justify-center px-6 text-center text-sm text-slate-500">
                  {t("campaignHome.mapPreviewEmpty")}
                </div>
              )}
            </div>

            {isObstacleEditMode && (
              <div className="mt-3 rounded-2xl border border-rose-500/20 bg-rose-500/8 px-4 py-3 text-xs text-rose-200">
                Modo obstáculos ativo — clique nas células do mapa para marcar ou desmarcar terreno bloqueado.
                {blockedCellSet.size > 0 && (
                  <span className="ml-2 font-semibold">{blockedCellSet.size} célula{blockedCellSet.size !== 1 ? "s" : ""} bloqueada{blockedCellSet.size !== 1 ? "s" : ""}.</span>
                )}
              </div>
            )}

            <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                {t("campaignHome.mapPreviewLegend")}
              </p>
              <p className="mt-2 text-sm text-slate-200">{calibrationSummary}</p>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
                  {isCreatingNew
                    ? t("campaignHome.mapEditorCreate")
                    : t("campaignHome.mapEditorEdit")}
                </p>
                <p className="mt-2 text-sm text-slate-300">
                  {t("campaignHome.mapImageHint")}
                </p>
              </div>
              <span
                className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] ${
                  isConfigured
                    ? "border border-emerald-400/25 bg-emerald-400/10 text-emerald-200"
                    : "border border-amber-300/20 bg-amber-300/10 text-amber-100"
                }`}
              >
                {isConfigured
                  ? t("campaignHome.mapStatusReady")
                  : t("campaignHome.mapStatusDraft")}
              </span>
            </div>
            <div className="mt-4 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={handleChooseImage}
                disabled={uploading}
                className="rounded-full border border-slate-700 bg-slate-900/70 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-100 hover:border-limiar-500/50 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {uploading
                  ? t("campaignHome.mapUploading")
                  : hasMapImage
                    ? t("campaignHome.mapReplaceImage")
                    : t("campaignHome.mapChooseImage")}
              </button>
              <button
                type="button"
                onClick={handleClear}
                className="rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-300 hover:border-slate-500"
              >
                {t("campaignHome.mapClear")}
              </button>
              {!isCreatingNew && (
                <button
                  type="button"
                  onClick={() => void handleDelete()}
                  disabled={deleting}
                  className="rounded-full border border-rose-500/30 bg-rose-500/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-rose-200 hover:bg-rose-500/20 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {deleting
                    ? t("campaignHome.mapDeleting")
                    : t("campaignHome.mapDelete")}
                </button>
              )}
            </div>
            <input
              ref={imageInputRef}
              type="file"
              accept={ACCEPTED_IMAGE_TYPES}
              onChange={handleImageSelected}
              className="hidden"
            />
          </div>
        </div>

        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">
                {t("campaignHome.mapName")}
              </span>
              <input
                value={form.mapName}
                onChange={(event) => updateField("mapName", event.target.value)}
                placeholder={t("campaignHome.mapNamePlaceholder")}
                className="w-full rounded-2xl border border-slate-700 bg-slate-950/70 px-4 py-3 text-sm text-slate-100 focus:border-limiar-500 focus:outline-none"
              />
            </label>

            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">
                {t("campaignHome.mapGridWidth")}
              </span>
              <input
                value={form.gridWidth}
                onChange={(event) => updateField("gridWidth", event.target.value)}
                type="number"
                min={1}
                max={150}
                className="w-full rounded-2xl border border-slate-700 bg-slate-950/70 px-4 py-3 text-sm text-slate-100 focus:border-limiar-500 focus:outline-none"
              />
            </label>

            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">
                {t("campaignHome.mapGridHeight")}
              </span>
              <input
                value={form.gridHeight}
                onChange={(event) => updateField("gridHeight", event.target.value)}
                type="number"
                min={1}
                max={150}
                className="w-full rounded-2xl border border-slate-700 bg-slate-950/70 px-4 py-3 text-sm text-slate-100 focus:border-limiar-500 focus:outline-none"
              />
            </label>
          </div>

          <div className="rounded-3xl border border-slate-800 bg-slate-950/60 p-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">
                  {t("campaignHome.mapCalibration")}
                </p>
                <p className="mt-2 text-sm leading-7 text-slate-300">
                  {t("campaignHome.mapCalibrationHint")}
                </p>
              </div>
              <button
                type="button"
                onClick={handleResetCalibration}
                className="rounded-full border border-slate-700 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-300 hover:border-slate-500"
              >
                {t("campaignHome.mapResetBounds")}
              </button>
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <label className="space-y-2">
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                  {t("campaignHome.mapCalibrationX")}
                </span>
                <input
                  value={form.calibrationX}
                  onChange={(event) =>
                    updateField("calibrationX", event.target.value)
                  }
                  type="number"
                  min={0}
                  max={1}
                  step="0.001"
                  className={calibrationFieldClassName}
                />
              </label>
              <label className="space-y-2">
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                  {t("campaignHome.mapCalibrationY")}
                </span>
                <input
                  value={form.calibrationY}
                  onChange={(event) =>
                    updateField("calibrationY", event.target.value)
                  }
                  type="number"
                  min={0}
                  max={1}
                  step="0.001"
                  className={calibrationFieldClassName}
                />
              </label>
              <label className="space-y-2">
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                  {t("campaignHome.mapCalibrationWidth")}
                </span>
                <input
                  value={form.calibrationWidth}
                  onChange={(event) =>
                    updateField("calibrationWidth", event.target.value)
                  }
                  type="number"
                  min={0}
                  max={1}
                  step="0.001"
                  className={calibrationFieldClassName}
                />
              </label>
              <label className="space-y-2">
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                  {t("campaignHome.mapCalibrationHeight")}
                </span>
                <input
                  value={form.calibrationHeight}
                  onChange={(event) =>
                    updateField("calibrationHeight", event.target.value)
                  }
                  type="number"
                  min={0}
                  max={1}
                  step="0.001"
                  className={calibrationFieldClassName}
                />
              </label>
            </div>
          </div>

          {error && (
            <p className="rounded-2xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
              {error}
            </p>
          )}
          {success && (
            <p className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
              {success}
            </p>
          )}

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={handleSave}
              disabled={saving || uploading || deleting}
              className="rounded-full bg-limiar-500 px-5 py-2 text-xs font-bold uppercase tracking-[0.2em] text-white hover:bg-limiar-400 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {saving ? t("campaignHome.mapSaving") : t("campaignHome.mapSave")}
            </button>
          </div>
        </div>
        </div>
      </div>

      {isPreviewOpen && hasMapImage && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 px-4 py-6 backdrop-blur-sm"
          onClick={() => setIsPreviewOpen(false)}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-label={t("campaignHome.mapPreviewDialogTitle")}
            onClick={(event) => event.stopPropagation()}
            className="w-full max-w-6xl rounded-[2rem] border border-slate-800 bg-slate-950/95 p-5 shadow-2xl shadow-black/40"
          >
            <div className="flex flex-col gap-3 border-b border-white/8 pb-4 md:flex-row md:items-start md:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
                  {t("campaignHome.mapPreviewDialogTitle")}
                </p>
                <h4 className="mt-2 text-lg font-semibold text-white">
                  {form.mapName.trim() || t("campaignHome.mapUntitled")}
                </h4>
                <p className="mt-2 text-sm text-slate-300">
                  {isObstacleEditMode
                    ? "Clique nas células para marcar ou desmarcar terreno bloqueado. Salve o mapa para persistir."
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
                    onClick={() => setIsObstacleEditMode((v) => !v)}
                    className={`rounded-full border px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] ${
                      isObstacleEditMode
                        ? "border-rose-500/50 bg-rose-500/15 text-rose-200"
                        : "border-slate-700 text-slate-300 hover:border-rose-500/30"
                    }`}
                  >
                    {isObstacleEditMode ? "Concluir edição" : "Editar obstáculos"}
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setIsPreviewOpen(false)}
                  className="rounded-full border border-slate-700 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-200 hover:border-slate-500"
                >
                  {t("campaignHome.mapPreviewClose")}
                </button>
              </div>
            </div>

            {isObstacleEditMode && (
              <div className="mt-4 rounded-2xl border border-rose-500/20 bg-rose-500/8 px-4 py-3 text-xs text-rose-200">
                Modo obstáculos ativo. Células em vermelho estão bloqueadas para movimento.
                {blockedCellSet.size > 0 && (
                  <span className="ml-2 font-semibold">{blockedCellSet.size} célula{blockedCellSet.size !== 1 ? "s" : ""} bloqueada{blockedCellSet.size !== 1 ? "s" : ""}.</span>
                )}
                {" "}Clique em <strong>"Salvar mapa"</strong> para persistir.
              </div>
            )}

            <div className="mt-5 rounded-3xl border border-slate-800 bg-slate-950/70 p-4">
              <div className="flex justify-center overflow-auto">
                <div className="inline-block max-w-full overflow-hidden rounded-2xl border border-slate-800 bg-slate-950">
                  <MapPreviewSurface
                    imageUrl={form.imageUrl}
                    alt={form.mapName || t("campaignHome.mapPreviewAlt")}
                    bounds={previewBounds}
                    gridWidth={previewGridWidth}
                    gridHeight={previewGridHeight}
                    imageClassName="block max-h-[72vh] max-w-full"
                    invalidMessage={t("campaignHome.mapPreviewInvalid")}
                    hoverHint={isObstacleEditMode ? "Clique para marcar/desmarcar célula bloqueada" : t("campaignHome.mapPreviewHoverHint")}
                    hoverMissingGrid={t("campaignHome.mapPreviewHoverMissingGrid")}
                    hoverCellLabel={t("campaignHome.mapPreviewHoverCell")}
                    blockedCellSet={blockedCellSet}
                    onCellToggle={isObstacleEditMode ? handleCellToggle : undefined}
                  />
                </div>
              </div>
            </div>

            <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
              <div className="rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3 flex-1">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                  {t("campaignHome.mapPreviewLegend")}
                </p>
                <p className="mt-2 text-sm text-slate-200">{calibrationSummary}</p>
              </div>
              <button
                type="button"
                onClick={() => { void handleSave(); setIsPreviewOpen(false); }}
                disabled={saving || uploading || deleting}
                className="rounded-full bg-limiar-500 px-5 py-2 text-xs font-bold uppercase tracking-[0.2em] text-white hover:bg-limiar-400 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {saving ? t("campaignHome.mapSaving") : t("campaignHome.mapSave")}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
