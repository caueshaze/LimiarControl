import { useEffect, useMemo, useState } from "react";
import { describeCombatAction } from "../../../entities/campaign-entity/describeCombatAction";
import type {
  ActiveEffectConditionType,
  ActiveEffectDurationType,
  ActiveEffectKind,
  CombatEntityActionResult,
  StandardActionType,
} from "../../../shared/api/combatRepo";
import { combatRepo } from "../../../shared/api/combatRepo";
import type { CharacterSheet } from "../../../features/character-sheet/model/characterSheet.types";
import { useSessionEntities } from "../../../features/session-entities/hooks/useSessionEntities";
import { useLocale } from "../../../shared/hooks/useLocale";
import { RollResultCard } from "../../../features/rolls/components/RollResultCard";
import { GmEntityActionRollDialog } from "../../../pages/GmDashboardPage/GmEntityActionRollDialog";
import { GmActionOverrideDialog } from "./GmActionOverrideDialog";
import { GmCombatDebugPanel } from "../../../pages/GmDashboardPage/GmCombatDebugPanel";
import type { PartyMemberSummary } from "../../../shared/api/partiesRepo";
import { buildCombatParticipantViews, getCombatStatusLabel } from "../combatUi.helpers";
import { CombatLogPanel } from "../components/CombatLogPanel";
import { CombatModeBar } from "../components/CombatModeBar";
import { CombatParticipantRoster } from "../components/CombatParticipantRoster";
import { useCombatUiState } from "../useCombatUiState";

type Props = {
  campaignId: string;
  expanded: boolean;
  onToggleExpanded: () => void;
  partyPlayers: PartyMemberSummary[];
  playerSheetByUserId: Record<string, CharacterSheet>;
  sessionId: string;
};

const NUMERIC_KINDS = new Set<ActiveEffectKind>(["temp_ac_bonus", "attack_bonus", "damage_bonus"]);
const ENTITY_STANDARD_ACTIONS: StandardActionType[] = [
  "dodge",
  "help",
  "hide",
  "use_object",
  "dash",
  "disengage",
];

