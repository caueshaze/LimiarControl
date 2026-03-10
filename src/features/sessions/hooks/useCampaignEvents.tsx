import { useEffect, useMemo, useRef, useState } from "react";
import type {
  ConnectionState,
  RealtimePresenceMember,
} from "../../../shared/realtime/centrifugoClient";
import {
  getPresence,
  subscribe,
  subscribeConnectionState,
} from "../../../shared/realtime/centrifugoClient";

export type CampaignEvent =
  | { type: "session_started"; payload: Record<string, unknown>; version?: number }
  | { type: "session_closed"; payload: Record<string, unknown>; version?: number }
  | { type: "session_resumed"; payload: Record<string, unknown>; version?: number }
  | {
      type: "session_lobby";
      payload: {
        campaignId: string;
        expectedPlayers: { userId: string; displayName: string }[];
        sessionId: string;
        title: string;
      };
      version?: number;
    }
  | {
      type: "player_joined_lobby";
      payload: {
        displayName: string;
        readyCount: number;
        sessionId: string;
        totalCount: number;
        userId: string;
      };
      version?: number;
    }
  | {
      type: "party_member_updated";
      payload: {
        campaignId: string;
        partyId: string;
        role: "GM" | "PLAYER";
        status: string;
        userId: string;
      };
      version?: number;
    }
  | {
      type: "session_state_updated";
      payload: {
        campaignId: string;
        partyId?: string | null;
        playerUserId: string;
        sessionId: string;
      };
      version?: number;
    };

const CAMPAIGN_EVENT_TYPES = new Set([
  "session_started",
  "session_closed",
  "session_resumed",
  "session_lobby",
  "player_joined_lobby",
  "party_member_updated",
  "session_state_updated",
]);

const getVersionKey = (
  campaignId: string | null | undefined,
  event: { payload?: Record<string, unknown>; type?: string },
) => {
  switch (event.type) {
    case "party_member_updated":
      return `${event.type}:${event.payload?.partyId ?? ""}:${event.payload?.userId ?? ""}`;
    case "session_state_updated":
      return `${event.type}:${event.payload?.sessionId ?? ""}:${event.payload?.playerUserId ?? ""}`;
    case "player_joined_lobby":
      return `${event.type}:${event.payload?.sessionId ?? ""}`;
    case "session_started":
    case "session_closed":
    case "session_resumed":
    case "session_lobby":
      return `${event.type}:${event.payload?.sessionId ?? campaignId ?? ""}`;
    default:
      return event.type ?? "unknown";
  }
};

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
        if (!message || typeof message !== "object") {
          return;
        }

        const data = message as {
          payload?: Record<string, unknown>;
          type?: string;
          version?: number;
        };
        if (!CAMPAIGN_EVENT_TYPES.has(data.type ?? "")) {
          return;
        }

        const versionKey = getVersionKey(campaignId, data);
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
