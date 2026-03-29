import type {
  ActiveEffectConditionType,
  ActiveEffectDurationType,
  ActiveEffectKind,
  CombatEntityActionResult,
  CombatParticipant,
  CombatPhase,
  StandardActionType,
} from "../../../shared/api/combatRepo";
import type { CombatAction } from "../../../entities/campaign-entity/campaignEntity.types";
import type { CombatParticipantView } from "../types";
import { useLocale } from "../../../shared/hooks/useLocale";
import { getCombatStatusLabel } from "../combatUi.helpers";
import { GmApplyEffectForm } from "./GmApplyEffectForm";
import { GmNpcActionPanel } from "./GmNpcActionPanel";

type Props = {
  combat: {
    state: { phase: CombatPhase; round: number } | null;
  };
  currentParticipant: CombatParticipant | null;
  currentParticipantVitals: CombatParticipantView | null;
  rosterParticipants: CombatParticipantView[];
  actionError: string | null;
  actionResult: string | null;
  submitting: boolean;
  debugOpen: boolean;
  applyEffectOpen: boolean;
  // Apply effect state
  targetParticipantId: string;
  effectKind: ActiveEffectKind;
  conditionType: ActiveEffectConditionType;
  numericValue: string;
  durationType: ActiveEffectDurationType;
  remainingRounds: string;
  // NPC action state
  npcCombatActions: CombatAction[];
  attackCombatActions: CombatAction[];
  spellCombatActions: CombatAction[];
  utilityCombatActions: CombatAction[];
  activeStructuredActions: CombatAction[];
  availableTargets: CombatParticipant[];
  availableStandardTargets: CombatParticipant[];
  entityActionPanel: "attack" | "spell" | "standard";
  attackPanelEnabled: boolean;
  spellPanelEnabled: boolean;
  selectedCombatActionId: string;
  selectedCombatAction: CombatAction | null;
  selectedTargetRefId: string;
  selectedUtilityActionId: string;
  selectedUtilityAction: CombatAction | null;
  selectedStandardAction: StandardActionType;
  selectedStandardTargetId: string;
  standardActionNote: string;
  lastEntityActionResult: CombatEntityActionResult | null;
  // Handlers
  onNextTurn: () => void;
  onMarkReaction: () => void;
  onToggleApplyEffect: () => void;
  onToggleDebug: () => void;
  onApplyEffect: () => void;
  onTargetChange: (value: string) => void;
  onEffectKindChange: (value: ActiveEffectKind) => void;
  onConditionTypeChange: (value: ActiveEffectConditionType) => void;
  onNumericValueChange: (value: string) => void;
  onDurationTypeChange: (value: ActiveEffectDurationType) => void;
  onRemainingRoundsChange: (value: string) => void;
  onSetEntityActionPanel: (panel: "attack" | "spell" | "standard") => void;
  onSetSelectedCombatActionId: (id: string) => void;
  onSetSelectedTargetRefId: (id: string) => void;
  onSetSelectedUtilityActionId: (id: string) => void;
  onSetSelectedStandardAction: (action: StandardActionType) => void;
  onSetSelectedStandardTargetId: (id: string) => void;
  onSetStandardActionNote: (note: string) => void;
  onEntityAction: () => void;
  onNpcStandardAction: () => void;
  onEntityUtilityAction: () => void;
};

