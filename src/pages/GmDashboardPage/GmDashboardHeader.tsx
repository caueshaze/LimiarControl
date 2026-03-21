import { Link } from "react-router-dom";
import { getCampaignSystemLabel, type CampaignSystemType } from "../../entities/campaign";

type Props = {
  backHref?: string | null;
  backLabel?: string | null;
  overviewName: string | null;
  overviewSystem: CampaignSystemType | null;
  selectedCampaignName?: string | null;
};

export const GmDashboardHeader = ({
  backHref = null,
  backLabel = null,
  overviewName,
  overviewSystem,
  selectedCampaignName,
}: Props) => (
  <header className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-6">
    <div>
      {backHref ? (
        <Link
          to={backHref}
          className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400 hover:text-slate-200"
        >
          {backLabel ?? "← Party"}
        </Link>
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
