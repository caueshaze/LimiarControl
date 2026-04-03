import { SessionTimer } from "../../shared/ui/SessionTimer";
import { useLocale } from "../../shared/hooks/useLocale";

type SessionStatusTone = "active" | "lobby" | "idle";

type PlayerBoardHeroProps = {
  campaignTitle: string;
  sessionTitle?: string | null;
  description: string;
  sessionNumber?: number | null;
  startedAt?: string | null;
  sessionStatusLabel: string;
  sessionStatusTone: SessionStatusTone;
  shopOpen: boolean;
  combatActive: boolean;
  inventoryTotal: number;
  onBack: () => void;
  primaryActionLabel?: string | null;
  onPrimaryAction?: () => void;
  secondaryActionLabel?: string | null;
  onSecondaryAction?: () => void;
};

const getStatusToneClass = (tone: SessionStatusTone) => {
  if (tone === "active") {
    return "border-emerald-400/20 bg-emerald-400/10 text-emerald-100";
  }
  if (tone === "lobby") {
    return "border-amber-300/20 bg-amber-400/10 text-amber-100";
  }
  return "border-white/10 bg-white/4 text-slate-200";
};

export const PlayerBoardHero = ({
  campaignTitle,
  sessionTitle = null,
  description,
  sessionNumber = null,
  startedAt = null,
  sessionStatusLabel,
  sessionStatusTone,
  shopOpen,
  combatActive,
  inventoryTotal,
  onBack,
  primaryActionLabel = null,
  onPrimaryAction,
  secondaryActionLabel = null,
  onSecondaryAction,
}: PlayerBoardHeroProps) => {
  const { t } = useLocale();

  const title = sessionTitle || campaignTitle;
  const showCampaignLabel = Boolean(sessionTitle && sessionTitle !== campaignTitle);

  const stats = [
    {
      label: t("playerBoard.sessionNumber"),
      value: sessionNumber ? `#${sessionNumber}` : "--",
    },
    {
      label: t("playerBoard.sessionTimer"),
      value: startedAt ? <SessionTimer startedAt={startedAt} /> : sessionStatusLabel,
    },
    {
      label: t("playerBoard.shopStateLabel"),
      value: shopOpen ? t("playerBoard.shopOpenState") : t("playerBoard.shopClosedState"),
    },
    {
      label: t("playerBoard.inventoryStateLabel"),
      value: inventoryTotal.toString(),
    },
  ];

  return (
    <header className="relative overflow-hidden rounded-[34px] border border-white/10 bg-[linear-gradient(180deg,rgba(17,24,39,0.94),rgba(2,6,23,0.98))] px-6 py-6 shadow-[0_24px_80px_rgba(2,6,23,0.34)] sm:px-7">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(34,197,94,0.12),transparent_28%),radial-gradient(circle_at_80%_10%,rgba(99,102,241,0.12),transparent_22%),linear-gradient(90deg,rgba(255,255,255,0.04)_1px,transparent_1px),linear-gradient(rgba(255,255,255,0.04)_1px,transparent_1px)] bg-size-[auto,auto,42px_42px,42px_42px]" />

      <div className="relative space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <button
            type="button"
            onClick={onBack}
            className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/3 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-300 transition hover:border-white/16 hover:text-white"
          >
            <span aria-hidden>←</span>
            {t("campaignHome.back")}
          </button>

          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full border border-limiar-300/20 bg-limiar-300/10 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.25em] text-limiar-200">
              {t("playerBoard.subtitle")}
            </span>
            <span
              className={`rounded-full border px-3 py-1 text-[10px] font-bold uppercase tracking-[0.25em] ${getStatusToneClass(sessionStatusTone)}`}
            >
              {sessionStatusLabel}
            </span>
            {combatActive && (
              <span className="rounded-full border border-rose-300/20 bg-rose-400/10 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.25em] text-rose-100">
                {t("playerBoard.combatOpenState")}
              </span>
            )}
            {shopOpen && (
              <span className="rounded-full border border-cyan-300/20 bg-cyan-400/10 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.25em] text-cyan-100">
                {t("playerBoard.shopOpenState")}
              </span>
            )}
          </div>
        </div>

        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.08fr)_minmax(320px,0.92fr)]">
          <div className="space-y-4">
            <div className="space-y-2">
              <h1 className="max-w-3xl font-display text-4xl font-bold leading-tight text-white sm:text-5xl">
                {title}
              </h1>
              {showCampaignLabel && (
                <p className="text-sm font-semibold text-slate-300">{campaignTitle}</p>
              )}
              <p className="max-w-2xl text-sm leading-7 text-slate-300 sm:text-base">
                {description}
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              {onPrimaryAction && primaryActionLabel && (
                <button
                  type="button"
                  onClick={onPrimaryAction}
                  className="rounded-full bg-emerald-500 px-5 py-3 text-xs font-bold uppercase tracking-[0.22em] text-white transition hover:bg-emerald-400"
                >
                  {primaryActionLabel}
                </button>
              )}
              {onSecondaryAction && secondaryActionLabel && (
                <button
                  type="button"
                  onClick={onSecondaryAction}
                  className="rounded-full border border-white/10 bg-white/4 px-5 py-3 text-xs font-semibold uppercase tracking-[0.22em] text-slate-100 transition hover:border-white/20 hover:bg-white/8"
                >
                  {secondaryActionLabel}
                </button>
              )}
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            {stats.map((stat) => (
              <div
                key={stat.label}
                className="rounded-3xl border border-white/8 bg-white/5 px-4 py-4 backdrop-blur-xl"
              >
                <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-500">
                  {stat.label}
                </p>
                <p className="mt-3 text-lg font-semibold text-white">{stat.value}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </header>
  );
};
