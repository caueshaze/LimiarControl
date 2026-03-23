import { useCallback, useEffect, useRef } from "react";
import type { EntityCategory } from "../../../entities/campaign-entity";
import type { SessionEntityPlayer } from "../../../entities/session-entity";
import type { CampaignEvent } from "../../sessions/hooks/useCampaignEvents";
import { useVisibleEntities } from "../hooks/useVisibleEntities";
import { PlayerEntityCard } from "./PlayerEntityCard";
import { useLocale } from "../../../shared/hooks/useLocale";
import {
  getHistory,
  subscribe,
  type RealtimeHistoryPublication,
} from "../../../shared/realtime/centrifugoClient";

const ENTITY_EVENT_TYPES = new Set([
  "session_entity_added",
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
  const { entities, loading, loaded, refresh, updateHp, removeEntity, upsertEntity } = useVisibleEntities(sessionId);
  const latestVersionsRef = useRef<Record<string, number>>({});
  const retryTimeoutsRef = useRef<number[]>([]);

  const scheduleRefreshRetries = useCallback(() => {
    retryTimeoutsRef.current.forEach((timeoutId) => window.clearTimeout(timeoutId));
    retryTimeoutsRef.current = [180, 650, 1400].map((delay) =>
      window.setTimeout(() => {
        refresh();
      }, delay),
    );
  }, [refresh]);

  const buildVisibleEntityFromPayload = useCallback((payload?: Record<string, unknown>): SessionEntityPlayer | null => {
    const nextSessionId = typeof payload?.sessionId === "string" ? payload.sessionId : null;
    const sessionEntityId =
      typeof payload?.sessionEntityId === "string" ? payload.sessionEntityId : null;
    const campaignEntityId =
      typeof payload?.campaignEntityId === "string" ? payload.campaignEntityId : null;
    const entityName = typeof payload?.entityName === "string" ? payload.entityName : null;
    const entityCategory: EntityCategory =
      payload?.entityCategory === "npc" ||
      payload?.entityCategory === "enemy" ||
      payload?.entityCategory === "creature" ||
      payload?.entityCategory === "ally"
        ? payload.entityCategory
        : "npc";

    if (!nextSessionId || !sessionEntityId || !campaignEntityId || !entityName) {
      return null;
    }

    return {
      id: sessionEntityId,
      sessionId: nextSessionId,
      campaignEntityId,
      currentHp: typeof payload?.currentHp === "number" ? payload.currentHp : null,
      label: typeof payload?.label === "string" ? payload.label : null,
      revealedAt: null,
        entity: {
          id: campaignEntityId,
          campaignId: typeof payload?.campaignId === "string" ? payload.campaignId : "",
          name: entityName,
          category: entityCategory,
          abilities: {
            strength: 10,
            dexterity: 10,
            constitution: 10,
            intelligence: 10,
            wisdom: 10,
            charisma: 10,
          },
          savingThrows: {},
          skills: {},
          damageResistances: [],
          damageImmunities: [],
          damageVulnerabilities: [],
          conditionImmunities: [],
          combatActions: [],
          maxHp: typeof payload?.maxHp === "number" ? payload.maxHp : null,
          createdAt: "",
        },
      };
  }, []);

  const processEntityEvent = useCallback((message: unknown) => {
    if (!message || typeof message !== "object") {
      return;
    }

    const data = message as {
      payload?: Record<string, unknown>;
      type?: string;
      version?: number;
    };
    if (!ENTITY_EVENT_TYPES.has(data.type ?? "")) {
      return;
    }

    const eventSessionId =
      typeof data.payload?.sessionId === "string" ? data.payload.sessionId : null;
    if (eventSessionId && sessionId && eventSessionId !== sessionId) {
      return;
    }

    const versionKey = `${data.type}:${eventSessionId ?? sessionId ?? ""}:${String(
      data.payload?.sessionEntityId ?? "",
    )}`;
    if (
      typeof data.version === "number" &&
      data.version <= (latestVersionsRef.current[versionKey] ?? 0)
    ) {
      return;
    }
    if (typeof data.version === "number") {
      latestVersionsRef.current[versionKey] = data.version;
    }

    if (data.type === "entity_hp_updated") {
      updateHp(
        String(data.payload?.sessionEntityId ?? ""),
        typeof data.payload?.currentHp === "number" ? data.payload.currentHp : null,
      );
      return;
    }

    if (data.type === "entity_hidden" || data.type === "session_entity_removed") {
      removeEntity(String(data.payload?.sessionEntityId ?? ""));
      return;
    }

    if (data.type === "entity_revealed") {
      const visibleEntity = buildVisibleEntityFromPayload(data.payload);
      if (visibleEntity) {
        upsertEntity(visibleEntity);
      }
      scheduleRefreshRetries();
      return;
    }

    if (data.type === "session_entity_added" && data.payload?.visibleToPlayers === true) {
      const visibleEntity = buildVisibleEntityFromPayload(data.payload);
      if (visibleEntity) {
        upsertEntity(visibleEntity);
      }
      scheduleRefreshRetries();
      return;
    }

    refresh();
  }, [buildVisibleEntityFromPayload, refresh, removeEntity, scheduleRefreshRetries, sessionId, updateHp, upsertEntity]);

  useEffect(() => {
    latestVersionsRef.current = {};
    if (!sessionId) {
      return;
    }

    const channel = `session:${sessionId}`;
    let active = true;
    const replayHistory = (publications: RealtimeHistoryPublication[]) => {
      [...publications]
        .sort((left, right) => {
          const leftVersion =
            typeof (left.data as { version?: unknown } | null | undefined)?.version === "number"
              ? (left.data as { version: number }).version
              : 0;
          const rightVersion =
            typeof (right.data as { version?: unknown } | null | undefined)?.version === "number"
              ? (right.data as { version: number }).version
              : 0;
          if (leftVersion !== rightVersion) {
            return leftVersion - rightVersion;
          }
          const leftOffset = left.offset ? Number(left.offset) : 0;
          const rightOffset = right.offset ? Number(right.offset) : 0;
          return leftOffset - rightOffset;
        })
        .forEach((publication) => processEntityEvent(publication.data));
    };

    const unsubscribeSession = subscribe(channel, {
      onSubscribed: () => {
        void getHistory(channel, 20)
          .then((publications) => {
            if (active) {
              replayHistory(publications);
            }
          })
          .catch(() => {});
      },
      onPublication: (message) => {
        processEntityEvent(message);
      },
    });

    return () => {
      active = false;
      unsubscribeSession();
    };
  }, [processEntityEvent, sessionId]);

  useEffect(() => {
    return () => {
      retryTimeoutsRef.current.forEach((timeoutId) => window.clearTimeout(timeoutId));
      retryTimeoutsRef.current = [];
    };
  }, []);

  useEffect(() => {
    if (!lastEvent) return;
    processEntityEvent(lastEvent);
  }, [lastEvent, processEntityEvent]);

  if (!sessionId) return null;

  return (
    <section className="rounded-[32px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] p-6 shadow-[0_18px_60px_rgba(2,6,23,0.2)]">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-slate-400">
            {t("playerBoard.liveStatusTitle")}
          </p>
          <h2 className="mt-2 text-lg font-semibold text-white">{t("entity.player.title")}</h2>
          <p className="mt-1 text-xs text-slate-400">
            {combatActive ? t("entity.player.combatLive") : t("entity.player.combatIdle")}
          </p>
        </div>
        {combatActive && (
          <span className="rounded-full border border-rose-500/30 bg-rose-500/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.22em] text-rose-200">
            {t("entity.player.combatLive")}
          </span>
        )}
      </div>
      {!loaded && loading ? (
        <div className="rounded-[24px] border border-white/8 bg-white/[0.04] px-4 py-4 text-sm text-slate-400">
          {t("entity.loading")}
        </div>
      ) : entities.length === 0 ? (
        <div className="rounded-[24px] border border-dashed border-white/10 bg-white/[0.03] px-4 py-5 text-sm text-slate-400">
          {combatActive ? t("entity.player.waitingReveal") : t("entity.player.waitingRevealIdle")}
        </div>
      ) : (
        <div className="space-y-2">
          {entities.map((se) => (
            <PlayerEntityCard key={se.id} entity={se} />
          ))}
        </div>
      )}
    </section>
  );
};
