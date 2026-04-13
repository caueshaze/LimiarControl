import type {
  ActiveEffectConditionType,
  ActiveEffectDurationType,
  ActiveEffectKind,
  CombatEntityActionResult,
  CombatParticipant,
  StandardActionType,
} from "../../../shared/api/combatRepo";
import { combatRepo } from "../../../shared/api/combatRepo";
import type { CombatAction } from "../../../entities/campaign-entity/campaignEntity.types";
import { useLocale } from "../../../shared/hooks/useLocale";

const NUMERIC_KINDS = new Set<ActiveEffectKind>(["temp_ac_bonus", "attack_bonus", "damage_bonus"]);

type UseCombatHandlersOptions = {
  sessionId: string;
  currentParticipant: CombatParticipant | null;
  selectedCombatAction: CombatAction | null;
  selectedUtilityAction: CombatAction | null;
  selectedCombatActionId: string;
  selectedTargetRefId: string;
  selectedUtilityActionId: string;
  selectedStandardAction: StandardActionType;
  selectedStandardTargetId: string;
  standardActionNote: string;
  targetParticipantId: string;
  effectKind: ActiveEffectKind;
  conditionType: ActiveEffectConditionType;
  numericValue: string;
  durationType: ActiveEffectDurationType;
  remainingRounds: string;
  refreshCombat: () => Promise<void>;
  setSubmitting: (v: boolean) => void;
  setActionError: (v: string | null) => void;
  setActionResult: (v: string | null) => void;
  setLastEntityActionResult: (v: CombatEntityActionResult | null) => void;
  setEntityActionDialogOpen: (v: boolean) => void;
  setApplyEffectOpen: (v: boolean) => void;
  setOverrideDialogOpen: (v: boolean) => void;
  setOverrideResourceName: (v: string) => void;
  setPendingOverrideAction: (fn: (() => Promise<void>) | null) => void;
};

export const useGmCombatHandlers = ({
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
  refreshCombat,
  setSubmitting,
  setActionError,
  setActionResult,
  setLastEntityActionResult,
  setEntityActionDialogOpen,
  setApplyEffectOpen,
  setOverrideDialogOpen,
  setOverrideResourceName,
  setPendingOverrideAction,
}: UseCombatHandlersOptions) => {
  const { t } = useLocale();
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
    if (result.action_kind === "heal") return `${actionName} healed ${result.healing ?? 0} HP.`;
    return `${actionName} executed.`;
  };

  const executeWithOverride = async (
    apiCall: (override: boolean) => Promise<any>,
    onSuccess: (result: any) => Promise<void>,
    fallbackMsg: string,
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
        setPendingOverrideAction(async () => {
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
      if (!is409) setSubmitting(false);
    }
  };

  const handleEntityActionResolved = async (result: CombatEntityActionResult) => {
    setLastEntityActionResult(result);
    setActionResult(formatEntityActionResult(result));
    setEntityActionDialogOpen(false);
    await refreshCombat();
  };

  const handleEntityAction = async () => {
    if (!currentParticipant || !selectedCombatActionId) return;
    if (selectedCombatAction?.kind !== "utility" && !selectedTargetRefId) return;
    setActionError(null);
    setActionResult(null);
    setLastEntityActionResult(null);
    if (selectedCombatAction?.kind === "weapon_attack" || selectedCombatAction?.kind === "spell_attack") {
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
        await refreshCombat();
      },
      "Failed to execute entity action",
    );
  };

  const handleNpcStandardAction = async () => {
    if (!currentParticipant) return;
    if (selectedStandardAction === "help" && !selectedStandardTargetId) return;
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
        await refreshCombat();
      },
      "Failed to execute standard action",
    );
  };

  const handleEntityUtilityAction = async () => {
    if (!currentParticipant || !selectedUtilityActionId) return;
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
        await refreshCombat();
      },
      "Failed to execute entity action",
    );
  };

  const handleNextTurn = async () => {
    if (!currentParticipant) return;
    setSubmitting(true);
    setActionError(null);
    setActionResult(null);
    try {
      await combatRepo.nextTurn(sessionId, { actor_participant_id: currentParticipant.id });
      await refreshCombat();
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
      async () => { await refreshCombat(); },
      "Failed to mark reaction",
    );
  };

  const handleResolveReaction = async (actorParticipantId: string, decision: "approve" | "deny") => {
    await executeWithOverride(
      (override) =>
        combatRepo.resolveReaction(sessionId, {
          actor_participant_id: actorParticipantId,
          decision,
          override_resource_limit: override,
        }),
      async () => { await refreshCombat(); },
      "Failed to resolve reaction request",
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
      await refreshCombat();
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
      await refreshCombat();
    } catch (err: any) {
      setActionError(err?.data?.detail || err?.message || "Failed to remove effect");
    } finally {
      setSubmitting(false);
    }
  };

  const handleRevive = async (
    targetParticipantId: string,
    hp: number = 1,
  ) => {
    setSubmitting(true);
    setActionError(null);
    setActionResult(null);
    try {
      const result = await combatRepo.revive(sessionId, {
        target_participant_id: targetParticipantId,
        hp,
      });
      setActionResult(
        t("combatUi.revivePlayerSuccess").replace("{hp}", String(result.new_hp)),
      );
      await refreshCombat();
    } catch (err: any) {
      setActionError(err?.data?.detail || err?.message || t("combatUi.revivePlayerError"));
    } finally {
      setSubmitting(false);
    }
  };

  return {
    handleEntityActionResolved,
    handleEntityAction,
    handleNpcStandardAction,
    handleEntityUtilityAction,
    handleNextTurn,
    handleMarkReaction,
    handleResolveReaction,
    handleApplyEffect,
    handleRemoveEffect,
    handleRevive,
  };
};
