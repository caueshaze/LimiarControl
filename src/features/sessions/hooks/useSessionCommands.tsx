import { useCallback, useEffect, useRef, useState } from "react";
import {
  type ConnectionState,
  type RealtimeHistoryPublication,
  getHistory,
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
  const latestVersionsRef = useRef<Record<string, number>>({});

  const getVersionKey = useCallback((data: { type?: string; payload?: any }) => {
    switch (data.type) {
      case "shop_opened":
      case "shop_closed":
      case "roll_requested":
      case "combat_started":
      case "combat_ended":
      case "session_closed":
      case "session_ended":
        return `${data.type}:${String(data.payload?.sessionId ?? selectedSessionId ?? "")}`;
      case "gm_command":
        return `${data.type}:${String(data.payload?.command ?? "")}:${String(
          data.payload?.data?.sessionId ?? selectedSessionId ?? "",
        )}`;
      default:
        return String(data.type ?? "unknown");
    }
  }, [selectedSessionId]);

  useEffect(() => {
    setLastCommand(null);
    setSessionEndedAt(null);
    setShopOpen(false);
    setCombatActive(false);
    latestVersionsRef.current = {};
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
    const processRealtimeMessage = (message: unknown) => {
      if (!message || typeof message !== "object") {
        return;
      }
      const data = message as { type?: string; version?: number; payload?: any };
      const versionKey = getVersionKey(data);
      if (
        typeof data.version === "number" &&
        data.version <= (latestVersionsRef.current[versionKey] ?? 0)
      ) {
        return;
      }
      if (typeof data.version === "number") {
        latestVersionsRef.current[versionKey] = data.version;
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
    };

    const replayHistory = (publications: RealtimeHistoryPublication[]) => {
      [...publications]
        .sort((left, right) => {
          const leftVersion =
            typeof (left.data as { version?: unknown } | null | undefined)?.version === "number"
              ? ((left.data as { version: number }).version)
              : 0;
          const rightVersion =
            typeof (right.data as { version?: unknown } | null | undefined)?.version === "number"
              ? ((right.data as { version: number }).version)
              : 0;
          if (leftVersion !== rightVersion) {
            return leftVersion - rightVersion;
          }
          const leftOffset = left.offset ? Number(left.offset) : 0;
          const rightOffset = right.offset ? Number(right.offset) : 0;
          return leftOffset - rightOffset;
        })
        .forEach((publication) => processRealtimeMessage(publication.data));
    };

    const unsubscribeState = subscribeConnectionState(setConnectionState);
    const unsubscribeSession = subscribe(`session:${selectedSessionId}`, {
      onSubscribed: () => {
        syncRuntime();
        void getHistory(`session:${selectedSessionId}`, 20)
          .then((publications) => replayHistory(publications))
          .catch(() => {});
      },
      onPublication: (message) => {
        processRealtimeMessage(message);
      },
    });

    return () => {
      clearInterval(runtimePoll);
      unsubscribeSession();
      unsubscribeState();
    };
  }, [getVersionKey, selectedSessionId]);

  const clearCommand = useCallback(() => {
    setLastCommand(null);
  }, []);

  const clearSessionEnded = useCallback(() => {
    setSessionEndedAt(null);
  }, []);

  return { lastCommand, clearCommand, connectionState, sessionEndedAt, clearSessionEnded, shopOpen, combatActive };
};
