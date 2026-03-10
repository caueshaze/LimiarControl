import { useParams, useSearchParams } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import type { RoleMode } from "../../shared/types/role";
import { CharacterSheet } from "./components/CharacterSheet";

type Props = {
  viewerUserId?: string | null;
  viewerRole?: RoleMode;
};

export const CharacterSheetPage = ({ viewerUserId = null, viewerRole = "PLAYER" }: Props) => {
  const { partyId } = useParams<{ partyId?: string }>();
  const [searchParams] = useSearchParams();
  const requestedMode = searchParams.get("mode") === "play" ? "play" : "creation";
  const requestedPlayerId = searchParams.get("playerId");
  const playPlayerUserId =
    requestedMode === "play"
      ? viewerRole === "GM"
        ? requestedPlayerId
        : viewerUserId
      : null;
  const backHref =
    partyId && viewerRole === "PLAYER"
      ? routes.playerPartyDetails.replace(":partyId", partyId)
      : null;

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
      mode={requestedMode}
      playPlayerUserId={playPlayerUserId}
      canEditPlay={viewerRole === "GM"}
      backHref={backHref}
    />
  );
};
