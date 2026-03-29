import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { partiesRepo } from "../../shared/api/partiesRepo";
import { useLocale } from "../../shared/hooks/useLocale";
import { CharacterSheet } from "./components/CharacterSheet";

export const CharacterSheetDraftPage = () => {
  const { partyId, draftId } = useParams<{ partyId?: string; draftId?: string }>();
  const { t } = useLocale();
  const [campaignId, setCampaignId] = useState<string | null>(null);

  useEffect(() => {
    if (!partyId) {
      setCampaignId(null);
      return;
    }
    partiesRepo.get(partyId)
      .then((party) => setCampaignId(party.campaignId))
      .catch(() => setCampaignId(null));
  }, [partyId]);

  return (
    <CharacterSheet
      partyId={partyId ?? null}
      campaignId={campaignId}
      mode="creation"
      creationDraftId={draftId ?? null}
      backHref={partyId ? routes.partyDetails.replace(":partyId", partyId) : null}
      backLabel={t("sheet.header.backToParty")}
    />
  );
};