export const GmQuickActionsPanel = ({
  combat,
  currentParticipant,
  currentParticipantVitals,
  rosterParticipants,
  actionError,
  actionResult,
  submitting,
  debugOpen,
  applyEffectOpen,
  targetParticipantId,
  effectKind,
  conditionType,
  numericValue,
  durationType,
  remainingRounds,
  npcCombatActions,
  attackCombatActions,
  spellCombatActions,
  utilityCombatActions,
  activeStructuredActions,
  availableTargets,
  availableStandardTargets,
  entityActionPanel,
  attackPanelEnabled,
  spellPanelEnabled,
  selectedCombatActionId,
  selectedCombatAction,
  selectedTargetRefId,
  selectedUtilityActionId,
  selectedUtilityAction,
  selectedStandardAction,
  selectedStandardTargetId,
  standardActionNote,
  lastEntityActionResult,
  onNextTurn,
  onMarkReaction,
  onToggleApplyEffect,
  onToggleDebug,
  onApplyEffect,
  onTargetChange,
  onEffectKindChange,
  onConditionTypeChange,
  onNumericValueChange,
  onDurationTypeChange,
  onRemainingRoundsChange,
  onSetEntityActionPanel,
  onSetSelectedCombatActionId,
  onSetSelectedTargetRefId,
  onSetSelectedUtilityActionId,
  onSetSelectedStandardAction,
  onSetSelectedStandardTargetId,
  onSetStandardActionNote,
  onEntityAction,
  onNpcStandardAction,
  onEntityUtilityAction,
}: Props) => {
  const { t } = useLocale();

  return (
    <section className="rounded-4xl border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.85),rgba(2,6,23,0.94))] p-5 shadow-[0_18px_60px_rgba(2,6,23,0.2)]">
      <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-slate-400">
        {t("combatUi.turnEyebrow")}
      </p>
      <h3 className="mt-2 text-lg font-semibold text-white">{t("combatUi.gmQuickActions")}</h3>

      {actionError ? (
        <div className="mt-4 rounded-3xl border border-rose-500/25 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
          {actionError}
        </div>
      ) : null}

      {actionResult ? (
        <div className="mt-4 rounded-3xl border border-emerald-500/25 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">
          {actionResult}
        </div>
      ) : null}

      <div className="mt-4 rounded-3xl border border-white/8 bg-white/4 px-4 py-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
          {t("combatUi.activeTurn")}
        </p>
        <p className="mt-2 text-lg font-semibold text-white">
          {currentParticipant?.display_name ?? "-"}
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-slate-300">
          <span>
            {t("combatUi.phase")}: {combat.state?.phase ?? "-"}
          </span>
          <span>
            {t("combatUi.round")}: {combat.state?.round ?? "-"}
          </span>
          {currentParticipant ? (
            <span>{getCombatStatusLabel(t, currentParticipant.status)}</span>
          ) : null}
          {currentParticipantVitals?.currentHp != null ? (
            <span>
              {t("combatUi.hp")}:{" "}
              {currentParticipantVitals.maxHp != null
                ? `${currentParticipantVitals.currentHp}/${currentParticipantVitals.maxHp}`
                : currentParticipantVitals.currentHp}
            </span>
          ) : null}
        </div>

        {currentParticipant?.turn_resources ? (
          <div className="mt-3 flex flex-wrap gap-2">
            <span
              className={`rounded flex items-center justify-center px-2 py-1 text-[10px] font-bold uppercase tracking-wider ${currentParticipant.turn_resources.action_used ? "bg-rose-500/20 text-rose-300" : "bg-emerald-500/20 border border-emerald-500/30 text-emerald-200"}`}
            >
              Action: {currentParticipant.turn_resources.action_used ? "Used" : "Avail"}
            </span>
            <span
              className={`rounded flex items-center justify-center px-2 py-1 text-[10px] font-bold uppercase tracking-wider ${currentParticipant.turn_resources.bonus_action_used ? "bg-rose-500/20 text-rose-300" : "bg-emerald-500/20 border border-emerald-500/30 text-emerald-200"}`}
            >
              Bonus: {currentParticipant.turn_resources.bonus_action_used ? "Used" : "Avail"}
            </span>
            <span
              className={`rounded flex items-center justify-center px-2 py-1 text-[10px] font-bold uppercase tracking-wider ${currentParticipant.turn_resources.reaction_used ? "bg-rose-500/20 text-rose-300" : "bg-emerald-500/20 border border-emerald-500/30 text-emerald-200"}`}
            >
              Reaction: {currentParticipant.turn_resources.reaction_used ? "Used" : "Avail"}
            </span>
          </div>
        ) : null}
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <button
          type="button"
          disabled={!currentParticipant || combat.state?.phase !== "active" || submitting}
          onClick={onNextTurn}
          className="rounded-3xl bg-sky-500 px-4 py-3 text-sm font-semibold uppercase tracking-[0.22em] text-slate-950 transition-colors hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {t("combatUi.advanceTurn")}
        </button>
        <button
          type="button"
          disabled={!currentParticipant || combat.state?.phase !== "active" || submitting}
          onClick={onMarkReaction}
          className="rounded-3xl border border-amber-400/30 bg-amber-500/10 px-4 py-3 text-sm font-semibold uppercase tracking-[0.22em] text-amber-100 transition-colors hover:bg-amber-500/20 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {t("combatUi.markReaction")}
        </button>
        <button
          type="button"
          onClick={onToggleApplyEffect}
          className="rounded-3xl border border-fuchsia-400/30 bg-fuchsia-500/10 px-4 py-3 text-sm font-semibold uppercase tracking-[0.22em] text-fuchsia-100 transition-colors hover:bg-fuchsia-500/20"
        >
          {t("combatUi.applyEffect")}
        </button>
        <button
          type="button"
          onClick={onToggleDebug}
          className="rounded-3xl border border-white/12 bg-white/6 px-4 py-3 text-sm font-semibold uppercase tracking-[0.22em] text-white transition-colors hover:bg-white/10"
        >
          {debugOpen ? t("combatUi.hideDebug") : t("combatUi.showDebug")}
        </button>
      </div>

      {applyEffectOpen ? (
        <GmApplyEffectForm
          rosterParticipants={rosterParticipants}
          submitting={submitting}
          targetParticipantId={targetParticipantId}
          effectKind={effectKind}
          conditionType={conditionType}
          numericValue={numericValue}
          durationType={durationType}
          remainingRounds={remainingRounds}
          onTargetChange={onTargetChange}
          onEffectKindChange={onEffectKindChange}
          onConditionTypeChange={onConditionTypeChange}
          onNumericValueChange={onNumericValueChange}
          onDurationTypeChange={onDurationTypeChange}
          onRemainingRoundsChange={onRemainingRoundsChange}
          onApply={onApplyEffect}
        />
      ) : null}

      {currentParticipant?.kind === "session_entity" ? (
        <GmNpcActionPanel
          currentParticipant={currentParticipant}
          npcCombatActions={npcCombatActions}
          attackCombatActions={attackCombatActions}
          spellCombatActions={spellCombatActions}
          utilityCombatActions={utilityCombatActions}
          activeStructuredActions={activeStructuredActions}
          availableTargets={availableTargets}
          availableStandardTargets={availableStandardTargets}
          entityActionPanel={entityActionPanel}
          attackPanelEnabled={attackPanelEnabled}
          spellPanelEnabled={spellPanelEnabled}
          selectedCombatActionId={selectedCombatActionId}
          selectedCombatAction={selectedCombatAction}
          selectedTargetRefId={selectedTargetRefId}
          selectedUtilityActionId={selectedUtilityActionId}
          selectedUtilityAction={selectedUtilityAction}
          selectedStandardAction={selectedStandardAction}
          selectedStandardTargetId={selectedStandardTargetId}
          standardActionNote={standardActionNote}
          submitting={submitting}
          lastEntityActionResult={lastEntityActionResult}
          onSetEntityActionPanel={onSetEntityActionPanel}
          onSetSelectedCombatActionId={onSetSelectedCombatActionId}
          onSetSelectedTargetRefId={onSetSelectedTargetRefId}
          onSetSelectedUtilityActionId={onSetSelectedUtilityActionId}
          onSetSelectedStandardAction={onSetSelectedStandardAction}
          onSetSelectedStandardTargetId={onSetSelectedStandardTargetId}
          onSetStandardActionNote={onSetStandardActionNote}
          onEntityAction={onEntityAction}
          onNpcStandardAction={onNpcStandardAction}
          onEntityUtilityAction={onEntityUtilityAction}
        />
      ) : null}
    </section>
  );
};
