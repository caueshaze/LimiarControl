import { useState } from "react";
import { RollResultCard } from "../../features/rolls/components/RollResultCard";
import type {
  CombatEntityActionResult,
  CombatParticipant,
} from "../../shared/api/combatRepo";
import { combatRepo } from "../../shared/api/combatRepo";
import {
  formatDamageDiceExpression,
  getDamageRollCount,
  getDamageRollSides,
} from "../../shared/utils/diceExpression";

type Props = {
  actionDescription?: string | null;
  actionId: string;
  actionKind: "weapon_attack" | "spell_attack";
  actionName: string;
  actorParticipantId: string;
  onClose: () => void;
  onResolved?: (result: CombatEntityActionResult) => void | Promise<void>;
  sessionId: string;
  target: CombatParticipant;
};

const D20_VALUES = Array.from({ length: 20 }, (_, i) => i + 1);

const formatSigned = (value: number) => `${value >= 0 ? "+" : ""}${value}`;

const formatDamageBreakdown = (result: CombatEntityActionResult) => {
  const rolls = result.damage_rolls ?? [];
  const damageDiceLabel =
    formatDamageDiceExpression(result.damage_dice, Boolean(result.is_critical)) ??
    result.damage_dice;
  if (!rolls.length) {
    return `Base ${result.base_damage ?? 0}${result.damage_bonus ? ` ${result.damage_bonus >= 0 ? "+" : "-"} ${Math.abs(result.damage_bonus)}` : ""} = ${result.damage}`;
  }
  const rollText = rolls.join(", ");
  return `${damageDiceLabel}: [${rollText}]${result.damage_bonus ? ` ${result.damage_bonus >= 0 ? "+" : "-"} ${Math.abs(result.damage_bonus)}` : ""} = ${result.damage}`;
};

