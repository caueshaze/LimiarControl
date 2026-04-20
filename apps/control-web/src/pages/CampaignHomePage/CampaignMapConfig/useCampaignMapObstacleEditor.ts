import { useState, type Dispatch, type SetStateAction } from "react";
import type {
  CampaignEdgeDirection,
  CampaignMapConfig,
  EdgeObstaclePresetId,
  ObstaclePresetId,
} from "../../../entities/campaign";
import { buildEdgeObstacleMap, buildObstacleMap } from "./utils";
import type { ObstacleEditTarget } from "./types";

type EditorState = {
  obstacleMap: ReadonlyMap<string, ObstaclePresetId>;
  edgeObstacleMap: ReadonlyMap<string, EdgeObstaclePresetId>;
  selectedPresetId: ObstaclePresetId;
  selectedEdgePresetId: EdgeObstaclePresetId;
  edgeDirection: CampaignEdgeDirection;
  isObstacleEditMode: boolean;
  obstacleEditTarget: ObstacleEditTarget;
};

export function useCampaignMapObstacleEditor(initialConfig: CampaignMapConfig | null) {
  const [obstacleMap, setObstacleMap] = useState<Map<string, ObstaclePresetId>>(
    () => buildObstacleMap(initialConfig),
  );
  const [edgeObstacleMap, setEdgeObstacleMap] = useState<
    Map<string, EdgeObstaclePresetId>
  >(() => buildEdgeObstacleMap(initialConfig));
  const [selectedPresetId, setSelectedPresetId] =
    useState<ObstaclePresetId>("solid_wall");
  const [selectedEdgePresetId, setSelectedEdgePresetId] =
    useState<EdgeObstaclePresetId>("edge_wall");
  const [edgeDirection, setEdgeDirection] =
    useState<CampaignEdgeDirection>("N");
  const [isObstacleEditMode, setIsObstacleEditMode] = useState(false);
  const [obstacleEditTarget, setObstacleEditTarget] =
    useState<ObstacleEditTarget>("cell");

  const resetFromConfig = (config: CampaignMapConfig | null) => {
    setObstacleMap(buildObstacleMap(config));
    setEdgeObstacleMap(buildEdgeObstacleMap(config));
    setIsObstacleEditMode(false);
    setObstacleEditTarget("cell");
    setEdgeDirection("N");
  };

  const clearAll = () => {
    setObstacleMap(new Map());
    setEdgeObstacleMap(new Map());
    setIsObstacleEditMode(false);
    setObstacleEditTarget("cell");
    setEdgeDirection("N");
  };

  const toggleCell = (x: number, y: number) => {
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

  const toggleEdge = (x: number, y: number, direction: CampaignEdgeDirection) => {
    const key = `${x}:${y}:${direction}`;
    setEdgeObstacleMap((current) => {
      const next = new Map(current);
      if (next.get(key) === selectedEdgePresetId) {
        next.delete(key);
      } else {
        next.set(key, selectedEdgePresetId);
      }
      return next;
    });
  };

  return {
    obstacleMap,
    edgeObstacleMap,
    selectedPresetId,
    selectedEdgePresetId,
    edgeDirection,
    isObstacleEditMode,
    obstacleEditTarget,
    resetFromConfig,
    clearAll,
    toggleCell,
    toggleEdge,
    setSelectedPresetId,
    setSelectedEdgePresetId,
    setEdgeDirection,
    setIsObstacleEditMode,
    setObstacleEditTarget,
  } satisfies EditorState & {
    resetFromConfig: (config: CampaignMapConfig | null) => void;
    clearAll: () => void;
    toggleCell: (x: number, y: number) => void;
    toggleEdge: (x: number, y: number, direction: CampaignEdgeDirection) => void;
    setSelectedPresetId: (presetId: ObstaclePresetId) => void;
    setSelectedEdgePresetId: (presetId: EdgeObstaclePresetId) => void;
    setEdgeDirection: (direction: CampaignEdgeDirection) => void;
    setIsObstacleEditMode: Dispatch<SetStateAction<boolean>>;
    setObstacleEditTarget: (target: ObstacleEditTarget) => void;
  };
}
