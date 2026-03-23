import { useLocale } from "../../shared/hooks/useLocale";
import type { PendingRoll, PlayerBoardStatusSummary } from "./playerBoard.types";
import {
  DeathSaveCard,
  getHpBarToneClass,
  getHpToneClass,
  ProgressCard,
  RestCard,
  StatCard,
  WeaponCard,
} from "./player-board-status/PlayerBoardStatusCards";

type Props = {
  combatActive: boolean;
  pendingRoll: PendingRoll | null;
  playerStatus: PlayerBoardStatusSummary | null;
  restState: "exploration" | "short_rest" | "long_rest";
  usingHitDie: boolean;
  onUseHitDie: () => void;
};

export const PlayerBoardStatusPanel = ({
  combatActive,
  pendingRoll,
  playerStatus,
  restState,
  usingHitDie,
  onUseHitDie,
}: Props) => {
  const { t } = useLocale();

  return (
    <section className="rounded-[32px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] p-6 shadow-[0_18px_60px_rgba(2,6,23,0.2)]">
      <div className="border-b border-white/8 pb-5">
        <div className="max-w-2xl">
          <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-slate-400">
            {t("playerBoard.statusPanelTitle")}
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-white">
            {t("playerBoard.statusPanelHeading")}
          </h2>
          <p className="mt-3 text-sm leading-7 text-slate-300">
            {t("playerBoard.statusPanelDescription")}
          </p>
        </div>
      </div>

      {!playerStatus ? (
        <p className="mt-5 text-sm leading-7 text-slate-300">
          {t("playerBoard.waitingSheetState")}
        </p>
      ) : (
        <>
          <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard label={t("sheet.basicInfo.level")} value={String(playerStatus.level)} />
            <StatCard
              label={t("playerBoard.currentHpLabel")}
              value={`${playerStatus.currentHp}/${playerStatus.maxHp}`}
              accent={getHpToneClass(playerStatus.hpPercent)}
              helper={
                playerStatus.tempHp > 0
                  ? `${t("playerBoard.tempHpLabel")}: ${playerStatus.tempHp}`
                  : null
              }
            />
            <StatCard
              label={t("playerBoard.xpProgressLabel")}
              value={`${playerStatus.xpPercent}%`}
              accent="text-sky-300"
              helper={
                playerStatus.nextLevelThreshold === null
                  ? t("sheet.progress.maxLevel")
                  : `${playerStatus.experiencePoints}/${playerStatus.nextLevelThreshold} XP`
              }
            />
            <StatCard
              label={t("playerBoard.armorClassLabel")}
              value={String(playerStatus.ac)}
              accent="text-amber-200"
            />
          </div>

          <div className="mt-5 grid gap-3 lg:grid-cols-2">
            <ProgressCard
              label={t("playerBoard.hpTrackLabel")}
              value={`${playerStatus.currentHp}/${playerStatus.maxHp}`}
              percent={playerStatus.hpPercent}
              toneClass={getHpBarToneClass(playerStatus.hpPercent)}
            />
            <ProgressCard
              label={t("playerBoard.xpTrackLabel")}
              value={`${playerStatus.xpPercent}%`}
              percent={playerStatus.xpPercent}
              toneClass="bg-gradient-to-r from-sky-500 via-limiar-500 to-emerald-400"
            />
          </div>

          <DeathSaveCard combatActive={combatActive} playerStatus={playerStatus} />

          <div className="mt-5 grid gap-3 xl:grid-cols-[minmax(0,0.68fr)_minmax(0,0.68fr)_minmax(0,1.64fr)]">
            <StatCard
              label={t("playerBoard.initiativeLabel")}
              value={`${playerStatus.initiative >= 0 ? "+" : ""}${playerStatus.initiative}`}
            />
            <StatCard
              label={t("sheet.skills.passivePerception")}
              value={String(playerStatus.passivePerception)}
            />
            <WeaponCard
              combatActive={combatActive}
              pendingRoll={pendingRoll}
              playerStatus={playerStatus}
            />
          </div>

          <RestCard
            playerStatus={playerStatus}
            restState={restState}
            usingHitDie={usingHitDie}
            onUseHitDie={onUseHitDie}
          />
        </>
      )}
    </section>
  );
};
