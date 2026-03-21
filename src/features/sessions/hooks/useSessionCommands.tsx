import { useCallback, useEffect, useRef, useState } from "react";
import {
  type ConnectionState,
  subscribe,
  subscribeConnectionState,
} from "../../../shared/realtime/centrifugoClient";
import { sessionsRepo } from "../../../shared/api/sessionsRepo";
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
  const [shopOpen, setShopOpen] = useState(false);
  const [combatActive, setCombatActive] = useState(false);
  const latestVersionRef = useRef(0);

  useEffect(() => {
    setLastCommand(null);
    setSessionEndedAt(null);
    setShopOpen(false);
    setCombatActive(false);
    latestVersionRef.current = 0;
    if (!selectedSessionId) {
      setConnectionState("offline");
      setLastCommand(null);
      setSessionEndedAt(null);
      setShopOpen(false);
      setCombatActive(false);
      return;
    }

    const syncRuntime = () => {
      void sessionsRepo.getRuntime(selectedSessionId)
        .then((runtime) => {
          setShopOpen(runtime.shopOpen);
          setCombatActive(runtime.combatActive);
        })
        .catch(() => {
          setShopOpen(false);
          setCombatActive(false);
        });
    };
    syncRuntime();
    const runtimePoll = setInterval(syncRuntime, 10_000);

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
        if (data.type === "shop_opened") {
          setShopOpen(true);
          setLastCommand({
            command: "open_shop",
            data: data.payload,
            issuedBy: data.payload?.issuedBy,
            issuedAt: data.payload?.issuedAt,
          });
          return;
        }
        if (data.type === "shop_closed") {
          setShopOpen(false);
          setLastCommand({
            command: "close_shop",
            data: data.payload,
            issuedBy: data.payload?.issuedBy,
            issuedAt: data.payload?.issuedAt,
          });
          return;
        }
        if (data.type === "roll_requested") {
          setLastCommand({
            command: "request_roll",
            data: data.payload,
            issuedBy: data.payload?.issuedBy,
            issuedAt: data.payload?.issuedAt,
          });
          return;
        }
        if (data.type === "combat_started") {
          setCombatActive(true);
          return;
        }
        if (data.type === "combat_ended") {
          setCombatActive(false);
          return;
        }
        if (data.type === "gm_command" && data.payload) {
          if (data.payload.command === "open_shop") {
            setShopOpen(true);
          }
          if (data.payload.command === "close_shop") {
            setShopOpen(false);
          }
          setLastCommand({
            command: data.payload.command,
            data: data.payload.data,
            issuedBy: data.payload.issuedBy,
            issuedAt: data.payload.issuedAt,
          });
          return;
        }
        if (data.type === "session_closed" || data.type === "session_ended") {
          setShopOpen(false);
          setCombatActive(false);
          setLastCommand(null);
          setSessionEndedAt(data.payload?.endedAt ?? new Date().toISOString());
        }
      },
    });

    return () => {
      clearInterval(runtimePoll);
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

  return { lastCommand, clearCommand, connectionState, sessionEndedAt, clearSessionEnded, shopOpen, combatActive };
};
