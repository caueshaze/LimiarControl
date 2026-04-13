import { useLocale } from "../../../shared/hooks/useLocale";
import { input } from "./styles";
import { getCharacterProgressState } from "../utils/progression";

type Props = {
  level: number;
  experiencePoints: number;
  pendingLevelUp: boolean;
  canRequestLevelUp: boolean;
  requestingLevelUp: boolean;
  requestLevelUpError: string | null;
  onRequestLevelUp: () => void;
};

export const CharacterProgressPanel = ({
  level,
  experiencePoints,
  pendingLevelUp,
  canRequestLevelUp,
  requestingLevelUp,
  requestLevelUpError,
  onRequestLevelUp,
}: Props) => {
  const { t } = useLocale();
  const {
    currentLevelThreshold,
    nextLevelThreshold,
    progressPercent,
    readyToLevelUp,
    isMaxLevel,
  } = getCharacterProgressState(level, experiencePoints);
  const remainingXp =
    nextLevelThreshold === null ? 0 : Math.max(nextLevelThreshold - experiencePoints, 0);

  return (
    <div className="xl:col-span-12">
      <div className="rounded-[24px] border border-white/8 bg-slate-950/55 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0 flex-1">
            <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
              {t("sheet.progress.title")}
            </p>
            <div className="mt-3 grid gap-3 md:grid-cols-3">
              <div>
                <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">
                  {t("sheet.basicInfo.level")}
                </p>
                <p className="mt-1 text-sm font-semibold text-slate-100">{level}</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">
                  {t("sheet.basicInfo.xp")}
                </p>
                <p className="mt-1 text-sm font-semibold text-slate-100">
                  {experiencePoints.toLocaleString()}
                </p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">
                  {t("sheet.progress.nextLevel")}
                </p>
                <p className="mt-1 text-sm font-semibold text-slate-100">
                  {nextLevelThreshold === null
                    ? t("sheet.progress.maxLevel")
                    : `${nextLevelThreshold.toLocaleString()} XP`}
                </p>
              </div>
            </div>

            <div className="mt-4">
              <div className="flex items-center justify-between text-[11px] text-slate-400">
                <span>{currentLevelThreshold.toLocaleString()} XP</span>
                <span>
                  {nextLevelThreshold === null
                    ? t("sheet.progress.maxLevel")
                    : `${remainingXp.toLocaleString()} XP ${t("sheet.progress.remaining")}`}
                </span>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-800">
                <div
                  className="h-full rounded-full bg-linear-to-r from-limiar-500 via-sky-400 to-emerald-400 transition-[width]"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
            </div>
          </div>

          <div className="flex min-w-[14rem] flex-col gap-2">
            {pendingLevelUp ? (
              <span className={`${input} border-amber-500/30 bg-amber-500/10 text-center text-amber-200`}>
                {t("sheet.progress.awaitingApproval")}
              </span>
            ) : readyToLevelUp ? (
              <span className={`${input} border-emerald-500/30 bg-emerald-500/10 text-center text-emerald-200`}>
                {t("sheet.progress.ready")}
              </span>
            ) : null}

            {canRequestLevelUp && readyToLevelUp && !pendingLevelUp && !isMaxLevel ? (
              <button
                type="button"
                onClick={onRequestLevelUp}
                disabled={requestingLevelUp}
                className="rounded-[16px] border border-limiar-500/30 bg-limiar-500/15 px-4 py-3 text-sm font-semibold text-limiar-100 transition hover:bg-limiar-500/25 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {requestingLevelUp
                  ? t("sheet.progress.requesting")
                  : t("sheet.progress.request")}
              </button>
            ) : null}

            {requestLevelUpError ? (
              <p className="text-xs text-rose-300">{requestLevelUpError}</p>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
};
