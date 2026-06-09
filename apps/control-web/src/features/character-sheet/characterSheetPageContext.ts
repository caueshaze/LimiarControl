import { buildCampaignDashboardPath, routes } from "../../app/routes/routes";
import type { RoleMode } from "../../shared/types/role";

type ResolveCharacterSheetPageContextParams = {
  requestedMode: "creation" | "play";
  requestedPlayerId: string | null;
  requestedCampaignId: string | null;
  requestedReturnTo: string | null;
  requestedPlayerName: string | null;
  viewerUserId: string | null;
  viewerRole: RoleMode;
  partyId: string | null;
  backToBoardLabel: string;
  backToPartyLabel: string;
};

export const resolveCharacterSheetPageContext = (
  params: ResolveCharacterSheetPageContextParams,
) => {
  const isManagingAnotherPlayer =
    !!params.requestedPlayerId &&
    !!params.viewerUserId &&
    params.requestedPlayerId !== params.viewerUserId;

  const creationPlayerUserId =
    params.requestedMode === "creation" && isManagingAnotherPlayer
      ? params.requestedPlayerId
      : null;
  const playPlayerUserId =
    params.requestedMode === "play"
      ? isManagingAnotherPlayer
        ? params.requestedPlayerId
        : params.viewerUserId
      : null;
  const canEditPlay = params.requestedMode === "play" && isManagingAnotherPlayer;
  const useGmBackNavigation = isManagingAnotherPlayer || params.viewerRole === "GM";

  const backHref =
    params.partyId
      ? !useGmBackNavigation
        ? params.requestedMode === "play" && params.requestedReturnTo === "board"
          ? routes.board.replace(":partyId", params.partyId)
          : routes.playerPartyDetails.replace(":partyId", params.partyId)
        : params.requestedCampaignId
          ? buildCampaignDashboardPath(params.requestedCampaignId, params.partyId)
          : routes.partyDetails.replace(":partyId", params.partyId)
      : null;

  const backLabel =
    useGmBackNavigation && params.requestedMode === "play"
      ? "Back To GM Dashboard"
      : !useGmBackNavigation &&
          params.requestedMode === "play" &&
          params.requestedReturnTo === "board"
        ? params.backToBoardLabel
        : params.backToPartyLabel;

  const playContextLabel =
    canEditPlay ? params.requestedPlayerName || "Selected Player" : null;

  return {
    creationPlayerUserId,
    playPlayerUserId,
    canEditPlay,
    backHref,
    backLabel,
    playContextLabel,
  };
};
