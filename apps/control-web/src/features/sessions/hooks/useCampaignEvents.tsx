import { useEffect, useMemo, useRef, useState } from "react";
import type {
  ConnectionState,
  RealtimePresenceMember,
} from "../../../shared/realtime/centrifugoClient";
import {
  getHistory,
  getPresence,
  subscribe,
  subscribeConnectionState,
} from "../../../shared/realtime/centrifugoClient";
import {
  getCampaignEventVersionKey,
  isSupportedCampaignEventType,
  sortRealtimeHistoryByVersion,
} from "./campaignEvents.realtime";
import type { CampaignEvent } from "./campaignEvents.types";

export type { CampaignEvent } from "./campaignEvents.types";

export const useCampaignEvents = (campaignId?: string | null) => {
  const [connectionState, setConnectionState] = useState<ConnectionState>("offline");
  const [lastEvent, setLastEvent] = useState<CampaignEvent | null>(null);
  const [presenceClients, setPresenceClients] = useState<Record<string, RealtimePresenceMember>>({});
  const latestVersionsRef = useRef<Record<string, number>>({});

  const onlineUsers = useMemo(() => {
    const next: Record<string, string> = {};
    Object.values(presenceClients).forEach((member) => {
      next[member.userId] = member.displayName;
    });
    return next;
  }, [presenceClients]);

  useEffect(() => {
    setLastEvent(null);
    setPresenceClients({});
    latestVersionsRef.current = {};

    if (!campaignId) {
      setConnectionState("offline");
      return;
    }

    const channel = `campaign:${campaignId}`;
    let active = true;
    const processRealtimeMessage = (message: unknown) => {
      if (!message || typeof message !== "object") {
        return;
      }

      const data = message as {
        payload?: Record<string, unknown>;
        type?: string;
        version?: number;
      };
      if (!isSupportedCampaignEventType(data.type)) {
        return;
      }

      const versionKey = getCampaignEventVersionKey(campaignId, data);
      if (
        typeof data.version === "number" &&
        data.version <= (latestVersionsRef.current[versionKey] ?? 0)
      ) {
        return;
      }
      if (typeof data.version === "number") {
        latestVersionsRef.current[versionKey] = data.version;
      }

      setLastEvent({
        payload: data.payload ?? {},
        type: data.type as CampaignEvent["type"],
        version: data.version,
      } as CampaignEvent);
    };

    const replayHistory = (publications: Awaited<ReturnType<typeof getHistory>>) => {
      sortRealtimeHistoryByVersion(publications)
        .forEach((publication) => processRealtimeMessage(publication.data));
    };

    const unsubscribeState = subscribeConnectionState(setConnectionState);
    const unsubscribeCampaign = subscribe(channel, {
      onSubscribed: () => {
        void getPresence(channel)
          .then((presence) => {
            if (active) {
              setPresenceClients(presence);
            }
          })
          .catch(() => {
            if (active) {
              setPresenceClients({});
            }
          });
        void getHistory(channel, 20)
          .then((publications) => {
            if (active) {
              replayHistory(publications);
            }
          })
          .catch(() => {});
      },
      onJoin: (member) => {
        setPresenceClients((current) => ({ ...current, [member.clientId]: member }));
      },
      onLeave: (member) => {
        setPresenceClients((current) => {
          const next = { ...current };
          delete next[member.clientId];
          return next;
        });
      },
      onPublication: (message) => {
        processRealtimeMessage(message);
      },
    });

    return () => {
      active = false;
      unsubscribeCampaign();
      unsubscribeState();
    };
  }, [campaignId]);

  return { lastEvent, connectionState, onlineUsers };
};
