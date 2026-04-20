import type {
  CampaignEdgeDirection,
  EdgeObstaclePresetId,
  ObstaclePresetId,
} from "../../../entities/campaign";
import { useLocale } from "../../../shared/hooks/useLocale";
import type { ObstacleEditTarget } from "./types";
import { EdgeObstaclePresetPicker } from "./EdgeObstaclePresetPicker";
import { ObstaclePresetPicker } from "./ObstaclePresetPicker";

type Props = {
  obstacleEditTarget: ObstacleEditTarget;
  selectedPresetId: ObstaclePresetId;
  selectedEdgePresetId: EdgeObstaclePresetId;
  edgeDirection: CampaignEdgeDirection;
  obstacleMap: ReadonlyMap<string, ObstaclePresetId>;
  edgeObstacleMap: ReadonlyMap<string, EdgeObstaclePresetId>;
  onSelectTarget: (target: ObstacleEditTarget) => void;
  onSelectPreset: (presetId: ObstaclePresetId) => void;
  onSelectEdgePreset: (presetId: EdgeObstaclePresetId) => void;
  onSelectEdgeDirection: (direction: CampaignEdgeDirection) => void;
};

export const ObstacleEditorControls = ({
  obstacleEditTarget,
  selectedPresetId,
  selectedEdgePresetId,
  edgeDirection,
  obstacleMap,
  edgeObstacleMap,
  onSelectTarget,
  onSelectPreset,
  onSelectEdgePreset,
  onSelectEdgeDirection,
}: Props) => {
  const { t } = useLocale();

  return (
    <div className="space-y-3">
      <div className="inline-flex rounded-full border border-slate-700 bg-slate-950/70 p-1">
        {(["cell", "edge"] as ObstacleEditTarget[]).map((target) => (
          <button
            key={target}
            type="button"
            onClick={() => onSelectTarget(target)}
            className={`rounded-full px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] transition-colors ${
              obstacleEditTarget === target
                ? "bg-white/12 text-white"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            {target === "cell"
              ? t("campaignHome.mapObstacleTargetCell")
              : t("campaignHome.mapObstacleTargetEdge")}
          </button>
        ))}
      </div>

      {obstacleEditTarget === "cell" ? (
        <ObstaclePresetPicker
          selectedPresetId={selectedPresetId}
          onSelectPreset={onSelectPreset}
          obstacleMap={obstacleMap}
        />
      ) : (
        <EdgeObstaclePresetPicker
          selectedPresetId={selectedEdgePresetId}
          edgeDirection={edgeDirection}
          onSelectPreset={onSelectEdgePreset}
          onSelectDirection={onSelectEdgeDirection}
          edgeObstacleMap={edgeObstacleMap}
        />
      )}
    </div>
  );
};
