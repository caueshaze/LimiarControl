import { useState } from "react";
import { RollResultCard } from "../../../features/rolls/components/RollResultCard";
import { ConcentrationSaveControl } from "../../../features/combat-ui/components/ConcentrationSaveControl";
import { participantHasActiveConcentration } from "../../../features/combat-ui/combatUi.helpers";
import { markRollEventKnown } from "../../../features/rolls/knownRollEvents";
import type {
  CombatAttackResult,
  CombatParticipant,
} from "../../../shared/api/combatRepo";
import { combatRepo } from "../../../shared/api/combatRepo";
import {
  formatDamageDiceExpression,
  getDamageRollCount,
  getDamageRollSides,
} from "../../../shared/utils/diceExpression";
import type { PlayerBoardWeaponSummary } from "../playerBoard.types";

type Props = {
  actorParticipantId: string;
  onClose: () => void;
  onResolved?: (result: CombatAttackResult) => void | Promise<void>;
  sessionId: string;
  target: CombatParticipant;
  weapon: PlayerBoardWeaponSummary | null;
};

const D20_VALUES = Array.from({ length: 20 }, (_, i) => i + 1);

const formatSigned = (value: number) => `${value >= 0 ? "+" : ""}${value}`;

const formatDamageBreakdown = (result: CombatAttackResult) => {
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

export const PlayerAttackRollDialog = ({
  actorParticipantId,
  onClose,
  onResolved,
  sessionId,
  target,
  weapon,
}: Props) => {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [attackMode, setAttackMode] = useState<"choose" | "manual" | "virtual">("choose");
  const [damageMode, setDamageMode] = useState<"choose" | "manual" | "virtual">("choose");
  const [manualDamageRolls, setManualDamageRolls] = useState<number[]>([]);
  const [concentrationRollMode, setConcentrationRollMode] = useState<"system" | "manual">("system");
  const [concentrationManualRoll, setConcentrationManualRoll] = useState("");
  const [result, setResult] = useState<CombatAttackResult | null>(null);
  const targetHasConcentration = participantHasActiveConcentration(target);

  const pendingDamage = Boolean(result?.damage_roll_required && result?.pending_attack_id);
  const damageRollCount = getDamageRollCount(result?.damage_dice, Boolean(result?.is_critical));
  const damageRollSides = getDamageRollSides(result?.damage_dice);
  const damageRollValues = Array.from({ length: damageRollSides }, (_, i) => i + 1);
  const effectiveDamageDiceLabel =
    formatDamageDiceExpression(result?.damage_dice, Boolean(result?.is_critical)) ??
    result?.damage_dice ??
    "dano";

  const submitAttack = async (payload: {
    manual_roll?: number;
    roll_source: "manual" | "system";
  }) => {
    setLoading(true);
    setError(null);

    try {
      const resolved = await combatRepo.attack(sessionId, {
        actor_participant_id: actorParticipantId,
        target_ref_id: target.ref_id,
        roll_source: payload.roll_source,
        manual_roll: payload.manual_roll ?? null,
      });
      if (resolved.roll_result?.event_id) {
        markRollEventKnown(resolved.roll_result.event_id);
      }
      setResult(resolved);
      setManualDamageRolls([]);
      setDamageMode("choose");
      if (!resolved.damage_roll_required) {
        await onResolved?.(resolved);
      }
    } catch (err: any) {
      setError(err?.data?.detail || err?.message || "Falha ao resolver ataque");
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
      const resolved = await combatRepo.attackDamage(sessionId, {
        actor_participant_id: actorParticipantId,
        pending_attack_id: result.pending_attack_id,
        roll_source: payload.roll_source,
        manual_rolls: payload.manual_rolls ?? null,
        concentration_roll_source: concentrationRollMode,
        concentration_manual_roll:
          targetHasConcentration && concentrationRollMode === "manual"
            ? Number.parseInt(concentrationManualRoll, 10) || null
            : null,
      });
      setResult(resolved);
      await onResolved?.(resolved);
    } catch (err: any) {
      setError(err?.data?.detail || err?.message || "Falha ao rolar dano");
    } finally {
      setLoading(false);
    }
  };

  const attackBonusLabel = weapon
    ? formatSigned(weapon.attackBonus)
    : "calculado automaticamente";
  const damageLabel = weapon?.damageLabel ?? "1 + modificador de Forca";
  const outcomeLabel = result?.is_critical
    ? "Acerto critico"
    : result?.is_hit
      ? "Acerto"
      : "Errou";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 px-4">
      <div className="w-full max-w-md rounded-3xl border border-limiar-400/30 bg-void-950 p-6 text-slate-100 shadow-2xl shadow-limiar-900/40">
        <p className="text-xs uppercase tracking-[0.3em] text-limiar-200">Ataque</p>
        <h2 className="mt-3 text-2xl font-semibold text-white">
          {weapon?.name ?? "Ataque desarmado"}
        </h2>
        <p className="mt-2 text-sm text-slate-300">
          Alvo: <span className="font-semibold text-white">{target.display_name}</span>
        </p>
        <p className="mt-1 text-sm text-slate-400">
          Bonus de ataque {attackBonusLabel} · Dano {damageLabel}
        </p>

        {error && (
          <div className="mt-4 rounded-2xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            {error}
          </div>
        )}

        {result ? (
          <div className="mt-5 space-y-4">
            <RollResultCard result={result.roll_result} hideDc />

            <div className="rounded-2xl border border-sky-500/20 bg-sky-950/30 px-4 py-3">
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-sky-300">
                {pendingDamage ? "Acerto confirmado" : outcomeLabel}
              </p>
              <p className="mt-2 text-sm text-slate-100">
                {result.is_hit
                  ? pendingDamage
                    ? `${result.weapon_name} acertou ${result.target_display_name}. Agora role o dano separadamente${result.is_critical ? ` como critico (${effectiveDamageDiceLabel})` : ""}.`
                    : `${result.weapon_name} acertou ${result.target_display_name} e causou ${result.damage} de dano${result.damage_type ? ` ${result.damage_type}` : ""}.`
                  : `${result.weapon_name} nao acertou ${result.target_display_name}.`}
              </p>
              {result.is_hit && !pendingDamage ? (
                <p className="mt-2 text-xs text-slate-300">{formatDamageBreakdown(result)}</p>
              ) : null}
              {result.is_hit && !pendingDamage && result.concentration_check?.summary_text ? (
                <p className="mt-2 text-xs text-amber-100">
                  {result.concentration_check.summary_text}
                </p>
              ) : null}
              {result.is_hit && result.new_hp != null && !pendingDamage ? (
                <p className="mt-2 text-xs text-slate-400">
                  PV restantes do alvo: {result.new_hp}
                </p>
              ) : null}
            </div>

            {pendingDamage && damageMode === "choose" ? (
              damageRollCount > 0 ? (
                <div className="space-y-3">
                  {targetHasConcentration ? (
                    <ConcentrationSaveControl
                      disabled={loading}
                      manualValue={concentrationManualRoll}
                      mode={concentrationRollMode}
                      onManualValueChange={setConcentrationManualRoll}
                      onModeChange={setConcentrationRollMode}
                    />
                  ) : null}
                  <p className="text-xs text-slate-400">
                    {result.is_critical
                      ? `Critico confirmado. Escolha como rolar o dano de ${effectiveDamageDiceLabel}.`
                      : `Escolha como rolar o dano de ${effectiveDamageDiceLabel}.`}
                  </p>
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      type="button"
                      onClick={() => setDamageMode("virtual")}
                      className="rounded-2xl bg-limiar-500 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white hover:bg-limiar-400"
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
                  {targetHasConcentration ? (
                    <ConcentrationSaveControl
                      disabled={loading}
                      manualValue={concentrationManualRoll}
                      mode={concentrationRollMode}
                      onManualValueChange={setConcentrationManualRoll}
                      onModeChange={setConcentrationRollMode}
                    />
                  ) : null}
                  <p className="text-xs text-slate-400">
                    Esse ataque nao usa dado de dano. Aplique o dano fixo para concluir.
                  </p>
                  <button
                    type="button"
                    disabled={loading}
                    onClick={() => {
                      void submitDamage({ roll_source: "system" });
                    }}
                    className="w-full rounded-full bg-limiar-500 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white disabled:opacity-50"
                  >
                    {loading ? "..." : "Aplicar dano"}
                  </button>
                </div>
              )
            ) : null}

            {pendingDamage && damageMode === "virtual" ? (
              <div className="space-y-3">
                {targetHasConcentration ? (
                  <ConcentrationSaveControl
                    disabled={loading}
                    manualValue={concentrationManualRoll}
                    mode={concentrationRollMode}
                    onManualValueChange={setConcentrationManualRoll}
                    onModeChange={setConcentrationRollMode}
                  />
                ) : null}
                <div className="flex gap-3">
                  <button
                    type="button"
                    disabled={loading}
                    onClick={() => {
                      void submitDamage({ roll_source: "system" });
                    }}
                    className="flex-1 rounded-full bg-limiar-500 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white disabled:opacity-50"
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
              </div>
            ) : null}

            {pendingDamage && damageMode === "manual" ? (
              <div className="space-y-3">
                {targetHasConcentration ? (
                  <ConcentrationSaveControl
                    disabled={loading}
                    manualValue={concentrationManualRoll}
                    mode={concentrationRollMode}
                    onManualValueChange={setConcentrationManualRoll}
                    onModeChange={setConcentrationRollMode}
                  />
                ) : null}
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
                      className="rounded-xl border border-slate-700 bg-slate-900 px-2 py-3 text-center text-lg font-bold text-white transition-colors hover:border-limiar-500/50 hover:bg-slate-800 disabled:opacity-50"
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
              className="rounded-2xl bg-limiar-500 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white hover:bg-limiar-400"
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
                void submitAttack({ roll_source: "system" });
              }}
              className="flex-1 rounded-full bg-limiar-500 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white disabled:opacity-50"
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
            <p className="text-xs text-slate-400">Selecione o d20 manual do ataque.</p>

            <div className="grid grid-cols-5 gap-2">
              {D20_VALUES.map((value) => (
                <button
                  key={value}
                  type="button"
                  disabled={loading}
                  onClick={() => {
                    void submitAttack({ roll_source: "manual", manual_roll: value });
                  }}
                  className="rounded-xl border border-slate-700 bg-slate-900 px-2 py-3 text-center text-lg font-bold text-white transition-colors hover:border-limiar-500/50 hover:bg-slate-800 disabled:opacity-50"
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
