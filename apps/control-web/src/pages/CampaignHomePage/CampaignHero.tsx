import { Link } from "react-router-dom";
import { useLocale } from "../../shared/hooks/useLocale";
import type { CampaignSystemType } from "../../entities/campaign";
import { getCampaignSystemLabel } from "../../entities/campaign";

type CampaignHeroProps = {
  campaignName: string | null;
  campaignSystem: CampaignSystemType | null;
  gmName: string | null;
  backFallbackTo: string;
};

export const CampaignHero = ({
  campaignName,
  campaignSystem,
  gmName,
  backFallbackTo,
}: CampaignHeroProps) => {
  const { t } = useLocale();

  const systemLabel = campaignSystem
    ? getCampaignSystemLabel(campaignSystem)
    : null;

  const stats = [
    {
      label: t("campaignHome.heroCampaign"),
      value: campaignName ?? t("campaignHome.none"),
      accent: Boolean(campaignName),
    },
    {
      label: t("campaignHome.heroSystem"),
      value: systemLabel ?? "—",
      accent: false,
    },
    {
      label: t("campaignHome.heroGm"),
      value: gmName ?? t("campaignHome.gmUnknown"),
      accent: Boolean(gmName),
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
          <Link
            to={backFallbackTo}
            className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/3 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-300 transition hover:border-white/16 hover:text-white"
          >
            <span aria-hidden>←</span> {t("campaignHome.back")}
          </Link>

          <p className="mt-5 text-[11px] font-semibold uppercase tracking-[0.32em] text-limiar-100/80">
            {t("campaignHome.title")}
          </p>
          <h1 className="mt-4 max-w-3xl font-display text-4xl font-bold leading-tight text-white sm:text-5xl">
            {campaignName ?? t("campaignHome.none")}
          </h1>

          <div className="mt-4 flex flex-wrap items-center gap-2">
            {systemLabel && (
              <span className="rounded-full border border-sky-300/15 bg-sky-400/10 px-4 py-2 text-xs font-semibold text-sky-100">
                {systemLabel}
              </span>
            )}
            {gmName && (
              <span className="rounded-full border border-white/10 bg-black/20 px-4 py-2 text-xs font-semibold text-slate-300">
                {t("campaignHome.gmLabel")} {gmName}
              </span>
            )}
          </div>

          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300 sm:text-base">
            {t("campaignHome.description")}
          </p>
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
                className={`mt-4 truncate font-display text-2xl font-bold ${
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
