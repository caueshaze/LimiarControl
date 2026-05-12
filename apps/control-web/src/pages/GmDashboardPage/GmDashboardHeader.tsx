import { getCampaignSystemLabel, type CampaignSystemType } from "../../entities/campaign";
import { useLocale } from "../../shared/hooks/useLocale";
import { BackButton } from "../../shared/ui";

type Props = {
  backHref?: string | null;
  backLabel?: string | null;
  overviewName: string | null;
  overviewSystem: CampaignSystemType | null;
  selectedCampaignName?: string | null;
};

export const GmDashboardHeader = ({
  backHref = null,
  overviewName,
  overviewSystem,
  selectedCampaignName,
}: Props) => {
  const { t } = useLocale();

  return (
    <header className="relative overflow-hidden rounded-[34px] border border-white/8 bg-[#070712] shadow-[0_30px_90px_rgba(0,0,0,0.28)]">
      {/* Atmospheric orbs */}
      <div
        aria-hidden
        className="pointer-events-none absolute top-[-60px] left-[-60px] h-[260px] w-[360px] rounded-full bg-limiar-500/18 blur-[120px] motion-safe:animate-[landing-drift_16s_ease-in-out_infinite]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute right-[-40px] bottom-[-40px] h-[200px] w-[300px] rounded-full bg-sky-400/10 blur-[130px] motion-safe:animate-[landing-float_14s_ease-in-out_infinite]"
      />
      {/* Grid overlay */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.08]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.18) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.18) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
        }}
      />
      {/* Content */}
      <div className="relative z-10 flex flex-wrap items-center justify-between gap-4 px-8 py-7">
        <div>
          {backHref ? (
            <BackButton
              fallbackTo={backHref}
              label={<><span aria-hidden>←</span>{t("campaignHome.back")}</>}
              className="mb-3 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-300 transition hover:border-white/20 hover:bg-white/8 hover:text-white"
            />
          ) : null}
          <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-limiar-300">
            {t("gm.dashboard.commandCenter")}
          </p>
          <h1 className="mt-2 font-display text-3xl font-bold text-white">
            {selectedCampaignName ?? overviewName ?? t("gm.dashboard.untitledCampaign")}
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            {overviewSystem ? getCampaignSystemLabel(overviewSystem) : t("gm.dashboard.noSystem")}
          </p>
        </div>
      </div>
    </header>
  );
};
