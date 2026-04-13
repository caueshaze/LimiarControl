import { useLocale } from "../../../shared/hooks/useLocale";

type Props = {
  disabled?: boolean;
  manualValue: string;
  mode: "system" | "manual";
  onManualValueChange: (value: string) => void;
  onModeChange: (mode: "system" | "manual") => void;
};

export const ConcentrationSaveControl = ({
  disabled = false,
  manualValue,
  mode,
  onManualValueChange,
  onModeChange,
}: Props) => {
  const { t } = useLocale();

  return (
    <div className="rounded-2xl border border-white/10 bg-slate-950/40 px-4 py-3">
      <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-300">
        {t("playerBoard.concentrationSaveMode")}
      </p>
      <p className="mt-2 text-xs leading-5 text-slate-400">
        {t("playerBoard.concentrationTargetActive")}
      </p>

      <div className="mt-3 inline-flex rounded-2xl border border-white/10 bg-slate-900/70 p-1">
        <button
          type="button"
          disabled={disabled}
          onClick={() => onModeChange("system")}
          className={`rounded-xl px-3 py-2 text-xs font-semibold uppercase tracking-[0.18em] transition ${
            mode === "system"
              ? "bg-emerald-500/20 text-emerald-100"
              : "text-slate-400 hover:text-white"
          }`}
        >
          {t("playerBoard.concentrationSaveAuto")}
        </button>
        <button
          type="button"
          disabled={disabled}
          onClick={() => onModeChange("manual")}
          className={`rounded-xl px-3 py-2 text-xs font-semibold uppercase tracking-[0.18em] transition ${
            mode === "manual"
              ? "bg-amber-500/20 text-amber-100"
              : "text-slate-400 hover:text-white"
          }`}
        >
          {t("playerBoard.concentrationSaveManual")}
        </button>
      </div>

      {mode === "manual" ? (
        <label className="mt-3 block space-y-2">
          <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
            {t("playerBoard.concentrationManualValue")}
          </span>
          <input
            type="number"
            min={1}
            max={20}
            step={1}
            inputMode="numeric"
            disabled={disabled}
            value={manualValue}
            onChange={(event) => onManualValueChange(event.target.value)}
            placeholder={t("playerBoard.concentrationManualPlaceholder")}
            className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none transition focus:border-amber-400"
          />
        </label>
      ) : null}
    </div>
  );
};
