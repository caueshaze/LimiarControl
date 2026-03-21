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
  combatActive?: boolean;
  lastEvent?: CampaignEvent | null;
};

export const PlayerEntityList = ({ sessionId, combatActive = false, lastEvent }: Props) => {
  const { t } = useLocale();
  const { entities, loading, refresh } = useVisibleEntities(sessionId);

  useEffect(() => {
    if (!lastEvent || !ENTITY_EVENT_TYPES.has(lastEvent.type)) return;
    refresh();
  }, [lastEvent, refresh]);

  if (!sessionId || (entities.length === 0 && !loading && !combatActive)) return null;

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-white">{t("entity.player.title")}</h2>
          <p className="mt-1 text-xs text-slate-500">
            {combatActive ? t("entity.player.combatLive") : t("entity.player.combatIdle")}
          </p>
        </div>
        {combatActive && (
          <span className="rounded-full border border-rose-500/30 bg-rose-500/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-rose-300">
            {t("entity.player.combatLive")}
          </span>
        )}
      </div>
      {loading ? (
        <p className="text-xs text-slate-500">{t("entity.loading")}</p>
      ) : entities.length === 0 ? (
        <p className="text-xs text-slate-500">{t("entity.player.waitingReveal")}</p>
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
