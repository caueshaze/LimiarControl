import { useLocale } from "../../../shared/hooks/useLocale";
import { GmEntityActionRollDialog } from "../../../pages/GmDashboardPage/GmEntityActionRollDialog";
import { GmActionOverrideDialog } from "./GmActionOverrideDialog";
import { GmCombatDebugPanel } from "../../../pages/GmDashboardPage/GmCombatDebugPanel";
import type { PartyMemberSummary } from "../../../shared/api/partiesRepo";
import type { CharacterSheet } from "../../../features/character-sheet/model/characterSheet.types";
import { CombatLogPanel } from "../components/CombatLogPanel";
import { CombatModeBar } from "../components/CombatModeBar";
import { CombatParticipantRoster } from "../components/CombatParticipantRoster";
import { GmPendingReactionsPanel } from "./GmPendingReactionsPanel";
import { GmQuickActionsPanel } from "./GmQuickActionsPanel";
import { useGmCombatShell } from "./useGmCombatShell";
import { CombatMapFrame } from "../map/CombatMapFrame";
import { GmDistancesPanel } from "./GmDistancesPanel";

type Props = {
  campaignId: string;
  expanded: boolean;
  onToggleExpanded: () => void;
  partyPlayers: PartyMemberSummary[];
  playerSheetByUserId: Record<string, CharacterSheet>;
  sessionId: string;
};

