import { useEffect, useState } from "react";
import {
  combatRepo,
  type CombatEntityActionResult,
  type CombatState,
} from "../../shared/api/combatRepo";
import { subscribe } from "../../shared/realtime/centrifugoClient";
import type { SessionEntity } from "../../entities/session-entity";
import { sessionEntitiesRepo } from "../../shared/api/sessionEntitiesRepo";
import { formatDamageDiceExpression } from "../../shared/utils/diceExpression";

export const useGmCombatDebug = (sessionId: string) => {
  const [state, setState] = useState<CombatState | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [initiatives, setInitiatives] = useState<Record<string, string>>({});
  const [sessionEntities, setSessionEntities] = useState<SessionEntity[]>([]);
  const [selectedCombatActionId, setSelectedCombatActionId] = useState<string>("");
  const [targetId, setTargetId] = useState<string>("");
  const [actionResult, setActionResult] = useState<string | null>(null);
  const [entityActionDialogOpen, setEntityActionDialogOpen] = useState(false);
  const [lastEntityActionResult, setLastEntityActionResult] = useState<CombatEntityActionResult | null>(null);

  useEffect(() => {
    let active = true;
    combatRepo.getState(sessionId).then((s: CombatState) => {
      if (active) setState(s);
    }).catch(() => {
        if (active) setState(null);
    });

    const channel = `session:${sessionId}`;
    const unsub = subscribe(channel, {
      onPublication: (message: any) => {
        if (message?.type === "combat_state_updated") {
          setState(message.payload as CombatState);
        }
      },
    });

    return () => {
      active = false;
      unsub();
    };
  }, [sessionId]);

  useEffect(() => {
    let active = true;
    sessionEntitiesRepo.list(sessionId).then((data) => {
      if (active) {
        setSessionEntities(Array.isArray(data) ? data : []);
      }
    }).catch(() => {
      if (active) {
        setSessionEntities([]);
      }
    });

    return () => {
      active = false;
    };
  }, [sessionId, state?.participants.length]);

  useEffect(() => {
    if (!state) {
      setInitiatives({});
      return;
    }

    setInitiatives((current) => {
      const next: Record<string, string> = {};
      for (const participant of state.participants) {
        const existingValue = current[participant.id];
        next[participant.id] =
          participant.initiative != null
            ? String(participant.initiative)
            : existingValue ?? "";
      }
      return next;
    });
  }, [state]);

  const currentParticipant = state?.participants[state.current_turn_index];
  const canActForNpc =
    state?.phase === "active" &&
    currentParticipant?.kind === "session_entity" &&
    currentParticipant?.status === "active";
  const activeSessionEntity =
    canActForNpc && currentParticipant
      ? sessionEntities.find((entity) => entity.id === currentParticipant.ref_id) ?? null
      : null;
  const npcCombatActions = activeSessionEntity?.entity?.combatActions ?? [];
  const selectedCombatAction =
    npcCombatActions.find((action) => action.id === selectedCombatActionId) ?? npcCombatActions[0] ?? null;
  const availableTargets = state?.phase === "active" && currentParticipant
    ? state.participants.filter((participant) => participant.status !== "dead" && participant.status !== "defeated")
    : [];
  const selectedTarget =
    availableTargets.find((participant) => participant.ref_id === targetId) ?? null;

  useEffect(() => {
    if (!npcCombatActions.length) {
      setSelectedCombatActionId("");
      return;
    }
    const hasCurrentAction = npcCombatActions.some((action) => action.id === selectedCombatActionId);
    if (!hasCurrentAction) {
      setSelectedCombatActionId(npcCombatActions[0].id);
    }
  }, [npcCombatActions, selectedCombatActionId]);

  useEffect(() => {
    if (!state || !currentParticipant || !selectedCombatAction) {
      setTargetId("");
      return;
    }

    if (selectedCombatAction.kind === "utility") {
      setTargetId("");
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

    const isCurrentTargetValid = availableTargets.some((participant) => participant.ref_id === targetId);
    if (!isCurrentTargetValid) {
      setTargetId(preferredTarget?.ref_id ?? "");
    }
  }, [availableTargets, currentParticipant, selectedCombatAction, state, targetId]);

  const formatEntityActionResult = (result: CombatEntityActionResult) => {
    if (!selectedCombatAction) {
      return "Action resolved.";
    }
    if (result?.action_kind === "weapon_attack" || result?.action_kind === "spell_attack") {
      const damageDiceLabel =
        formatDamageDiceExpression(result.damage_dice, Boolean(result.is_critical)) ??
        result.damage_dice;
      return result?.is_hit
        ? `${selectedCombatAction.name} acertou e causou ${result?.damage ?? 0} de dano${damageDiceLabel ? ` (${damageDiceLabel}${typeof result.damage_bonus === "number" ? ` + ${result.damage_bonus}` : ""})` : ""}.`
        : `${selectedCombatAction.name} errou com ${result?.roll ?? "-"}.`;
    }
    if (result?.action_kind === "saving_throw") {
      const rolledTotal = Math.max(0, (result.base_damage ?? 0) + (result.damage_bonus ?? 0));
      return result?.is_saved
        ? result?.save_success_outcome === "half_damage"
          ? `${selectedCombatAction.name}: target saved (${result?.save_roll ?? "-"} vs DC ${result?.save_dc ?? "-"}) and took half damage (${result?.damage ?? 0} of ${rolledTotal}).`
          : `${selectedCombatAction.name}: target saved (${result?.save_roll ?? "-"} vs DC ${result?.save_dc ?? "-"}) and took no damage.`
        : `${selectedCombatAction.name}: target failed the save and took ${result?.damage ?? 0} damage.`;
    }
    if (result?.action_kind === "heal") {
      return `${selectedCombatAction.name} healed ${result?.healing ?? 0} HP.`;
    }
    return `${selectedCombatAction.name} executed.`;
  };

  const handleSetInitiative = async () => {
    if (!state) return;
    setLoading(true);
    setError(null);
    setActionResult(null);
    try {
      const req = Object.entries(initiatives).map(([id, val]) => ({
        id,
        initiative: parseInt(val, 10) || 0,
      }));
      const updated = await combatRepo.setInitiative(sessionId, { initiatives: req });
      if (updated) setState(updated);
    } catch (err: any) {
      setError(err?.data?.detail || err?.message || "Failed to set initiative");
    } finally {
      setLoading(false);
    }
  };

  const handleNextTurn = async () => {
    if (!state) return;
    setLoading(true);
    setError(null);
    setActionResult(null);
    try {
      const updated = await combatRepo.nextTurn(sessionId, {
        actor_participant_id: state.participants[state.current_turn_index]?.id ?? null,
      });
      if (updated) setState(updated);
    } catch (err: any) {
      setError(err?.data?.detail || err?.message || "Failed to advance turn");
    } finally {
      setLoading(false);
    }
  };

  const handleMarkReaction = async () => {
    const active = state?.participants[state.current_turn_index];
    if (!active) return;
    try {
      setLoading(true);
      await combatRepo.consumeReaction(sessionId, { participant_id: active.id });
    } catch {} finally { setLoading(false); }
  };

  const executeEntityActionDirectly = async () => {
    if (!state || !selectedCombatActionId) return;
    if (selectedCombatAction?.kind !== "utility" && !targetId) return;
    setLoading(true);
    setError(null);
    setActionResult(null);
    try {
      const result = await combatRepo.entityAction(sessionId, {
        actor_participant_id: state.participants[state.current_turn_index]?.id ?? null,
        combat_action_id: selectedCombatActionId,
        target_ref_id: selectedCombatAction?.kind === "utility" ? null : targetId,
      });
      const refreshed = await combatRepo.getState(sessionId);
      setState(refreshed);
      setActionResult(formatEntityActionResult(result));
    } catch (err: any) {
      setError(err?.data?.detail || err?.message || "Failed to execute action");
    } finally {
      setLoading(false);
    }
  };

  const handleEntityAction = async () => {
    if (!state || !selectedCombatActionId) return;
    if (selectedCombatAction?.kind !== "utility" && !targetId) return;

    if (
      selectedCombatAction?.kind === "weapon_attack" ||
      selectedCombatAction?.kind === "spell_attack"
    ) {
      setError(null);
      setActionResult(null);
      setLastEntityActionResult(null);
      setEntityActionDialogOpen(true);
      return;
    }

    await executeEntityActionDirectly();
  };

  const handleEntityActionResolved = async (result: CombatEntityActionResult) => {
    setLastEntityActionResult(result);
    setActionResult(formatEntityActionResult(result));
    const refreshed = await combatRepo.getState(sessionId);
    if (refreshed) {
      setState(refreshed);
    }
  };

  return {
    state,
    setState,
    loading,
    setLoading,
    error,
    initiatives,
    setInitiatives,
    selectedCombatActionId,
    setSelectedCombatActionId,
    targetId,
    setTargetId,
    actionResult,
    entityActionDialogOpen,
    setEntityActionDialogOpen,
    lastEntityActionResult,
    currentParticipant,
    canActForNpc,
    npcCombatActions,
    selectedCombatAction,
    availableTargets,
    selectedTarget,
    handleSetInitiative,
    handleNextTurn,
    handleMarkReaction,
    handleEntityAction,
    handleEntityActionResolved,
  };
};
