import type {
  CampaignEdgeDirection,
  EdgeObstaclePresetId,
  CampaignMapConfig,
  ObstaclePresetId,
} from "../../../entities/campaign";

export type Props = {
  campaignId: string;
  initialMaps: CampaignMapConfig[];
  onSaved: (maps: CampaignMapConfig[]) => void;
};

export type FormState = {
  mapName: string;
  imageUrl: string;
  /** Number of columns (grid count, drives combat coordinates). */
  gridWidth: string;
  /** Number of rows (grid count, drives combat coordinates). */
  gridHeight: string;
  /** Grid origin on the image (top-left), as a fraction 0-1. */
  calibrationX: string;
  calibrationY: string;
  /** Size of a single cell, as a fraction of the image (independent of count). */
  cellWidth: string;
  cellHeight: string;
};

export type CalibrationPreviewBounds = {
  x: number;
  y: number;
  width: number;
  height: number;
};

export type CalibrationPreviewState =
  | {
      status: "full-image";
      bounds: CalibrationPreviewBounds;
    }
  | {
      status: "custom";
      bounds: CalibrationPreviewBounds;
    }
  | {
      status: "invalid";
      bounds: null;
    };

export type HoveredGridCell = {
  row: number;
  column: number;
};

export type ObstacleEditTarget = "cell" | "edge";

export type EditorMode = "calibrate" | "obstacles" | "view";

export type ObstacleEditorState = {
  obstacleMap: ReadonlyMap<string, ObstaclePresetId>;
  edgeObstacleMap: ReadonlyMap<string, EdgeObstaclePresetId>;
  selectedPresetId: ObstaclePresetId;
  selectedEdgePresetId: EdgeObstaclePresetId;
  edgeDirection: CampaignEdgeDirection;
  isObstacleEditMode: boolean;
  obstacleEditTarget: ObstacleEditTarget;
};

export type MapPreviewSurfaceProps = {
  imageUrl: string;
  alt: string;
  bounds: CalibrationPreviewBounds | null;
  gridWidth: number | null;
  gridHeight: number | null;
  imageClassName: string;
  invalidMessage: string;
  hoverHint: string;
  hoverMissingGrid: string;
  hoverCellLabel: string;
  hoverColumnLabel: string;
  hoverRowLabel: string;
  /** 0-based cell keys ("x:y") → preset ID for obstacle overlay colors. */
  obstacleMap?: ReadonlyMap<string, string>;
  /** 0-based edge keys ("x:y:direction") → preset ID for edge overlay colors. */
  edgeObstacleMap?: ReadonlyMap<string, string>;
  obstacleEditTarget?: ObstacleEditTarget;
  edgeDirection?: CampaignEdgeDirection;
  /** When false, the generated grid lines are hidden (overlays stay). */
  showGridLines?: boolean;
  /**
   * The reference (top-left) cell rectangle, in image fractions. When
   * calibrating, the user drags/resizes THIS single cell and the grid replicates
   * it `gridWidth × gridHeight` times. Its position also sets the grid origin.
   */
  calibrationCell?: CalibrationPreviewBounds | null;
  /** Called with 0-based (x, y) when a cell is clicked in obstacle-edit mode. */
  onCellToggle?: (x: number, y: number) => void;
  /** Called with 0-based (x, y, direction) when an edge is toggled in edge-edit mode. */
  onEdgeToggle?: (x: number, y: number, direction: CampaignEdgeDirection) => void;
  onHoveredCellChange?: (cell: HoveredGridCell | null) => void;
  /**
   * When true, the grid rectangle can be drawn/moved/resized directly on the
   * image. Calibration changes are normalized (0-1) and emitted via
   * `onCalibrationChange`.
   */
  calibrationEditing?: boolean;
  /** Called with the new reference-cell rectangle (normalized) while calibrating. */
  onCalibrationChange?: (cell: CalibrationPreviewBounds) => void;
};
