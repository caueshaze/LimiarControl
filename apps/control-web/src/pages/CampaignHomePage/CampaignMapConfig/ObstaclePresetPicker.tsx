import type { ObstaclePresetId } from "../../../entities/campaign";
import { CAMPAIGN_OBSTACLE_PRESETS } from "../../../entities/campaign";
import { useLocale } from "../../../shared/hooks/useLocale";

type Props = {
  selectedPresetId: ObstaclePresetId;
  onSelectPreset: (presetId: ObstaclePresetId) => void;
  obstacleMap: ReadonlyMap<string, ObstaclePresetId>;
};

export const ObstaclePresetPicker = ({
  selectedPresetId,
  onSelectPreset,
  obstacleMap,
}: Props) => {
  const { t } = useLocale();
  const selectedPreset =
    CAMPAIGN_OBSTACLE_PRESETS.find((preset) => preset.id === selectedPresetId) ??
    CAMPAIGN_OBSTACLE_PRESETS[0];
  const selectedPresetCount = Array.from(obstacleMap.values()).filter(
    (presetId) => presetId === selectedPresetId,
  ).length;

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1.5">
        {CAMPAIGN_OBSTACLE_PRESETS.map((preset) => (
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
          {t("campaignHome.mapPreviewEditHint")}
        </p>
      </div>
    </div>
  );
};
