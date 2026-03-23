import { useState } from "react";
import { RollResultCard } from "../../../features/rolls/components/RollResultCard";
import type { AbilityName } from "../../../entities/roll/rollResolution.types";
import type {
  CombatParticipant,
  CombatSpellMode,
  CombatSpellResult,
} from "../../../shared/api/combatRepo";
import { combatRepo } from "../../../shared/api/combatRepo";
import {
  formatDamageDiceExpression,
  getDamageRollCount,
  getDamageRollSides,
} from "../../../shared/utils/diceExpression";
import type { CombatSpellOption } from "./types";

type Props = {
  actorParticipantId: string;
  onClose: () => void;
  onResolved?: (result: CombatSpellResult) => void | Promise<void>;
  sessionId: string;
  spell: CombatSpellOption;
  spellDamageType: string;
  spellEffectBonus: string;
  spellEffectDice: string;
  spellMode: CombatSpellMode;
  spellSaveAbility: AbilityName | "";
  target: CombatParticipant;
};

const D20_VALUES = Array.from({ length: 20 }, (_, i) => i + 1);

const parseBonus = (value: string) => {
  const parsed = Number.parseInt(value.trim(), 10);
  return Number.isFinite(parsed) ? parsed : 0;
};

const formatSpellEffectBreakdown = (result: CombatSpellResult) => {
  const rolls = result.effect_rolls ?? [];
  const effectDiceLabel =
    formatDamageDiceExpression(result.effect_dice, Boolean(result.is_critical)) ??
    result.effect_dice;
  const effectTotal = result.effect_kind === "healing" ? result.healing : result.damage;

  if (!rolls.length) {
    return `Base ${result.base_effect ?? 0}${result.effect_bonus ? ` ${result.effect_bonus >= 0 ? "+" : "-"} ${Math.abs(result.effect_bonus)}` : ""} = ${effectTotal}`;
  }
  return `${effectDiceLabel}: [${rolls.join(", ")}]${result.effect_bonus ? ` ${result.effect_bonus >= 0 ? "+" : "-"} ${Math.abs(result.effect_bonus)}` : ""} = ${effectTotal}`;
};

