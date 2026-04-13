import type { CampaignMapConfig } from "../../../entities/campaign";
import type { FormState, CalibrationPreviewState, HoveredGridCell } from "./types";

export const EMPTY_FORM: FormState = {
  mapName: "",
  imageUrl: "",
  gridWidth: "",
  gridHeight: "",
  calibrationX: "",
  calibrationY: "",
  calibrationWidth: "",
  calibrationHeight: "",
};

export const configToForm = (config: CampaignMapConfig | null | undefined): FormState => ({
  mapName: config?.mapName ?? "",
  imageUrl: config?.imageUrl ?? "",
  gridWidth: config?.gridWidth != null ? String(config.gridWidth) : "",
  gridHeight: config?.gridHeight != null ? String(config.gridHeight) : "",
  calibrationX: config?.calibration?.x != null ? String(config.calibration.x) : "",
  calibrationY: config?.calibration?.y != null ? String(config.calibration.y) : "",
  calibrationWidth:
    config?.calibration?.width != null ? String(config.calibration.width) : "",
  calibrationHeight:
    config?.calibration?.height != null ? String(config.calibration.height) : "",
});

export const normalizeOptionalInt = (value: string, label: string): number | null => {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parsed = Number.parseInt(trimmed, 10);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    throw new Error(`${label} precisa ser um inteiro positivo.`);
  }
  return parsed;
};

export const normalizeOptionalFloat = (value: string, label: string): number | null => {
  const trimmed = value.trim().replace(",", ".");
  if (!trimmed) return null;
  const parsed = Number.parseFloat(trimmed);
  if (!Number.isFinite(parsed)) {
    throw new Error(`${label} precisa ser um numero valido.`);
  }
  return parsed;
};

export const parsePreviewInt = (value: string): number | null => {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parsed = Number.parseInt(trimmed, 10);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return null;
  }
  return parsed;
};

export const parsePreviewFloat = (value: string): number | null => {
  const trimmed = value.trim().replace(",", ".");
  if (!trimmed) return null;
  const parsed = Number.parseFloat(trimmed);
  if (!Number.isFinite(parsed)) {
    return null;
  }
  return parsed;
};

export const getCalibrationPreview = (form: FormState): CalibrationPreviewState => {
  const x = parsePreviewFloat(form.calibrationX);
  const y = parsePreviewFloat(form.calibrationY);
  const width = parsePreviewFloat(form.calibrationWidth);
  const height = parsePreviewFloat(form.calibrationHeight);

  if (x == null && y == null && width == null && height == null) {
    return {
      status: "full-image",
      bounds: { x: 0, y: 0, width: 1, height: 1 },
    };
  }

  if (x == null || y == null || width == null || height == null) {
    return { status: "invalid", bounds: null };
  }

  if (
    x < 0 ||
    y < 0 ||
    width <= 0 ||
    height <= 0 ||
    x + width > 1 ||
    y + height > 1
  ) {
    return { status: "invalid", bounds: null };
  }

  return {
    status: "custom",
    bounds: { x, y, width, height },
  };
};

export const isMapReady = (config: CampaignMapConfig | null | undefined) =>
  Boolean(config?.imageUrl) &&
  config?.gridWidth != null &&
  config?.gridHeight != null;

export const sortMaps = (maps: CampaignMapConfig[]) =>
  [...maps].sort((left, right) => {
    const leftValue = Date.parse(left.updatedAt ?? left.createdAt);
    const rightValue = Date.parse(right.updatedAt ?? right.createdAt);
    return rightValue - leftValue;
  });

export const formatHoveredCell = ({ row, column }: HoveredGridCell) => `${row}.${column}`;
