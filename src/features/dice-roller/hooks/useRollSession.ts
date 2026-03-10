import { useCallback, useEffect, useState } from "react";
import type { RollEvent, RollRequest } from "../../../entities/roll";
import { sessionsRepo } from "../../../shared/api/sessionsRepo";
import {
  type ConnectionState,
  subscribe,
  subscribeConnectionState,
} from "../../../shared/realtime/centrifugoClient";
import { useSession } from "../../sessions";

const MAX_EVENTS = 50;

type RollError = {
  requestId: string | null;
  message: string;
};

export const useRollSession = () => {
  const { selectedSessionId } = useSession();
  const [events, setEvents] = useState<RollEvent[]>([]);
  const [connectionState, setConnectionState] = useState<ConnectionState>("offline");
  const [lastError, setLastError] = useState<RollError | null>(null);

  const appendEvent = useCallback((event: RollEvent) => {
    setEvents((current) => {
      if (current.some((entry) => entry.id === event.id)) {
        return current;
      }
      return [event, ...current].slice(0, MAX_EVENTS);
    });
  }, []);

  useEffect(() => {
    setLastError(null);
    if (!selectedSessionId) {
      setEvents([]);
      setConnectionState("offline");
      return;
    }

    const unsubscribeState = subscribeConnectionState(setConnectionState);
    const unsubscribeSession = subscribe(`session:${selectedSessionId}`, {
      onPublication: (message) => {
        if (!message || typeof message !== "object") {
          return;
        }
        const data = message as { type?: string; payload?: unknown };
        if (data.type === "roll_created" && data.payload) {
          appendEvent(data.payload as RollEvent);
        }
      },
    });

    return () => {
      unsubscribeSession();
      unsubscribeState();
    };
  }, [appendEvent, selectedSessionId]);

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

  const roll = useCallback(async (
    expression: string,
    label?: string,
    advantage?: "advantage" | "disadvantage" | null,
  ) => {
    if (!selectedSessionId) {
      setLastError({ requestId: null, message: "No session selected" });
      return;
    }
    const payload: RollRequest = {
      label: label?.trim() || null,
      expression: expression.trim(),
      advantage: advantage ?? null,
    };
    try {
      const created = await sessionsRepo.submitRoll(selectedSessionId, payload);
      appendEvent(created);
      setLastError(null);
    } catch (error) {
      setLastError({
        requestId: null,
        message: (error as { message?: string }).message ?? "Failed to submit roll",
      });
    }
  }, [appendEvent, selectedSessionId]);

  return {
    events,
    connectionState,
    lastError,
    roll,
  };
};
