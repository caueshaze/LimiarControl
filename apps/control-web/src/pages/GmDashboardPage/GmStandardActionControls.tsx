import { useState } from "react";
import { combatRepo, type CombatState, type StandardActionType } from "../../shared/api/combatRepo";
import { STANDARD_ACTIONS } from "./gmCombatDebug.types";

export const GmStandardActionControls = ({
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