export const GmCombatModeShell = ({
  campaignId,
  expanded,
  onToggleExpanded,
  partyPlayers,
  playerSheetByUserId,
  sessionId,
}: Props) => {
  const { t } = useLocale();
  const shell = useGmCombatShell({ sessionId, playerSheetByUserId });
  const mapSelectionMode =
    shell.combat.state?.phase === "active" &&
    shell.currentParticipant?.kind === "session_entity" &&
    (shell.entityActionPanel === "attack" || shell.entityActionPanel === "spell") &&
    shell.selectedCombatAction
      ? "select-token"
      : "none";
  const mapHint =
    shell.currentParticipant?.kind !== "session_entity"
      ? t("combatUi.mapHintIdle")
      : shell.entityActionPanel === "attack"
        ? t("combatUi.mapHintAttack")
        : shell.entityActionPanel === "spell"
          ? t("combatUi.mapHintSpell")
          : t("combatUi.mapHintIdle");

  return (
    <section className="space-y-6">
      <CombatModeBar
        currentParticipantName={shell.currentParticipant?.display_name ?? null}
        expanded={expanded}
        onToggleExpanded={onToggleExpanded}
        phase={shell.combat.state?.phase ?? null}
        round={shell.combat.state?.round ?? null}
        turnResources={shell.currentParticipant?.turn_resources ?? null}
      />

      <div className="space-y-6">
        {shell.combat.state?.use_map === false ? (
          <GmDistancesPanel
            highlightPair={shell.missingDistancePair}
            participants={shell.combat.state.participants}
            localDistances={shell.combat.state.local_distances}
            sessionId={sessionId}
            onDistancesUpdated={(updatedState) => {
              shell.combat.applyState(updatedState);
              shell.setMissingDistancePair(null);
            }}
          />
        ) : (
          <CombatMapFrame
            sessionId={sessionId}
            title={t("combatUi.mapTitle")}
            hint={mapHint}
            combatPhase={shell.combat.state?.phase ?? null}
            actor={{ actorId: "gm-control", actorType: "gm" }}
            selectionMode={mapSelectionMode}
            selectedTargetRefId={shell.selectedTargetRefId || null}
            frameClassName="h-[420px] w-full border-0 bg-slate-950 md:h-[560px] xl:h-[720px]"
            onTokenSelected={(selection) => {
              if (selection.combatantId) {
                shell.setSelectedTargetRefId(selection.combatantId);
              }
            }}
          />
        )}

        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.02fr)_minmax(340px,0.98fr)]">
          <div className="space-y-6">
          <CombatParticipantRoster
            onRemoveEffect={(participantId, effectId) => void shell.handleRemoveEffect(participantId, effectId)}
            participants={shell.rosterParticipants}
            subtitle={t("combatUi.gmParticipantsDescription")}
            title={t("combatUi.participants")}
          />
          {shell.debugOpen ? (
            <GmCombatDebugPanel
              campaignId={campaignId}
              partyPlayers={partyPlayers}
              sessionId={sessionId}
            />
          ) : null}
        </div>

          <div className="space-y-6">
            <GmPendingReactionsPanel
              pendingReactionRequests={shell.pendingReactionRequests}
              submitting={shell.submitting}
              onResolveReaction={(id, decision) => void shell.handleResolveReaction(id, decision)}
            />

            <GmQuickActionsPanel
              combat={shell.combat}
              currentParticipant={shell.currentParticipant}
              currentParticipantVitals={shell.currentParticipantVitals}
              rosterParticipants={shell.rosterParticipants}
              deadPlayerParticipants={shell.deadPlayerParticipants}
              actionError={shell.actionError}
              actionResult={shell.actionResult}
              submitting={shell.submitting}
              debugOpen={shell.debugOpen}
              applyEffectOpen={shell.applyEffectOpen}
              targetParticipantId={shell.targetParticipantId}
              effectKind={shell.effectKind}
              conditionType={shell.conditionType}
              numericValue={shell.numericValue}
              durationType={shell.durationType}
              remainingRounds={shell.remainingRounds}
              npcCombatActions={shell.npcCombatActions}
              attackCombatActions={shell.attackCombatActions}
              spellCombatActions={shell.spellCombatActions}
              utilityCombatActions={shell.utilityCombatActions}
              activeStructuredActions={shell.activeStructuredActions}
              availableTargets={shell.availableTargets}
              availableStandardTargets={shell.availableStandardTargets}
              entityActionPanel={shell.entityActionPanel}
              attackPanelEnabled={shell.attackPanelEnabled}
              spellPanelEnabled={shell.spellPanelEnabled}
              selectedCombatActionId={shell.selectedCombatActionId}
              selectedCombatAction={shell.selectedCombatAction}
              selectedTargetRefId={shell.selectedTargetRefId}
              selectedUtilityActionId={shell.selectedUtilityActionId}
              selectedUtilityAction={shell.selectedUtilityAction}
              selectedStandardAction={shell.selectedStandardAction}
              selectedStandardTargetId={shell.selectedStandardTargetId}
              standardActionNote={shell.standardActionNote}
              selectedReviveParticipantId={shell.selectedReviveParticipantId}
              reviveHp={shell.reviveHp}
              lastEntityActionResult={shell.lastEntityActionResult}
              onNextTurn={() => void shell.handleNextTurn()}
              onMarkReaction={() => void shell.handleMarkReaction()}
              onToggleApplyEffect={() => shell.setApplyEffectOpen((v) => !v)}
              onToggleDebug={() => shell.setDebugOpen((v) => !v)}
              onApplyEffect={() => void shell.handleApplyEffect()}
              onTargetChange={shell.setTargetParticipantId}
              onEffectKindChange={shell.setEffectKind}
              onConditionTypeChange={shell.setConditionType}
              onNumericValueChange={shell.setNumericValue}
              onDurationTypeChange={shell.setDurationType}
              onRemainingRoundsChange={shell.setRemainingRounds}
              onSetEntityActionPanel={shell.setEntityActionPanel}
              onSetSelectedCombatActionId={shell.setSelectedCombatActionId}
              onSetSelectedTargetRefId={shell.setSelectedTargetRefId}
              onSetSelectedUtilityActionId={shell.setSelectedUtilityActionId}
              onSetSelectedStandardAction={shell.setSelectedStandardAction}
              onSetSelectedStandardTargetId={shell.setSelectedStandardTargetId}
              onSetStandardActionNote={shell.setStandardActionNote}
              onSetSelectedReviveParticipantId={shell.setSelectedReviveParticipantId}
              onSetReviveHp={shell.setReviveHp}
              onEntityAction={() => void shell.handleEntityAction()}
              onNpcStandardAction={() => void shell.handleNpcStandardAction()}
              onEntityUtilityAction={() => void shell.handleEntityUtilityAction()}
              onRevive={() =>
                void shell.handleRevive(
                  shell.selectedReviveParticipantId,
                  Math.max(1, Number.parseInt(shell.reviveHp, 10) || 1),
                )
              }
            />

            <CombatLogPanel logs={shell.combat.logs} />
          </div>
        </div>
      </div>

      {shell.entityActionDialogOpen &&
      shell.currentParticipant &&
      shell.selectedCombatAction &&
      shell.selectedTarget &&
      (shell.selectedCombatAction.kind === "weapon_attack" ||
        shell.selectedCombatAction.kind === "spell_attack") ? (
        <GmEntityActionRollDialog
          actorParticipantId={shell.currentParticipant.id}
          actorRefId={shell.currentParticipant.ref_id}
          sessionId={sessionId}
          actionId={shell.selectedCombatActionId}
          actionName={shell.selectedCombatAction?.name || ""}
          actionKind={shell.selectedCombatAction?.kind as "weapon_attack" | "spell_attack"}
          actionDescription={shell.selectedCombatAction?.description}
          target={shell.selectedTarget as any}
          onClose={() => shell.setEntityActionDialogOpen(false)}
          onMissingDistance={() =>
            shell.setMissingDistancePair({
              fromRefId: shell.currentParticipant?.ref_id ?? "",
              toRefId: shell.selectedTarget?.ref_id ?? "",
            })
          }
          onResolved={shell.handleEntityActionResolved}
        />
      ) : null}

      <GmActionOverrideDialog
        isOpen={shell.overrideDialogOpen}
        onClose={() => {
          shell.setOverrideDialogOpen(false);
          shell.setPendingOverrideAction(null);
        }}
        onConfirm={() => {
          if (shell.pendingOverrideAction) void shell.pendingOverrideAction();
        }}
        resourceName={shell.overrideResourceName}
        isSubmitting={shell.submitting}
      />
    </section>
  );
};
