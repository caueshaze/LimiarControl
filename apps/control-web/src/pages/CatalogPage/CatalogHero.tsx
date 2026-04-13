import type { CampaignSystemType } from "../../entities/campaign";
import { useLocale } from "../../shared/hooks/useLocale";
import { BackButton } from "../../shared/ui";

type CatalogHeroProps = {
  campaignName: string;
  filteredCount: number;
  linkedCount: number;
  systemType: CampaignSystemType | null;
  totalCount: number;
  customCount: number;
  backTo: string;
};

export const CatalogHero = ({
  campaignName,
  filteredCount,
  linkedCount,
  systemType,
  totalCount,
  customCount,
  backTo,
}: CatalogHeroProps) => {
  const { t } = useLocale();

  const stats = [
    { label: t("catalog.stats.total"), value: totalCount },
    { label: t("catalog.stats.linked"), value: linkedCount },
    { label: t("catalog.stats.custom"), value: customCount },
    { label: t("catalog.stats.filtered"), value: filteredCount },
  ];

  return (
    <section className="relative overflow-hidden rounded-[34px] border border-white/8 bg-[#070712] px-6 py-8 shadow-[0_30px_90px_rgba(0,0,0,0.28)] sm:px-8">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(167,139,250,0.18),transparent_28%),radial-gradient(circle_at_80%_15%,rgba(34,211,238,0.12),transparent_24%),linear-gradient(180deg,rgba(15,23,42,0.88),rgba(2,6,23,0.96))]" />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.18)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.18)_1px,transparent_1px)] bg-size-[48px_48px] opacity-[0.08]" />
      </div>

      <div className="relative grid gap-8 xl:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)]">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-limiar-100/80">
            {t("catalog.heroEyebrow")}
          </p>
          <h1 className="mt-4 max-w-3xl font-display text-4xl font-bold leading-tight text-white sm:text-5xl">
            {t("catalog.subtitle")}
          </h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300 sm:text-base">
            {t("catalog.heroDescription")}
          </p>

          <div className="mt-6 flex flex-wrap gap-3">
            <div className="rounded-full border border-white/10 bg-white/6 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-white">
              {campaignName}
            </div>
            {systemType && (
              <div className="rounded-full border border-sky-300/15 bg-sky-400/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-sky-100">
                {systemType}
              </div>
            )}
            <BackButton
              fallbackTo={backTo}
              label={`← ${t("campaignHome.back")}`}
              className="inline-flex items-center rounded-full border border-white/10 bg-white/4 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-200 transition hover:border-white/20 hover:bg-white/8"
            />
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
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