export const GmCombatModeShell = ({
  campaignId,
  expanded,
  onToggleExpanded,
  partyPlayers,
  playerSheetByUserId,
  sessionId,
}: Props) => {
  const { t } = useLocale();
  const combat = useCombatUiState({ sessionId });
  const sessionEntities = useSessionEntities(sessionId);
  const [debugOpen, setDebugOpen] = useState(false);
  const [applyEffectOpen, setApplyEffectOpen] = useState(false);
  const [targetParticipantId, setTargetParticipantId] = useState("");
  const [effectKind, setEffectKind] = useState<ActiveEffectKind>("condition");
  const [conditionType, setConditionType] = useState<ActiveEffectConditionType>("prone");
  const [numericValue, setNumericValue] = useState("2");
  const [durationType, setDurationType] = useState<ActiveEffectDurationType>("manual");
  const [remainingRounds, setRemainingRounds] = useState("1");
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionResult, setActionResult] = useState<string | null>(null);
  const [entityActionDialogOpen, setEntityActionDialogOpen] = useState(false);
  const [lastEntityActionResult, setLastEntityActionResult] = useState<CombatEntityActionResult | null>(null);
  const [entityActionPanel, setEntityActionPanel] = useState<"attack" | "spell" | "standard">("attack");
  const [selectedCombatActionId, setSelectedCombatActionId] = useState("");
  const [selectedTargetRefId, setSelectedTargetRefId] = useState("");
  const [selectedUtilityActionId, setSelectedUtilityActionId] = useState("");
  const [selectedStandardAction, setSelectedStandardAction] = useState<StandardActionType>("dodge");
  const [selectedStandardTargetId, setSelectedStandardTargetId] = useState("");
  const [standardActionNote, setStandardActionNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [overrideDialogOpen, setOverrideDialogOpen] = useState(false);
  const [overrideResourceName, setOverrideResourceName] = useState("");
  const [pendingOverrideAction, setPendingOverrideAction] = useState<(() => Promise<void>) | null>(null);

  const playerVitalsByUserId = useMemo(
    () =>
      Object.fromEntries(
        Object.entries(playerSheetByUserId).map(([userId, sheet]) => [
          userId,
          {
            currentHp: sheet.currentHP,
            maxHp: sheet.maxHP,
          },
        ]),
      ),
    [playerSheetByUserId],
  );

  const entityVitalsByRefId = useMemo(
    () =>
      Object.fromEntries(
        sessionEntities.entities.map((entity) => [
          entity.id,
          {
            currentHp: entity.currentHp ?? null,
            maxHp: entity.entity?.maxHp ?? null,
          },
        ]),
      ),
    [sessionEntities.entities],
  );

  const rosterParticipants = useMemo(
    () =>
      buildCombatParticipantViews({
        currentTurnIndex: combat.state?.current_turn_index ?? -1,
        entityVitalsByRefId,
        participants: combat.state?.participants ?? [],
        playerVitalsByUserId,
      }),
    [combat.state?.current_turn_index, combat.state?.participants, entityVitalsByRefId, playerVitalsByUserId],
  );

  const currentParticipant = combat.currentParticipant;
  const currentParticipantVitals = currentParticipant
    ? rosterParticipants.find((participant) => participant.id === currentParticipant.id) ?? null
    : null;
  const activeSessionEntity =
    currentParticipant?.kind === "session_entity"
      ? sessionEntities.entities.find((entity) => entity.id === currentParticipant.ref_id) ?? null
      : null;
  const npcCombatActions = activeSessionEntity?.entity?.combatActions ?? [];
  const attackCombatActions = useMemo(
    () => npcCombatActions.filter((action) => action.kind === "weapon_attack"),
    [npcCombatActions],
  );
  const spellCombatActions = useMemo(
    () =>
      npcCombatActions.filter(
        (action) =>
          action.kind === "spell_attack" ||
          action.kind === "saving_throw" ||
          action.kind === "heal",
      ),
    [npcCombatActions],
  );
  const utilityCombatActions = useMemo(
    () => npcCombatActions.filter((action) => action.kind === "utility"),
    [npcCombatActions],
  );
  const attackPanelEnabled = attackCombatActions.length > 0;
  const spellPanelEnabled = spellCombatActions.length > 0;
  const activeStructuredActions = entityActionPanel === "attack" ? attackCombatActions : spellCombatActions;
  const selectedCombatAction =
    activeStructuredActions.find((action) => action.id === selectedCombatActionId) ??
    activeStructuredActions[0] ??
    null;
  const selectedUtilityAction =
    utilityCombatActions.find((action) => action.id === selectedUtilityActionId) ??
    utilityCombatActions[0] ??
    null;
  const availableTargets = combat.state?.participants.filter(
    (participant) => participant.status !== "dead" && participant.status !== "defeated",
  ) ?? [];
  const selectedTarget =
    availableTargets.find((participant) => participant.ref_id === selectedTargetRefId) ?? null;
  const availableStandardTargets = availableTargets.filter(
    (participant) => participant.id !== currentParticipant?.id,
  );

  const formatEntityActionResult = (result: CombatEntityActionResult) => {
    const actionName = result.action_name || selectedCombatAction?.name || selectedUtilityAction?.name || "Action";
    if (result.action_kind === "weapon_attack" || result.action_kind === "spell_attack") {
      return result.is_hit
        ? `${actionName} hit ${result.target_display_name ?? "the target"} for ${result.damage ?? 0}.`
        : `${actionName} missed ${result.target_display_name ?? "the target"}.`;
    }
    if (result.action_kind === "saving_throw") {
      return result.is_saved
        ? `${actionName}: target saved.`
        : `${actionName}: target failed the save and took ${result.damage ?? 0}.`;
    }
    if (result.action_kind === "heal") {
      return `${actionName} healed ${result.healing ?? 0} HP.`;
    }
    return `${actionName} executed.`;
  };

  const handleEntityActionResolved = async (result: CombatEntityActionResult) => {
    setLastEntityActionResult(result);
    setActionResult(formatEntityActionResult(result));
    setEntityActionDialogOpen(false);
    await combat.refreshState();
  };

  const executeWithOverride = async (
    apiCall: (override: boolean) => Promise<any>,
    onSuccess: (result: any) => Promise<void>,
    fallbackMsg: string
  ) => {
    setSubmitting(true);
    setActionError(null);
    let is409 = false;
    try {
      const result = await apiCall(false);
      await onSuccess(result);
    } catch (err: any) {
      if (err?.status === 409 && err?.data?.resource_limit_exceeded) {
        is409 = true;
        setOverrideResourceName(err.data.resource || "Ação");
        setPendingOverrideAction(() => async () => {
          setSubmitting(true);
          setActionError(null);
          try {
            const overrideResult = await apiCall(true);
            await onSuccess(overrideResult);
          } catch (overrideErr: any) {
            setActionError(overrideErr?.data?.detail || overrideErr?.message || fallbackMsg);
          } finally {
            setSubmitting(false);
            setOverrideDialogOpen(false);
            setPendingOverrideAction(null);
          }
        });
        setOverrideDialogOpen(true);
        setSubmitting(false);
      } else {
        setActionError(err?.data?.detail || err?.message || fallbackMsg);
      }
    } finally {
      if (!is409) {
        setSubmitting(false);
      }
    }
  };

  const handleEntityAction = async () => {
    if (!currentParticipant || !selectedCombatActionId) {
      return;
    }
    if (selectedCombatAction?.kind !== "utility" && !selectedTargetRefId) {
      return;
    }

    setActionError(null);
    setActionResult(null);
    setLastEntityActionResult(null);

    if (
      selectedCombatAction?.kind === "weapon_attack" ||
      selectedCombatAction?.kind === "spell_attack"
    ) {
      setEntityActionDialogOpen(true);
      return;
    }

    await executeWithOverride(
      (override) =>
        combatRepo.entityAction(sessionId, {
          actor_participant_id: currentParticipant.id,
          combat_action_id: selectedCombatActionId,
          target_ref_id: selectedCombatAction?.kind === "utility" ? null : selectedTargetRefId,
          override_resource_limit: override,
        }),
      async (result) => {
        setActionResult(formatEntityActionResult(result));
        await combat.refreshState();
      },
      "Failed to execute entity action"
    );
  };

  useEffect(() => {
    if (!activeStructuredActions.length) {
      setSelectedCombatActionId("");
      return;
    }
    if (!activeStructuredActions.some((action) => action.id === selectedCombatActionId)) {
      setSelectedCombatActionId(activeStructuredActions[0]?.id ?? "");
    }
  }, [activeStructuredActions, selectedCombatActionId]);

  useEffect(() => {
    if (!utilityCombatActions.length) {
      setSelectedUtilityActionId("");
      return;
    }
    if (!utilityCombatActions.some((action) => action.id === selectedUtilityActionId)) {
      setSelectedUtilityActionId(utilityCombatActions[0]?.id ?? "");
    }
  }, [selectedUtilityActionId, utilityCombatActions]);

  useEffect(() => {
    if (currentParticipant?.kind === "session_entity") {
      return;
    }
    setEntityActionPanel("attack");
    setSelectedCombatActionId("");
    setSelectedTargetRefId("");
    setSelectedUtilityActionId("");
    setEntityActionDialogOpen(false);
    setSelectedStandardAction("dodge");
    setSelectedStandardTargetId("");
    setStandardActionNote("");
  }, [currentParticipant?.kind]);

  useEffect(() => {
    if (
      currentParticipant?.kind !== "session_entity" ||
      entityActionPanel === "standard" ||
      !selectedCombatAction ||
      selectedCombatAction.kind === "utility"
    ) {
      if (selectedCombatAction?.kind === "utility" && selectedTargetRefId) {
        setSelectedTargetRefId("");
      }
      return;
    }

    if (selectedTarget) {
      return;
    }

    const preferredTarget =
      selectedCombatAction.kind === "heal"
        ? availableTargets.find((participant) => participant.id === currentParticipant.id) ??
          availableTargets.find((participant) => participant.team === currentParticipant.team) ??
          availableTargets[0]
        : availableTargets.find(
            (participant) =>
              participant.id !== currentParticipant.id &&
              participant.team !== currentParticipant.team,
          ) ??
          availableTargets.find((participant) => participant.id !== currentParticipant.id) ??
          availableTargets[0];

    if (preferredTarget?.ref_id) {
      setSelectedTargetRefId(preferredTarget.ref_id);
    }
  }, [availableTargets, currentParticipant, entityActionPanel, selectedCombatAction, selectedTarget, selectedTargetRefId]);

  useEffect(() => {
    if (entityActionPanel !== "attack" && entityActionPanel !== "spell") {
      return;
    }

    if (entityActionPanel === "attack" && attackCombatActions.length === 0) {
      if (spellCombatActions.length > 0) {
        setEntityActionPanel("spell");
        return;
      }
      setEntityActionPanel("standard");
      return;
    }

    if (entityActionPanel === "spell" && spellCombatActions.length === 0) {
      if (attackCombatActions.length > 0) {
        setEntityActionPanel("attack");
        return;
      }
      setEntityActionPanel("standard");
    }
  }, [attackCombatActions.length, entityActionPanel, spellCombatActions.length]);

  useEffect(() => {
    if (selectedStandardAction !== "help") {
      setSelectedStandardTargetId("");
    }
    if (selectedStandardAction !== "use_object") {
      setStandardActionNote("");
    }
  }, [selectedStandardAction]);

  useEffect(() => {
    setActionError(null);
    setActionResult(null);
    setLastEntityActionResult(null);
  }, [currentParticipant?.id]);

  const handleNpcStandardAction = async () => {
    if (!currentParticipant) {
      return;
    }

    if (selectedStandardAction === "help" && !selectedStandardTargetId) {
      return;
    }

    await executeWithOverride(
      (override) =>
        combatRepo.standardAction(sessionId, {
          action: selectedStandardAction,
          actor_participant_id: currentParticipant.id,
          target_participant_id: selectedStandardAction === "help" ? selectedStandardTargetId : undefined,
          description:
            selectedStandardAction === "use_object" && standardActionNote.trim()
              ? standardActionNote.trim()
              : undefined,
          roll_source: "system",
          override_resource_limit: override,
        }),
      async (result) => {
        setActionResult(result.message);
        await combat.refreshState();
      },
      "Failed to execute standard action"
    );
  };

  const handleEntityUtilityAction = async () => {
    if (!currentParticipant || !selectedUtilityActionId) {
      return;
    }

    await executeWithOverride(
      (override) =>
        combatRepo.entityAction(sessionId, {
          actor_participant_id: currentParticipant.id,
          combat_action_id: selectedUtilityActionId,
          target_ref_id: null,
          override_resource_limit: override,
        }),
      async (result) => {
        setActionResult(formatEntityActionResult(result));
        await combat.refreshState();
      },
      "Failed to execute entity action"
    );
  };

  const handleNextTurn = async () => {
    if (!currentParticipant) return;
    setSubmitting(true);
    setActionError(null);
    setActionResult(null);
    try {
      await combatRepo.nextTurn(sessionId, {
        actor_participant_id: currentParticipant.id,
      });
      await combat.refreshState();
    } catch (err: any) {
      setActionError(err?.data?.detail || err?.message || "Failed to advance turn");
    } finally {
      setSubmitting(false);
    }
  };

  const handleMarkReaction = async () => {
    if (!currentParticipant) return;
    await executeWithOverride(
      (override) =>
        combatRepo.consumeReaction(sessionId, {
          participant_id: currentParticipant.id,
          override_resource_limit: override,
        }),
      async () => {
        await combat.refreshState();
      },
      "Failed to mark reaction"
    );
  };

  const pendingReactionRequests = useMemo(() => {
    return (combat.state?.participants ?? []).filter(
      (p) => p.reaction_request?.status === "pending"
    );
  }, [combat.state?.participants]);

  const handleResolveReaction = async (
    actorParticipantId: string,
    decision: "approve" | "deny"
  ) => {
    await executeWithOverride(
      (override) =>
        combatRepo.resolveReaction(sessionId, {
          actor_participant_id: actorParticipantId,
          decision,
          override_resource_limit: override,
        }),
      async () => {
        await combat.refreshState();
      },
      "Failed to resolve reaction request"
    );
  };

  const handleApplyEffect = async () => {
    if (!targetParticipantId) return;
    setSubmitting(true);
    setActionError(null);
    setActionResult(null);
    try {
      await combatRepo.applyEffect(sessionId, {
        condition_type: effectKind === "condition" ? conditionType : undefined,
        duration_type: durationType,
        kind: effectKind,
        numeric_value: NUMERIC_KINDS.has(effectKind) ? parseInt(numericValue, 10) || 0 : undefined,
        remaining_rounds: durationType === "rounds" ? parseInt(remainingRounds, 10) || 1 : undefined,
        target_participant_id: targetParticipantId,
      });
      await combat.refreshState();
      setApplyEffectOpen(false);
    } catch (err: any) {
      setActionError(err?.data?.detail || err?.message || "Failed to apply effect");
    } finally {
      setSubmitting(false);
    }
  };

  const handleRemoveEffect = async (participantId: string, effectId: string) => {
    setSubmitting(true);
    setActionError(null);
    setActionResult(null);
    try {
      await combatRepo.removeEffect(sessionId, {
        effect_id: effectId,
        target_participant_id: participantId,
      });
      await combat.refreshState();
    } catch (err: any) {
      setActionError(err?.data?.detail || err?.message || "Failed to remove effect");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="space-y-6">
      <CombatModeBar
        currentParticipantName={currentParticipant?.display_name ?? null}
        expanded={expanded}
        onToggleExpanded={onToggleExpanded}
        phase={combat.state?.phase ?? null}
        round={combat.state?.round ?? null}
        turnResources={currentParticipant?.turn_resources ?? null}
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.08fr)_minmax(340px,0.92fr)]">
        <div className="space-y-6">
          <CombatParticipantRoster
            onRemoveEffect={handleRemoveEffect}
            participants={rosterParticipants}
            subtitle={t("combatUi.gmParticipantsDescription")}
            title={t("combatUi.participants")}
          />

          {debugOpen ? (
            <GmCombatDebugPanel
              campaignId={campaignId}
              partyPlayers={partyPlayers}
              sessionId={sessionId}
            />
          ) : null}
        </div>

        <div className="space-y-6">
          {pendingReactionRequests.length > 0 && (
            <section className="rounded-4xl border border-amber-500/25 bg-amber-500/10 p-5 shadow-[0_18px_60px_rgba(2,6,23,0.2)]">
              <h3 className="text-sm font-bold uppercase tracking-widest text-amber-200">Reações Solicitadas</h3>
              <div className="mt-4 space-y-3">
                {pendingReactionRequests.map((reqP) => (
                  <div key={reqP.id} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-slate-950/40 p-3">
                    <span className="text-sm font-semibold text-slate-200">
                      {reqP.display_name} deseja usar Reação
                      {reqP.turn_resources?.reaction_used ? <span className="ml-2 text-[10px] text-rose-400 uppercase">(Já gasta)</span> : null}
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        disabled={submitting}
                        onClick={() => void handleResolveReaction(reqP.id, "approve")}
                        className="rounded-full bg-emerald-500/20 border border-emerald-500/30 px-3 py-1.5 text-xs font-semibold uppercase text-emerald-300 hover:bg-emerald-500/30 disabled:opacity-50"
                      >
                        Aprovar
                      </button>
                      <button
                        type="button"
                        disabled={submitting}
                        onClick={() => void handleResolveReaction(reqP.id, "deny")}
                        className="rounded-full bg-rose-500/20 border border-rose-500/30 px-3 py-1.5 text-xs font-semibold uppercase text-rose-300 hover:bg-rose-500/30 disabled:opacity-50"
                      >
                        Recusar
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

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
                    {t("combatUi.hp")}: {currentParticipantVitals.maxHp != null ? `${currentParticipantVitals.currentHp}/${currentParticipantVitals.maxHp}` : currentParticipantVitals.currentHp}
                  </span>
                ) : null}
              </div>
              
              {currentParticipant?.turn_resources ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  <span className={`rounded flex items-center justify-center px-2 py-1 text-[10px] font-bold uppercase tracking-wider ${currentParticipant.turn_resources.action_used ? "bg-rose-500/20 text-rose-300" : "bg-emerald-500/20 border border-emerald-500/30 text-emerald-200"}`}>
                    Action: {currentParticipant.turn_resources.action_used ? "Used" : "Avail"}
                  </span>
                  <span className={`rounded flex items-center justify-center px-2 py-1 text-[10px] font-bold uppercase tracking-wider ${currentParticipant.turn_resources.bonus_action_used ? "bg-rose-500/20 text-rose-300" : "bg-emerald-500/20 border border-emerald-500/30 text-emerald-200"}`}>
                    Bonus: {currentParticipant.turn_resources.bonus_action_used ? "Used" : "Avail"}
                  </span>
                  <span className={`rounded flex items-center justify-center px-2 py-1 text-[10px] font-bold uppercase tracking-wider ${currentParticipant.turn_resources.reaction_used ? "bg-rose-500/20 text-rose-300" : "bg-emerald-500/20 border border-emerald-500/30 text-emerald-200"}`}>
                    Reaction: {currentParticipant.turn_resources.reaction_used ? "Used" : "Avail"}
                  </span>
                </div>
              ) : null}
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <button
                type="button"
                disabled={!currentParticipant || combat.state?.phase !== "active" || submitting}
                onClick={() => {
                  void handleNextTurn();
                }}
                className="rounded-3xl bg-sky-500 px-4 py-3 text-sm font-semibold uppercase tracking-[0.22em] text-slate-950 transition-colors hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {t("combatUi.advanceTurn")}
              </button>
              <button
                type="button"
                disabled={!currentParticipant || combat.state?.phase !== "active" || submitting}
                onClick={() => {
                  void handleMarkReaction();
                }}
                className="rounded-3xl border border-amber-400/30 bg-amber-500/10 px-4 py-3 text-sm font-semibold uppercase tracking-[0.22em] text-amber-100 transition-colors hover:bg-amber-500/20 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {t("combatUi.markReaction")}
              </button>
              <button
                type="button"
                onClick={() => setApplyEffectOpen((value) => !value)}
                className="rounded-3xl border border-fuchsia-400/30 bg-fuchsia-500/10 px-4 py-3 text-sm font-semibold uppercase tracking-[0.22em] text-fuchsia-100 transition-colors hover:bg-fuchsia-500/20"
              >
                {t("combatUi.applyEffect")}
              </button>
              <button
                type="button"
                onClick={() => setDebugOpen((value) => !value)}
                className="rounded-3xl border border-white/12 bg-white/6 px-4 py-3 text-sm font-semibold uppercase tracking-[0.22em] text-white transition-colors hover:bg-white/10"
              >
                {debugOpen ? t("combatUi.hideDebug") : t("combatUi.showDebug")}
              </button>
            </div>

            {applyEffectOpen ? (
              <div className="mt-4 space-y-3 rounded-3xl border border-fuchsia-500/20 bg-fuchsia-950/20 p-4">
                <label className="block space-y-2">
                  <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
                    {t("combatUi.effectTarget")}
                  </span>
                  <select
                    value={targetParticipantId}
                    onChange={(event) => setTargetParticipantId(event.target.value)}
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
                      onChange={(event) => setEffectKind(event.target.value as ActiveEffectKind)}
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
                      onChange={(event) => setDurationType(event.target.value as ActiveEffectDurationType)}
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
                      onChange={(event) => setConditionType(event.target.value as ActiveEffectConditionType)}
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
                      onChange={(event) => setNumericValue(event.target.value)}
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
                      onChange={(event) => setRemainingRounds(event.target.value)}
                      className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-fuchsia-400"
                    />
                  </label>
                ) : null}

                <button
                  type="button"
                  disabled={!targetParticipantId || submitting}
                  onClick={() => {
                    void handleApplyEffect();
                  }}
                  className="w-full rounded-3xl bg-fuchsia-500 px-4 py-3 text-sm font-semibold uppercase tracking-[0.22em] text-white transition-colors hover:bg-fuchsia-400 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {t("combatUi.applyEffect")}
                </button>
              </div>
            ) : null}

            {currentParticipant?.kind === "session_entity" ? (
              <div className="mt-4 rounded-3xl border border-white/8 bg-white/4 px-4 py-4">
                <p className="text-sm text-slate-200">{t("combatUi.npcTurnHint")}</p>
                <p className="mt-2 text-xs text-slate-400">
                  {t("combatUi.npcTurnDescription")}
                </p>
                <div className="mt-4 space-y-3">
                  {npcCombatActions.length === 0 ? (
                    <p className="rounded-2xl border border-white/8 bg-slate-950/40 px-3 py-3 text-xs text-slate-400">
                      {t("combatUi.entityNoStructuredActions")}
                    </p>
                  ) : null}

                  <div className="grid gap-2 sm:grid-cols-3">
                    {([
                      ["attack", t("combatUi.attack")],
                      ["spell", t("combatUi.castSpell")],
                      ["standard", t("combatUi.standardActions")],
                    ] as const).map(([panel, label]) => {
                      const isActive = entityActionPanel === panel;
                      const isDisabled =
                        panel === "attack" ? !attackPanelEnabled : panel === "spell" ? !spellPanelEnabled : false;
                      return (
                        <button
                          key={panel}
                          type="button"
                          disabled={isDisabled}
                          onClick={() => setEntityActionPanel(panel)}
                          className={`rounded-2xl px-4 py-3 text-sm font-semibold transition-colors ${
                            isActive
                              ? "bg-white text-slate-950"
                              : isDisabled
                                ? "cursor-not-allowed bg-slate-950/30 text-slate-500 opacity-60"
                                : "bg-slate-950/50 text-slate-200 hover:bg-slate-900/70"
                          }`}
                        >
                          <span className="block whitespace-normal break-words leading-5">
                            {label}
                          </span>
                        </button>
                      );
                    })}
                  </div>

                  {(entityActionPanel === "attack" || entityActionPanel === "spell") ? (
                    activeStructuredActions.length === 0 ? (
                      <p className="rounded-2xl border border-white/8 bg-slate-950/40 px-3 py-3 text-xs text-slate-400">
                        {entityActionPanel === "attack"
                          ? t("combatUi.entityNoAttackActions")
                          : t("combatUi.entityNoSpellActions")}
                      </p>
                    ) : (
                      <>
                        <select
                          value={selectedCombatActionId}
                          onChange={(event) => setSelectedCombatActionId(event.target.value)}
                          className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-rose-400"
                        >
                          {activeStructuredActions.map((action) => (
                            <option key={action.id} value={action.id}>
                              {action.name}
                            </option>
                          ))}
                        </select>

                        {selectedCombatAction ? (
                          <div className="rounded-2xl border border-white/8 bg-slate-950/40 px-3 py-3 text-xs text-slate-300">
                            <p className="font-semibold text-white">{selectedCombatAction.name}</p>
                            {describeCombatAction(selectedCombatAction) ? (
                              <p className="mt-1 text-slate-400">{describeCombatAction(selectedCombatAction)}</p>
                            ) : null}
                            {selectedCombatAction.description ? (
                              <p className="mt-2 text-slate-500">{selectedCombatAction.description}</p>
                            ) : null}
                          </div>
                        ) : null}

                        <select
                          value={selectedTargetRefId}
                          onChange={(event) => setSelectedTargetRefId(event.target.value)}
                          className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-rose-400"
                        >
                          <option value="">{t("combatUi.selectTarget")}</option>
                          {availableTargets.map((participant) => (
                            <option key={participant.id} value={participant.ref_id}>
                              {participant.display_name}
                              {participant.id === currentParticipant.id ? ` (${t("combatUi.self")})` : ""}
                              {" "}
                              [{getCombatStatusLabel(t, participant.status)}]
                            </option>
                          ))}
                        </select>

                        <button
                          type="button"
                          disabled={submitting || !selectedCombatActionId || !selectedTargetRefId}
                          onClick={() => {
                            void handleEntityAction();
                          }}
                          className="w-full rounded-3xl bg-rose-600 px-4 py-3 text-sm font-semibold uppercase tracking-[0.22em] text-white transition-colors hover:bg-rose-500 disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          {selectedCombatAction?.kind === "weapon_attack" ||
                          selectedCombatAction?.kind === "spell_attack"
                            ? t("combatUi.entityOpenActionRoll")
                            : t("combatUi.entityExecuteAction")}
                        </button>
                      </>
                    )
                  ) : null}

                  {entityActionPanel === "standard" ? (
                    <div className="space-y-4">
                      <div className="space-y-3">
                        <div className="grid gap-2 sm:grid-cols-2">
                          {ENTITY_STANDARD_ACTIONS.map((action) => {
                            const isActive = selectedStandardAction === action;
                            const labelKey =
                              action === "use_object"
                                ? "combatUi.useObject"
                                : action === "dodge"
                                  ? "combatUi.dodge"
                                  : action === "help"
                                    ? "combatUi.help"
                                    : action === "hide"
                                      ? "combatUi.hide"
                                      : action === "dash"
                                        ? "combatUi.dash"
                                        : "combatUi.disengage";
                            return (
                              <button
                                key={action}
                                type="button"
                                onClick={() => setSelectedStandardAction(action)}
                                className={`rounded-2xl border px-4 py-3 text-left text-sm font-semibold transition-colors ${
                                  isActive
                                    ? "border-rose-400/50 bg-rose-500/20 text-white"
                                    : "border-white/10 bg-slate-950/50 text-slate-200 hover:bg-slate-900/70"
                                }`}
                              >
                                <span className="block whitespace-normal break-words leading-5">
                                  {t(labelKey)}
                                </span>
                              </button>
                            );
                          })}
                        </div>

                        {selectedStandardAction === "help" ? (
                          <select
                            value={selectedStandardTargetId}
                            onChange={(event) => setSelectedStandardTargetId(event.target.value)}
                            className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-rose-400"
                          >
                            <option value="">{t("combatUi.selectTarget")}</option>
                            {availableStandardTargets.map((participant) => (
                              <option key={participant.id} value={participant.id}>
                                {participant.display_name} [{getCombatStatusLabel(t, participant.status)}]
                              </option>
                            ))}
                          </select>
                        ) : null}

                        {selectedStandardAction === "use_object" ? (
                          <input
                            type="text"
                            value={standardActionNote}
                            onChange={(event) => setStandardActionNote(event.target.value)}
                            placeholder={t("combatUi.useObjectPlaceholder")}
                            className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none transition-colors placeholder:text-slate-500 focus:border-rose-400"
                          />
                        ) : null}

                        <button
                          type="button"
                          disabled={
                            submitting ||
                            (selectedStandardAction === "help" && !selectedStandardTargetId)
                          }
                          onClick={() => {
                            void handleNpcStandardAction();
                          }}
                          className="w-full rounded-3xl bg-rose-600 px-4 py-3 text-sm font-semibold uppercase tracking-[0.22em] text-white transition-colors hover:bg-rose-500 disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          {t("combatUi.entityUseStandardAction")}
                        </button>
                      </div>

                      {utilityCombatActions.length > 0 ? (
                        <div className="space-y-3 rounded-3xl border border-white/8 bg-slate-950/35 px-4 py-4">
                          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                            {t("combatUi.entityUtilityActions")}
                          </p>

                          <select
                            value={selectedUtilityActionId}
                            onChange={(event) => setSelectedUtilityActionId(event.target.value)}
                            className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-rose-400"
                          >
                            {utilityCombatActions.map((action) => (
                              <option key={action.id} value={action.id}>
                                {action.name}
                              </option>
                            ))}
                          </select>

                          {selectedUtilityAction ? (
                            <div className="rounded-2xl border border-white/8 bg-slate-950/40 px-3 py-3 text-xs text-slate-300">
                              <p className="font-semibold text-white">{selectedUtilityAction.name}</p>
                              {describeCombatAction(selectedUtilityAction) ? (
                                <p className="mt-1 text-slate-400">{describeCombatAction(selectedUtilityAction)}</p>
                              ) : null}
                              {selectedUtilityAction.description ? (
                                <p className="mt-2 text-slate-500">{selectedUtilityAction.description}</p>
                              ) : null}
                            </div>
                          ) : null}

                          <button
                            type="button"
                            disabled={submitting || !selectedUtilityActionId}
                            onClick={() => {
                              void handleEntityUtilityAction();
                            }}
                            className="w-full rounded-3xl border border-white/12 bg-white/6 px-4 py-3 text-sm font-semibold uppercase tracking-[0.22em] text-white transition-colors hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40"
                          >
                            {t("combatUi.entityExecuteAction")}
                          </button>
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              </div>
            ) : null}

            {lastEntityActionResult?.roll_result ? (
              <div className="mt-4 rounded-3xl border border-amber-500/20 bg-amber-500/10 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-amber-200">
                  {t("combatUi.lastEntityRoll")}
                </p>
                <div className="mt-3">
                  <RollResultCard result={lastEntityActionResult.roll_result} />
                </div>
              </div>
            ) : null}
          </section>

          <CombatLogPanel logs={combat.logs} />
        </div>
      </div>

      {entityActionDialogOpen &&
      currentParticipant &&
      selectedCombatAction &&
      selectedTarget &&
      (selectedCombatAction.kind === "weapon_attack" || selectedCombatAction.kind === "spell_attack") ? (
        <GmEntityActionRollDialog
          actorParticipantId={currentParticipant.id}
          sessionId={sessionId}
          actionId={selectedCombatActionId}
          actionName={selectedCombatAction?.name || ""}
          actionKind={selectedCombatAction?.kind as "weapon_attack" | "spell_attack"}
          actionDescription={selectedCombatAction?.description}
          target={selectedTarget as any}
          onClose={() => setEntityActionDialogOpen(false)}
          onResolved={handleEntityActionResolved}
        />
      ) : null}

      <GmActionOverrideDialog
        isOpen={overrideDialogOpen}
        onClose={() => {
          setOverrideDialogOpen(false);
          setPendingOverrideAction(null);
        }}
        onConfirm={() => {
          if (pendingOverrideAction) {
            void pendingOverrideAction();
          }
        }}
        resourceName={overrideResourceName}
        isSubmitting={submitting}
      />
    </section>
  );
};
