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
  | {
      type: "session_started";
      payload: {
        campaignId: string;
        partyId?: string | null;
        sessionId: string;
        startedAt: string;
        title: string;
      };
      version?: number;
    }
  | { type: "session_closed"; payload: Record<string, unknown>; version?: number }
  | { type: "session_resumed"; payload: Record<string, unknown>; version?: number }
  | {
      type: "session_lobby";
      payload: {
        campaignId: string;
        partyId?: string | null;
        expectedPlayers: { userId: string; displayName: string }[];
        readyUserIds?: string[];
        readyCount?: number;
        totalCount?: number;
        sessionId: string;
        title: string;
      };
      version?: number;
    }
  | {
      type: "player_joined_lobby";
      payload: {
        displayName: string;
        partyId?: string | null;
        readyCount: number;
        readyUserIds?: string[];
        sessionId: string;
        totalCount: number;
        userId: string;
      };
      version?: number;
    }
  | {
      type: "shop_opened" | "shop_closed";
      payload: {
        campaignId: string;
        partyId?: string | null;
        sessionId: string;
        issuedAt?: string;
        issuedBy?: string;
        shopOpen?: boolean;
      };
      version?: number;
    }
  | {
      type: "combat_started" | "combat_ended";
      payload: {
        campaignId: string;
        partyId?: string | null;
        sessionId: string;
        issuedAt?: string;
        issuedBy?: string;
        combatActive?: boolean;
        note?: string;
      };
      version?: number;
    }
  | {
      type: "roll_requested";
      payload: {
        campaignId: string;
        expression: string;
        issuedAt?: string;
        issuedBy?: string;
        mode?: "advantage" | "disadvantage" | null;
        partyId?: string | null;
        reason?: string;
        sessionId: string;
        targetUserId?: string | null;
      };
      version?: number;
    }
  | {
      type: "dice_rolled";
      payload: {
        campaignId: string;
        partyId?: string | null;
        sessionId: string;
        userId?: string | null;
      };
      version?: number;
    }
  | {
      type: "shop_purchase_created";
      payload: {
        campaignId: string;
        itemId: string;
        itemName: string;
        partyId?: string | null;
        quantity: number;
        sessionId: string;
        userId?: string | null;
      };
      version?: number;
    }
  | {
      type: "shop_sale_created";
      payload: {
        campaignId: string;
        itemId: string;
        itemName: string;
        partyId?: string | null;
        quantity: number;
        refundLabel?: string;
        sessionId: string;
        userId?: string | null;
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
    }
  | {
      type: "gm_granted_currency";
      payload: {
        campaignId: string;
        partyId?: string | null;
        playerUserId: string;
        sessionId: string;
        currentCurrency?: {
          cp?: number;
          sp?: number;
          ep?: number;
          gp?: number;
          pp?: number;
        };
        grantedCurrency?: {
          cp?: number;
          sp?: number;
          ep?: number;
          gp?: number;
          pp?: number;
        };
      };
      version?: number;
    }
  | {
      type: "gm_granted_item";
      payload: {
        campaignId: string;
        partyId?: string | null;
        playerUserId: string;
        sessionId: string;
        itemId: string;
        itemName: string;
        quantity: number;
        inventoryItemId?: string | null;
      };
      version?: number;
    }
  | {
      type: "entity_revealed" | "entity_hidden";
      payload: {
        sessionId: string;
        campaignId: string;
        partyId?: string | null;
        sessionEntityId: string;
        campaignEntityId: string;
        visibleToPlayers: boolean;
        label?: string | null;
        currentHp?: number | null;
        entityName?: string | null;
        entityCategory?: string | null;
        maxHp?: number | null;
      };
      version?: number;
    }
  | {
      type: "entity_hp_updated";
      payload: {
        sessionId: string;
        campaignId: string;
        partyId?: string | null;
        sessionEntityId: string;
        campaignEntityId: string;
        visibleToPlayers: boolean;
        label?: string | null;
        currentHp?: number | null;
        entityName?: string | null;
        entityCategory?: string | null;
        maxHp?: number | null;
        previousHp?: number | null;
        hpDelta?: number | null;
      };
      version?: number;
    }
  | {
      type: "session_entity_added" | "session_entity_removed";
      payload: {
        sessionId: string;
        campaignId: string;
        partyId?: string | null;
        sessionEntityId: string;
        campaignEntityId: string;
        visibleToPlayers?: boolean;
        label?: string | null;
        currentHp?: number | null;
        entityName?: string | null;
        entityCategory?: string | null;
        maxHp?: number | null;
      };
      version?: number;
    };

const CAMPAIGN_EVENT_TYPES = new Set([
  "session_started",
  "session_closed",
  "session_resumed",
  "session_lobby",
  "player_joined_lobby",
  "shop_opened",
  "shop_closed",
  "combat_started",
  "combat_ended",
  "roll_requested",
  "dice_rolled",
  "shop_purchase_created",
  "shop_sale_created",
  "party_member_updated",
  "session_state_updated",
  "gm_granted_currency",
  "gm_granted_item",
  "entity_revealed",
  "entity_hidden",
  "entity_hp_updated",
  "session_entity_added",
  "session_entity_removed",
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
    case "gm_granted_currency":
    case "gm_granted_item":
      return `${event.type}:${event.payload?.sessionId ?? ""}:${event.payload?.playerUserId ?? ""}`;
    case "player_joined_lobby":
      return `${event.type}:${event.payload?.sessionId ?? ""}:${event.payload?.userId ?? ""}`;
    case "session_started":
    case "session_closed":
    case "session_resumed":
    case "session_lobby":
    case "shop_opened":
    case "shop_closed":
    case "combat_started":
    case "combat_ended":
    case "roll_requested":
    case "dice_rolled":
    case "shop_purchase_created":
    case "shop_sale_created":
      return `${event.type}:${event.payload?.sessionId ?? campaignId ?? ""}`;
    case "entity_revealed":
    case "entity_hidden":
    case "entity_hp_updated":
    case "session_entity_added":
    case "session_entity_removed":
      return `${event.type}:${event.payload?.sessionId ?? ""}:${event.payload?.sessionEntityId ?? ""}`;
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
