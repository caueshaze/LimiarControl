import { D20_VALUES } from "./spellCastHelpers";

type Props = {
  attackMode: "choose" | "manual" | "virtual";
  canSubmitArea: boolean;
  hasError?: boolean;
  isAreaSpell: boolean;
  loading: boolean;
  onAttackModeChange: (mode: "choose" | "manual" | "virtual") => void;
  onCancel: () => void;
  onClearArea: () => void;
  onShowAreaHint: boolean;
  onSubmitCast: (payload?: { manual_roll?: number; roll_source?: "manual" | "system" }) => void;
  spellMode: string;
  spellOutOfRange: boolean;
  submitDisabled?: boolean;
  validationMessage?: string | null;
};

export const SpellCastDialogActions = ({
  attackMode,
  canSubmitArea,
  hasError = false,
  isAreaSpell,
  loading,
  onAttackModeChange,
  onCancel,
  onClearArea,
  onShowAreaHint,
  onSubmitCast,
  spellMode,
  spellOutOfRange,
  submitDisabled = false,
  validationMessage = null,
}: Props) => (
  <>
    {spellMode === "spell_attack" && !isAreaSpell && attackMode === "choose" ? (
      <div className="mt-5 flex flex-col gap-3">
        {!hasError ? (
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              disabled={spellOutOfRange || submitDisabled}
              onClick={() => onAttackModeChange("virtual")}
              className="rounded-2xl bg-fuchsia-600 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white hover:bg-fuchsia-500 disabled:opacity-40"
            >
              Virtual
            </button>
            <button
              type="button"
              disabled={spellOutOfRange || submitDisabled}
              onClick={() => onAttackModeChange("manual")}
              className="rounded-2xl border border-slate-600 bg-slate-800 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-slate-200 hover:bg-slate-700 disabled:opacity-40"
            >
              Manual
            </button>
          </div>
        ) : null}
        <button
          type="button"
          onClick={onCancel}
          className={`rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400 hover:bg-slate-800 transition-colors ${hasError ? "w-full" : ""}`}
        >
          Cancelar
        </button>
      </div>
    ) : null}

    {spellMode === "spell_attack" && !isAreaSpell && attackMode === "virtual" ? (
      <div className="mt-5 flex gap-3">
        {!hasError ? (
          <button
            type="button"
            disabled={loading || submitDisabled}
            onClick={() => onSubmitCast({ roll_source: "system" })}
            className="flex-1 rounded-full bg-fuchsia-600 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white disabled:opacity-50"
          >
            {loading ? "..." : "Rolar ataque magico"}
          </button>
        ) : null}
        <button
          type="button"
          onClick={() => onAttackModeChange("choose")}
          className="rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400 transition-colors hover:bg-slate-800"
        >
          Voltar
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400 transition-colors hover:bg-slate-800"
        >
          Cancelar
        </button>
      </div>
    ) : null}

    {spellMode === "spell_attack" && !isAreaSpell && attackMode === "manual" ? (
      <div className="mt-5 space-y-3">
        <p className="text-xs text-slate-400">Selecione o d20 manual do ataque.</p>
        <div className="grid grid-cols-5 gap-2">
          {D20_VALUES.map((value) => (
            <button
              key={value}
              type="button"
              disabled={loading || submitDisabled}
              onClick={() => onSubmitCast({ roll_source: "manual", manual_roll: value })}
              className="rounded-xl border border-slate-700 bg-slate-900 px-2 py-3 text-center text-lg font-bold text-white transition-colors hover:border-fuchsia-500/50 hover:bg-slate-800 disabled:opacity-50"
            >
              {value}
            </button>
          ))}
        </div>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={() => onAttackModeChange("choose")}
            className="flex-1 rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400 transition-colors hover:bg-slate-800"
          >
            Voltar
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400 transition-colors hover:bg-slate-800"
          >
            Cancelar
          </button>
        </div>
      </div>
    ) : null}

    {spellMode !== "spell_attack" ? (
      <div className="mt-5 flex gap-3">
        {!hasError ? (
          <button
            type="button"
            disabled={isAreaSpell ? !canSubmitArea || loading : loading || spellOutOfRange || submitDisabled}
            onClick={() => onSubmitCast()}
            className="flex-1 rounded-full bg-fuchsia-600 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white disabled:opacity-50"
          >
            {loading ? "..." : "Conjurar"}
          </button>
        ) : null}
        {isAreaSpell ? (
          <button
            type="button"
            onClick={onClearArea}
            className="rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400"
          >
            Limpar area
          </button>
        ) : null}
        <button
          type="button"
          onClick={onCancel}
          className="rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400"
        >
          Cancelar
        </button>
      </div>
    ) : null}

    {!isAreaSpell && validationMessage ? (
      <p className="mt-3 text-xs text-rose-300">{validationMessage}</p>
    ) : null}

    {onShowAreaHint ? (
      <p className="mt-3 text-xs text-slate-500">
        Clique no grid para escolher a ancora. O preview usa o Map como autoridade geometrica.
      </p>
    ) : null}
  </>
);
