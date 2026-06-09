import { useCharacterSheetView } from "../../hooks/useCharacterSheetView";
import { CharacterSheetStateScreen } from "../CharacterSheetStateScreen";
import { CharacterSheetView } from "./CharacterSheetView";

type Props = {
  partyId: string | null;
  playerUserId: string | null;
  campaignId: string | null;
  backHref?: string | null;
  backLabel?: string | null;
};

export const CharacterSheetViewScreen = ({
  partyId,
  playerUserId,
  campaignId,
  backHref = null,
  backLabel = null,
}: Props) => {
  const { sheet, loading, error, missing } = useCharacterSheetView(partyId, playerUserId, campaignId);

  if (loading) {
    return <CharacterSheetStateScreen />;
  }

  if (error) {
    return <CharacterSheetStateScreen error={error} />;
  }

  if (missing || !sheet) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-void-950 px-6 text-center text-slate-400">
        Esta ficha ainda não foi criada.
      </div>
    );
  }

  return (
    <CharacterSheetView
      sheet={sheet}
      campaignId={campaignId}
      backHref={backHref}
      backLabel={backLabel}
    />
  );
};
