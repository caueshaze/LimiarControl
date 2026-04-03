import { useLocale } from "../../shared/hooks/useLocale";

type GmWorkspaceHeroProps = {
  displayName: string;
  campaignsCount: number;
  partiesCount: number;
  activeCampaignName: string | null;
  onOpenAdmin?: () => void;
};

export const GmWorkspaceHero = ({
  displayName,
  campaignsCount,
  partiesCount,
  activeCampaignName,
  onOpenAdmin,
}: GmWorkspaceHeroProps) => {
  const { t } = useLocale();

  const stats = [
    { label: t("gm.home.heroCampaigns"), value: campaignsCount.toString() },
    { label: t("gm.home.heroParties"), value: partiesCount.toString() },
    {
      label: t("gm.home.heroFocus"),
      value: activeCampaignName ?? t("gm.home.heroNoCampaign"),
      accent: Boolean(activeCampaignName),
    },
  ];

  return (
    <section className="relative overflow-hidden rounded-[34px] border border-white/8 bg-[#070712] px-6 py-8 shadow-[0_30px_90px_rgba(0,0,0,0.28)] sm:px-8">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(167,139,250,0.18),transparent_28%),radial-gradient(circle_at_82%_18%,rgba(34,211,238,0.12),transparent_24%),linear-gradient(180deg,rgba(15,23,42,0.88),rgba(2,6,23,0.96))]" />
        <div className="absolute inset-0 opacity-[0.08] bg-[linear-gradient(rgba(255,255,255,0.18)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.18)_1px,transparent_1px)] bg-size-[48px_48px]" />
      </div>
      <div className="pointer-events-none absolute -left-20 top-8 h-60 w-60 rounded-full bg-limiar-500/18 blur-[120px] motion-safe:animate-[landing-drift_16s_ease-in-out_infinite]" />
      <div className="pointer-events-none absolute right-0 top-0 h-72 w-72 rounded-full bg-sky-400/12 blur-[130px] motion-safe:animate-[landing-float_14s_ease-in-out_infinite]" />

      <div className="relative grid gap-8 xl:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)]">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-limiar-100/80">
            {t("gm.home.heroEyebrow")}
          </p>
          <h1 className="mt-4 max-w-3xl font-display text-4xl font-bold leading-tight text-white sm:text-5xl">
            {t("home.gm.welcome")} {displayName}
          </h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300 sm:text-base">
            {t("gm.home.heroDescription")}
          </p>
          {onOpenAdmin && (
            <div className="mt-6">
              <button
                type="button"
                onClick={onOpenAdmin}
                className="rounded-full border border-amber-400/25 bg-amber-400/10 px-5 py-3 text-xs font-bold uppercase tracking-[0.22em] text-amber-100 transition hover:bg-amber-400/18"
              >
                {t("admin.menuLabel")}
              </button>
            </div>
          )}
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
              <p
                className={`mt-4 font-display text-3xl font-bold ${
                  stat.accent ? "text-white" : "text-slate-200"
                }`}
              >
                {stat.value}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
