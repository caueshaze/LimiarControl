import { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { useCampaignEvents } from "../sessions";
import { partiesRepo } from "../../shared/api/partiesRepo";
import type { RoleMode } from "../../shared/types/role";
import { CharacterSheet } from "./components/CharacterSheet";

type Props = {
  viewerUserId?: string | null;
  viewerRole?: RoleMode;
};

export const CharacterSheetPage = ({ viewerUserId = null, viewerRole = "PLAYER" }: Props) => {
  const { partyId } = useParams<{ partyId?: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [campaignId, setCampaignId] = useState<string | null>(null);
  const requestedMode = searchParams.get("mode") === "play" ? "play" : "creation";
  const requestedPlayerId = searchParams.get("playerId");
  const requestedCampaignId = searchParams.get("campaignId");
  const requestedPlayerName = searchParams.get("playerName");
  const playPlayerUserId =
    requestedMode === "play"
      ? viewerRole === "GM"
        ? requestedPlayerId
        : viewerUserId
      : null;
  const backHref =
    partyId
      ? viewerRole === "PLAYER"
        ? routes.playerPartyDetails.replace(":partyId", partyId)
        : requestedCampaignId
          ? routes.campaignDashboard.replace(":campaignId", requestedCampaignId)
          : routes.partyDetails.replace(":partyId", partyId)
      : null;
  const backLabel =
    viewerRole === "GM" && requestedMode === "play"
      ? "Back To GM Dashboard"
      : "Back To Party";
  const playContextLabel =
    viewerRole === "GM" && requestedMode === "play"
      ? requestedPlayerName || "Selected Player"
      : null;

  useEffect(() => {
    if (!partyId || requestedCampaignId) {
      setCampaignId(requestedCampaignId ?? null);
      return;
    }
    partiesRepo.get(partyId)
      .then((party) => setCampaignId(party.campaignId))
      .catch(() => setCampaignId(null));
  }, [partyId, requestedCampaignId]);

  const { lastEvent } = useCampaignEvents(campaignId);

  useEffect(() => {
    if (
      viewerRole !== "PLAYER" ||
      requestedMode !== "play" ||
      !lastEvent ||
      lastEvent.type !== "session_closed"
    ) {
      return;
    }
    const eventPartyId =
      typeof lastEvent.payload.partyId === "string" ? lastEvent.payload.partyId : null;
    if (eventPartyId && partyId && eventPartyId !== partyId) {
      return;
    }
    navigate(routes.home, { replace: true });
  }, [lastEvent, navigate, partyId, requestedMode, viewerRole]);

  if (requestedMode === "play" && !playPlayerUserId) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-void-950 text-slate-400">
        Select a player to open the play sheet.
      </div>
    );
  }

  return (
    <CharacterSheet
      partyId={partyId ?? null}
      campaignId={campaignId}
      mode={requestedMode}
      playPlayerUserId={playPlayerUserId}
      canEditPlay={viewerRole === "GM"}
      backHref={backHref}
      backLabel={backLabel}
      playContextLabel={playContextLabel}
    />
  );
};
