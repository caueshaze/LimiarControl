import { combatRepo, type ActiveEffect, type CombatState } from "../../shared/api/combatRepo";

export const GmCombatParticipantList = ({
  state,
  initiatives,
  setInitiatives,
  sessionId,
}: {
  state: CombatState;
  initiatives: Record<string, string>;
  setInitiatives: (v: Record<string, string>) => void;
  sessionId: string;
}) => {
  return (
    <div className="space-y-2">
      {state.participants.map((p: any, idx: number) => (
        <div
          key={p.id}
          className={`flex items-center gap-2 rounded border px-3 py-2 ${
            state.current_turn_index === idx && state.phase === "active"
              ? "border-amber-500 bg-amber-500/20"
              : "border-slate-700 bg-slate-800"
          }`}
        >
          <span className="w-6 font-mono text-slate-500">{idx + 1}.</span>
          <span className="flex-1 font-semibold">
            {p.display_name} {p.kind === "session_entity" ? "(NPC)" : "(Player)"}
            <em className="ml-2 text-[10px] uppercase font-bold text-rose-500">
              {p.status !== "active" && p.status}
            </em>
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
            {state.current_turn_index === idx && state.phase === "active" && p.turn_resources && (
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
  );
};
