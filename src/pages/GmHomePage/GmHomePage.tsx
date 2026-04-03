import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { getCampaignSystemLabel } from "../../entities/campaign";
import { useCampaigns, CampaignManagementPanel } from "../../features/campaign-select";
import { useAuth } from "../../features/auth";
import { usePartyManagement } from "../../features/party-management/hooks/usePartyManagement";
import { useLocale, useToast } from "../../shared/hooks";
import { Toast } from "../../shared/ui";
import type { PartySummary } from "../../shared/api/partiesRepo";
import { PartyListCard } from "./PartyListCard";
import { EmptyPartyState } from "./EmptyPartyState";
import { NewPartyForm } from "./NewPartyForm";
import { GmWorkspaceHero } from "./GmWorkspaceHero";

export const GmHomePage = () => {
  const { campaigns, selectCampaign, selectedCampaign } = useCampaigns();
  const { user } = useAuth();
  const { t } = useLocale();
  const { toast, clearToast } = useToast();
  const navigate = useNavigate();

  const {
    parties,
    loading,
    partyName,
    setPartyName,
    campaignId,
    setCampaignId,
    createParty,
    saving,
    error,
  } = usePartyManagement(campaigns);

  const campaignMap = useMemo(
    () => new Map(campaigns.map((c) => [c.id, c])),
    [campaigns]
  );
  const latestParty = parties[0] ?? null;
  const otherParties = latestParty ? parties.slice(1) : [];

  const handleOpenParty = (party: PartySummary) => {
    if (party.campaignId) selectCampaign(party.campaignId);
    navigate(routes.partyDetails.replace(":partyId", party.id));
  };

  const handleCreateParty = async () => {
    const result = await createParty();
    if (result.ok && result.party?.id) {
      if (result.party.campaignId) selectCampaign(result.party.campaignId);
      navigate(routes.partyDetails.replace(":partyId", result.party.id));
    }
  };

  return (
    <>
      <Toast toast={toast} onClose={clearToast} />
      <section className="space-y-6">
        <GmWorkspaceHero
          displayName={user?.displayName || user?.username || "GM"}
          campaignsCount={campaigns.length}
          partiesCount={parties.length}
          activeCampaignName={selectedCampaign?.name ?? null}
          onOpenAdmin={
            user?.isSystemAdmin ? () => navigate(routes.adminHome) : undefined
          }
        />

        <section className="rounded-[34px] border border-limiar-300/10 bg-[linear-gradient(180deg,rgba(26,12,55,0.4),rgba(2,6,23,0.92))] p-1 shadow-[0_24px_70px_rgba(2,6,23,0.32)]">
          <section className="rounded-4xl border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] p-6 shadow-[0_24px_70px_rgba(2,6,23,0.28)]">
            <header className="flex flex-col gap-4 border-b border-white/8 pb-5">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-slate-400">
                  {t("gm.home.activeParties")}
                </p>
                <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-300">
                  {t("gm.home.partiesSectionDescription")}
                </p>
              </div>
            </header>

            <div className="mt-5 space-y-4">
              {loading ? (
                <div className="rounded-3xl border border-white/8 bg-white/3 p-4 text-sm text-slate-400">
                  {t("gm.home.partyLoading")}
                </div>
              ) : parties.length === 0 ? (
                <EmptyPartyState />
              ) : (
                <>
                  {latestParty && (
                    <PartyListCard
                      party={latestParty}
                      campaignName={campaignMap.get(latestParty.campaignId)?.name}
                      systemLabel={
                        campaignMap.get(latestParty.campaignId)
                          ? getCampaignSystemLabel(campaignMap.get(latestParty.campaignId)!.systemType)
                          : undefined
                      }
                      onOpen={() => handleOpenParty(latestParty)}
                      featured
                    />
                  )}

                  {otherParties.length > 0 && (
                    <div className="grid gap-3 lg:grid-cols-2">
                      {otherParties.map((party) => {
                        const campaign = campaignMap.get(party.campaignId);
                        return (
                          <PartyListCard
                            key={party.id}
                            party={party}
                            campaignName={campaign?.name}
                            systemLabel={
                              campaign ? getCampaignSystemLabel(campaign.systemType) : undefined
                            }
                            onOpen={() => handleOpenParty(party)}
                          />
                        );
                      })}
                    </div>
                  )}
                </>
              )}
            </div>
          </section>
        </section>

        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <section className="rounded-[34px] border border-limiar-300/10 bg-[linear-gradient(180deg,rgba(26,12,55,0.4),rgba(2,6,23,0.92))] p-1 shadow-[0_24px_70px_rgba(2,6,23,0.32)]">
            <CampaignManagementPanel />
          </section>

          <div>
            <NewPartyForm
              campaigns={campaigns}
              partyName={partyName}
              setPartyName={setPartyName}
              campaignId={campaignId}
              setCampaignId={setCampaignId}
              onCreate={handleCreateParty}
              saving={saving}
              error={error}
            />
          </div>
        </div>
      </section>
    </>
  );
};
