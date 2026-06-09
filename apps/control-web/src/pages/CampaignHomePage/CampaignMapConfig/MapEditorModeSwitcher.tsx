import { useLocale } from "../../../shared/hooks/useLocale";
import type { EditorMode } from "./types";

type Props = {
  editorMode: EditorMode;
  /** Obstacle editing needs grid dimensions; disabled until they exist. */
  obstaclesDisabled: boolean;
  onSelectMode: (mode: EditorMode) => void;
};

const MODES = [
  { id: "calibrate", labelKey: "campaignHome.mapModeCalibrate" },
  { id: "obstacles", labelKey: "campaignHome.mapModeObstacles" },
  { id: "view", labelKey: "campaignHome.mapModeView" },
] as const satisfies readonly { id: EditorMode; labelKey: string }[];

export const MapEditorModeSwitcher = ({
  editorMode,
  obstaclesDisabled,
  onSelectMode,
}: Props) => {
  const { t } = useLocale();

  return (
    <div className="inline-flex rounded-full border border-slate-700 bg-slate-950/70 p-1">
      {MODES.map((mode) => {
        const active = editorMode === mode.id;
        const disabled = mode.id === "obstacles" && obstaclesDisabled;
        return (
          <button
            key={mode.id}
            type="button"
            disabled={disabled}
            onClick={() => onSelectMode(mode.id)}
            className={`rounded-full px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] transition-colors ${
              active
                ? "bg-white/12 text-white"
                : "text-slate-400 hover:text-slate-200"
            } ${disabled ? "cursor-not-allowed opacity-40 hover:text-slate-400" : ""}`}
          >
            {t(mode.labelKey)}
          </button>
        );
      })}
    </div>
  );
};
