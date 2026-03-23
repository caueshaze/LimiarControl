import { useEffect, useState } from "react";
import {
  combatRepo,
  type CombatEntityActionResult,
  type CombatState,
} from "../../shared/api/combatRepo";
import { subscribe } from "../../shared/realtime/centrifugoClient";
import type { PartyMemberSummary } from "../../shared/api/partiesRepo";
import type { SessionEntity } from "../../entities/session-entity";
import { describeCombatAction } from "../../entities/campaign-entity/describeCombatAction";
import { sessionEntitiesRepo } from "../../shared/api/sessionEntitiesRepo";
import { RollResultCard } from "../../features/rolls/components/RollResultCard";
import { formatDamageDiceExpression } from "../../shared/utils/diceExpression";
import { GmEntityActionRollDialog } from "./GmEntityActionRollDialog";

export const GmCombatDebugPanel = ({
  sessionId,
  campaignId,
  partyPlayers,
}: {
  sessionId: string;
  campaignId: string;
  partyPlayers: PartyMemberSummary[];
}) => {
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
      return result?.is_saved
        ? `${selectedCombatAction.name}: target saved (${result?.save_roll ?? "-"} vs DC ${result?.save_dc ?? "-"})`
        : `${selectedCombatAction.name}: target failed the save and took ${result?.damage ?? 0} damage.`;
    }
    if (result?.action_kind === "heal") {
      return `${selectedCombatAction.name} healed ${result?.healing ?? 0} HP.`;
    }
    return `${selectedCombatAction.name} executed.`;
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

  return (
    <div className="rounded-xl border border-rose-500/30 bg-rose-950/20 p-4 mt-6">
      <div className="flex items-center justify-between">
         <h3 className="text-lg font-bold text-rose-300">Phase 2 Turn Controller (Debug)</h3>
      </div>
      
      {error && (
        <div className="mt-4 rounded border border-rose-500 bg-rose-500/10 p-2 text-rose-200 text-sm">
          <strong>Error:</strong> {error}
        </div>
      )}

      {actionResult && (
        <div className="mt-4 rounded border border-emerald-500/40 bg-emerald-500/10 p-2 text-sm text-emerald-200">
          <strong>Result:</strong> {actionResult}
        </div>
      )}

      {lastEntityActionResult?.roll_result && (
        <div className="mt-4 rounded border border-amber-500/30 bg-amber-500/10 p-3">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-amber-200">
            Last NPC Attack
          </p>
          <div className="mt-3">
            <RollResultCard result={lastEntityActionResult.roll_result} />
          </div>
        </div>
      )}

      {!state || state.phase === "ended" ? (
        <div className="mt-4 text-slate-400 text-sm italic">
          Fetching backend state or no combat currently tracked...
        </div>
      ) : (
        <div className="mt-4 space-y-4 text-sm text-slate-300">
          <div className="flex justify-between items-center rounded border border-rose-500/20 bg-rose-900/10 p-2">
             <span>Phase: <strong className="uppercase text-rose-400">{state.phase}</strong></span>
             <span>Round: <strong className="text-white">{state.round}</strong></span>
          </div>

          <div className="space-y-2">
             {state.participants.map((p: any, idx: number) => (
                <div key={p.id} className={`flex items-center gap-2 rounded border px-3 py-2 ${state.current_turn_index === idx && state.phase === 'active' ? 'border-amber-500 bg-amber-500/20' : 'border-slate-700 bg-slate-800'}`}>
                   <span className="w-6 font-mono text-slate-500">{idx + 1}.</span>
                   <span className="flex-1 font-semibold">
                      {p.display_name} {p.kind === 'session_entity' ? '(NPC)' : '(Player)'}
                      <em className="ml-2 text-[10px] uppercase font-bold text-rose-500">{p.status !== "active" && p.status}</em>
                   </span>
                   
                   {state.phase === "initiative" ? (
                      <input 
                         type="number" 
                         value={initiatives[p.id] || ""}
                         onChange={(e) => setInitiatives({ ...initiatives, [p.id]: e.target.value })}
                         placeholder="Init"
                         className="w-16 rounded bg-slate-900 px-2 py-1 text-center"
                      />
                   ) : (
                      <strong className="text-amber-400">{p.initiative}</strong>
                   )}
                </div>
             ))}
          </div>

          <div className="flex gap-2">
            {state.phase === "initiative" && (
                <button
                    disabled={loading}
                    onClick={handleSetInitiative}
                    className="flex-1 rounded bg-amber-600 px-4 py-2 font-bold text-white hover:bg-amber-500 disabled:opacity-50"
                  >
                    Confirm Initiatives
                </button>
            )}
            
            {state.phase === "active" && (
                <button
                    disabled={loading}
                    onClick={handleNextTurn}
                    className="flex-1 rounded bg-sky-600 px-4 py-2 font-bold text-white hover:bg-sky-500 disabled:opacity-50"
                  >
                    Next Turn (Bypass)
                </button>
            )}
          </div>

          {canActForNpc && (
            <div className="rounded border border-rose-500/20 bg-slate-950/60 p-4">
              <h4 className="mb-2 font-bold text-rose-300">
                NPC Active Actions: {currentParticipant.display_name}
              </h4>
              {npcCombatActions.length === 0 ? (
                <div className="rounded border border-slate-800 bg-slate-900/60 p-3 text-xs text-slate-400">
                  This entity has no structured combat actions configured yet.
                </div>
              ) : (
                <div className="space-y-3">
                  <select
                    className="w-full rounded border border-slate-700 bg-slate-900 p-2 text-white"
                    value={selectedCombatActionId}
                    onChange={(e) => setSelectedCombatActionId(e.target.value)}
                  >
                    {npcCombatActions.map((action) => (
                      <option key={action.id} value={action.id}>
                        {action.name} [{action.kind}]
                      </option>
                    ))}
                  </select>

                  {selectedCombatAction && (
                    <div className="rounded border border-slate-800 bg-slate-900/70 p-3 text-xs text-slate-300">
                      <p className="font-semibold text-slate-100">{selectedCombatAction.name}</p>
                      {describeCombatAction(selectedCombatAction) && (
                        <p className="mt-1 text-slate-400">{describeCombatAction(selectedCombatAction)}</p>
                      )}
                      {selectedCombatAction.description && (
                        <p className="mt-2 text-slate-500">{selectedCombatAction.description}</p>
                      )}
                    </div>
                  )}

                  {selectedCombatAction?.kind !== "utility" && (
                    <select
                      className="w-full rounded bg-slate-900 p-2 text-white border border-slate-700"
                      value={targetId}
                      onChange={(e) => setTargetId(e.target.value)}
                    >
                      <option value="">Select Target...</option>
                      {availableTargets.map((participant) => (
                        <option key={participant.id} value={participant.ref_id}>
                          {participant.display_name}
                          {participant.id === currentParticipant.id ? " (self)" : ""}
                          {" "}
                          [{participant.status}]
                        </option>
                      ))}
                    </select>
                  )}

                  <button
                    disabled={loading || !selectedCombatActionId || (selectedCombatAction?.kind !== "utility" && !targetId)}
                    onClick={handleEntityAction}
                    className="w-full rounded bg-rose-600 px-4 py-3 font-bold text-white hover:bg-rose-500 disabled:opacity-50"
                  >
                    {selectedCombatAction?.kind === "weapon_attack" || selectedCombatAction?.kind === "spell_attack"
                      ? "Abrir rolagem da acao"
                      : "Execute Structured Action"}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {entityActionDialogOpen &&
      currentParticipant &&
      selectedCombatAction &&
      selectedTarget &&
      (selectedCombatAction.kind === "weapon_attack" || selectedCombatAction.kind === "spell_attack") ? (
        <GmEntityActionRollDialog
          actorParticipantId={currentParticipant.id}
          actionDescription={describeCombatAction(selectedCombatAction)}
          actionId={selectedCombatAction.id}
          actionKind={selectedCombatAction.kind}
          actionName={selectedCombatAction.name}
          sessionId={sessionId}
          target={selectedTarget}
          onClose={() => setEntityActionDialogOpen(false)}
          onResolved={handleEntityActionResolved}
        />
      ) : null}
    </div>
  );
};
