import { Link } from "react-router-dom";
import { useLocale } from "../../shared/hooks/useLocale";

type NpcsHeroProps = {
  campaignName: string;
  totalCount: number;
  visibleCount: number;
  backTo: string;
  eyebrow: string;
  title: string;
  description: string;
};

export const NpcsHero = ({
  campaignName,
  totalCount,
  visibleCount,
  backTo,
  eyebrow,
  title,
  description,
}: NpcsHeroProps) => {
  const { t } = useLocale();

  const stats = [
    { label: t("npc.stats.total"), value: totalCount },
    { label: t("npc.stats.visible"), value: visibleCount },
  ];

  return (
    <section className="relative overflow-hidden rounded-[34px] border border-white/8 bg-[#070712] px-6 py-8 shadow-[0_30px_90px_rgba(0,0,0,0.28)] sm:px-8">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.16),transparent_28%),radial-gradient(circle_at_82%_18%,rgba(34,211,238,0.12),transparent_24%),linear-gradient(180deg,rgba(15,23,42,0.88),rgba(2,6,23,0.96))]" />
        <div className="absolute inset-0 opacity-[0.08] [background-image:linear-gradient(rgba(255,255,255,0.18)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.18)_1px,transparent_1px)] [background-size:48px_48px]" />
      </div>
      <div className="pointer-events-none absolute -left-20 top-8 h-60 w-60 rounded-full bg-emerald-500/18 blur-[120px] motion-safe:animate-[landing-drift_16s_ease-in-out_infinite]" />
      <div className="pointer-events-none absolute right-0 top-0 h-72 w-72 rounded-full bg-sky-400/12 blur-[130px] motion-safe:animate-[landing-float_14s_ease-in-out_infinite]" />

      <div className="relative grid gap-8 xl:grid-cols-[minmax(0,1.08fr)_minmax(320px,0.92fr)]">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-emerald-100/80">
            {eyebrow}
          </p>
          <h1 className="mt-4 max-w-3xl font-display text-4xl font-bold leading-tight text-white sm:text-5xl">
            {title}
          </h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300 sm:text-base">
            {description}
          </p>

          <div className="mt-6 flex flex-wrap gap-3">
            <span className="rounded-full border border-white/10 bg-white/[0.05] px-4 py-2 text-xs font-semibold text-white">
              {campaignName}
            </span>
            <Link
              to={backTo}
              className="rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-200 transition hover:border-white/20 hover:bg-white/[0.08]"
            >
              {t("npc.backCampaign")}
            </Link>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          {stats.map((stat) => (
            <div
              key={stat.label}
              className="rounded-[28px] border border-white/8 bg-white/[0.05] p-5 backdrop-blur-xl"
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
