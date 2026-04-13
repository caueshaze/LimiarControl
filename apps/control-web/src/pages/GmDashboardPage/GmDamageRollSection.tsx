type DamageMode = "choose" | "manual" | "virtual";

type Props = {
  damageMode: DamageMode;
  damageRollCount: number;
  damageRollValues: number[];
  effectiveDamageDiceLabel: string;
  isCritical: boolean;
  loading: boolean;
  manualDamageRolls: number[];
  onBack: () => void;
  onClearManualRolls: () => void;
  onSelectManualRoll: (value: number) => void;
  onSetDamageMode: (mode: DamageMode) => void;
  onSubmitDamage: (payload: { roll_source: "manual" | "system"; manual_rolls?: number[] }) => void;
};

export const GmDamageRollSection = ({
  damageMode,
  damageRollCount,
  damageRollValues,
  effectiveDamageDiceLabel,
  isCritical,
  loading,
  manualDamageRolls,
  onBack,
  onClearManualRolls,
  onSelectManualRoll,
  onSetDamageMode,
  onSubmitDamage,
}: Props) => {
  if (damageMode === "choose") {
    if (damageRollCount > 0) {
      return (
        <div className="space-y-3">
          <p className="text-xs text-slate-400">
            {isCritical
              ? `Critico confirmado. Escolha como rolar o dano de ${effectiveDamageDiceLabel}.`
              : `Escolha como rolar o dano de ${effectiveDamageDiceLabel}.`}
          </p>
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => onSetDamageMode("virtual")}
              className="rounded-2xl bg-rose-600 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white hover:bg-rose-500"
            >
              Virtual
            </button>
            <button
              type="button"
              onClick={() => onSetDamageMode("manual")}
              className="rounded-2xl border border-slate-600 bg-slate-800 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-slate-200 hover:bg-slate-700"
            >
              Manual
            </button>
          </div>
        </div>
      );
    }

    return (
      <div className="space-y-3">
        <p className="text-xs text-slate-400">
          Essa acao nao usa dado de dano. Aplique o dano fixo para concluir.
        </p>
        <button
          type="button"
          disabled={loading}
          onClick={() => onSubmitDamage({ roll_source: "system" })}
          className="w-full rounded-full bg-rose-600 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white disabled:opacity-50"
        >
          {loading ? "..." : "Aplicar dano"}
        </button>
      </div>
    );
  }

  if (damageMode === "virtual") {
    return (
      <div className="flex gap-3">
        <button
          type="button"
          disabled={loading}
          onClick={() => onSubmitDamage({ roll_source: "system" })}
          className="flex-1 rounded-full bg-rose-600 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white disabled:opacity-50"
        >
          {loading ? "..." : "Rolar dano"}
        </button>
        <button
          type="button"
          onClick={onBack}
          className="rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400"
        >
          Voltar
        </button>
      </div>
    );
  }

  if (damageMode === "manual") {
    return (
      <div className="space-y-3">
        <p className="text-xs text-slate-400">
          Escolha cada dado manualmente ({manualDamageRolls.length}/{damageRollCount}).
        </p>

        {manualDamageRolls.length > 0 ? (
          <div className="rounded-2xl border border-slate-700 bg-slate-900/60 px-3 py-2 text-xs text-slate-300">
            Dados escolhidos: {manualDamageRolls.join(", ")}
          </div>
        ) : null}

        <div className="grid grid-cols-5 gap-2">
          {damageRollValues.map((value) => (
            <button
              key={value}
              type="button"
              disabled={loading}
              onClick={() => onSelectManualRoll(value)}
              className="rounded-xl border border-slate-700 bg-slate-900 px-2 py-3 text-center text-lg font-bold text-white transition-colors hover:border-rose-500/50 hover:bg-slate-800 disabled:opacity-50"
            >
              {value}
            </button>
          ))}
        </div>

        <div className="flex gap-3">
          <button
            type="button"
            onClick={onClearManualRolls}
            className="flex-1 rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400"
          >
            Limpar
          </button>
          <button
            type="button"
            onClick={onBack}
            className="flex-1 rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400"
          >
            Voltar
          </button>
        </div>
      </div>
    );
  }

  return null;
};
