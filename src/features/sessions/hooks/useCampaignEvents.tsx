import { useEffect, useRef, useState } from "react";
import type { ConnectionState } from "../../../shared/realtime/wsClient";
import { connectCampaign } from "../../../shared/realtime/wsClient";
import { useAuth } from "../../auth";

export type CampaignEvent = {
  type: "session_started" | "session_closed" | "session_resumed";
  payload: Record<string, unknown>;
};

export const useCampaignEvents = (campaignId?: string | null) => {
  const { token } = useAuth();
  const [connectionState, setConnectionState] = useState<ConnectionState>("offline");
  const [lastEvent, setLastEvent] = useState<CampaignEvent | null>(null);
  const clientRef = useRef<ReturnType<typeof connectCampaign> | null>(null);

  useEffect(() => {
    setLastEvent(null);
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
      if (!message || typeof message !== "object") {
        return;
      }
      const data = message as { type?: string; payload?: any };
      if (
        data.type === "session_started" ||
        data.type === "session_closed" ||
        data.type === "session_resumed"
      ) {
        setLastEvent({ type: data.type, payload: data.payload ?? {} });
      }
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

  return { lastEvent, connectionState };
};
