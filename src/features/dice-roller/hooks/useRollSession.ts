import { useCallback, useEffect, useRef, useState } from "react";
import { nanoid } from "nanoid";
import type { RollEvent, RollRequest } from "../../../entities/roll";
import { sessionsRepo } from "../../../shared/api/sessionsRepo";
import type { ConnectionState } from "../../../shared/realtime/wsClient";
import { connect } from "../../../shared/realtime/wsClient";
import { useSession } from "../../sessions";
import { useAuth } from "../../auth";

const MAX_EVENTS = 50;

type RollError = {
  requestId: string | null;
  message: string;
};

export const useRollSession = () => {
  const { selectedSessionId } = useSession();
  const { token } = useAuth();
  const [events, setEvents] = useState<RollEvent[]>([]);
  const [connectionState, setConnectionState] = useState<ConnectionState>("offline");
  const [lastError, setLastError] = useState<RollError | null>(null);
  const clientRef = useRef<ReturnType<typeof connect> | null>(null);

  const appendEvent = useCallback((event: RollEvent) => {
    setEvents((current) => {
      if (current.some((entry) => entry.id === event.id)) {
        return current;
      }
      return [event, ...current].slice(0, MAX_EVENTS);
    });
  }, []);

  useEffect(() => {
    if (!selectedSessionId || !token) {
      setEvents([]);
      setConnectionState("offline");
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
      if (data.type === "roll_created" && data.payload) {
        appendEvent(data.payload as RollEvent);
      } else if (data.type === "error" && data.payload) {
        setLastError({
          requestId: data.payload.requestId ?? null,
          message: data.payload.message ?? "Unknown error",
        });
      }
    });

    const unsubscribeState = client.onStateChange((state) => {
      setConnectionState(state);
      if (state === "connected") {
        client.send({
          type: "join",
          payload: {
            ready: true,
          },
        });
      }
    });

    return () => {
      unsubscribeMessage();
      unsubscribeState();
      client.close();
      clientRef.current = null;
    };
  }, [appendEvent, selectedSessionId, token]);

  useEffect(() => {
    if (!selectedSessionId) {
      return;
    }
    sessionsRepo
      .rolls(selectedSessionId, MAX_EVENTS)
      .then((data) => {
        if (Array.isArray(data)) {
          setEvents(data.slice(0, MAX_EVENTS));
        }
      })
      .catch((error: { message?: string }) => {
        setLastError({
          requestId: null,
          message: error?.message ?? "Failed to load roll history",
        });
      });
  }, [selectedSessionId]);

  const roll = (expression: string, label?: string) => {
    if (!selectedSessionId) {
      setLastError({ requestId: null, message: "No session selected" });
      return;
    }
    const client = clientRef.current;
    if (!client) {
      setLastError({ requestId: null, message: "Not connected" });
      return;
    }
    const payload: RollRequest = {
      requestId: nanoid(),
      label: label?.trim() || null,
      expression: expression.trim(),
    };
    const ok = client.send({ type: "roll", payload });
    if (!ok) {
      setLastError({ requestId: payload.requestId, message: "Connection unavailable" });
    }
  };

  return {
    events,
    connectionState,
    lastError,
    roll,
  };
};
