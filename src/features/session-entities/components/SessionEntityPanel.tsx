import { useEffect, useState } from "react";
import type { CampaignEvent } from "../../sessions/hooks/useCampaignEvents";
import { useSessionEntities } from "../hooks/useSessionEntities";
import { SessionEntityRow } from "./SessionEntityRow";
import { AddEntityToSessionPanel } from "./AddEntityToSessionPanel";
import { useLocale } from "../../../shared/hooks/useLocale";

type Props = {
  sessionId: string;
  campaignId: string;
  combatActive?: boolean;
  lastEvent?: CampaignEvent | null;
};

const ENTITY_EVENT_TYPES = new Set([
  "session_entity_added",
  "session_entity_removed",
  "entity_revealed",
  "entity_hidden",
  "entity_hp_updated",
]);

export const SessionEntityPanel = ({
  sessionId,
  campaignId,
  combatActive = false,
  lastEvent,
}: Props) => {
  const { t } = useLocale();
  const { entities, loading, refresh, addEntity, removeEntity, toggleVisibility, updateHp } =
    useSessionEntities(sessionId);
  const [showPicker, setShowPicker] = useState(false);

  // React to realtime events from other clients
  useEffect(() => {
    if (!lastEvent || !ENTITY_EVENT_TYPES.has(lastEvent.type)) return;
    refresh();
  }, [lastEvent, refresh]);

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold text-white">{t("entity.session.panelTitle")}</h2>
          <p className="mt-1 text-xs text-slate-500">
            {combatActive ? t("entity.session.combatLive") : t("entity.session.combatIdle")}
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowPicker((v) => !v)}
          className="rounded-full border border-slate-700 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-slate-200 hover:bg-slate-800"
        >
          {showPicker ? t("entity.session.closePicker") : t("entity.session.add")}
        </button>
      </div>

      {showPicker && (
        <div className="mb-4">
          <AddEntityToSessionPanel
            campaignId={campaignId}
            onAdd={async (campaignEntityId, label, currentHp) => {
              await addEntity(campaignEntityId, label, currentHp);
            }}
            onClose={() => setShowPicker(false)}
          />
        </div>
      )}

      {loading ? (
        <p className="text-xs text-slate-500">{t("entity.loading")}</p>
      ) : entities.length === 0 ? (
        <p className="text-xs text-slate-500">{t("entity.session.empty")}</p>
      ) : (
        <div className="space-y-2">
          {entities.map((se) => (
            <SessionEntityRow
              key={se.id}
              entity={se}
              onToggleVisibility={toggleVisibility}
              onUpdateHp={updateHp}
              onRemove={removeEntity}
            />
          ))}
        </div>
      )}
    </div>
  );
};
