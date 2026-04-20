import type {
  CampaignEdgeDirection,
  EdgeObstaclePresetId,
} from "../../../entities/campaign";
import { CAMPAIGN_EDGE_OBSTACLE_PRESETS } from "../../../entities/campaign";
import { useLocale } from "../../../shared/hooks/useLocale";

type Props = {
  selectedPresetId: EdgeObstaclePresetId;
  edgeDirection: CampaignEdgeDirection;
  onSelectPreset: (presetId: EdgeObstaclePresetId) => void;
  onSelectDirection: (direction: CampaignEdgeDirection) => void;
  edgeObstacleMap: ReadonlyMap<string, EdgeObstaclePresetId>;
};

export const EdgeObstaclePresetPicker = ({
  selectedPresetId,
  edgeDirection,
  onSelectPreset,
  onSelectDirection,
  edgeObstacleMap,
}: Props) => {
  const { t } = useLocale();
  const selectedPreset =
    CAMPAIGN_EDGE_OBSTACLE_PRESETS.find((preset) => preset.id === selectedPresetId) ??
    CAMPAIGN_EDGE_OBSTACLE_PRESETS[0];
  const selectedPresetCount = Array.from(edgeObstacleMap.values()).filter(
    (presetId) => presetId === selectedPresetId,
  ).length;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-1.5">
        {(["N", "E", "S", "W"] as CampaignEdgeDirection[]).map((direction) => (
          <button
            key={direction}
            type="button"
            onClick={() => onSelectDirection(direction)}
            className={`rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] transition-colors ${
              edgeDirection === direction
                ? "border-white/40 bg-white/10 text-white"
                : "border-slate-700 text-slate-400 hover:border-slate-500"
            }`}
          >
            {direction}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap gap-1.5">
        {CAMPAIGN_EDGE_OBSTACLE_PRESETS.map((preset) => (
          <button
            key={preset.id}
            type="button"
            onClick={() => onSelectPreset(preset.id)}
            title={preset.description}
            className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] transition-colors ${
              selectedPresetId === preset.id
                ? "border-white/40 bg-white/10 text-white"
                : "border-slate-700 text-slate-400 hover:border-slate-500"
            }`}
          >
            <span
              className="inline-block h-2.5 w-2.5 shrink-0 rounded-sm"
              style={{ backgroundColor: preset.color }}
            />
            {preset.label}
          </button>
        ))}
      </div>

      <div className="rounded-2xl border border-slate-700/50 bg-slate-950/60 px-4 py-3 text-xs text-slate-300">
        <div className="flex items-center justify-between gap-3">
          <span className="font-semibold text-white">{selectedPreset.label}</span>
          <span className="rounded-full border border-slate-700 bg-slate-900/70 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-200">
            {selectedPresetCount}
          </span>
        </div>
        <p className="mt-2 leading-6 text-slate-400">{selectedPreset.description}</p>
        <p className="mt-2 text-[11px] uppercase tracking-[0.16em] text-slate-500">
          {t("campaignHome.mapPreviewEdgeEditHint").replace("{direction}", edgeDirection)}
        </p>
      </div>
    </div>
  );
};
