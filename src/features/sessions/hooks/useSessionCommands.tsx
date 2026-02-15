import { useCallback, useEffect, useRef, useState } from "react";
import type { ConnectionState } from "../../../shared/realtime/wsClient";
import { connect } from "../../../shared/realtime/wsClient";
import { useAuth } from "../../auth";
import { useSession } from "./useSession";

export type SessionCommand = {
  command: "open_shop" | "close_shop" | "request_roll";
  data?: Record<string, unknown>;
  issuedBy?: string;
  issuedAt?: string;
};

export const useSessionCommands = () => {
  const { selectedSessionId } = useSession();
  const { token } = useAuth();
  const [connectionState, setConnectionState] = useState<ConnectionState>("offline");
  const [lastCommand, setLastCommand] = useState<SessionCommand | null>(null);
  const [sessionEndedAt, setSessionEndedAt] = useState<string | null>(null);
  const clientRef = useRef<ReturnType<typeof connect> | null>(null);

  useEffect(() => {
    setLastCommand(null);
    setSessionEndedAt(null);
    if (!selectedSessionId || !token) {
      setConnectionState("offline");
      setLastCommand(null);
      setSessionEndedAt(null);
      clientRef.current?.close();
      clientRef.current = null;
      return;
    }

    setConnectionState("reconnecting");
    const client = connect(selectedSessionId, token);
    clientRef.current = client;

    const unsubscribeMessage = client.onMessage((message) => {
      if (!message || typeof message !== "object") {
        return;
      }
      const data = message as { type?: string; payload?: any };
      if (data.type === "gm_command" && data.payload) {
        setLastCommand({
          command: data.payload.command,
          data: data.payload.data,
          issuedBy: data.payload.issuedBy,
          issuedAt: data.payload.issuedAt,
        });
        return;
      }
      if (data.type === "session_closed" || data.type === "session_ended") {
        setLastCommand(null);
        setSessionEndedAt(data.payload?.endedAt ?? new Date().toISOString());
        return;
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
  }, [selectedSessionId, token]);

  const clearCommand = useCallback(() => {
    setLastCommand(null);
  }, []);

  const clearSessionEnded = useCallback(() => {
    setSessionEndedAt(null);
  }, []);

  return { lastCommand, clearCommand, connectionState, sessionEndedAt, clearSessionEnded };
};