export const GmEntityActionRollDialog = ({
  actionDescription,
  actionId,
  actionKind,
  actionName,
  actorParticipantId,
  onClose,
  onResolved,
  sessionId,
  target,
}: Props) => {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [attackMode, setAttackMode] = useState<"choose" | "manual" | "virtual">("choose");
  const [damageMode, setDamageMode] = useState<"choose" | "manual" | "virtual">("choose");
  const [manualDamageRolls, setManualDamageRolls] = useState<number[]>([]);
  const [result, setResult] = useState<CombatEntityActionResult | null>(null);

  const pendingDamage = Boolean(result?.damage_roll_required && result?.pending_attack_id);
  const damageRollCount = getDamageRollCount(result?.damage_dice, Boolean(result?.is_critical));
  const damageRollSides = getDamageRollSides(result?.damage_dice);
  const damageRollValues = Array.from({ length: damageRollSides }, (_, i) => i + 1);
  const effectiveDamageDiceLabel =
    formatDamageDiceExpression(result?.damage_dice, Boolean(result?.is_critical)) ??
    result?.damage_dice ??
    "dano";

  const submitAction = async (payload: {
    manual_roll?: number;
    roll_source: "manual" | "system";
  }) => {
    setLoading(true);
    setError(null);

    try {
      const resolved = await combatRepo.entityAction(sessionId, {
        actor_participant_id: actorParticipantId,
        combat_action_id: actionId,
        target_ref_id: target.ref_id,
        roll_source: payload.roll_source,
        manual_roll: payload.manual_roll ?? null,
      });
      setResult(resolved);
      setManualDamageRolls([]);
      setDamageMode("choose");
      if (!resolved.damage_roll_required) {
        await onResolved?.(resolved);
      }
    } catch (err: any) {
      setError(err?.data?.detail || err?.message || "Falha ao resolver a acao");
    } finally {
      setLoading(false);
    }
  };

  const submitDamage = async (payload: {
    manual_rolls?: number[];
    roll_source: "manual" | "system";
  }) => {
    if (!result?.pending_attack_id) return;
    setLoading(true);
    setError(null);

    try {
      const resolved = await combatRepo.entityActionDamage(sessionId, {
        actor_participant_id: actorParticipantId,
        pending_attack_id: result.pending_attack_id,
        roll_source: payload.roll_source,
        manual_rolls: payload.manual_rolls ?? null,
      });
      setResult(resolved);
      await onResolved?.(resolved);
    } catch (err: any) {
      setError(err?.data?.detail || err?.message || "Falha ao rolar dano");
    } finally {
      setLoading(false);
    }
  };

  const attackBonusText =
    result?.attack_bonus != null
      ? formatSigned(result.attack_bonus)
      : "calculado automaticamente";
  const damageProfile =
    result?.damage_dice != null
      ? `${effectiveDamageDiceLabel}${typeof result.damage_bonus === "number" ? ` ${result.damage_bonus >= 0 ? "+" : "-"} ${Math.abs(result.damage_bonus)}` : ""}`
      : "calculado automaticamente";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 px-4">
      <div className="w-full max-w-md rounded-3xl border border-rose-400/30 bg-void-950 p-6 text-slate-100 shadow-2xl shadow-rose-900/30">
        <p className="text-xs uppercase tracking-[0.3em] text-rose-200">
          {actionKind === "spell_attack" ? "Ataque magico" : "Ataque de NPC"}
        </p>
        <h2 className="mt-3 text-2xl font-semibold text-white">{actionName}</h2>
        <p className="mt-2 text-sm text-slate-300">
          Alvo: <span className="font-semibold text-white">{target.display_name}</span>
        </p>
        {actionDescription ? (
          <p className="mt-2 text-sm text-slate-400">{actionDescription}</p>
        ) : null}

        {error && (
          <div className="mt-4 rounded-2xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            {error}
          </div>
        )}

        {result ? (
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
                <p className="mt-1 text-xs text-slate-400">
                  {formatDamageBreakdown(result)}
                </p>
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
                      onClick={() => setDamageMode("virtual")}
                      className="rounded-2xl bg-rose-600 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white hover:bg-rose-500"
                    >
                      Virtual
                    </button>
                    <button
                      type="button"
                      onClick={() => setDamageMode("manual")}
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
                    onClick={() => {
                      void submitDamage({ roll_source: "system" });
                    }}
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
                  onClick={() => {
                    void submitDamage({ roll_source: "system" });
                  }}
                  className="flex-1 rounded-full bg-rose-600 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white disabled:opacity-50"
                >
                  {loading ? "..." : "Rolar dano"}
                </button>
                <button
                  type="button"
                  onClick={() => setDamageMode("choose")}
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
                          setManualDamageRolls([]);
                          void submitDamage({
                            roll_source: "manual",
                            manual_rolls: nextRolls,
                          });
                          return;
                        }
                        setManualDamageRolls(nextRolls);
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
                    onClick={() => setManualDamageRolls([])}
                    className="flex-1 rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400"
                  >
                    Limpar
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setManualDamageRolls([]);
                      setDamageMode("choose");
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
        ) : null}

        {!result && attackMode === "choose" ? (
          <div className="mt-5 grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setAttackMode("virtual")}
              className="rounded-2xl bg-rose-600 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white hover:bg-rose-500"
            >
              Virtual
            </button>
            <button
              type="button"
              onClick={() => setAttackMode("manual")}
              className="rounded-2xl border border-slate-600 bg-slate-800 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-slate-200 hover:bg-slate-700"
            >
              Manual
            </button>
          </div>
        ) : null}

        {!result && attackMode === "virtual" ? (
          <div className="mt-5 flex gap-3">
            <button
              type="button"
              disabled={loading}
              onClick={() => {
                void submitAction({ roll_source: "system" });
              }}
              className="flex-1 rounded-full bg-rose-600 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white disabled:opacity-50"
            >
              {loading ? "..." : "Rolar ataque"}
            </button>
            <button
              type="button"
              onClick={() => setAttackMode("choose")}
              className="rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400"
            >
              Voltar
            </button>
          </div>
        ) : null}

        {!result && attackMode === "manual" ? (
          <div className="mt-5 space-y-3">
            <p className="text-xs text-slate-400">Selecione o d20 manual da acao.</p>

            <div className="grid grid-cols-5 gap-2">
              {D20_VALUES.map((value) => (
                <button
                  key={value}
                  type="button"
                  disabled={loading}
                  onClick={() => {
                    void submitAction({ roll_source: "manual", manual_roll: value });
                  }}
                  className="rounded-xl border border-slate-700 bg-slate-900 px-2 py-3 text-center text-lg font-bold text-white transition-colors hover:border-rose-500/50 hover:bg-slate-800 disabled:opacity-50"
                >
                  {value}
                </button>
              ))}
            </div>

            <button
              type="button"
              onClick={() => setAttackMode("choose")}
              className="rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400"
            >
              Voltar
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
};
