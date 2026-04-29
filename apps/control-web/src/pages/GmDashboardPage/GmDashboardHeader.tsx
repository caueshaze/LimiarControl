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
    <header className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-6">
      <div>
        {backHref ? (
          <BackButton
            fallbackTo={backHref}
            label={<><span aria-hidden>←</span>{t("campaignHome.back")}</>}
            className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/3 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-300 transition hover:border-white/16 hover:text-white"
          />
        ) : null}
        <p className="text-xs uppercase tracking-[0.3em] text-limiar-300">GM Command Center</p>
        <h1 className="mt-2 text-3xl font-bold text-white">
          {selectedCampaignName ?? overviewName ?? "Untitled Campaign"}
        </h1>
        <p className="mt-1 text-sm text-slate-400">
          {overviewSystem ? getCampaignSystemLabel(overviewSystem) : "No System"}
        </p>
      </div>
      <div className="flex gap-3" />
    </header>
  );
};
