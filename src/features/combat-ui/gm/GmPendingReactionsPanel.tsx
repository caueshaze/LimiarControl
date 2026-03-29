import type { CombatParticipant } from "../../../shared/api/combatRepo";

type Props = {
  pendingReactionRequests: CombatParticipant[];
  submitting: boolean;
  onResolveReaction: (actorParticipantId: string, decision: "approve" | "deny") => void;
};

export const GmPendingReactionsPanel = ({
  pendingReactionRequests,
  submitting,
  onResolveReaction,
}: Props) => {
  if (pendingReactionRequests.length === 0) {
    return null;
  }

  return (
    <section className="rounded-4xl border border-amber-500/25 bg-amber-500/10 p-5 shadow-[0_18px_60px_rgba(2,6,23,0.2)]">
      <h3 className="text-sm font-bold uppercase tracking-widest text-amber-200">Reações Solicitadas</h3>
      <div className="mt-4 space-y-3">
        {pendingReactionRequests.map((reqP) => (
          <div key={reqP.id} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-slate-950/40 p-3">
            <span className="text-sm font-semibold text-slate-200">
              {reqP.display_name} deseja usar Reação
              {reqP.turn_resources?.reaction_used ? (
                <span className="ml-2 text-[10px] text-rose-400 uppercase">(Já gasta)</span>
              ) : null}
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={submitting}
                onClick={() => onResolveReaction(reqP.id, "approve")}
                className="rounded-full bg-emerald-500/20 border border-emerald-500/30 px-3 py-1.5 text-xs font-semibold uppercase text-emerald-300 hover:bg-emerald-500/30 disabled:opacity-50"
              >
                Aprovar
              </button>
              <button
                type="button"
                disabled={submitting}
                onClick={() => onResolveReaction(reqP.id, "deny")}
                className="rounded-full bg-rose-500/20 border border-rose-500/30 px-3 py-1.5 text-xs font-semibold uppercase text-rose-300 hover:bg-rose-500/30 disabled:opacity-50"
              >
                Recusar
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};
