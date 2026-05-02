import { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { buildCampaignDashboardPath, routes } from "../../app/routes/routes";
import { useCampaignEvents, usePartyActiveSession } from "../sessions";
import { partiesRepo } from "../../shared/api/partiesRepo";
import type { RoleMode } from "../../shared/types/role";
import { useLocale } from "../../shared/hooks/useLocale";
import { CharacterSheet } from "./components/CharacterSheet";
import { useCombatUiState } from "../combat-ui/useCombatUiState";

type Props = {
  viewerUserId?: string | null;
  viewerRole?: RoleMode;
};

export const CharacterSheetPage = ({ viewerUserId = null, viewerRole = "PLAYER" }: Props) => {
  const { partyId } = useParams<{ partyId?: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { t } = useLocale();
  const requestedMode = searchParams.get("mode") === "play" ? "play" : "creation";
  const requestedPlayerId = searchParams.get("playerId");
  const requestedCampaignId = searchParams.get("campaignId");
  const [campaignId, setCampaignId] = useState<string | null>(requestedCampaignId ?? null);
  const [campaignIdResolved, setCampaignIdResolved] = useState(!partyId || !!requestedCampaignId);
  const requestedPlayerName = searchParams.get("playerName");
  const requestedReturnTo = searchParams.get("returnTo");
  const creationPlayerUserId =
    requestedMode === "creation" && viewerRole === "GM"
      ? requestedPlayerId
      : null;
  const playPlayerUserId =
    requestedMode === "play"
      ? viewerRole === "GM"
        ? requestedPlayerId
        : viewerUserId
      : null;
  const backHref =
    partyId
      ? viewerRole === "PLAYER"
        ? requestedMode === "play" && requestedReturnTo === "board"
          ? routes.board.replace(":partyId", partyId)
          : routes.playerPartyDetails.replace(":partyId", partyId)
        : requestedCampaignId
          ? buildCampaignDashboardPath(requestedCampaignId, partyId)
          : routes.partyDetails.replace(":partyId", partyId)
      : null;
  const backLabel =
    viewerRole === "GM" && requestedMode === "play"
      ? "Back To GM Dashboard"
      : viewerRole === "PLAYER" && requestedMode === "play" && requestedReturnTo === "board"
        ? t("sheet.header.backToBoard")
        : t("sheet.header.backToParty");
  const playContextLabel =
    viewerRole === "GM" && requestedMode === "play"
      ? requestedPlayerName || "Selected Player"
      : null;
  const { activeSession } = usePartyActiveSession(
    requestedMode === "play" ? (partyId ?? null) : null,
  );
  const combat = useCombatUiState({
    enabled: requestedMode === "play" && activeSession?.status === "ACTIVE" && !!playPlayerUserId,
    pollMs: 15_000,
    sessionId: activeSession?.id ?? "",
    userId: playPlayerUserId,
  });
  const activeEffects = combat.myParticipant?.active_effects ?? [];

  useEffect(() => {
    if (!partyId || requestedCampaignId) {
      setCampaignId(requestedCampaignId ?? null);
      setCampaignIdResolved(true);
      return;
    }
    partiesRepo.get(partyId)
      .then((party) => {
        setCampaignId(party.campaignId);
        setCampaignIdResolved(true);
      })
      .catch(() => {
        setCampaignId(null);
        setCampaignIdResolved(true);
      });
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

  if (requestedMode === "creation" && !campaignIdResolved) {
    return null;
  }

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
      creationPlayerUserId={creationPlayerUserId}
      canEditPlay={viewerRole === "GM"}
      backHref={backHref}
      backLabel={backLabel}
      playContextLabel={playContextLabel}
      activeEffects={activeEffects}
    />
  );
};
