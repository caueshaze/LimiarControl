import {
  CAMPAIGN_EDGE_OBSTACLE_PRESETS,
  CAMPAIGN_OBSTACLE_PRESETS,
  edgeObstacleToPresetId,
  obstacleToPresetId,
  type CampaignMapConfig,
  type CampaignEdgeDirection,
  type CampaignEdgeObstacle,
  type EdgeObstaclePresetId,
  type CampaignObstacle,
  type ObstaclePresetId,
} from "../../../entities/campaign";
import type {
  FormState,
  CalibrationPreviewBounds,
  CalibrationPreviewState,
  HoveredGridCell,
} from "./types";

/** Smallest grid rectangle (as a fraction of the image) the user can draw. */
const MIN_CALIBRATION_SIZE = 0.02;

const clamp01 = (value: number) => Math.min(1, Math.max(0, value));

/**
 * Clamp a freshly-dragged rectangle so it stays inside the image (0-1 on both
 * axes) and keeps a minimum size. Mirrors the validation rules in
 * `getCalibrationPreview` / the save handler.
 */
export const clampCalibrationBounds = (
  bounds: CalibrationPreviewBounds,
): CalibrationPreviewBounds => {
  const width = Math.min(1, Math.max(MIN_CALIBRATION_SIZE, bounds.width));
  const height = Math.min(1, Math.max(MIN_CALIBRATION_SIZE, bounds.height));
  const x = clamp01(Math.min(bounds.x, 1 - width));
  const y = clamp01(Math.min(bounds.y, 1 - height));
  return { x, y, width, height };
};

export const EMPTY_FORM: FormState = {
  mapName: "",
  imageUrl: "",
  gridWidth: "",
  gridHeight: "",
  calibrationX: "",
  calibrationY: "",
  cellWidth: "",
  cellHeight: "",
};

