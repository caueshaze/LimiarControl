import { useCallback, useEffect, useRef, useState } from "react";
import {
  type ConnectionState,
  subscribe,
  subscribeConnectionState,
} from "../../../shared/realtime/centrifugoClient";
import { useSession } from "./useSession";

export type SessionCommand = {
  command: "open_shop" | "close_shop" | "request_roll";
  data?: Record<string, unknown>;
  issuedBy?: string;
  issuedAt?: string;
};

export const useSessionCommands = () => {
  const { selectedSessionId } = useSession();
  const [connectionState, setConnectionState] = useState<ConnectionState>("offline");
  const [lastCommand, setLastCommand] = useState<SessionCommand | null>(null);
  const [sessionEndedAt, setSessionEndedAt] = useState<string | null>(null);
  const latestVersionRef = useRef(0);

  useEffect(() => {
    setLastCommand(null);
    setSessionEndedAt(null);
    latestVersionRef.current = 0;
    if (!selectedSessionId) {
      setConnectionState("offline");
      setLastCommand(null);
      setSessionEndedAt(null);
      return;
    }

    const unsubscribeState = subscribeConnectionState(setConnectionState);
    const unsubscribeSession = subscribe(`session:${selectedSessionId}`, {
      onPublication: (message) => {
        if (!message || typeof message !== "object") {
          return;
        }
        const data = message as { type?: string; version?: number; payload?: any };
        if (
          typeof data.version === "number" &&
          data.version <= latestVersionRef.current
        ) {
          return;
        }
        if (typeof data.version === "number") {
          latestVersionRef.current = data.version;
        }
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
        }
      },
    });

    return () => {
      unsubscribeSession();
      unsubscribeState();
    };
  }, [selectedSessionId]);

  const clearCommand = useCallback(() => {
    setLastCommand(null);
  }, []);

  const clearSessionEnded = useCallback(() => {
    setSessionEndedAt(null);
  }, []);

  return { lastCommand, clearCommand, connectionState, sessionEndedAt, clearSessionEnded };
};
