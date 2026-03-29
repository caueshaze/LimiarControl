import { RollResultCard } from "../../features/rolls/components/RollResultCard";
import type { CombatEntityActionResult, CombatParticipant } from "../../shared/api/combatRepo";
import { formatDamageBreakdown, formatSigned } from "./gmEntityActionRollDialog.helpers";

type Props = {
  actionName: string;
  damageMode: "choose" | "manual" | "virtual";
  damageRollCount: number;
  damageRollValues: number[];
  effectiveDamageDiceLabel: string;
  loading: boolean;
  manualDamageRolls: number[];
  onClose: () => void;
  onDamageModeChange: (mode: "choose" | "manual" | "virtual") => void;
  onManualDamageRollAdd: (value: number) => void;
  onManualDamageRollsClear: () => void;
  onSubmitDamageManual: (rolls: number[]) => void;
  onSubmitDamageVirtual: () => void;
  onSubmitFixedDamage: () => void;
  result: CombatEntityActionResult;
  target: CombatParticipant;
};

export const GmActionResultPanel = ({
  actionName,
  damageMode,
  damageRollCount,
  damageRollValues,
  effectiveDamageDiceLabel,
  loading,
  manualDamageRolls,
  onClose,
  onDamageModeChange,
  onManualDamageRollAdd,
  onManualDamageRollsClear,
  onSubmitDamageManual,
  onSubmitDamageVirtual,
  onSubmitFixedDamage,
  result,
  target,
}: Props) => {
  const pendingDamage = Boolean(result.damage_roll_required && result.pending_attack_id);

  const attackBonusText =
    result.attack_bonus != null
      ? formatSigned(result.attack_bonus)
      : "calculado automaticamente";

  const damageProfile =
    result.damage_dice != null
      ? `${effectiveDamageDiceLabel}${typeof result.damage_bonus === "number" ? ` ${result.damage_bonus >= 0 ? "+" : "-"} ${Math.abs(result.damage_bonus)}` : ""}`
      : "calculado automaticamente";

  return (
    <div className="mt-5 space-y-4">
      {result.roll_result ? <RollResultCard result={result.roll_result} /> : null}

      <div className="rounded-2xl border border-amber-500/20 bg-amber-500/10 px-4 py-3">
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-amber-200">
          {pendingDamage ? "Acerto confirmado" : "Resultado final"}
        </p>
        <p className="mt-2 text-sm text-slate-100">
          {result.is_hit
            ? pendingDamage
              ? `${actionName} acertou ${result.target_display_name ?? target.display_name}. Agora role o dano separadamente${result.is_critical ? ` como critico (${effectiveDamageDiceLabel})` : ""}.`
              : `${actionName} acertou ${result.target_display_name ?? target.display_name} e causou ${result.damage} de dano.`
            : `${actionName} nao acertou ${result.target_display_name ?? target.display_name}.`}
        </p>
        {result.roll_result ? (
          <p className="mt-2 text-xs text-slate-300">
            Ataque: d20 {attackBonusText} vs AC {result.target_ac ?? "-"}
          </p>
        ) : null}
        {result.is_hit && !pendingDamage ? (
          <p className="mt-1 text-xs text-slate-400">{formatDamageBreakdown(result)}</p>
        ) : null}
        {result.is_hit && !pendingDamage ? (
          <p className="mt-1 text-xs text-slate-400">Perfil de dano: {damageProfile}</p>
        ) : null}
      </div>

      {pendingDamage && damageMode === "choose" ? (
        damageRollCount > 0 ? (
          <div className="space-y-3">
            <p className="text-xs text-slate-400">
              {result.is_critical
                ? `Critico confirmado. Escolha como rolar o dano de ${effectiveDamageDiceLabel}.`
                : `Escolha como rolar o dano de ${effectiveDamageDiceLabel}.`}
            </p>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => onDamageModeChange("virtual")}
                className="rounded-2xl bg-rose-600 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white hover:bg-rose-500"
              >
                Virtual
              </button>
              <button
                type="button"
                onClick={() => onDamageModeChange("manual")}
                className="rounded-2xl border border-slate-600 bg-slate-800 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-slate-200 hover:bg-slate-700"
              >
                Manual
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-xs text-slate-400">
              Essa acao nao usa dado de dano. Aplique o dano fixo para concluir.
            </p>
            <button
              type="button"
              disabled={loading}
              onClick={onSubmitFixedDamage}
              className="w-full rounded-full bg-rose-600 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white disabled:opacity-50"
            >
              {loading ? "..." : "Aplicar dano"}
            </button>
          </div>
        )
      ) : null}

      {pendingDamage && damageMode === "virtual" ? (
        <div className="flex gap-3">
          <button
            type="button"
            disabled={loading}
            onClick={onSubmitDamageVirtual}
            className="flex-1 rounded-full bg-rose-600 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white disabled:opacity-50"
          >
            {loading ? "..." : "Rolar dano"}
          </button>
          <button
            type="button"
            onClick={() => onDamageModeChange("choose")}
            className="rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400"
          >
            Voltar
          </button>
        </div>
      ) : null}

      {pendingDamage && damageMode === "manual" ? (
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
                onClick={() => {
                  const nextRolls = [...manualDamageRolls, value];
                  if (nextRolls.length >= damageRollCount) {
                    onSubmitDamageManual(nextRolls);
                    return;
                  }
                  onManualDamageRollAdd(value);
                }}
                className="rounded-xl border border-slate-700 bg-slate-900 px-2 py-3 text-center text-lg font-bold text-white transition-colors hover:border-rose-500/50 hover:bg-slate-800 disabled:opacity-50"
              >
                {value}
              </button>
            ))}
          </div>

          <div className="flex gap-3">
            <button
              type="button"
              onClick={onManualDamageRollsClear}
              className="flex-1 rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400"
            >
              Limpar
            </button>
            <button
              type="button"
              onClick={() => {
                onManualDamageRollsClear();
                onDamageModeChange("choose");
              }}
              className="flex-1 rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400"
            >
              Voltar
            </button>
          </div>
        </div>
      ) : null}

      {!pendingDamage ? (
        <button
          type="button"
          onClick={onClose}
          className="w-full rounded-full bg-slate-800 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-slate-200 hover:bg-slate-700"
        >
          Fechar
        </button>
      ) : null}
    </div>
  );
};
