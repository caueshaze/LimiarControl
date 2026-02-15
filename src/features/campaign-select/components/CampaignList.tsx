import type { Campaign } from "../../../entities/campaign";
import { getCampaignSystemLabel } from "../../../entities/campaign";
import { useLocale } from "../../../shared/hooks/useLocale";

type CampaignListProps = {
  campaigns: Campaign[];
  selectedCampaignId: string | null;
  onSelect: (id: string) => void;
};

export const CampaignList = ({
  campaigns,
  selectedCampaignId,
  onSelect,
}: CampaignListProps) => {
  const { t } = useLocale();

  if (campaigns.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-300">
        {t("campaign.empty")}
      </div>
    );
  }

  return (
    <ul className="space-y-3">
      {campaigns.map((campaign) => {
        const isSelected = campaign.id === selectedCampaignId;

        return (
          <li
            key={campaign.id}
            className={`group relative overflow-hidden rounded-2xl border transition-all ${isSelected
              ? "border-limiar-500 bg-limiar-500/10 shadow-[0_0_20px_rgba(139,92,246,0.1)]"
              : "border-slate-800 bg-slate-900/40 hover:border-slate-700"
            }`}
          >
            <div className="flex flex-wrap items-center justify-between gap-3 p-4">
              <div>
                <p className="text-sm font-bold text-slate-100">{campaign.name}</p>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-400">
                    {getCampaignSystemLabel(campaign.systemType)}
                  </span>
                </div>
              </div>
              <button
                type="button"
                onClick={() => onSelect(campaign.id)}
                className={
                  isSelected
                    ? "rounded-full bg-slate-100 px-4 py-1.5 text-xs font-bold text-slate-900 shadow-md"
                    : "rounded-full border border-slate-700 px-4 py-1.5 text-xs font-medium text-slate-300 transition-colors hover:bg-slate-800 hover:text-white"
                }
              >
                {isSelected ? t("campaign.selected") : t("campaign.select")}
              </button>
            </div>
            {isSelected && (
              <div className="absolute inset-x-0 bottom-0 h-0.5 bg-gradient-to-r from-transparent via-limiar-500 to-transparent opacity-50" />
            )}
          </li>
        );
      })}
    </ul>
  );
};
