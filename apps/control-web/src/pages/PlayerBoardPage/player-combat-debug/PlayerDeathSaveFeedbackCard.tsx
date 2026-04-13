import type { DeathSaveFeedback } from "./types";

type Props = {
  feedback: DeathSaveFeedback;
};

export const PlayerDeathSaveFeedbackCard = ({ feedback }: Props) => {
  const toneClass =
    feedback.status === "active"
      ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-100"
      : feedback.status === "stable"
        ? "border-sky-500/40 bg-sky-500/10 text-sky-100"
        : feedback.status === "dead"
          ? "border-rose-600/50 bg-rose-950/60 text-rose-100"
          : "border-amber-500/40 bg-amber-500/10 text-amber-100";

  return (
    <div className={`mt-4 rounded border p-4 ${toneClass}`}>
      <div className="flex items-center justify-between gap-3">
        <h4 className="text-sm font-bold uppercase tracking-widest">Death Save Result</h4>
        <span className="rounded-full border border-white/15 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em]">
          {feedback.roll != null ? `Roll ${feedback.roll}` : "Auto Update"}
        </span>
      </div>
      <p className="mt-3 text-sm">{feedback.message ?? ""}</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="rounded border border-white/10 bg-black/10 px-3 py-2">
          <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-300">
            Successes
          </p>
          <p className="mt-2 text-lg font-semibold">
            {feedback.death_saves?.successes ?? 0}/3
          </p>
        </div>
        <div className="rounded border border-white/10 bg-black/10 px-3 py-2">
          <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-300">
            Failures
          </p>
          <p className="mt-2 text-lg font-semibold">
            {feedback.death_saves?.failures ?? 0}/3
          </p>
        </div>
      </div>
    </div>
  );
};
