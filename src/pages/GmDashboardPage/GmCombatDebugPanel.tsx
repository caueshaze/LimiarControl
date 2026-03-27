import { useEffect, useState } from "react";
import {
  combatRepo,
  type ActiveEffect,
  type ActiveEffectConditionType,
  type ActiveEffectDurationType,
  type ActiveEffectKind,
  type CombatApplyEffectRequest,
  type CombatEntityActionResult,
  type CombatState,
  type StandardActionType,
} from "../../shared/api/combatRepo";
import { subscribe } from "../../shared/realtime/centrifugoClient";
import type { PartyMemberSummary } from "../../shared/api/partiesRepo";
import type { SessionEntity } from "../../entities/session-entity";
import { describeCombatAction } from "../../entities/campaign-entity/describeCombatAction";
import { sessionEntitiesRepo } from "../../shared/api/sessionEntitiesRepo";
import { RollResultCard } from "../../features/rolls/components/RollResultCard";
import { formatDamageDiceExpression } from "../../shared/utils/diceExpression";
import { GmEntityActionRollDialog } from "./GmEntityActionRollDialog";

const EFFECT_KINDS: { value: ActiveEffectKind; label: string }[] = [
  { value: "condition", label: "Condition" },
  { value: "temp_ac_bonus", label: "Temp AC Bonus" },
  { value: "attack_bonus", label: "Attack Bonus" },
  { value: "damage_bonus", label: "Damage Bonus" },
  { value: "advantage_on_attacks", label: "Advantage on Attacks" },
  { value: "disadvantage_on_attacks", label: "Disadvantage on Attacks" },
];

const CONDITION_TYPES: { value: ActiveEffectConditionType; label: string }[] = [
  { value: "prone", label: "Prone" },
  { value: "poisoned", label: "Poisoned" },
  { value: "restrained", label: "Restrained" },
  { value: "blinded", label: "Blinded" },
  { value: "frightened", label: "Frightened" },
];

const DURATION_TYPES: { value: ActiveEffectDurationType; label: string }[] = [
  { value: "manual", label: "Manual (remove manually)" },
  { value: "rounds", label: "Rounds" },
  { value: "until_turn_start", label: "Until Turn Start" },
  { value: "until_turn_end", label: "Until Turn End" },
];

const NUMERIC_KINDS = new Set<ActiveEffectKind>(["temp_ac_bonus", "attack_bonus", "damage_bonus"]);

const STANDARD_ACTIONS: { value: StandardActionType; label: string }[] = [
  { value: "dodge", label: "Dodge" },
  { value: "help", label: "Help" },
  { value: "hide", label: "Hide" },
  { value: "use_object", label: "Use Object" },
  { value: "dash", label: "Dash" },
  { value: "disengage", label: "Disengage" },
];

const GmStandardActionControls = ({
  loading,
  participants,
  currentParticipantId,
  sessionId,
  setLoading,
}: {
  loading: boolean;
  participants: CombatState["participants"];
  currentParticipantId: string | null;
  sessionId: string;
  setLoading: (v: boolean) => void;
}) => {
  const [open, setOpen] = useState(false);
  const [action, setAction] = useState<StandardActionType>("dodge");
  const [targetId, setTargetId] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const needsTarget = action === "help";
  const needsDescription = action === "use_object";

  const otherParticipants = participants.filter((p) => p.id !== currentParticipantId);

  const handleSubmit = async () => {
    if (!currentParticipantId) return;
    try {
      setSubmitting(true);
      setLoading(true);
      await combatRepo.standardAction(sessionId, {
        action,
        actor_participant_id: currentParticipantId,
        target_participant_id: needsTarget && targetId ? targetId : undefined,
        description: needsDescription && description ? description : undefined,
        roll_source: "system",
      });
      setOpen(false);
      setDescription("");
    } catch {} finally {
      setSubmitting(false);
      setLoading(false);
    }
  };

  if (!open) {
    return (
      <button
        disabled={loading || !currentParticipantId}
        onClick={() => setOpen(true)}
        className="rounded border border-violet-500/50 bg-transparent px-3 py-2 text-xs font-bold text-violet-400 hover:bg-violet-500/10 disabled:opacity-50"
        title="Execute a standard action (Dodge, Help, Hide, etc.)"
      >
        Standard Action
      </button>
    );
  }

  return (
    <div className="col-span-2 flex flex-col gap-2 rounded border border-violet-500/30 bg-violet-950/20 p-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold text-violet-300">Standard Action (GM)</span>
        <button onClick={() => setOpen(false)} className="text-xs text-slate-400 hover:text-slate-200">✕</button>
      </div>
      <select
        value={action}
        onChange={(e) => setAction(e.target.value as StandardActionType)}
        className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-white"
      >
        {STANDARD_ACTIONS.map((a) => (
          <option key={a.value} value={a.value}>{a.label}</option>
        ))}
      </select>
      {needsTarget && (
        <select
          value={targetId}
          onChange={(e) => setTargetId(e.target.value)}
          className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-white"
        >
          <option value="">— select target —</option>
          {otherParticipants.map((p) => (
            <option key={p.id} value={p.id}>{p.display_name}</option>
          ))}
        </select>
      )}
      {needsDescription && (
        <input
          type="text"
          placeholder="Description (e.g. drink healing potion)"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-white placeholder-slate-500"
        />
      )}
      <button
        disabled={submitting || (needsTarget && !targetId)}
        onClick={handleSubmit}
        className="rounded bg-violet-600 px-3 py-1 text-xs font-bold text-white hover:bg-violet-500 disabled:opacity-50"
      >
        Execute
      </button>
    </div>
  );
};

