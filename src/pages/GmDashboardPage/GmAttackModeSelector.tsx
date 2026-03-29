import { D20_VALUES } from "./gmEntityActionRollDialog.helpers";

type Props = {
  attackMode: "choose" | "manual" | "virtual";
  loading: boolean;
  onClose: () => void;
  onModeChange: (mode: "choose" | "manual" | "virtual") => void;
  onSubmitVirtual: () => void;
  onSubmitManual: (value: number) => void;
};

export const GmAttackModeSelector = ({
  attackMode,
  loading,
  onClose,
  onModeChange,
  onSubmitVirtual,
  onSubmitManual,
}: Props) => {
  if (attackMode === "choose") {
    return (
      <div className="mt-5 space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <button
            type="button"
            onClick={() => onModeChange("virtual")}
            className="rounded-2xl bg-rose-600 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white hover:bg-rose-500"
          >
            Virtual
          </button>
          <button
            type="button"
            onClick={() => onModeChange("manual")}
            className="rounded-2xl border border-slate-600 bg-slate-800 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-slate-200 hover:bg-slate-700"
          >
            Manual
          </button>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="w-full rounded-2xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-rose-200 hover:bg-rose-500/20"
        >
          Cancelar
        </button>
      </div>
    );
  }

  if (attackMode === "virtual") {
    return (
      <div className="mt-5 flex gap-3">
        <button
          type="button"
          disabled={loading}
          onClick={onSubmitVirtual}
          className="flex-1 rounded-full bg-rose-600 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white disabled:opacity-50"
        >
          {loading ? "..." : "Rolar ataque"}
        </button>
        <button
          type="button"
          onClick={() => onModeChange("choose")}
          className="rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400"
        >
          Voltar
        </button>
      </div>
    );
  }

  // attackMode === "manual"
  return (
    <div className="mt-5 space-y-3">
      <p className="text-xs text-slate-400">Selecione o d20 manual da acao.</p>

      <div className="grid grid-cols-5 gap-2">
        {D20_VALUES.map((value) => (
          <button
            key={value}
            type="button"
            disabled={loading}
            onClick={() => onSubmitManual(value)}
            className="rounded-xl border border-slate-700 bg-slate-900 px-2 py-3 text-center text-lg font-bold text-white transition-colors hover:border-rose-500/50 hover:bg-slate-800 disabled:opacity-50"
          >
            {value}
          </button>
        ))}
      </div>

      <button
        type="button"
        onClick={() => onModeChange("choose")}
        className="rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400"
      >
        Voltar
      </button>
    </div>
  );
};