export const configToForm = (config: CampaignMapConfig | null | undefined): FormState => {
  // Cell size is the source of truth in the editor; reconstruct it from the
  // stored calibration area divided by the grid count (round-trips on save).
  const cols = config?.gridWidth ?? null;
  const rows = config?.gridHeight ?? null;
  const calibration = config?.calibration ?? null;
  const cellWidth =
    calibration?.width != null && cols != null && cols > 0
      ? calibration.width / cols
      : null;
  const cellHeight =
    calibration?.height != null && rows != null && rows > 0
      ? calibration.height / rows
      : null;

  return {
    mapName: config?.mapName ?? "",
    imageUrl: config?.imageUrl ?? "",
    gridWidth: cols != null ? String(cols) : "",
    gridHeight: rows != null ? String(rows) : "",
    calibrationX: calibration?.x != null ? String(calibration.x) : "",
    calibrationY: calibration?.y != null ? String(calibration.y) : "",
    cellWidth: cellWidth != null ? String(cellWidth) : "",
    cellHeight: cellHeight != null ? String(cellHeight) : "",
  };
};

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
  const cols = parsePreviewInt(form.gridWidth);
  const rows = parsePreviewInt(form.gridHeight);
  const cellWidth = parsePreviewFloat(form.cellWidth);
  const cellHeight = parsePreviewFloat(form.cellHeight);
  const originX = parsePreviewFloat(form.calibrationX) ?? 0;
  const originY = parsePreviewFloat(form.calibrationY) ?? 0;

  // No cell size set yet → the grid fills the whole image.
  if (cellWidth == null && cellHeight == null) {
    return {
      status: "full-image",
      bounds: { x: 0, y: 0, width: 1, height: 1 },
    };
  }

  if (
    cellWidth == null ||
    cellHeight == null ||
    cols == null ||
    rows == null ||
    cellWidth <= 0 ||
    cellHeight <= 0
  ) {
    return { status: "invalid", bounds: null };
  }

  if (originX < 0 || originY < 0) {
    return { status: "invalid", bounds: null };
  }

  // The grid may extend past the image (count × cell size). We still preview it
  // (clipped by the surface's overflow-hidden); saving is what enforces fitting.
  const width = cols * cellWidth;
  const height = rows * cellHeight;

  return {
    status: "custom",
    bounds: { x: originX, y: originY, width, height },
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

export function buildObstacleMap(
  config: CampaignMapConfig | null | undefined,
): Map<string, ObstaclePresetId> {
  const map = new Map<string, ObstaclePresetId>();
  if (config?.obstacles) {
    for (const obstacle of config.obstacles) {
      map.set(`${obstacle.x}:${obstacle.y}`, obstacleToPresetId(obstacle));
    }
  } else if (config?.blockedCells) {
    for (const cell of config.blockedCells) {
      map.set(`${cell.x}:${cell.y}`, "solid_wall");
    }
  }
  return map;
}

export function buildEdgeObstacleMap(
  config: CampaignMapConfig | null | undefined,
): Map<string, EdgeObstaclePresetId> {
  const map = new Map<string, EdgeObstaclePresetId>();
  for (const edge of config?.edgeObstacles ?? []) {
    map.set(
      `${edge.x}:${edge.y}:${edge.direction}`,
      edgeObstacleToPresetId(edge),
    );
  }
  return map;
}

export function serializeObstacleMap(
  obstacleMap: ReadonlyMap<string, ObstaclePresetId>,
): CampaignObstacle[] {
  return Array.from(obstacleMap.entries()).map(([key, presetId]) => {
    const [x, y] = key.split(":").map(Number);
    const preset = CAMPAIGN_OBSTACLE_PRESETS.find((entry) => entry.id === presetId)!;
    return { x, y, ...preset.style };
  });
}

export function serializeEdgeObstacleMap(
  edgeObstacleMap: ReadonlyMap<string, EdgeObstaclePresetId>,
): CampaignEdgeObstacle[] {
  return Array.from(edgeObstacleMap.entries()).map(([key, presetId]) => {
    const [x, y, direction] = key.split(":");
    const preset = CAMPAIGN_EDGE_OBSTACLE_PRESETS.find(
      (entry) => entry.id === presetId,
    )!;
    return {
      x: Number(x),
      y: Number(y),
      direction: direction as CampaignEdgeDirection,
      ...preset.style,
    };
  });
}

export function summarizeObstacleMap(
  obstacleMap: ReadonlyMap<string, ObstaclePresetId>,
) {
  return CAMPAIGN_OBSTACLE_PRESETS.map((preset) => ({
    ...preset,
    count: Array.from(obstacleMap.values()).filter((value) => value === preset.id).length,
  }));
}

export function summarizeEdgeObstacleMap(
  edgeObstacleMap: ReadonlyMap<string, EdgeObstaclePresetId>,
) {
  return CAMPAIGN_EDGE_OBSTACLE_PRESETS.map((preset) => ({
    ...preset,
    count: Array.from(edgeObstacleMap.values()).filter(
      (value) => value === preset.id,
    ).length,
  }));
}

export function getHoveredCellObstaclePreset(
  obstacleMap: ReadonlyMap<string, ObstaclePresetId>,
  hoveredCell: HoveredGridCell | null,
): ObstaclePresetId | null {
  if (hoveredCell == null) {
    return null;
  }
  return obstacleMap.get(`${hoveredCell.column - 1}:${hoveredCell.row - 1}`) ?? null;
}

export function getHoveredCellEdgePresets(
  edgeObstacleMap: ReadonlyMap<string, EdgeObstaclePresetId>,
  hoveredCell: HoveredGridCell | null,
) {
  if (hoveredCell == null) {
    return [];
  }
  const x = hoveredCell.column - 1;
  const y = hoveredCell.row - 1;
  const directions: CampaignEdgeDirection[] = ["N", "E", "S", "W"];
  return directions
    .map((direction) => {
      const presetId = edgeObstacleMap.get(`${x}:${y}:${direction}`);
      if (presetId == null) {
        return null;
      }
      return { direction, presetId };
    })
    .filter(
      (
        entry,
      ): entry is {
        direction: CampaignEdgeDirection;
        presetId: EdgeObstaclePresetId;
      } => entry != null,
    );
}

export function formatCalibrationBounds(
  bounds: CalibrationPreviewState["bounds"],
): string {
  if (bounds == null) {
    return "X - | Y - | W - | H -";
  }
  return `X ${bounds.x.toFixed(3)} | Y ${bounds.y.toFixed(3)} | W ${bounds.width.toFixed(3)} | H ${bounds.height.toFixed(3)}`;
}

export const formatHoveredCell = (
  { row, column }: HoveredGridCell,
  labels?: { columnLabel?: string; rowLabel?: string },
) =>
  `${labels?.columnLabel ?? "Col"} ${column} • ${labels?.rowLabel ?? "Row"} ${row}`;