const ApplyEffectForm = ({
  participants,
  sessionId,
}: {
  participants: CombatState["participants"];
  sessionId: string;
}) => {
  const [open, setOpen] = useState(false);
  const [targetId, setTargetId] = useState("");
  const [kind, setKind] = useState<ActiveEffectKind>("condition");
  const [conditionType, setConditionType] = useState<ActiveEffectConditionType>("prone");
  const [numericValue, setNumericValue] = useState("2");
  const [durationType, setDurationType] = useState<ActiveEffectDurationType>("manual");
  const [remainingRounds, setRemainingRounds] = useState("1");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!targetId) return;
    setSubmitting(true);
    setFormError(null);
    try {
      const payload: CombatApplyEffectRequest = {
        target_participant_id: targetId,
        kind,
        duration_type: durationType,
      };
      if (kind === "condition") {
        payload.condition_type = conditionType;
      }
      if (NUMERIC_KINDS.has(kind)) {
        payload.numeric_value = parseInt(numericValue, 10) || 0;
      }
      if (durationType === "rounds") {
        payload.remaining_rounds = parseInt(remainingRounds, 10) || 1;
      }
      await combatRepo.applyEffect(sessionId, payload);
    } catch (err: any) {
      setFormError(err?.data?.detail || err?.message || "Failed to apply effect");
    } finally {
      setSubmitting(false);
    }
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="w-full rounded border border-purple-500/30 bg-purple-500/10 px-3 py-2 text-xs text-purple-300 hover:bg-purple-500/20"
      >
        + Apply Effect
      </button>
    );
  }

  return (
    <div className="rounded border border-purple-500/30 bg-purple-950/20 p-3 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold text-purple-300 uppercase tracking-wider">Apply Effect</span>
        <button onClick={() => setOpen(false)} className="text-xs text-slate-400 hover:text-white">Close</button>
      </div>

      {formError && (
        <div className="rounded border border-rose-500 bg-rose-500/10 p-1.5 text-rose-200 text-[11px]">{formError}</div>
      )}

      <select
        className="w-full rounded border border-slate-700 bg-slate-900 p-1.5 text-xs text-white"
        value={targetId}
        onChange={(e) => setTargetId(e.target.value)}
      >
        <option value="">Select Target...</option>
        {participants
          .filter((p) => p.status !== "dead" && p.status !== "defeated")
          .map((p) => (
            <option key={p.id} value={p.id}>
              {p.display_name} [{p.status}]
            </option>
          ))}
      </select>

      <select
        className="w-full rounded border border-slate-700 bg-slate-900 p-1.5 text-xs text-white"
        value={kind}
        onChange={(e) => setKind(e.target.value as ActiveEffectKind)}
      >
        {EFFECT_KINDS.map((k) => (
          <option key={k.value} value={k.value}>{k.label}</option>
        ))}
      </select>

      {kind === "condition" && (
        <select
          className="w-full rounded border border-slate-700 bg-slate-900 p-1.5 text-xs text-white"
          value={conditionType}
          onChange={(e) => setConditionType(e.target.value as ActiveEffectConditionType)}
        >
          {CONDITION_TYPES.map((c) => (
            <option key={c.value} value={c.value}>{c.label}</option>
          ))}
        </select>
      )}

      {NUMERIC_KINDS.has(kind) && (
        <input
          type="number"
          className="w-full rounded border border-slate-700 bg-slate-900 p-1.5 text-xs text-white"
          placeholder="Value (e.g. 2, -1)"
          value={numericValue}
          onChange={(e) => setNumericValue(e.target.value)}
        />
      )}

      <select
        className="w-full rounded border border-slate-700 bg-slate-900 p-1.5 text-xs text-white"
        value={durationType}
        onChange={(e) => setDurationType(e.target.value as ActiveEffectDurationType)}
      >
        {DURATION_TYPES.map((d) => (
          <option key={d.value} value={d.value}>{d.label}</option>
        ))}
      </select>

      {durationType === "rounds" && (
        <input
          type="number"
          min={1}
          className="w-full rounded border border-slate-700 bg-slate-900 p-1.5 text-xs text-white"
          placeholder="Rounds"
          value={remainingRounds}
          onChange={(e) => setRemainingRounds(e.target.value)}
        />
      )}

      <button
        disabled={submitting || !targetId}
        onClick={handleSubmit}
        className="w-full rounded bg-purple-600 px-3 py-2 text-xs font-bold text-white hover:bg-purple-500 disabled:opacity-50"
      >
        Apply
      </button>
    </div>
  );
};

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
                      {(p.active_effects ?? []).length > 0 && (
                        <span className="ml-2 inline-flex gap-1 flex-wrap align-middle">
                          {(p.active_effects ?? []).map((eff: ActiveEffect) => (
                            <span
                              key={eff.id}
                              className="inline-flex items-center gap-0.5 rounded bg-purple-600/30 border border-purple-500/40 px-1.5 py-0.5 text-[9px] text-purple-200 font-normal"
                              title={`${eff.kind}${eff.condition_type ? `: ${eff.condition_type}` : ""}${eff.numeric_value != null ? ` (${eff.numeric_value > 0 ? "+" : ""}${eff.numeric_value})` : ""}${eff.remaining_rounds ? ` ${eff.remaining_rounds}rd` : ""} [${eff.duration_type}]`}
                            >
                              {eff.kind === "condition" ? eff.condition_type : eff.kind.replace(/_/g, " ")}
                              {eff.numeric_value != null && (
                                <span className="text-purple-400">
                                  {eff.numeric_value > 0 ? "+" : ""}{eff.numeric_value}
                                </span>
                              )}
                              {eff.remaining_rounds != null && (
                                <span className="text-purple-400">{eff.remaining_rounds}rd</span>
                              )}
                              <button
                                className="ml-0.5 text-rose-400 hover:text-rose-300 font-bold"
                                onClick={async (e) => {
                                  e.stopPropagation();
                                  try {
                                    await combatRepo.removeEffect(sessionId, {
                                      target_participant_id: p.id,
                                      effect_id: eff.id,
                                    });
                                  } catch {}
                                }}
                              >
                                ×
                              </button>
                            </span>
                          ))}
                        </span>
                      )}
                      {state.current_turn_index === idx && state.phase === 'active' && p.turn_resources && (
                        <span className="ml-1 text-[9px] font-mono text-slate-400">
                          [A:{p.turn_resources.action_used ? "×" : "✓"}
                          {" "}B:{p.turn_resources.bonus_action_used ? "×" : "✓"}
                          {" "}R:{p.turn_resources.reaction_used ? "×" : "✓"}]
                        </span>
                      )}
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
                <>
                  <button
                      disabled={loading}
                      onClick={handleNextTurn}
                      className="flex-1 rounded bg-sky-600 px-4 py-2 font-bold text-white hover:bg-sky-500 disabled:opacity-50"
                    >
                      Next Turn (Bypass)
                  </button>
                  <button
                      disabled={loading}
                      onClick={async () => {
                        const active = state.participants[state.current_turn_index];
                        if (!active) return;
                        try {
                          setLoading(true);
                          await combatRepo.consumeReaction(sessionId, { participant_id: active.id });
                        } catch {} finally { setLoading(false); }
                      }}
                      className="rounded border border-orange-500/50 bg-transparent px-3 py-2 text-xs font-bold text-orange-400 hover:bg-orange-500/10 disabled:opacity-50"
                      title="Mark the active participant's reaction as used"
                    >
                      Mark Reaction
                  </button>
                  <GmStandardActionControls
                    loading={loading}
                    participants={state.participants}
                    currentParticipantId={state.participants[state.current_turn_index]?.id ?? null}
                    sessionId={sessionId}
                    setLoading={setLoading}
                  />
                </>
            )}
          </div>

          {state.phase === "active" && (
            <ApplyEffectForm
              participants={state.participants}
              sessionId={sessionId}
            />
          )}

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
