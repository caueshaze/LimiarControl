import { useState } from "react";
import {
  combatRepo,
  type ActiveEffectConditionType,
  type ActiveEffectDurationType,
  type ActiveEffectKind,
  type CombatApplyEffectRequest,
  type CombatState,
} from "../../shared/api/combatRepo";
import {
  CONDITION_TYPES,
  DURATION_TYPES,
  EFFECT_KINDS,
  NUMERIC_KINDS,
} from "./gmCombatDebug.types";

export const ApplyEffectForm = ({
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
