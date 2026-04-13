import type {
  ActiveEffectConditionType,
  ActiveEffectDurationType,
  ActiveEffectKind,
} from "../../../shared/api/combatRepo";
import type { CombatParticipantView } from "../types";
import { useLocale } from "../../../shared/hooks/useLocale";

const NUMERIC_KINDS = new Set<ActiveEffectKind>(["temp_ac_bonus", "attack_bonus", "damage_bonus"]);

type Props = {
  rosterParticipants: CombatParticipantView[];
  submitting: boolean;
  targetParticipantId: string;
  effectKind: ActiveEffectKind;
  conditionType: ActiveEffectConditionType;
  numericValue: string;
  durationType: ActiveEffectDurationType;
  remainingRounds: string;
  onTargetChange: (value: string) => void;
  onEffectKindChange: (value: ActiveEffectKind) => void;
  onConditionTypeChange: (value: ActiveEffectConditionType) => void;
  onNumericValueChange: (value: string) => void;
  onDurationTypeChange: (value: ActiveEffectDurationType) => void;
  onRemainingRoundsChange: (value: string) => void;
  onApply: () => void;
};

export const GmApplyEffectForm = ({
  rosterParticipants,
  submitting,
  targetParticipantId,
  effectKind,
  conditionType,
  numericValue,
  durationType,
  remainingRounds,
  onTargetChange,
  onEffectKindChange,
  onConditionTypeChange,
  onNumericValueChange,
  onDurationTypeChange,
  onRemainingRoundsChange,
  onApply,
}: Props) => {
  const { t } = useLocale();

  return (
    <div className="mt-4 space-y-3 rounded-3xl border border-fuchsia-500/20 bg-fuchsia-950/20 p-4">
      <label className="block space-y-2">
        <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
          {t("combatUi.effectTarget")}
        </span>
        <select
          value={targetParticipantId}
          onChange={(event) => onTargetChange(event.target.value)}
          className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-fuchsia-400"
        >
          <option value="">{t("combatUi.selectTarget")}</option>
          {rosterParticipants.map((participant) => (
            <option key={participant.id} value={participant.id}>
              {participant.display_name}
            </option>
          ))}
        </select>
      </label>

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block space-y-2">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
            {t("combatUi.effectKind")}
          </span>
          <select
            value={effectKind}
            onChange={(event) => onEffectKindChange(event.target.value as ActiveEffectKind)}
            className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-fuchsia-400"
          >
            <option value="condition">{t("combatUi.effect.condition")}</option>
            <option value="temp_ac_bonus">{t("combatUi.effect.temp_ac_bonus")}</option>
            <option value="attack_bonus">{t("combatUi.effect.attack_bonus")}</option>
            <option value="damage_bonus">{t("combatUi.effect.damage_bonus")}</option>
            <option value="advantage_on_attacks">{t("combatUi.effect.advantage_on_attacks")}</option>
            <option value="disadvantage_on_attacks">{t("combatUi.effect.disadvantage_on_attacks")}</option>
            <option value="dodging">{t("combatUi.effect.dodging")}</option>
            <option value="hidden">{t("combatUi.effect.hidden")}</option>
          </select>
        </label>

        <label className="block space-y-2">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
            {t("combatUi.effectDuration")}
          </span>
          <select
            value={durationType}
            onChange={(event) => onDurationTypeChange(event.target.value as ActiveEffectDurationType)}
            className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-fuchsia-400"
          >
            <option value="manual">{t("combatUi.duration.manual")}</option>
            <option value="rounds">{t("combatUi.duration.rounds")}</option>
            <option value="until_turn_start">{t("combatUi.duration.until_turn_start")}</option>
            <option value="until_turn_end">{t("combatUi.duration.until_turn_end")}</option>
          </select>
        </label>
      </div>

      {effectKind === "condition" ? (
        <label className="block space-y-2">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
            {t("combatUi.effectCondition")}
          </span>
          <select
            value={conditionType}
            onChange={(event) => onConditionTypeChange(event.target.value as ActiveEffectConditionType)}
            className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-fuchsia-400"
          >
            <option value="prone">{t("combatUi.condition.prone")}</option>
            <option value="poisoned">{t("combatUi.condition.poisoned")}</option>
            <option value="restrained">{t("combatUi.condition.restrained")}</option>
            <option value="blinded">{t("combatUi.condition.blinded")}</option>
            <option value="frightened">{t("combatUi.condition.frightened")}</option>
          </select>
        </label>
      ) : null}

      {NUMERIC_KINDS.has(effectKind) ? (
        <label className="block space-y-2">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
            {t("combatUi.effectValue")}
          </span>
          <input
            type="number"
            value={numericValue}
            onChange={(event) => onNumericValueChange(event.target.value)}
            className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-fuchsia-400"
          />
        </label>
      ) : null}

      {durationType === "rounds" ? (
        <label className="block space-y-2">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
            {t("combatUi.effectRounds")}
          </span>
          <input
            type="number"
            min={1}
            value={remainingRounds}
            onChange={(event) => onRemainingRoundsChange(event.target.value)}
            className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-fuchsia-400"
          />
        </label>
      ) : null}

      <button
        type="button"
        disabled={!targetParticipantId || submitting}
        onClick={onApply}
        className="w-full rounded-3xl bg-fuchsia-500 px-4 py-3 text-sm font-semibold uppercase tracking-[0.22em] text-white transition-colors hover:bg-fuchsia-400 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {t("combatUi.applyEffect")}
      </button>
    </div>
  );
};
