import { RollResultCard } from "../../../features/rolls/components/RollResultCard";
import {
  formatAppliedDeclarativeEffectsByTarget,
  formatManualNotesByTarget,
  formatVariantAssignmentDebug,
  originLabel,
  resolveTargetVariantLabel,
} from "../../../features/combat-ui/spellVariantUi";
import type { CombatSpellResult } from "../../../shared/api/combatRepo";
import {
  formatAreaTargetOutcome,
  formatEffectInstanceOutcome,
  formatSpellEffectBreakdown,
  getOutcomeLabel,
} from "./spellCastHelpers";

type EffectMode = "choose" | "manual" | "virtual";

type Props = {
  effectDiceLabel: string;
  effectKindLabel: string;
  effectMode: EffectMode;
  effectRollCount: number;
  effectRollValues: number[];
  loading: boolean;
  manualEffectRolls: number[];
  onClose: () => void;
  onEffectModeChange: (mode: EffectMode) => void;
  onManualEffectRollsChange: (rolls: number[]) => void;
  onSubmitEffect: (payload: {
    manual_rolls?: number[];
    roll_source: "manual" | "system";
  }) => void;
  result: CombatSpellResult;
};

export const SpellCastResultPanel = ({
  effectDiceLabel,
  effectKindLabel,
  effectMode,
  effectRollCount,
  effectRollValues,
  loading,
  manualEffectRolls,
  onClose,
  onEffectModeChange,
  onManualEffectRollsChange,
  onSubmitEffect,
  result,
}: Props) => {
  const pendingEffect = Boolean(result.effect_roll_required && result.pending_spell_id);
  const outcomeLabel = getOutcomeLabel(result);
  const hasEffectInstanceOutcomes = Boolean(result.effect_instance_outcomes?.length);
  const hasAreaTargetOutcomes = Boolean(result.area_target_outcomes?.length);
  const guardrailBlockedCount = result.area_target_outcomes?.filter((outcome) => outcome.excluded_by_guardrail).length ?? 0;
  const resolvedVariantLabel = resolveTargetVariantLabel({
    targetVariantAssignments: result.target_variant_assignments,
    manualNotesByTarget: result.manual_notes_by_target,
    selectedVariantKey: result.selected_variant_key,
    targetRefId: null,
    targetParticipantId: null,
  });
  const variantAssignmentLines = formatVariantAssignmentDebug(
    result.target_variant_assignments,
    result.manual_notes_by_target,
  );
  const appliedDeclarativeEffectsByTarget = formatAppliedDeclarativeEffectsByTarget(
    result.applied_declarative_effects_by_target,
    result.manual_notes_by_target,
  );
  const appliedTargetKeys = new Set(
    (result.applied_declarative_effects_by_target ?? []).map(
      (entry) => `${entry.target_participant_id ?? ""}:${entry.target_ref_id ?? ""}`,
    ),
  );
  const manualNoteLines = formatManualNotesByTarget(
    appliedTargetKeys.size
      ? (result.manual_notes_by_target ?? []).filter(
          (entry) =>
            !appliedTargetKeys.has(`${entry.target_participant_id ?? ""}:${entry.target_ref_id ?? ""}`),
        )
      : result.manual_notes_by_target,
  );

  return (
    <div className="mt-5 space-y-4">
      {result.roll_result ? <RollResultCard result={result.roll_result} hideDc /> : null}

      <div className="rounded-2xl border border-fuchsia-500/20 bg-fuchsia-950/30 px-4 py-3">
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-fuchsia-300">
          {pendingEffect ? "Efeito confirmado" : outcomeLabel}
        </p>
        <p className="mt-2 text-sm text-slate-100">
          {result.summary_text
            ? result.summary_text
            : result.action_kind === "spell_attack"
            ? result.is_hit
              ? pendingEffect
                ? `${result.spell_name} acertou ${result.target_display_name}. Agora role o ${effectKindLabel}${result.is_critical ? ` critico (${effectDiceLabel})` : ""}.`
                : `${result.spell_name} acertou ${result.target_display_name} e ${result.effect_kind === "healing" ? `curou ${result.healing}` : `causou ${result.damage} de dano`}.`
              : `${result.spell_name} nao acertou ${result.target_display_name}.`
            : result.action_kind === "saving_throw"
              ? result.is_saved
                ? result.save_success_outcome === "half_damage"
                  ? pendingEffect
                    ? `${result.target_display_name} passou no save. Agora role o ${effectKindLabel} de ${effectDiceLabel}; metade sera aplicada.`
                    : `${result.target_display_name} passou no save e sofreu metade do ${effectKindLabel}: ${result.damage}.`
                  : `${result.target_display_name} passou no save e evitou o ataque!`
                : pendingEffect
                  ? `${result.target_display_name} falhou no save. Agora role o ${effectKindLabel} de ${effectDiceLabel}.`
                  : `${result.target_display_name} falhou no save e ${result.effect_kind === "healing" ? `recebeu ${result.healing} HP` : `sofreu ${result.damage} de dano`}.`
              : pendingEffect
                ? `${result.spell_name} foi conjurada. Agora role o ${effectKindLabel} de ${effectDiceLabel}.`
                : result.effect_kind === "healing"
                  ? `${result.spell_name} restaurou ${result.healing} HP em ${result.target_display_name}.`
                  : `${result.spell_name} causou ${result.damage} de dano em ${result.target_display_name}.`}
        </p>

        {!pendingEffect && hasEffectInstanceOutcomes ? (
          <div className="mt-3 space-y-2 text-xs text-slate-300">
            {result.effect_instance_outcomes?.map((outcome) => (
              <p key={`${outcome.instance_index}:${outcome.target_ref_id}`}>
                {formatEffectInstanceOutcome(result, outcome)}
              </p>
            ))}
          </div>
        ) : null}
        {!pendingEffect && hasAreaTargetOutcomes ? (
          <div className="mt-3 space-y-2 text-xs text-slate-300">
            {result.area_target_outcomes?.map((outcome) => (
              <p key={outcome.target_ref_id}>
                {formatAreaTargetOutcome(outcome)}
              </p>
            ))}
          </div>
        ) : null}
        {!pendingEffect && guardrailBlockedCount > 0 ? (
          <p className="mt-2 text-xs text-amber-100">
            {guardrailBlockedCount} alvo{guardrailBlockedCount !== 1 ? "s" : ""} na área {guardrailBlockedCount === 1 ? "foi excluído" : "foram excluídos"} por regras mecânicas.
          </p>
        ) : null}
        {!pendingEffect && !hasEffectInstanceOutcomes && !hasAreaTargetOutcomes && (result.damage > 0 || result.healing > 0) ? (
          <p className="mt-2 text-xs text-slate-300">{formatSpellEffectBreakdown(result)}</p>
        ) : null}
        {result.area_shape ? (
          <p className="mt-2 text-xs text-slate-300">
            Area {result.area_shape} · {result.target_count ?? result.affected_target_ref_ids?.length ?? 0} alvos · {result.affected_cells?.length ?? 0} celulas
          </p>
        ) : null}
        {result.elemental_affinity_eligible ? (
          <p className="mt-2 text-xs text-amber-100">
            Afinidade Elemental elegível: {result.elemental_affinity_damage_type ?? "tipo"}{typeof result.elemental_affinity_bonus === "number" ? ` · bonus potencial +${result.elemental_affinity_bonus}` : ""}
          </p>
        ) : null}
        {(variantAssignmentLines.length || resolvedVariantLabel || result.context_origin || result.concentration_group) ? (
          <div className="mt-3 space-y-1 text-xs text-sky-100">
            {variantAssignmentLines.length ? (
              variantAssignmentLines.map((line, index) => (
                <p key={`variant:${index}`}>{line}</p>
              ))
            ) : resolvedVariantLabel ? (
              <p>Variante: {resolvedVariantLabel}</p>
            ) : null}
            {originLabel(result.context_origin) ? (
              <p>Origem: {originLabel(result.context_origin)}</p>
            ) : null}
            {result.concentration_group ? (
              <p>Concentração: {result.concentration_group}</p>
            ) : null}
          </div>
        ) : null}
        {appliedDeclarativeEffectsByTarget.length ? (
          <div className="mt-3 space-y-3 text-xs text-emerald-100">
            {appliedDeclarativeEffectsByTarget.map((entry, index) => (
              <div key={`${entry.targetDisplayName}:${index}`} className="space-y-1">
                <p className="font-semibold text-emerald-200">{entry.targetDisplayName}</p>
                {entry.variantLabel ? <p>Variante: {entry.variantLabel}</p> : null}
                {entry.effectLines.map((line, lineIndex) => (
                  <p key={`effect:${index}:${lineIndex}`}>{line}</p>
                ))}
                {entry.manualNoteLines.map((line, lineIndex) => (
                  <p key={`effect-note:${index}:${lineIndex}`}>{line}</p>
                ))}
              </div>
            ))}
          </div>
        ) : null}
        {manualNoteLines.length ? (
          <div className="mt-3 space-y-2 text-xs text-amber-100">
            {manualNoteLines.map((line, index) => (
              <p key={`note:${index}`}>
                {line}
              </p>
            ))}
          </div>
        ) : null}
        {!pendingEffect && result.concentration_check?.summary_text ? (
          <p className="mt-2 text-xs text-amber-100">{result.concentration_check.summary_text}</p>
        ) : null}
        {!pendingEffect && !hasEffectInstanceOutcomes && result.new_hp != null ? (
          <p className="mt-2 text-xs text-slate-400">PV atuais do alvo: {result.new_hp}</p>
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
                onClick={() => onEffectModeChange("virtual")}
                className="rounded-2xl bg-fuchsia-600 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white hover:bg-fuchsia-500"
              >
                Virtual
              </button>
              <button
                type="button"
                onClick={() => onEffectModeChange("manual")}
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
            onClick={() => onSubmitEffect({ roll_source: "system" })}
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
            onClick={() => onSubmitEffect({ roll_source: "system" })}
            className="flex-1 rounded-full bg-fuchsia-600 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white disabled:opacity-50"
          >
            {loading ? "..." : `Rolar ${effectKindLabel}`}
          </button>
          <button
            type="button"
            onClick={() => onEffectModeChange("choose")}
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
                    onManualEffectRollsChange([]);
                    onSubmitEffect({ roll_source: "manual", manual_rolls: nextRolls });
                    return;
                  }
                  onManualEffectRollsChange(nextRolls);
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
              onClick={() => onManualEffectRollsChange([])}
              className="flex-1 rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400"
            >
              Limpar
            </button>
            <button
              type="button"
              onClick={() => {
                onManualEffectRollsChange([]);
                onEffectModeChange("choose");
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
  );
};
