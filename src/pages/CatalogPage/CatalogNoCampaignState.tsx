import { Link } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { useLocale } from "../../shared/hooks/useLocale";

export const CatalogNoCampaignState = () => {
  const { t } = useLocale();

  return (
    <div className="relative overflow-hidden rounded-[34px] border border-white/8 bg-[#070712] px-6 py-8 shadow-[0_30px_90px_rgba(0,0,0,0.28)] sm:px-8">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(167,139,250,0.18),transparent_28%),radial-gradient(circle_at_80%_15%,rgba(34,211,238,0.12),transparent_24%),linear-gradient(180deg,rgba(15,23,42,0.88),rgba(2,6,23,0.96))]" />
      <div className="relative max-w-2xl">
        <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-limiar-100/80">
          {t("catalog.title")}
        </p>
        <h1 className="mt-4 font-display text-4xl font-bold text-white">
          {t("catalog.noCampaignTitle")}
        </h1>
        <p className="mt-4 text-sm leading-7 text-slate-300">{t("catalog.noCampaign")}</p>
        <Link
          to={routes.home}
          className="mt-6 inline-flex rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-100 transition hover:border-white/20 hover:bg-white/[0.08]"
        >
          {t("catalog.goCampaigns")}
        </Link>
      </div>
    </div>
  );
};
