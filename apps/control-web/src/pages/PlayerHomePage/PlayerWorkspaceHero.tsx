import { useLocale } from "../../shared/hooks/useLocale";

type SessionHeroStatus = "ACTIVE" | "LOBBY" | "IDLE";

type PlayerWorkspaceHeroProps = {
  displayName: string;
  partiesCount: number;
  invitesCount: number;
  liveCount: number;
  status: SessionHeroStatus;
  focusPartyName: string | null;
  onOpenCurrent?: () => void;
  onOpenInvites?: () => void;
  onOpenAdmin?: () => void;
};

export const PlayerWorkspaceHero = ({
  displayName,
  partiesCount,
  invitesCount,
  liveCount,
  status,
  focusPartyName,
  onOpenCurrent,
  onOpenInvites,
  onOpenAdmin,
}: PlayerWorkspaceHeroProps) => {
  const { t } = useLocale();

  const statusLabel =
    status === "ACTIVE"
      ? t("home.player.statusLive")
      : status === "LOBBY"
        ? t("home.player.statusLobby")
        : null;

  const descriptionKey =
    status === "ACTIVE"
      ? "home.player.heroDescriptionActive"
      : status === "LOBBY"
        ? "home.player.heroDescriptionLobby"
        : "home.player.heroDescriptionIdle";

  const stats = [
    { label: t("home.player.heroParties"), value: partiesCount.toString() },
    { label: t("home.player.heroInvites"), value: invitesCount.toString() },
    { label: t("home.player.heroLive"), value: liveCount.toString() },
  ];

  return (
    <section className="relative overflow-hidden rounded-[34px] border border-white/8 bg-[#070712] px-6 py-8 shadow-[0_30px_90px_rgba(0,0,0,0.28)] sm:px-8">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.18),transparent_28%),radial-gradient(circle_at_80%_15%,rgba(139,92,246,0.14),transparent_24%),linear-gradient(180deg,rgba(8,18,28,0.9),rgba(2,6,23,0.96))]" />
        <div className="absolute inset-0 opacity-[0.08] bg-[linear-gradient(rgba(255,255,255,0.18)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.18)_1px,transparent_1px)] bg-size-[48px_48px]" />
      </div>
      <div className="pointer-events-none absolute -left-24 top-6 h-64 w-64 rounded-full bg-emerald-500/14 blur-[120px] motion-safe:animate-[landing-drift_18s_ease-in-out_infinite]" />
      <div className="pointer-events-none absolute right-0 top-10 h-72 w-72 rounded-full bg-limiar-400/12 blur-[130px] motion-safe:animate-[landing-float_15s_ease-in-out_infinite]" />

      <div className="relative grid gap-8 xl:grid-cols-[minmax(0,1.08fr)_minmax(320px,0.92fr)]">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-emerald-100/80">
              {t("home.player.heroEyebrow")}
            </p>
            {statusLabel && (
              <span
                className={`rounded-full border px-3 py-1 text-[10px] font-bold uppercase tracking-[0.24em] ${
                  status === "ACTIVE"
                    ? "border-emerald-300/20 bg-emerald-400/10 text-emerald-100"
                    : "border-amber-300/20 bg-amber-400/10 text-amber-100"
                }`}
              >
                {statusLabel}
              </span>
            )}
          </div>

          <h1 className="mt-4 max-w-3xl font-display text-4xl font-bold leading-tight text-white sm:text-5xl">
            {t("home.player.welcome")} {displayName}
          </h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300 sm:text-base">
            {t(descriptionKey)}
          </p>

          {focusPartyName && (
            <div className="mt-5 inline-flex flex-wrap items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs font-semibold text-slate-100">
              <span className="uppercase tracking-[0.22em] text-slate-400">
                {t("home.player.yourParties")}
              </span>
              <span>{focusPartyName}</span>
            </div>
          )}

          <div className="mt-6 flex flex-wrap gap-3">
            {onOpenCurrent && (
              <button
                type="button"
                onClick={onOpenCurrent}
                className="rounded-full bg-emerald-500 px-5 py-3 text-xs font-bold uppercase tracking-[0.22em] text-white transition hover:bg-emerald-400"
              >
                {status === "LOBBY" ? t("home.player.joinLobbyAction") : t("home.player.enterSession")}
              </button>
            )}
            {onOpenInvites && invitesCount > 0 && (
              <button
                type="button"
                onClick={onOpenInvites}
                className="rounded-full border border-white/10 bg-white/4 px-5 py-3 text-xs font-semibold uppercase tracking-[0.22em] text-slate-100 transition hover:border-white/20 hover:bg-white/8"
              >
                {t("home.player.pendingInvites")}
              </button>
            )}
            {onOpenAdmin && (
              <button
                type="button"
                onClick={onOpenAdmin}
                className="rounded-full border border-amber-400/25 bg-amber-400/10 px-5 py-3 text-xs font-bold uppercase tracking-[0.22em] text-amber-100 transition hover:bg-amber-400/18"
              >
                {t("admin.menuLabel")}
              </button>
            )}
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
          {stats.map((stat) => (
            <div
              key={stat.label}
              className="rounded-[28px] border border-white/8 bg-white/5 p-5 backdrop-blur-xl"
            >
              <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                {stat.label}
              </p>
              <p className="mt-4 font-display text-3xl font-bold text-white">{stat.value}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
