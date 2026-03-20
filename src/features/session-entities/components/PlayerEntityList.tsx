import { useEffect } from "react";
import type { CampaignEvent } from "../../sessions/hooks/useCampaignEvents";
import { useVisibleEntities } from "../hooks/useVisibleEntities";
import { PlayerEntityCard } from "./PlayerEntityCard";
import { useLocale } from "../../../shared/hooks/useLocale";

const ENTITY_EVENT_TYPES = new Set([
  "entity_revealed",
  "entity_hidden",
  "entity_hp_updated",
  "session_entity_removed",
]);

type Props = {
  sessionId: string | null | undefined;
  lastEvent?: CampaignEvent | null;
};

export const PlayerEntityList = ({ sessionId, lastEvent }: Props) => {
  const { t } = useLocale();
  const { entities, loading, refresh } = useVisibleEntities(sessionId);

  useEffect(() => {
    if (!lastEvent || !ENTITY_EVENT_TYPES.has(lastEvent.type)) return;
    refresh();
  }, [lastEvent, refresh]);

  if (!sessionId || (entities.length === 0 && !loading)) return null;

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6">
      <h2 className="text-lg font-semibold text-white mb-4">{t("entity.player.title")}</h2>
      {loading ? (
        <p className="text-xs text-slate-500">{t("entity.loading")}</p>
      ) : (
        <div className="space-y-2">
          {entities.map((se) => (
            <PlayerEntityCard key={se.id} entity={se} />
          ))}
        </div>
      )}
    </div>
  );
};
