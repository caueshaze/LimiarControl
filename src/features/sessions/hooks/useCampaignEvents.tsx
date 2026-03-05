import { useEffect, useRef, useState } from "react";
import type { ConnectionState } from "../../../shared/realtime/wsClient";
import { connectCampaign } from "../../../shared/realtime/wsClient";
import { useAuth } from "../../auth";

export type CampaignEvent =
  | { type: "session_started"; payload: Record<string, unknown> }
  | { type: "session_closed"; payload: Record<string, unknown> }
  | { type: "session_resumed"; payload: Record<string, unknown> }
  | { type: "session_lobby"; payload: { sessionId: string; campaignId: string; title: string; expectedPlayers: { userId: string; displayName: string }[] } }
  | { type: "player_joined_lobby"; payload: { sessionId: string; userId: string; displayName: string; readyCount: number; totalCount: number } }
  | { type: "user_online"; payload: { userId: string; displayName: string } }
  | { type: "user_offline"; payload: { userId: string; displayName: string } };

const SESSION_EVENT_TYPES = new Set([
  "session_started",
  "session_closed",
  "session_resumed",
  "session_lobby",
  "player_joined_lobby",
  "user_online",
  "user_offline",
]);

export const useCampaignEvents = (campaignId?: string | null) => {
  const { token } = useAuth();
  const [connectionState, setConnectionState] = useState<ConnectionState>("offline");
  const [lastEvent, setLastEvent] = useState<CampaignEvent | null>(null);
  const [onlineUsers, setOnlineUsers] = useState<Record<string, string>>({});
  const clientRef = useRef<ReturnType<typeof connectCampaign> | null>(null);

  useEffect(() => {
    setLastEvent(null);
    setOnlineUsers({});
    if (!campaignId || !token) {
      setConnectionState("offline");
      clientRef.current?.close();
      clientRef.current = null;
      return;
    }
    setConnectionState("reconnecting");
    const client = connectCampaign(campaignId, token);
    clientRef.current = client;

    const unsubscribeMessage = client.onMessage((message) => {
      if (!message || typeof message !== "object") return;
      const data = message as { type?: string; payload?: any };

      if (data.type === "connected" && data.payload?.onlineUsers) {
        setOnlineUsers(data.payload.onlineUsers as Record<string, string>);
        return;
      }

      if (!SESSION_EVENT_TYPES.has(data.type ?? "")) return;

      if (data.type === "user_online") {
        setOnlineUsers(prev => ({ ...prev, [data.payload.userId]: data.payload.displayName }));
      } else if (data.type === "user_offline") {
        setOnlineUsers(prev => {
          const next = { ...prev };
          delete next[data.payload.userId];
          return next;
        });
      }

      setLastEvent({ type: data.type as CampaignEvent["type"], payload: data.payload ?? {} } as CampaignEvent);
    });
    const unsubscribeState = client.onStateChange((state) => {
      setConnectionState(state);
    });

    return () => {
      unsubscribeMessage();
      unsubscribeState();
      client.close();
      clientRef.current = null;
    };
  }, [campaignId, token]);

  return { lastEvent, connectionState, onlineUsers };
};
