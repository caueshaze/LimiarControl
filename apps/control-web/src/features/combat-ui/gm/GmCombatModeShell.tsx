import { useEffect, useState } from "react";
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
import { GmPendingSavesPanel } from "./GmPendingSavesPanel";
import { GmQuickActionsPanel } from "./GmQuickActionsPanel";
import { useGmCombatShell } from "./useGmCombatShell";
import { CombatMapFrame } from "../map/CombatMapFrame";
import { GmDistancesPanel } from "./GmDistancesPanel";
import {
  formatMovementMeters,
  getMovementPreviewReasonLabel,
  pathCostUnitsToMeters,
  resolveMovementCellSelection,
  useMovementPreview
} from "../map/useMovementPreview";
import { combatRepo } from "../../../shared/api/combatRepo";

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
  sessionId
}: Props) => {
  const { locale, t } = useLocale();
  const shell = useGmCombatShell({ sessionId, playerSheetByUserId });
  const [movementMode, setMovementMode] = useState(false);
  const [movementSelectedCell, setMovementSelectedCell] = useState<{
    x: number;
    y: number;
  } | null>(null);
  const [movementSubmitting, setMovementSubmitting] = useState(false);
  const [placementSubmitting, setPlacementSubmitting] = useState(false);
  const [placementError, setPlacementError] = useState<string | null>(null);
  const [movementRejectionReason, setMovementRejectionReason] = useState<
    string | null
  >(null);
  const movementEnabled =
    movementMode &&
    shell.combat.state?.use_map !== false &&
    shell.combat.state?.phase === "active" &&
    shell.currentParticipant?.status === "active";
  const movementPreview = useMovementPreview({
    sessionId,
    actorParticipantId: shell.currentParticipant?.id,
    actorRefId: shell.currentParticipant?.ref_id,
    destinationCell: movementEnabled ? movementSelectedCell : null,
    enabled: movementEnabled
  });

  useEffect(() => {
    if (movementEnabled) {
      return;
    }
    setMovementMode(false);
    setMovementSelectedCell(null);
    setMovementRejectionReason(null);
  }, [movementEnabled]);

  const clearMovementMode = () => {
    setMovementMode(false);
    setMovementSelectedCell(null);
    setMovementRejectionReason(null);
  };

  const submitMovement = (cell: { x: number; y: number }) => {
    if (!shell.currentParticipant?.id || movementSubmitting) return;
    const actorParticipantId = shell.currentParticipant.id;
    setMovementSubmitting(true);
    setMovementSelectedCell(cell);
    setMovementRejectionReason(null);
    combatRepo
      .confirmMovement(sessionId, {
        actor_participant_id: actorParticipantId,
        destination_cell: cell
      })
      .then((response) => {
        if (!response.is_valid) {
          setMovementRejectionReason(
            getMovementPreviewReasonLabel(response.reason)
          );
          return;
        }
        clearMovementMode();
        return shell.combat.refreshState();
      })
      .catch((error) => {
        setMovementRejectionReason(
          error?.data?.detail ||
            error?.message ||
            "Falha ao confirmar movimento."
        );
      })
      .finally(() => setMovementSubmitting(false));
  };

  const canMoveNow =
    shell.combat.state?.phase === "active" &&
    shell.currentParticipant?.status === "active" &&
    shell.combat.state?.use_map !== false;
  const isTargetingAction =
    shell.currentParticipant?.kind === "session_entity" &&
    (shell.entityActionPanel === "attack" ||
      shell.entityActionPanel === "spell") &&
    Boolean(shell.selectedCombatAction);

  const mapSelectionMode = movementEnabled
    ? "select-cell"
    : canMoveNow || isTargetingAction
      ? "select-token"
      : "none";
  const movementPreviewMessage =
    movementPreview.preview != null && movementSelectedCell != null
      ? t("combatUi.mapHintMoveLocked")
          .replace(
            "{cost}",
            formatMovementMeters(
              pathCostUnitsToMeters(movementPreview.preview.path_cost_units),
              locale
            )
          )
          .replace(
            "{remaining}",
            formatMovementMeters(
              pathCostUnitsToMeters(movementPreview.preview.remaining_budget),
              locale
            )
          )
      : null;
  const movementHintMessage = movementRejectionReason ?? movementPreview.error;
  const mapHint =
    shell.combat.state?.phase === "placement"
      ? (placementError ?? t("combatUi.mapHintPlacement"))
      : movementEnabled && movementHintMessage
        ? movementHintMessage
        : movementEnabled && movementPreview.loading && movementSelectedCell
          ? t("combatUi.movementChecking")
          : movementEnabled && movementPreviewMessage
            ? movementPreviewMessage
            : movementEnabled
              ? t("combatUi.mapHintMove")
              : shell.currentParticipant?.kind !== "session_entity"
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
            previewCells={[]}
            selectedCell={movementEnabled ? movementSelectedCell : null}
            selectedTargetRefId={
              movementEnabled ? null : shell.selectedTargetRefId || null
            }
            frameClassName="h-[420px] w-full border-0 bg-slate-950 md:h-[560px] xl:h-[720px]"
            onCellSelected={(selection) => {
              if (!movementEnabled) {
                return;
              }
              if (
                selection.combatantId &&
                selection.combatantId === shell.currentParticipant?.ref_id
              ) {
                clearMovementMode();
                return;
              }
              const nextAction = resolveMovementCellSelection({
                currentSelectedCell: movementSelectedCell,
                nextCell: selection.cell,
                preview: movementPreview.preview,
                loading: movementPreview.loading
              });
              if (nextAction === "confirm") {
                submitMovement(selection.cell);
                return;
              }
              setMovementSelectedCell(selection.cell);
              setMovementRejectionReason(null);
            }}
            onTokenSelected={(selection) => {
              if (movementEnabled) {
                if (
                  selection.combatantId &&
                  selection.combatantId === shell.currentParticipant?.ref_id
                ) {
                  clearMovementMode();
                }
                return;
              }
              const isActiveToken =
                selection.combatantId != null &&
                selection.combatantId === shell.currentParticipant?.ref_id;
              if (isActiveToken && canMoveNow && !isTargetingAction) {
                setMovementMode(true);
                setMovementSelectedCell(null);
                return;
              }
              if (selection.combatantId) {
                shell.setSelectedTargetRefId(selection.combatantId);
              }
            }}
          />
        )}

        {shell.combat.state?.phase === "placement" ? (
          <section className="rounded-2xl border border-amber-400/25 bg-amber-500/10 p-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm text-amber-100">
                {t("combatUi.mapHintPlacement")}
              </p>
              <button
                type="button"
                disabled={placementSubmitting}
                onClick={() => {
                  setPlacementSubmitting(true);
                  setPlacementError(null);
                  combatRepo
                    .confirmPlacement(sessionId)
                    .then((updated) => {
                      shell.combat.applyState(updated);
                    })
                    .catch((error) => {
                      setPlacementError(
                        error?.data?.detail ||
                          error?.message ||
                          "Nao foi possivel confirmar as posicoes."
                      );
                    })
                    .finally(() => setPlacementSubmitting(false));
                }}
                className="rounded-full bg-amber-500 px-4 py-2 text-xs font-bold uppercase tracking-[0.18em] text-slate-950 transition hover:bg-amber-300 disabled:opacity-50"
              >
                {placementSubmitting ? "..." : t("combatUi.confirmPlacement")}
              </button>
            </div>
          </section>
        ) : null}

        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.02fr)_minmax(340px,0.98fr)]">
          <div className="space-y-6">
            <CombatParticipantRoster
              onRemoveEffect={(participantId, effectId) =>
                void shell.handleRemoveEffect(participantId, effectId)
              }
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
              onResolveReaction={(id, decision) =>
                void shell.handleResolveReaction(id, decision)
              }
            />

            <GmPendingSavesPanel
              pendingSaves={shell.pendingSaves}
              submitting={shell.submitting}
              onResolveSave={(targetId, saveId, rollSource, manualRoll) =>
                void shell.handleResolveSave(targetId, saveId, rollSource, manualRoll)
              }
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
              onSetSelectedReviveParticipantId={
                shell.setSelectedReviveParticipantId
              }
              onSetReviveHp={shell.setReviveHp}
              onEntityAction={() => void shell.handleEntityAction()}
              onNpcStandardAction={() => void shell.handleNpcStandardAction()}
              onEntityUtilityAction={() =>
                void shell.handleEntityUtilityAction()
              }
              onRevive={() =>
                void shell.handleRevive(
                  shell.selectedReviveParticipantId,
                  Math.max(1, Number.parseInt(shell.reviveHp, 10) || 1)
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
          actionKind={
            shell.selectedCombatAction?.kind as "weapon_attack" | "spell_attack"
          }
          actionDescription={shell.selectedCombatAction?.description}
          target={shell.selectedTarget as any}
          onClose={() => shell.setEntityActionDialogOpen(false)}
          onMissingDistance={() =>
            shell.setMissingDistancePair({
              fromRefId: shell.currentParticipant?.ref_id ?? "",
              toRefId: shell.selectedTarget?.ref_id ?? ""
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
