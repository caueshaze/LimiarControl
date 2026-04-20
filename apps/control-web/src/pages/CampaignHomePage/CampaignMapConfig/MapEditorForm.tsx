import type { ChangeEvent, RefObject } from "react";
import { useLocale } from "../../../shared/hooks/useLocale";
import type { FormState } from "./types";

type FileInputChangeEvent = ChangeEvent<HTMLInputElement>;

type Props = {
  form: FormState;
  isCreatingNew: boolean;
  isConfigured: boolean;
  uploading: boolean;
  deleting: boolean;
  saving: boolean;
  error: string | null;
  success: string | null;
  imageInputRef: RefObject<HTMLInputElement | null>;
  acceptedImageTypes: string;
  calibrationFieldClassName: string;
  onUpdateField: (field: keyof FormState, value: string) => void;
  onChooseImage: () => void;
  onImageSelected: (event: FileInputChangeEvent) => void;
  onResetCalibration: () => void;
  onClear: () => void;
  onDelete: () => void;
  onSave: () => void;
};

export const MapEditorForm = ({
  form,
  isCreatingNew,
  isConfigured,
  uploading,
  deleting,
  saving,
  error,
  success,
  imageInputRef,
  acceptedImageTypes,
  calibrationFieldClassName,
  onUpdateField,
  onChooseImage,
  onImageSelected,
  onResetCalibration,
  onClear,
  onDelete,
  onSave,
}: Props) => {
  const { t } = useLocale();
  const hasMapImage = Boolean(form.imageUrl.trim());

  return (
    <div className="space-y-4">
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
            onClick={onChooseImage}
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
            onClick={onClear}
            className="rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-300 hover:border-slate-500"
          >
            {t("campaignHome.mapClear")}
          </button>
          {!isCreatingNew && (
            <button
              type="button"
              onClick={onDelete}
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
          accept={acceptedImageTypes}
          onChange={onImageSelected}
          className="hidden"
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <label className="block w-full space-y-2 md:col-span-2">
          <span className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">
            {t("campaignHome.mapName")}
          </span>
          <input
            value={form.mapName}
            onChange={(event) => onUpdateField("mapName", event.target.value)}
            placeholder={t("campaignHome.mapNamePlaceholder")}
            className="w-full rounded-2xl border border-slate-700 bg-slate-950/70 px-4 py-3 text-sm text-slate-100 focus:border-limiar-500 focus:outline-none"
          />
        </label>

        <label className="block w-full space-y-2">
          <span className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">
            {t("campaignHome.mapGridWidth")}
          </span>
          <input
            value={form.gridWidth}
            onChange={(event) => onUpdateField("gridWidth", event.target.value)}
            type="number"
            min={1}
            max={150}
            className="w-full rounded-2xl border border-slate-700 bg-slate-950/70 px-4 py-3 text-sm text-slate-100 focus:border-limiar-500 focus:outline-none"
          />
        </label>

        <label className="block w-full space-y-2">
          <span className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">
            {t("campaignHome.mapGridHeight")}
          </span>
          <input
            value={form.gridHeight}
            onChange={(event) => onUpdateField("gridHeight", event.target.value)}
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
            onClick={onResetCalibration}
            className="self-start rounded-full border border-slate-700 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-300 hover:border-slate-500"
          >
            {t("campaignHome.mapResetBounds")}
          </button>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <label className="block w-full space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
              {t("campaignHome.mapCalibrationX")}
            </span>
            <input
              value={form.calibrationX}
              onChange={(event) => onUpdateField("calibrationX", event.target.value)}
              type="number"
              min={0}
              max={1}
              step="0.001"
              className={calibrationFieldClassName}
            />
          </label>
          <label className="block w-full space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
              {t("campaignHome.mapCalibrationY")}
            </span>
            <input
              value={form.calibrationY}
              onChange={(event) => onUpdateField("calibrationY", event.target.value)}
              type="number"
              min={0}
              max={1}
              step="0.001"
              className={calibrationFieldClassName}
            />
          </label>
          <label className="block w-full space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
              {t("campaignHome.mapCalibrationWidth")}
            </span>
            <input
              value={form.calibrationWidth}
              onChange={(event) => onUpdateField("calibrationWidth", event.target.value)}
              type="number"
              min={0}
              max={1}
              step="0.001"
              className={calibrationFieldClassName}
            />
          </label>
          <label className="block w-full space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
              {t("campaignHome.mapCalibrationHeight")}
            </span>
            <input
              value={form.calibrationHeight}
              onChange={(event) => onUpdateField("calibrationHeight", event.target.value)}
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
          onClick={onSave}
          disabled={saving || uploading || deleting}
          className="rounded-full bg-limiar-500 px-5 py-2 text-xs font-bold uppercase tracking-[0.2em] text-white hover:bg-limiar-400 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {saving ? t("campaignHome.mapSaving") : t("campaignHome.mapSave")}
        </button>
      </div>
    </div>
  );
};
