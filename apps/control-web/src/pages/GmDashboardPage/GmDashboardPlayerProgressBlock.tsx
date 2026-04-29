import type { CharacterSheet } from "../../features/character-sheet/model/characterSheet.types";
import { getCharacterProgressState } from "../../features/character-sheet/utils/progression";
import { useLocale } from "../../shared/hooks/useLocale";
import type { HpActionState } from "./gmDashboard.types";

type Props = {
  grantingHpAction: boolean;
  grantingXp: boolean;
  hpActionState: HpActionState | null;
  hpDraft: string;
  isApproving: boolean;
  isDamaging: boolean;
  isDenying: boolean;
  isHealing: boolean;
  onDamagePlayer: () => void;
  onApproveLevelUp: () => void;
  onDenyLevelUp: () => void;
  onGrantXp: () => void;
  onHealPlayer: () => void;
  setHpDraftByUserId: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  setXpDraftByUserId: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  sheet?: CharacterSheet;
  userId: string;
  xpDraft: string;
};

export const GmDashboardPlayerProgressBlock = ({
  grantingHpAction,
  grantingXp,
  hpActionState,
  hpDraft,
  isApproving,
  isDamaging,
  isDenying,
  isHealing,
  onDamagePlayer,
  onApproveLevelUp,
  onDenyLevelUp,
  onGrantXp,
  onHealPlayer,
  setHpDraftByUserId,
  setXpDraftByUserId,
  sheet,
  userId,
  xpDraft,
}: Props) => {
  const { t } = useLocale();

  if (!sheet) {
    return (
      <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950/60 p-3 text-xs text-slate-500">
        {t("gm.dashboard.loadingCharacterProgress")}
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
            {t("gm.dashboard.characterProgress")}
          </p>
          <div className="mt-2 flex flex-wrap gap-4 text-xs text-slate-300">
            <span>{t("gm.dashboard.level")} {sheet.level}</span>
            <span>{sheet.experiencePoints.toLocaleString()} XP</span>
            <span>
              {nextLevelThreshold === null
                ? t("gm.dashboard.maxLevel")
                : t("gm.dashboard.nextThreshold").replace("{xp}", nextLevelThreshold.toLocaleString())}
            </span>
          </div>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-800">
            <div
              className="h-full rounded-full bg-linear-to-r from-sky-500 via-limiar-500 to-emerald-400 transition-[width]"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2">
          {sheet.pendingLevelUp ? (
            <>
              <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-amber-200">
                {t("gm.dashboard.awaitingApproval")}
              </span>
              <button
                type="button"
                onClick={onApproveLevelUp}
                disabled={isApproving || isDenying}
                className="rounded-xl bg-emerald-500/80 px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-white hover:bg-emerald-500 disabled:opacity-60"
              >
                {isApproving ? t("gm.dashboard.approving") : t("gm.dashboard.approve")}
              </button>
              <button
                type="button"
                onClick={onDenyLevelUp}
                disabled={isApproving || isDenying}
                className="rounded-xl bg-rose-500/80 px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-white hover:bg-rose-500 disabled:opacity-60"
              >
                {isDenying ? t("gm.dashboard.denying") : t("gm.dashboard.deny")}
              </button>
            </>
          ) : readyToLevelUp ? (
            <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-emerald-200">
              {t("gm.dashboard.readyForLevelUp")}
            </span>
          ) : null}
          {hpActionState && (
            <span className="rounded-full border border-sky-500/30 bg-sky-500/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-sky-200">
              {hpActionState.action === "damage" ? t("gm.dashboard.applyingDamage") : t("gm.dashboard.applyingHealing")}
            </span>
          )}
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-500">{t("gm.dashboard.grantXp")}</p>
          <p className="mt-2 text-xs text-slate-400">
            {t("gm.dashboard.currentXp")}: <span className="font-semibold text-white">{sheet.experiencePoints.toLocaleString()}</span>
          </p>
          <div className="mt-3 flex gap-2">
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
              {grantingXp ? t("gm.dashboard.sending") : t("gm.dashboard.grantXp")}
            </button>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-500">{t("gm.dashboard.adjustHp")}</p>
          <p className="mt-2 text-xs text-slate-400">
            {t("gm.dashboard.currentHp")}: <span className="font-semibold text-white">{sheet.currentHP}/{sheet.maxHP}</span>
            {sheet.tempHP > 0 ? <span className="ml-2 text-cyan-300">{t("gm.dashboard.tempHpShort")} {sheet.tempHP}</span> : null}
          </p>
          <div className="mt-3 flex gap-2">
            <input
              type="number"
              min={1}
              value={hpDraft}
              onChange={(event) =>
                setHpDraftByUserId((current) => ({
                  ...current,
                  [userId]: event.target.value,
                }))
              }
              placeholder="5"
              className="w-24 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-limiar-500 focus:outline-none"
            />
            <button
              type="button"
              onClick={onDamagePlayer}
              disabled={grantingHpAction}
              className="rounded-xl bg-rose-500/80 px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-white hover:bg-rose-500 disabled:opacity-60"
            >
              {isDamaging ? t("gm.dashboard.applying") : t("gm.dashboard.damage")}
            </button>
            <button
              type="button"
              onClick={onHealPlayer}
              disabled={grantingHpAction}
              className="rounded-xl bg-emerald-500/80 px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-white hover:bg-emerald-500 disabled:opacity-60"
            >
              {isHealing ? t("gm.dashboard.applying") : t("gm.dashboard.heal")}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