export const PlayerSpellCastDialog = ({
  actorParticipantId,
  onClose,
  onResolved,
  sessionId,
  spell,
  spellDamageType,
  spellEffectBonus,
  spellEffectDice,
  spellMode,
  spellSaveAbility,
  target,
}: Props) => {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [attackMode, setAttackMode] = useState<"choose" | "manual" | "virtual">("choose");
  const [effectMode, setEffectMode] = useState<"choose" | "manual" | "virtual">("choose");
  const [manualEffectRolls, setManualEffectRolls] = useState<number[]>([]);
  const [result, setResult] = useState<CombatSpellResult | null>(null);

  const pendingEffect = Boolean(result?.effect_roll_required && result?.pending_spell_id);
  const effectDiceLabel =
    formatDamageDiceExpression(result?.effect_dice ?? spellEffectDice, Boolean(result?.is_critical)) ??
    result?.effect_dice ??
    spellEffectDice;
  const effectRollCount = getDamageRollCount(result?.effect_dice ?? spellEffectDice, Boolean(result?.is_critical));
  const effectRollSides = getDamageRollSides(result?.effect_dice ?? spellEffectDice);
  const effectRollValues = Array.from({ length: effectRollSides }, (_, i) => i + 1);
  const effectKindLabel = result?.effect_kind === "healing" || spellMode === "heal" ? "cura" : "dano";
  const parsedBonus = parseBonus(spellEffectBonus);

  const submitCast = async (payload?: {
    manual_roll?: number;
    roll_source?: "manual" | "system";
  }) => {
    setLoading(true);
    setError(null);

    try {
      const resolved = await combatRepo.castSpell(sessionId, {
        actor_participant_id: actorParticipantId,
        target_ref_id: target.ref_id,
        spell_canonical_key: spell.canonicalKey,
        spell_id: spell.canonicalKey,
        spell_mode: spellMode,
        slot_level: spell.level > 0 ? spell.level : null,
        roll_source: payload?.roll_source ?? "system",
        manual_roll: payload?.manual_roll ?? null,
        damage_dice: spellMode === "heal" ? null : spellEffectDice || null,
        damage_bonus: spellMode === "heal" ? null : parsedBonus,
        heal_dice: spellMode === "heal" ? spellEffectDice || null : null,
        heal_bonus: spellMode === "heal" ? parsedBonus : null,
        damage_type: spellMode === "heal" ? null : spellDamageType || null,
        save_ability: spellMode === "saving_throw" ? spellSaveAbility || null : null,
      });
      setResult(resolved);
      setManualEffectRolls([]);
      setEffectMode("choose");
      if (!resolved.effect_roll_required) {
        await onResolved?.(resolved);
      }
    } catch (err: any) {
      setError(err?.data?.detail || err?.message || "Falha ao conjurar magia");
    } finally {
      setLoading(false);
    }
  };

  const submitEffect = async (payload: {
    manual_rolls?: number[];
    roll_source: "manual" | "system";
  }) => {
    if (!result?.pending_spell_id) return;
    setLoading(true);
    setError(null);

    try {
      const resolved = await combatRepo.castSpellEffect(sessionId, {
        actor_participant_id: actorParticipantId,
        pending_spell_id: result.pending_spell_id,
        roll_source: payload.roll_source,
        manual_rolls: payload.manual_rolls ?? null,
      });
      setResult(resolved);
      await onResolved?.(resolved);
    } catch (err: any) {
      setError(err?.data?.detail || err?.message || `Falha ao rolar ${effectKindLabel}`);
    } finally {
      setLoading(false);
    }
  };

  const outcomeLabel =
    result?.action_kind === "saving_throw"
      ? result.is_saved
        ? "Save bem-sucedido"
        : "Save falhou"
      : result?.is_critical
        ? "Acerto critico"
        : result?.is_hit
          ? "Acerto"
          : result?.action_kind === "spell_attack"
            ? "Errou"
            : result?.effect_kind === "healing"
              ? "Cura"
              : "Resultado";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 px-4">
      <div className="w-full max-w-md rounded-3xl border border-fuchsia-400/30 bg-void-950 p-6 text-slate-100 shadow-2xl shadow-fuchsia-950/30">
        <p className="text-xs uppercase tracking-[0.3em] text-fuchsia-200">Magia</p>
        <h2 className="mt-3 text-2xl font-semibold text-white">{spell.name}</h2>
        <p className="mt-2 text-sm text-slate-300">
          Alvo: <span className="font-semibold text-white">{target.display_name}</span>
        </p>
        <p className="mt-1 text-sm text-slate-400">
          Fluxo: {spellMode.replaceAll("_", " ")}
          {spellMode !== "heal" && spellDamageType ? ` · ${spellDamageType}` : ""}
          {spellMode === "saving_throw" && spellSaveAbility ? ` · save ${spellSaveAbility}` : ""}
        </p>

        {error && (
          <div className="mt-4 rounded-2xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            {error}
          </div>
        )}

        {result ? (
          <div className="mt-5 space-y-4">
            {result.roll_result ? <RollResultCard result={result.roll_result} /> : null}

            <div className="rounded-2xl border border-fuchsia-500/20 bg-fuchsia-950/30 px-4 py-3">
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-fuchsia-300">
                {pendingEffect ? "Efeito confirmado" : outcomeLabel}
              </p>
              <p className="mt-2 text-sm text-slate-100">
                {result.action_kind === "spell_attack"
                  ? result.is_hit
                    ? pendingEffect
                      ? `${result.spell_name} acertou ${result.target_display_name}. Agora role o ${effectKindLabel}${result.is_critical ? ` critico (${effectDiceLabel})` : ""}.`
                      : `${result.spell_name} acertou ${result.target_display_name} e ${result.effect_kind === "healing" ? `curou ${result.healing}` : `causou ${result.damage} de dano`}.`
                    : `${result.spell_name} nao acertou ${result.target_display_name}.`
                  : result.action_kind === "saving_throw"
                    ? result.is_saved
                      ? `${result.target_display_name} passou no save e evitou o efeito desta fase.`
                      : pendingEffect
                        ? `${result.target_display_name} falhou no save. Agora role o ${effectKindLabel} de ${effectDiceLabel}.`
                        : `${result.target_display_name} falhou no save e ${result.effect_kind === "healing" ? `recebeu ${result.healing} HP` : `sofreu ${result.damage} de dano`}.`
                    : pendingEffect
                      ? `${result.spell_name} foi conjurada. Agora role o ${effectKindLabel} de ${effectDiceLabel}.`
                      : result.effect_kind === "healing"
                        ? `${result.spell_name} restaurou ${result.healing} HP em ${result.target_display_name}.`
                        : `${result.spell_name} causou ${result.damage} de dano em ${result.target_display_name}.`}
              </p>

              {!pendingEffect && (result.damage > 0 || result.healing > 0) ? (
                <p className="mt-2 text-xs text-slate-300">{formatSpellEffectBreakdown(result)}</p>
              ) : null}
              {!pendingEffect && result.new_hp != null ? (
                <p className="mt-2 text-xs text-slate-400">
                  PV atuais do alvo: {result.new_hp}
                </p>
              ) : null}
            </div>

            {pendingEffect && effectMode === "choose" ? (
              effectRollCount > 0 ? (
                <div className="space-y-3">
                  <p className="text-xs text-slate-400">
                    Escolha como rolar o {effectKindLabel} de {effectDiceLabel}.
                  </p>
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      type="button"
                      onClick={() => setEffectMode("virtual")}
                      className="rounded-2xl bg-fuchsia-600 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white hover:bg-fuchsia-500"
                    >
                      Virtual
                    </button>
                    <button
                      type="button"
                      onClick={() => setEffectMode("manual")}
                      className="rounded-2xl border border-slate-600 bg-slate-800 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-slate-200 hover:bg-slate-700"
                    >
                      Manual
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  type="button"
                  disabled={loading}
                  onClick={() => {
                    void submitEffect({ roll_source: "system" });
                  }}
                  className="w-full rounded-full bg-fuchsia-600 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white disabled:opacity-50"
                >
                  {loading ? "..." : `Aplicar ${effectKindLabel}`}
                </button>
              )
            ) : null}

            {pendingEffect && effectMode === "virtual" ? (
              <div className="flex gap-3">
                <button
                  type="button"
                  disabled={loading}
                  onClick={() => {
                    void submitEffect({ roll_source: "system" });
                  }}
                  className="flex-1 rounded-full bg-fuchsia-600 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white disabled:opacity-50"
                >
                  {loading ? "..." : `Rolar ${effectKindLabel}`}
                </button>
                <button
                  type="button"
                  onClick={() => setEffectMode("choose")}
                  className="rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400"
                >
                  Voltar
                </button>
              </div>
            ) : null}

            {pendingEffect && effectMode === "manual" ? (
              <div className="space-y-3">
                <p className="text-xs text-slate-400">
                  Escolha cada dado manualmente ({manualEffectRolls.length}/{effectRollCount}).
                </p>

                {manualEffectRolls.length > 0 ? (
                  <div className="rounded-2xl border border-slate-700 bg-slate-900/60 px-3 py-2 text-xs text-slate-300">
                    Dados escolhidos: {manualEffectRolls.join(", ")}
                  </div>
                ) : null}

                <div className="grid grid-cols-5 gap-2">
                  {effectRollValues.map((value) => (
                    <button
                      key={value}
                      type="button"
                      disabled={loading}
                      onClick={() => {
                        const nextRolls = [...manualEffectRolls, value];
                        if (nextRolls.length >= effectRollCount) {
                          setManualEffectRolls([]);
                          void submitEffect({
                            roll_source: "manual",
                            manual_rolls: nextRolls,
                          });
                          return;
                        }
                        setManualEffectRolls(nextRolls);
                      }}
                      className="rounded-xl border border-slate-700 bg-slate-900 px-2 py-3 text-center text-lg font-bold text-white transition-colors hover:border-fuchsia-500/50 hover:bg-slate-800 disabled:opacity-50"
                    >
                      {value}
                    </button>
                  ))}
                </div>

                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => setManualEffectRolls([])}
                    className="flex-1 rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400"
                  >
                    Limpar
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setManualEffectRolls([]);
                      setEffectMode("choose");
                    }}
                    className="flex-1 rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400"
                  >
                    Voltar
                  </button>
                </div>
              </div>
            ) : null}

            {!pendingEffect ? (
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

        {!result && spellMode === "spell_attack" && attackMode === "choose" ? (
          <div className="mt-5 grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setAttackMode("virtual")}
              className="rounded-2xl bg-fuchsia-600 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white hover:bg-fuchsia-500"
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

        {!result && spellMode === "spell_attack" && attackMode === "virtual" ? (
          <div className="mt-5 flex gap-3">
            <button
              type="button"
              disabled={loading}
              onClick={() => {
                void submitCast({ roll_source: "system" });
              }}
              className="flex-1 rounded-full bg-fuchsia-600 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white disabled:opacity-50"
            >
              {loading ? "..." : "Rolar ataque magico"}
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

        {!result && spellMode === "spell_attack" && attackMode === "manual" ? (
          <div className="mt-5 space-y-3">
            <p className="text-xs text-slate-400">Selecione o d20 manual do ataque.</p>

            <div className="grid grid-cols-5 gap-2">
              {D20_VALUES.map((value) => (
                <button
                  key={value}
                  type="button"
                  disabled={loading}
                  onClick={() => {
                    void submitCast({ roll_source: "manual", manual_roll: value });
                  }}
                  className="rounded-xl border border-slate-700 bg-slate-900 px-2 py-3 text-center text-lg font-bold text-white transition-colors hover:border-fuchsia-500/50 hover:bg-slate-800 disabled:opacity-50"
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

        {!result && spellMode !== "spell_attack" ? (
          <div className="mt-5 flex gap-3">
            <button
              type="button"
              disabled={loading}
              onClick={() => {
                void submitCast();
              }}
              className="flex-1 rounded-full bg-fuchsia-600 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white disabled:opacity-50"
            >
              {loading ? "..." : "Conjurar"}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400"
            >
              Fechar
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
};
