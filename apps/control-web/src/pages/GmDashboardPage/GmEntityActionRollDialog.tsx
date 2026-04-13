import { useState } from "react";
import { ConcentrationSaveControl } from "../../features/combat-ui/components/ConcentrationSaveControl";
import { participantHasActiveConcentration } from "../../features/combat-ui/combatUi.helpers";
import { RollResultCard } from "../../features/rolls/components/RollResultCard";
import type {
  CombatEntityActionResult,
  CombatParticipant,
} from "../../shared/api/combatRepo";
import { combatRepo } from "../../shared/api/combatRepo";
import {
  getDamageRollCount,
  getDamageRollSides,
  formatDamageDiceExpression,
} from "../../shared/utils/diceExpression";
import { GmActionOverrideDialog } from "../../features/combat-ui/gm/GmActionOverrideDialog";
import { D20_VALUES, formatSigned, formatDamageBreakdown } from "./gmEntityActionRollHelpers";
import { GmDamageRollSection } from "./GmDamageRollSection";

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
  const [concentrationRollMode, setConcentrationRollMode] = useState<"system" | "manual">("system");
  const [concentrationManualRoll, setConcentrationManualRoll] = useState("");
  const [result, setResult] = useState<CombatEntityActionResult | null>(null);
  const targetHasConcentration = participantHasActiveConcentration(target);

  const [overrideDialogOpen, setOverrideDialogOpen] = useState(false);
  const [overrideResourceName, setOverrideResourceName] = useState("");
  const [pendingOverridePayload, setPendingOverridePayload] = useState<{
    manual_roll?: number;
    roll_source: "manual" | "system";
  } | null>(null);

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
    override_resource_limit?: boolean;
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
        concentration_roll_source: concentrationRollMode,
        concentration_manual_roll:
          targetHasConcentration && concentrationRollMode === "manual"
            ? Number.parseInt(concentrationManualRoll, 10) || null
            : null,
        override_resource_limit: payload.override_resource_limit,
      });
      setResult(resolved);
      setManualDamageRolls([]);
      setDamageMode("choose");
      if (!resolved.damage_roll_required) {
        await onResolved?.(resolved);
      }
    } catch (err: any) {
      if (err?.status === 409 && err?.data?.resource_limit_exceeded) {
        setOverrideResourceName(err.data.resource || "Ação");
        setPendingOverridePayload(payload);
        setOverrideDialogOpen(true);
      } else {
        setError(err?.data?.detail || err?.message || "Falha ao resolver a acao");
      }
    } finally {
      if (!overrideDialogOpen) setLoading(false);
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

  const handleSelectManualDamageRoll = (value: number) => {
    const nextRolls = [...manualDamageRolls, value];
    if (nextRolls.length >= damageRollCount) {
      setManualDamageRolls([]);
      void submitDamage({ roll_source: "manual", manual_rolls: nextRolls });
      return;
    }
    setManualDamageRolls(nextRolls);
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

            {pendingDamage ? (
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
                <GmDamageRollSection
                  damageMode={damageMode}
                  damageRollCount={damageRollCount}
                  damageRollValues={damageRollValues}
                  effectiveDamageDiceLabel={effectiveDamageDiceLabel}
                  isCritical={Boolean(result.is_critical)}
                  loading={loading}
                  manualDamageRolls={manualDamageRolls}
                  onBack={() => setDamageMode("choose")}
                  onClearManualRolls={() => setManualDamageRolls([])}
                  onSelectManualRoll={handleSelectManualDamageRoll}
                  onSetDamageMode={setDamageMode}
                  onSubmitDamage={(payload) => void submitDamage(payload)}
                />
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
          <div className="mt-5 space-y-3">
            <div className="grid grid-cols-2 gap-3">
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
            <button
              type="button"
              onClick={onClose}
              className="w-full rounded-2xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-rose-200 hover:bg-rose-500/20"
            >
              Cancelar
            </button>
          </div>
        ) : null}

        {!result && attackMode === "virtual" ? (
          <div className="mt-5 flex gap-3">
            <button
              type="button"
              disabled={loading}
              onClick={() => void submitAction({ roll_source: "system" })}
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
                  onClick={() => void submitAction({ roll_source: "manual", manual_roll: value })}
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

      <GmActionOverrideDialog
        isOpen={overrideDialogOpen}
        onClose={() => {
          setOverrideDialogOpen(false);
          setPendingOverridePayload(null);
          setLoading(false);
        }}
        onConfirm={() => {
          if (pendingOverridePayload) {
            void submitAction({ ...pendingOverridePayload, override_resource_limit: true });
          }
          setOverrideDialogOpen(false);
          setPendingOverridePayload(null);
        }}
        resourceName={overrideResourceName}
        isSubmitting={loading}
      />
    </div>
  );
};
