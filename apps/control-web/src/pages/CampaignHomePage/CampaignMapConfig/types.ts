import type { CampaignMapConfig } from "../../../entities/campaign";

export type Props = {
  campaignId: string;
  initialMaps: CampaignMapConfig[];
  onSaved: (maps: CampaignMapConfig[]) => void;
};

export type FormState = {
  mapName: string;
  imageUrl: string;
  gridWidth: string;
  gridHeight: string;
  calibrationX: string;
  calibrationY: string;
  calibrationWidth: string;
  calibrationHeight: string;
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
  /** 0-based cell keys ("x:y") → preset ID for obstacle overlay colors. */
  obstacleMap?: ReadonlyMap<string, string>;
  /** Called with 0-based (x, y) when a cell is clicked in obstacle-edit mode. */
  onCellToggle?: (x: number, y: number) => void;
};
