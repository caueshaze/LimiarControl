import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { routes } from "../../../app/routes/routes";
import type { Campaign } from "../../../entities/campaign";
import { getCampaignSystemLabel } from "../../../entities/campaign";
import { useLocale } from "../../../shared/hooks/useLocale";
import { usePartyManagement } from "../hooks/usePartyManagement";

type PartyManagementPanelProps = {
  campaigns: Campaign[];
  onSelectCampaign: (campaignId: string) => void;
};

export const PartyManagementPanel = ({
  campaigns,
  onSelectCampaign,
}: PartyManagementPanelProps) => {
  const { t } = useLocale();
  const navigate = useNavigate();
  const {
    parties,
    loading,
    error,
    saving,
    partyName,
    setPartyName,
    campaignId,
    setCampaignId,
    createParty,
  } = usePartyManagement(campaigns);

  const campaignMap = useMemo(
    () => new Map(campaigns.map((campaign) => [campaign.id, campaign])),
    [campaigns]
  );

  const handleOpenParty = (partyId: string, selectedCampaignId?: string) => {
    if (selectedCampaignId) {
      onSelectCampaign(selectedCampaignId);
    }
    navigate(routes.partyDetails.replace(":partyId", partyId));
  };

  const handleCreateParty = async () => {
    const fallbackCampaignId = campaignId;
    const result = await createParty();
    if (result.ok && result.party?.id) {
      handleOpenParty(
        result.party.id,
        result.party.campaignId ?? fallbackCampaignId
      );
    }
  };

  return (
    <div className="grid gap-6 xl:grid-cols-[1fr_1.2fr]">
      <aside className="space-y-4 rounded-3xl border border-slate-800 bg-slate-900/40 p-6">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
            {t("gm.home.partyFormTitle")}
          </p>
          <p className="mt-2 text-sm text-slate-300">
            {t("gm.home.partyFormDescription")}
          </p>
        </div>

        <input
          value={partyName}
          onChange={(event) => setPartyName(event.target.value)}
          placeholder={t("gm.home.partyNamePlaceholder")}
          disabled={campaigns.length === 0 || saving}
          className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-slate-500 focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
        />

        <select
          value={campaignId}
          onChange={(event) => setCampaignId(event.target.value)}
          disabled={campaigns.length === 0 || saving}
          className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-slate-500 focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
        >
          {campaigns.length === 0 && <option value="">{t("gm.home.partyCampaignMissing")}</option>}
          {campaigns.map((campaign) => (
            <option key={campaign.id} value={campaign.id}>
              {campaign.name} · {getCampaignSystemLabel(campaign.systemType)}
            </option>
          ))}
        </select>

        <button
          type="button"
          onClick={handleCreateParty}
          disabled={
            campaigns.length === 0 ||
            saving ||
            !partyName.trim() ||
            !campaignId
          }
          className="w-full rounded-full bg-limiar-500 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white disabled:cursor-not-allowed disabled:opacity-60"
        >
          {saving ? t("gm.home.partyCreating") : t("gm.home.partyCreate")}
        </button>

        {error && (
          <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-200">
            {error}
          </div>
        )}
      </aside>

      <section className="space-y-4 rounded-3xl border border-slate-800 bg-slate-900/40 p-6">
        <header>
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
            {t("gm.home.partyPanelTitle")}
          </p>
          <p className="mt-2 text-sm text-slate-300">
            {t("gm.home.partyPanelDescription")}
          </p>
        </header>

        {loading && (
          <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4 text-sm text-slate-300">
            {t("gm.home.partyLoading")}
          </div>
        )}

        {!loading && parties.length === 0 && (
          <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-950/70 p-5 text-sm text-slate-400">
            {t("gm.home.partyEmpty")}
          </div>
        )}

        {!loading &&
          parties.map((party) => {
            const linkedCampaign = campaignMap.get(party.campaignId);
            return (
              <article
                key={party.id}
                className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h3 className="text-lg font-semibold text-white">{party.name}</h3>
                    <p className="mt-2 text-sm text-slate-400">
                      {linkedCampaign?.name ?? t("gm.home.partyCampaignUnknown")}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      {linkedCampaign
                        ? getCampaignSystemLabel(linkedCampaign.systemType)
                        : t("gm.home.partyCampaignUnknown")}
                    </p>
                  </div>

                  <div className="text-right">
                    <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
                      {t("gm.home.partyCreatedAt")}
                    </p>
                    <p className="mt-1 text-sm text-slate-300">
                      {new Date(party.createdAt).toLocaleDateString()}
                    </p>
                  </div>
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => handleOpenParty(party.id, party.campaignId)}
                    className="rounded-full bg-slate-100 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-900"
                  >
                    {t("gm.home.partyOpen")}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      onSelectCampaign(party.campaignId);
                      navigate(routes.campaignEdit.replace(":campaignId", party.campaignId));
                    }}
                    className="rounded-full border border-slate-700 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-200 hover:border-slate-500"
                  >
                    {t("gm.home.campaignOpen")}
                  </button>
                </div>
              </article>
            );
          })}
      </section>
    </div>
  );
};
