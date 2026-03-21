import type { PendingRoll } from "./playerBoard.types";
import { useLocale } from "../../shared/hooks/useLocale";

type Props = {
  activeSessionId: string | null;
  manualValue: string;
  pendingRoll: PendingRoll;
  rollMode: "virtual" | "manual" | null;
  onManualValueChange: (value: string) => void;
  onRollModeChange: (mode: "virtual" | "manual" | null) => void;
  onSubmitManual: () => Promise<void>;
  onVirtualRoll: () => void;
};

export const PlayerBoardRollDialog = ({
  activeSessionId,
  manualValue,
  pendingRoll,
  rollMode,
  onManualValueChange,
  onRollModeChange,
  onSubmitManual,
  onVirtualRoll,
}: Props) => {
  const { t } = useLocale();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 px-4">
      <div className="w-full max-w-md rounded-3xl border border-limiar-400/30 bg-void-950 p-6 text-slate-100 shadow-2xl shadow-limiar-900/40">
        <p className="text-xs uppercase tracking-[0.3em] text-limiar-200">
          {t("playerBoard.rollRequest")}
        </p>
        {pendingRoll.reason && (
          <p className="mt-2 text-base font-semibold text-white">{pendingRoll.reason}</p>
        )}
        <div className={`flex items-center gap-3 ${pendingRoll.reason ? "mt-1" : "mt-3"}`}>
          <h2 className="text-2xl font-semibold text-limiar-300">
            {pendingRoll.expression.toUpperCase()}
          </h2>
          {pendingRoll.mode === "advantage" && (
            <span className="rounded-full border border-emerald-500/30 bg-emerald-500/15 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-widest text-emerald-400">
              Advantage
            </span>
          )}
          {pendingRoll.mode === "disadvantage" && (
            <span className="rounded-full border border-red-500/30 bg-red-500/15 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-widest text-red-400">
              Disadvantage
            </span>
          )}
        </div>
        {pendingRoll.issuedBy && (
          <p className="mt-2 text-sm text-slate-400">
            {t("playerBoard.requestedBy")} {pendingRoll.issuedBy}
          </p>
        )}

        {rollMode === null && (
          <div className="mt-5 grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => onRollModeChange("virtual")}
              className="rounded-2xl bg-limiar-500 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white hover:bg-limiar-400"
            >
              🎲 Virtual
            </button>
            <button
              type="button"
              onClick={() => onRollModeChange("manual")}
              className="rounded-2xl border border-slate-600 bg-slate-800 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-slate-200 hover:bg-slate-700"
            >
              ✍️ Manual
            </button>
          </div>
        )}

        {rollMode === "virtual" && (
          <div className="mt-5 flex gap-3">
            <button
              type="button"
              onClick={onVirtualRoll}
              className="flex-1 rounded-full bg-limiar-500 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white"
            >
              {t("playerBoard.rollNow")}
            </button>
            <button
              type="button"
              onClick={() => onRollModeChange(null)}
              className="rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400"
            >
              ←
            </button>
          </div>
        )}

        {rollMode === "manual" && (
          <div className="mt-5 space-y-3">
            {pendingRoll.mode && (
              <p className="text-xs text-slate-400">
                {pendingRoll.mode === "advantage"
                  ? "Role 2 dados e insira o maior resultado."
                  : "Role 2 dados e insira o menor resultado."}
              </p>
            )}
            <label className="text-xs uppercase tracking-widest text-slate-400">Resultado obtido</label>
            <input
              type="number"
              min={1}
              value={manualValue}
              onChange={(event) => onManualValueChange(event.target.value)}
              placeholder="Ex: 17"
              className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-center text-2xl font-bold text-white focus:border-limiar-500 focus:outline-none"
              autoFocus
            />
            <div className="flex gap-3">
              <button
                type="button"
                disabled={!activeSessionId || !manualValue || Number.isNaN(Number(manualValue))}
                onClick={() => {
                  void onSubmitManual();
                }}
                className="flex-1 rounded-full bg-limiar-500 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white disabled:opacity-50"
              >
                Confirmar
              </button>
              <button
                type="button"
                onClick={() => onRollModeChange(null)}
                className="rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400"
              >
                ←
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
