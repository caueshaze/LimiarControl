import { formatMod } from "../../features/character-sheet/utils/calculations";
import { useLocale } from "../../shared/hooks/useLocale";
import type { PendingRoll, PlayerBoardStatusSummary } from "./playerBoard.types";

type Props = {
  combatActive: boolean;
  pendingRoll: PendingRoll | null;
  playerStatus: PlayerBoardStatusSummary | null;
  restState: "exploration" | "short_rest" | "long_rest";
  shopAvailable: boolean;
  shopOpen: boolean;
  usingHitDie: boolean;
  onUseHitDie: () => void;
  onOpenShop: () => void;
};

export const PlayerBoardStatusPanel = ({
  combatActive,
  pendingRoll,
  playerStatus,
  restState,
  shopAvailable,
  shopOpen,
  usingHitDie,
  onUseHitDie,
  onOpenShop,
}: Props) => {
  const { t } = useLocale();
  const showShopAction = shopAvailable || shopOpen;

  return (
    <section className="rounded-[32px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] p-6 shadow-[0_18px_60px_rgba(2,6,23,0.2)]">
      <div className="flex flex-col gap-5 border-b border-white/8 pb-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-2xl">
          <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-slate-400">
            {t("playerBoard.statusPanelTitle")}
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-white">{t("playerBoard.statusPanelHeading")}</h2>
          <p className="mt-3 text-sm leading-7 text-slate-300">
            {t("playerBoard.statusPanelDescription")}
          </p>
        </div>

        {showShopAction ? (
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={onOpenShop}
              className="rounded-full bg-cyan-500 px-5 py-3 text-xs font-bold uppercase tracking-[0.22em] text-slate-950 transition hover:bg-cyan-400"
            >
              {t("playerBoard.goShop")}
            </button>
          </div>
        ) : null}
      </div>

      {!playerStatus ? (
        <p className="mt-5 text-sm leading-7 text-slate-300">{t("playerBoard.waitingSheetState")}</p>
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

          <div className="mt-5 grid gap-3 xl:grid-cols-[minmax(0,0.68fr)_minmax(0,0.68fr)_minmax(0,1.64fr)]">
            <StatCard
              label={t("playerBoard.initiativeLabel")}
              value={formatMod(playerStatus.initiative)}
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

type StatCardProps = {
  accent?: string;
  helper?: string | null;
  label: string;
  value: string;
};

const StatCard = ({ accent = "text-white", helper = null, label, value }: StatCardProps) => (
  <div className="rounded-[24px] border border-white/8 bg-white/[0.04] px-4 py-4">
    <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-500">{label}</p>
    <p className={`mt-3 text-lg font-semibold ${accent}`}>{value}</p>
    {helper ? <p className="mt-2 text-xs text-slate-400">{helper}</p> : null}
  </div>
);

type ProgressCardProps = {
  label: string;
  percent: number;
  toneClass: string;
  value: string;
};

const ProgressCard = ({ label, percent, toneClass, value }: ProgressCardProps) => (
  <div className="rounded-[24px] border border-white/8 bg-white/[0.04] px-4 py-4">
    <div className="flex items-center justify-between gap-3">
      <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-500">{label}</p>
      <span className="text-sm font-semibold text-white">{value}</span>
    </div>
    <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-800">
      <div className={`h-full rounded-full transition-[width] ${toneClass}`} style={{ width: `${Math.max(0, Math.min(percent, 100))}%` }} />
    </div>
  </div>
);

const getHpToneClass = (hpPercent: number) =>
  hpPercent > 50 ? "text-emerald-300" : hpPercent > 25 ? "text-amber-200" : "text-rose-300";

const getHpBarToneClass = (hpPercent: number) =>
  hpPercent > 50
    ? "bg-emerald-500"
    : hpPercent > 25
      ? "bg-amber-500"
      : "bg-rose-500";

const WeaponCard = ({
  combatActive,
  pendingRoll,
  playerStatus,
}: {
  combatActive: boolean;
  pendingRoll: PendingRoll | null;
  playerStatus: PlayerBoardStatusSummary;
}) => {
  const { t } = useLocale();
  const weapon = playerStatus.currentWeapon;

  return (
    <div className="rounded-[24px] border border-white/8 bg-white/[0.04] px-4 py-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-500">
            {t("playerBoard.equippedWeaponLabel")}
          </p>
          <h3 className="mt-3 text-lg font-semibold text-white">
            {weapon?.name ?? t("playerBoard.noCurrentWeapon")}
          </h3>
        </div>
        {weapon && (
          <span
            className={`rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] ${
              weapon.proficient
                ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-300"
                : "border-rose-500/25 bg-rose-500/10 text-rose-200"
            }`}
          >
            {weapon.proficient
              ? t("playerBoard.weaponProficient")
              : t("playerBoard.weaponNotProficient")}
          </span>
        )}
      </div>

      {weapon ? (
        <div className="mt-4 space-y-2">
          <p className="text-base font-semibold text-amber-200">
            {formatMod(weapon.attackBonus)} {t("playerBoard.weaponToHitSuffix")}
          </p>
          <p className="text-sm text-slate-300">{weapon.damageLabel}</p>
        </div>
      ) : (
        <p className="mt-4 text-sm text-slate-400">
          {t("playerBoard.noCurrentWeaponHint")}
        </p>
      )}

      {(combatActive || pendingRoll) && (
        <p className="mt-4 text-xs text-slate-400">
          {combatActive ? t("playerBoard.combatOpenState") : t("playerBoard.rollRequest")}
        </p>
      )}
    </div>
  );
};

const RestCard = ({
  playerStatus,
  restState,
  usingHitDie,
  onUseHitDie,
}: {
  playerStatus: PlayerBoardStatusSummary;
  restState: "exploration" | "short_rest" | "long_rest";
  usingHitDie: boolean;
  onUseHitDie: () => void;
}) => {
  const { t } = useLocale();
  const restTone =
    restState === "short_rest"
      ? "border-amber-500/20 bg-amber-500/10 text-amber-200"
      : restState === "long_rest"
        ? "border-sky-500/20 bg-sky-500/10 text-sky-200"
        : "border-slate-700 bg-slate-900/40 text-slate-300";

  return (
    <div className={`mt-5 rounded-[24px] border px-4 py-4 ${restTone}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-400">
            {t("playerBoard.restStateTitle")}
          </p>
          <h3 className="mt-2 text-lg font-semibold">
            {restState === "short_rest"
              ? t("playerBoard.restStateShort")
              : restState === "long_rest"
                ? t("playerBoard.restStateLong")
                : t("playerBoard.restStateExploration")}
          </h3>
        </div>
        {restState === "short_rest" ? (
          <span className="rounded-full border border-amber-500/30 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-amber-200">
            {`${playerStatus.hitDiceRemaining}/${playerStatus.hitDiceTotal} ${playerStatus.hitDieType || "HD"}`}
          </span>
        ) : null}
      </div>

      <p className="mt-3 text-sm leading-7">
        {restState === "short_rest"
          ? t("playerBoard.shortRestDescription")
          : restState === "long_rest"
            ? t("playerBoard.longRestDescription")
            : t("playerBoard.explorationDescription")}
      </p>

      {restState === "short_rest" ? (
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <div className="text-xs text-slate-300">
            {t("playerBoard.hitDiceAvailable")
              .replace("{remaining}", String(playerStatus.hitDiceRemaining))
              .replace("{total}", String(playerStatus.hitDiceTotal))}
          </div>
          <button
            type="button"
            onClick={onUseHitDie}
            disabled={usingHitDie || playerStatus.hitDiceRemaining <= 0}
            className="rounded-full bg-amber-200 px-4 py-2 text-xs font-bold uppercase tracking-[0.22em] text-slate-950 transition hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {usingHitDie ? t("playerBoard.usingHitDie") : t("playerBoard.useHitDie")}
          </button>
        </div>
      ) : null}

      {restState === "short_rest" && playerStatus.hitDiceRemaining <= 0 ? (
        <p className="mt-3 text-xs text-rose-200">{t("playerBoard.noHitDiceRemaining")}</p>
      ) : null}
    </div>
  );
};
