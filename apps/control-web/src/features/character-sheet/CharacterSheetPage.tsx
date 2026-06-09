import { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { useCampaignEvents } from "../sessions";
import { partiesRepo } from "../../shared/api/partiesRepo";
import type { RoleMode } from "../../shared/types/role";
import { useLocale } from "../../shared/hooks/useLocale";
import { CharacterSheet } from "./components/CharacterSheet";
import { CharacterSheetViewScreen } from "./components/view/CharacterSheetViewScreen";
import { resolveCharacterSheetPageContext } from "./characterSheetPageContext";

type Props = {
  viewerUserId?: string | null;
  viewerRole?: RoleMode;
};

export const CharacterSheetPage = ({ viewerUserId = null, viewerRole = "PLAYER" }: Props) => {
  const { partyId } = useParams<{ partyId?: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { t } = useLocale();
  const rawMode = searchParams.get("mode");
  const isViewMode = rawMode === "view";
  const requestedMode = rawMode === "play" ? "play" : "creation";
  const requestedPlayerId = searchParams.get("playerId");
  const requestedCampaignId = searchParams.get("campaignId");
  const [campaignId, setCampaignId] = useState<string | null>(requestedCampaignId ?? null);
  const [campaignIdResolved, setCampaignIdResolved] = useState(!partyId || !!requestedCampaignId);
  const requestedPlayerName = searchParams.get("playerName");
  const requestedReturnTo = searchParams.get("returnTo");
  const {
    creationPlayerUserId,
    playPlayerUserId,
    canEditPlay,
    backHref,
    backLabel,
    playContextLabel,
  } = resolveCharacterSheetPageContext({
    requestedMode,
    requestedPlayerId,
    requestedCampaignId,
    requestedReturnTo,
    requestedPlayerName,
    viewerUserId,
    viewerRole,
    partyId: partyId ?? null,
    backToBoardLabel: t("sheet.header.backToBoard"),
    backToPartyLabel: t("sheet.header.backToParty"),
  });

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
      canEditPlay ||
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
  }, [canEditPlay, lastEvent, navigate, partyId, requestedMode]);

  if (isViewMode) {
    // Load the target player's sheet whenever a playerId is supplied (GM inspect).
    // Authorization is enforced server-side (party GM check), so we must not gate
    // on the viewer's *global* role here — a campaign GM may have a PLAYER role.
    const viewPlayerUserId =
      requestedPlayerId && requestedPlayerId !== viewerUserId ? requestedPlayerId : null;
    return (
      <CharacterSheetViewScreen
        partyId={partyId ?? null}
        playerUserId={viewPlayerUserId}
        campaignId={campaignId}
        backHref={backHref}
        backLabel={backLabel}
      />
    );
  }

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
      canEditPlay={canEditPlay}
      backHref={backHref}
      backLabel={backLabel}
      playContextLabel={playContextLabel}
    />
  );
};
