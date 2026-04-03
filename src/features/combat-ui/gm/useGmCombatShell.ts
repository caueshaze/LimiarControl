import { useEffect, useMemo, useState } from "react";
import type {
  ActiveEffectConditionType,
  ActiveEffectDurationType,
  ActiveEffectKind,
  CombatEntityActionResult,
  StandardActionType,
} from "../../../shared/api/combatRepo";
import type { CharacterSheet } from "../../../features/character-sheet/model/characterSheet.types";
import { useSessionEntities } from "../../../features/session-entities/hooks/useSessionEntities";
import { buildCombatParticipantViews } from "../combatUi.helpers";
import { useCombatUiState } from "../useCombatUiState";
import { useGmCombatHandlers } from "./useGmCombatHandlers";

type UseGmCombatShellOptions = {
  sessionId: string;
  playerSheetByUserId: Record<string, CharacterSheet>;
};

export const useGmCombatShell = ({ sessionId, playerSheetByUserId }: UseGmCombatShellOptions) => {
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
  const [selectedReviveParticipantId, setSelectedReviveParticipantId] = useState("");
  const [reviveHp, setReviveHp] = useState("1");
  const [submitting, setSubmitting] = useState(false);
  const [overrideDialogOpen, setOverrideDialogOpen] = useState(false);
  const [overrideResourceName, setOverrideResourceName] = useState("");
  const [pendingOverrideAction, setPendingOverrideAction] = useState<(() => Promise<void>) | null>(null);

  const playerVitalsByUserId = useMemo(
    () =>
      Object.fromEntries(
        Object.entries(playerSheetByUserId).map(([userId, sheet]) => [
          userId,
          { currentHp: sheet.currentHP, maxHp: sheet.maxHP },
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
    ? rosterParticipants.find((p) => p.id === currentParticipant.id) ?? null
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
          action.kind === "spell_attack" || action.kind === "saving_throw" || action.kind === "heal",
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
  const availableTargets =
    combat.state?.participants.filter(
      (p) => p.status !== "dead" && p.status !== "defeated",
    ) ?? [];
  const selectedTarget = availableTargets.find((p) => p.ref_id === selectedTargetRefId) ?? null;
  const availableStandardTargets = availableTargets.filter((p) => p.id !== currentParticipant?.id);

  const pendingReactionRequests = useMemo(
    () => (combat.state?.participants ?? []).filter((p) => p.reaction_request?.status === "pending"),
    [combat.state?.participants],
  );
  const deadPlayerParticipants = useMemo(
    () =>
      rosterParticipants.filter(
        (participant) => participant.kind === "player" && participant.status === "dead",
      ),
    [rosterParticipants],
  );

  const handlers = useGmCombatHandlers({
    sessionId,
    currentParticipant,
    selectedCombatAction,
    selectedUtilityAction,
    selectedCombatActionId,
    selectedTargetRefId,
    selectedUtilityActionId,
    selectedStandardAction,
    selectedStandardTargetId,
    standardActionNote,
    targetParticipantId,
    effectKind,
    conditionType,
    numericValue,
    durationType,
    remainingRounds,
    refreshCombat: combat.refreshState,
    setSubmitting,
    setActionError,
    setActionResult,
    setLastEntityActionResult,
    setEntityActionDialogOpen,
    setApplyEffectOpen,
    setOverrideDialogOpen,
    setOverrideResourceName,
    setPendingOverrideAction,
  });

  useEffect(() => {
    if (!activeStructuredActions.length) {
      setSelectedCombatActionId("");
      return;
    }
    if (!activeStructuredActions.some((a) => a.id === selectedCombatActionId)) {
      setSelectedCombatActionId(activeStructuredActions[0]?.id ?? "");
    }
  }, [activeStructuredActions, selectedCombatActionId]);

  useEffect(() => {
    if (!utilityCombatActions.length) {
      setSelectedUtilityActionId("");
      return;
    }
    if (!utilityCombatActions.some((a) => a.id === selectedUtilityActionId)) {
      setSelectedUtilityActionId(utilityCombatActions[0]?.id ?? "");
    }
  }, [selectedUtilityActionId, utilityCombatActions]);

  useEffect(() => {
    if (currentParticipant?.kind === "session_entity") return;
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
    if (selectedTarget) return;
    const preferredTarget =
      selectedCombatAction.kind === "heal"
        ? availableTargets.find((p) => p.id === currentParticipant.id) ??
          availableTargets.find((p) => p.team === currentParticipant.team) ??
          availableTargets[0]
        : availableTargets.find(
            (p) => p.id !== currentParticipant.id && p.team !== currentParticipant.team,
          ) ??
          availableTargets.find((p) => p.id !== currentParticipant.id) ??
          availableTargets[0];
    if (preferredTarget?.ref_id) setSelectedTargetRefId(preferredTarget.ref_id);
  }, [availableTargets, currentParticipant, entityActionPanel, selectedCombatAction, selectedTarget, selectedTargetRefId]);

  useEffect(() => {
    if (entityActionPanel !== "attack" && entityActionPanel !== "spell") return;
    if (entityActionPanel === "attack" && attackCombatActions.length === 0) {
      setEntityActionPanel(spellCombatActions.length > 0 ? "spell" : "standard");
      return;
    }
    if (entityActionPanel === "spell" && spellCombatActions.length === 0) {
      setEntityActionPanel(attackCombatActions.length > 0 ? "attack" : "standard");
    }
  }, [attackCombatActions.length, entityActionPanel, spellCombatActions.length]);

  useEffect(() => {
    if (selectedStandardAction !== "help") setSelectedStandardTargetId("");
    if (selectedStandardAction !== "use_object") setStandardActionNote("");
  }, [selectedStandardAction]);

  useEffect(() => {
    setActionError(null);
    setActionResult(null);
    setLastEntityActionResult(null);
  }, [currentParticipant?.id]);

  useEffect(() => {
    if (!deadPlayerParticipants.length) {
      setSelectedReviveParticipantId("");
      return;
    }
    if (!deadPlayerParticipants.some((participant) => participant.id === selectedReviveParticipantId)) {
      setSelectedReviveParticipantId(deadPlayerParticipants[0]?.id ?? "");
    }
  }, [deadPlayerParticipants, selectedReviveParticipantId]);

  return {
    // Combat state
    combat,
    rosterParticipants,
    currentParticipant,
    currentParticipantVitals,
    pendingReactionRequests,
    deadPlayerParticipants,
    // UI state
    debugOpen,
    setDebugOpen,
    applyEffectOpen,
    setApplyEffectOpen,
    submitting,
    actionError,
    actionResult,
    entityActionDialogOpen,
    setEntityActionDialogOpen,
    lastEntityActionResult,
    overrideDialogOpen,
    setOverrideDialogOpen,
    overrideResourceName,
    pendingOverrideAction,
    setPendingOverrideAction,
    // Effect form state
    targetParticipantId,
    setTargetParticipantId,
    effectKind,
    setEffectKind,
    conditionType,
    setConditionType,
    numericValue,
    setNumericValue,
    durationType,
    setDurationType,
    remainingRounds,
    setRemainingRounds,
    // NPC action state
    npcCombatActions,
    attackCombatActions,
    spellCombatActions,
    utilityCombatActions,
    activeStructuredActions,
    availableTargets,
    availableStandardTargets,
    entityActionPanel,
    setEntityActionPanel,
    attackPanelEnabled,
    spellPanelEnabled,
    selectedCombatActionId,
    setSelectedCombatActionId,
    selectedCombatAction,
    selectedTargetRefId,
    setSelectedTargetRefId,
    selectedUtilityActionId,
    setSelectedUtilityActionId,
    selectedUtilityAction,
    selectedStandardAction,
    setSelectedStandardAction,
    selectedStandardTargetId,
    setSelectedStandardTargetId,
    standardActionNote,
    setStandardActionNote,
    selectedReviveParticipantId,
    setSelectedReviveParticipantId,
    reviveHp,
    setReviveHp,
    selectedTarget,
    // Handlers (from useGmCombatHandlers)
    ...handlers,
  };
};
