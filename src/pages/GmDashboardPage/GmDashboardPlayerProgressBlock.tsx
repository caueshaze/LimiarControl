import type { CharacterSheet } from "../../features/character-sheet/model/characterSheet.types";
import { getCharacterProgressState } from "../../features/character-sheet/utils/progression";

type Props = {
  grantingXp: boolean;
  isApproving: boolean;
  isDenying: boolean;
  onApproveLevelUp: () => void;
  onDenyLevelUp: () => void;
  onGrantXp: () => void;
  setXpDraftByUserId: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  sheet?: CharacterSheet;
  userId: string;
  xpDraft: string;
};

export const GmDashboardPlayerProgressBlock = ({
  grantingXp,
  isApproving,
  isDenying,
  onApproveLevelUp,
  onDenyLevelUp,
  onGrantXp,
  setXpDraftByUserId,
  sheet,
  userId,
  xpDraft,
}: Props) => {
  if (!sheet) {
    return (
      <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950/60 p-3 text-xs text-slate-500">
        Loading character progress...
      </div>
    );
  }

  const { nextLevelThreshold, progressPercent, readyToLevelUp } = getCharacterProgressState(
    sheet.level,
    sheet.experiencePoints,
  );

  return (
    <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950/60 p-3">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0 flex-1">
          <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-500">
            Character Progress
          </p>
          <div className="mt-2 flex flex-wrap gap-4 text-xs text-slate-300">
            <span>Level {sheet.level}</span>
            <span>{sheet.experiencePoints.toLocaleString()} XP</span>
            <span>
              {nextLevelThreshold === null
                ? "Max level"
                : `Next threshold: ${nextLevelThreshold.toLocaleString()} XP`}
            </span>
          </div>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-800">
            <div
              className="h-full rounded-full bg-gradient-to-r from-sky-500 via-limiar-500 to-emerald-400 transition-[width]"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {sheet.pendingLevelUp ? (
            <>
              <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-amber-200">
                Awaiting approval
              </span>
              <button
                type="button"
                onClick={onApproveLevelUp}
                disabled={isApproving || isDenying}
                className="rounded-xl bg-emerald-500/80 px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-white hover:bg-emerald-500 disabled:opacity-60"
              >
                {isApproving ? "Approving..." : "Approve"}
              </button>
              <button
                type="button"
                onClick={onDenyLevelUp}
                disabled={isApproving || isDenying}
                className="rounded-xl bg-rose-500/80 px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-white hover:bg-rose-500 disabled:opacity-60"
              >
                {isDenying ? "Denying..." : "Deny"}
              </button>
            </>
          ) : readyToLevelUp ? (
            <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-emerald-200">
              Ready for level-up
            </span>
          ) : null}
          <div className="flex gap-2">
            <input
              type="number"
              min={1}
              value={xpDraft}
              onChange={(event) =>
                setXpDraftByUserId((current) => ({
                  ...current,
                  [userId]: event.target.value,
                }))
              }
              placeholder="300"
              className="w-24 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-limiar-500 focus:outline-none"
            />
            <button
              type="button"
              onClick={onGrantXp}
              disabled={grantingXp}
              className="rounded-xl bg-sky-500/80 px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-white hover:bg-sky-500 disabled:opacity-60"
            >
              {grantingXp ? "Sending..." : "Grant XP"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
