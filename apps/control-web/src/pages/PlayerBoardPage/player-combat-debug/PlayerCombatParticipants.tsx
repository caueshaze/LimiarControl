import type { CombatState } from "../../../shared/api/combatRepo";

type Props = {
  state: CombatState;
  userId: string;
};

export const PlayerCombatParticipants = ({ state, userId }: Props) => (
  <div className="space-y-2">
    {state.participants.map((participant, index) => (
      <div
        key={participant.id}
        className={`flex items-center gap-2 rounded border px-3 py-2 ${
          state.current_turn_index === index && state.phase === "active"
            ? "border-amber-500 bg-amber-500/20 text-white"
            : "border-slate-700 bg-slate-800 text-slate-400"
        }`}
      >
        <span className="w-6 font-mono font-bold">{index + 1}.</span>
        <span className="flex-1 font-semibold">
          {participant.display_name} {participant.ref_id === userId && "(You)"}
          <em className="ml-2 text-[10px] font-bold uppercase tracking-widest text-rose-500">
            {participant.status !== "active" && participant.status}
          </em>
        </span>
        {state.phase === "active" && (
          <strong className="font-mono text-amber-400">{participant.initiative}</strong>
        )}
      </div>
    ))}
  </div>
);
