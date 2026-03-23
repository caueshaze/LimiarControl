import { formatMod } from "../../../features/character-sheet/utils/calculations";
import { useLocale } from "../../../shared/hooks/useLocale";
import type { PendingRoll, PlayerBoardStatusSummary } from "../playerBoard.types";

type StatCardProps = {
  accent?: string;
  helper?: string | null;
  label: string;
  value: string;
};

export const StatCard = ({
  accent = "text-white",
  helper = null,
  label,
  value,
}: StatCardProps) => (
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

export const ProgressCard = ({ label, percent, toneClass, value }: ProgressCardProps) => (
  <div className="rounded-[24px] border border-white/8 bg-white/[0.04] px-4 py-4">
    <div className="flex items-center justify-between gap-3">
      <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-500">{label}</p>
      <span className="text-sm font-semibold text-white">{value}</span>
    </div>
    <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-800">
      <div
        className={`h-full rounded-full transition-[width] ${toneClass}`}
        style={{ width: `${Math.max(0, Math.min(percent, 100))}%` }}
      />
    </div>
  </div>
);

export const DeathSaveCard = ({
  combatActive,
  playerStatus,
}: {
  combatActive: boolean;
  playerStatus: PlayerBoardStatusSummary;
}) => {
  const hasDeathSaveState =
    combatActive &&
    (playerStatus.currentHp <= 0 ||
      playerStatus.deathSaveSuccesses > 0 ||
      playerStatus.deathSaveFailures > 0);

  if (!hasDeathSaveState) {
    return null;
  }

  const status =
    playerStatus.currentHp > 0
      ? "active"
      : playerStatus.deathSaveFailures >= 3
        ? "dead"
        : playerStatus.deathSaveSuccesses >= 3
          ? "stable"
          : "downed";

  const toneClass =
    status === "active"
      ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-100"
      : status === "stable"
        ? "border-sky-500/30 bg-sky-500/10 text-sky-100"
        : status === "dead"
          ? "border-rose-600/40 bg-rose-950/60 text-rose-100"
          : "border-rose-500/40 bg-rose-500/10 text-rose-100";

  const label =
    status === "active"
      ? "Back Up"
      : status === "stable"
        ? "Stable"
        : status === "dead"
          ? "Dead"
          : "Downed";

  const description =
    status === "active"
      ? `You are conscious again at ${playerStatus.currentHp}/${playerStatus.maxHp} HP.`
      : status === "stable"
        ? "You are stable at 0 HP and no longer rolling death saves."
        : status === "dead"
          ? "You reached 3 failed death saves."
          : "You are at 0 HP and waiting on death save resolution.";

  return (
    <div className={`mt-5 rounded-[24px] border px-4 py-4 ${toneClass}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-300">
            Death Save Status
          </p>
          <h3 className="mt-2 text-lg font-semibold">{label}</h3>
        </div>
        <span className="rounded-full border border-white/15 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em]">
          HP {playerStatus.currentHp}/{playerStatus.maxHp}
        </span>
      </div>

      <p className="mt-3 text-sm leading-7">{description}</p>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="rounded-2xl border border-white/10 bg-black/10 px-4 py-3">
          <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-300">
            Successes
          </p>
          <p className="mt-2 text-xl font-semibold">{playerStatus.deathSaveSuccesses}/3</p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-black/10 px-4 py-3">
          <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-300">
            Failures
          </p>
          <p className="mt-2 text-xl font-semibold">{playerStatus.deathSaveFailures}/3</p>
        </div>
      </div>
    </div>
  );
};

export const WeaponCard = ({
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
        <p className="mt-4 text-sm text-slate-400">{t("playerBoard.noCurrentWeaponHint")}</p>
      )}

      {(combatActive || pendingRoll) && (
        <p className="mt-4 text-xs text-slate-400">
          {combatActive ? t("playerBoard.combatOpenState") : t("playerBoard.rollRequest")}
        </p>
      )}
    </div>
  );
};

export const RestCard = ({
  onUseHitDie,
  playerStatus,
  restState,
  usingHitDie,
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
            {`${playerStatus.hitDiceRemaining}/${playerStatus.hitDiceTotal} ${
              playerStatus.hitDieType || "HD"
            }`}
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

export const getHpToneClass = (hpPercent: number) =>
  hpPercent > 50 ? "text-emerald-300" : hpPercent > 25 ? "text-amber-200" : "text-rose-300";

export const getHpBarToneClass = (hpPercent: number) =>
  hpPercent > 50
    ? "bg-emerald-500"
    : hpPercent > 25
      ? "bg-amber-500"
      : "bg-rose-500";
