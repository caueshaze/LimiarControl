import type { ReactNode } from "react";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import {
  type RealtimeHistoryPublication,
  getHistory,
  subscribe,
  subscribeConnectionState,
} from "../../../shared/realtime/centrifugoClient";
import { sessionsRepo } from "../../../shared/api/sessionsRepo";
import { reduceSessionRuntimeMessage } from "./sessionRuntime.reducer";
import {
  createInitialSessionRuntimeState,
  type SessionCommand,
  type SessionRestState,
  type SessionRuntimeState,
} from "./sessionRuntime.types";

const SESSION_KEY = "limiar:selectedSessionId";

const readStoredSession = () => {
  if (typeof window === "undefined") {
    return null;
  }
  return window.sessionStorage.getItem(SESSION_KEY);
};

type SessionContextValue = {
  selectedSessionId: string | null;
  setSelectedSessionId: (sessionId: string | null) => void;
  clearSelectedSession: () => void;
  connectionState: SessionRuntimeState["connectionState"];
  lastCommand: SessionCommand | null;
  clearCommand: () => void;
  sessionEndedAt: string | null;
  clearSessionEnded: () => void;
  shopOpen: boolean;
  combatActive: boolean;
  combatUiActive: boolean;
  combatUiExpanded: boolean;
  combatModeVisible: boolean;
  toggleCombatUiExpanded: () => void;
  expandCombatUi: () => void;
  collapseCombatUi: () => void;
  restState: SessionRestState;
};

const SessionContext = createContext<SessionContextValue | null>(null);

const getVersionKey = (
  selectedSessionId: string | null,
  data: { type?: string; payload?: Record<string, unknown> },
) => {
  switch (data.type) {
    case "shop_opened":
    case "shop_closed":
    case "roll_requested":
    case "combat_started":
    case "combat_ended":
    case "rest_started":
    case "rest_ended":
    case "session_closed":
    case "session_ended":
      return `${data.type}:${String(data.payload?.sessionId ?? selectedSessionId ?? "")}`;
    case "gm_command":
      return `${data.type}:${String(data.payload?.command ?? "")}:${String(
        (data.payload?.data as { sessionId?: string } | undefined)?.sessionId ?? selectedSessionId ?? "",
      )}`;
    default:
      return String(data.type ?? "unknown");
  }
};

export const SessionProvider = ({ children }: { children: ReactNode }) => {
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(
    readStoredSession
  );
  const [runtime, setRuntime] = useState<SessionRuntimeState>(createInitialSessionRuntimeState);
  const [combatUiExpanded, setCombatUiExpanded] = useState(false);
  const latestVersionsRef = useRef<Record<string, number>>({});

  useEffect(() => {
    latestVersionsRef.current = {};
    setCombatUiExpanded(false);
    setRuntime(createInitialSessionRuntimeState());
    if (!selectedSessionId) {
      return;
    }

    const syncRuntime = () => {
      void sessionsRepo.getRuntime(selectedSessionId)
        .then((nextRuntime) => {
          setRuntime((current) => ({
            ...current,
            shopOpen: nextRuntime.shopOpen,
            combatActive: nextRuntime.combatActive,
            restState: nextRuntime.restState,
          }));
        })
        .catch(() => {
          setRuntime((current) => ({
            ...current,
            shopOpen: false,
            combatActive: false,
            restState: "exploration",
          }));
        });
    };

    const processRealtimeMessage = (message: unknown) => {
      if (!message || typeof message !== "object") {
        return;
      }
      const data = message as { type?: string; version?: number; payload?: Record<string, unknown> };
      const versionKey = getVersionKey(selectedSessionId, data);
      if (
        typeof data.version === "number" &&
        data.version <= (latestVersionsRef.current[versionKey] ?? 0)
      ) {
        return;
      }
      if (typeof data.version === "number") {
        latestVersionsRef.current[versionKey] = data.version;
      }
      setRuntime((current) => reduceSessionRuntimeMessage(current, data));
    };

    const replayHistory = (publications: RealtimeHistoryPublication[]) => {
      [...publications]
        .sort((left, right) => {
          const leftVersion =
            typeof (left.data as { version?: unknown } | null | undefined)?.version === "number"
              ? (left.data as { version: number }).version
              : 0;
          const rightVersion =
            typeof (right.data as { version?: unknown } | null | undefined)?.version === "number"
              ? (right.data as { version: number }).version
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

    syncRuntime();
    const runtimePoll = window.setInterval(syncRuntime, 10_000);
    const unsubscribeState = subscribeConnectionState((connectionState) => {
      setRuntime((current) => ({ ...current, connectionState }));
    });
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
      window.clearInterval(runtimePoll);
      unsubscribeSession();
      unsubscribeState();
    };
  }, [selectedSessionId]);

  useEffect(() => {
    if (!runtime.combatActive) {
      setCombatUiExpanded(false);
    }
  }, [runtime.combatActive]);

  const persistSelectedSessionId = useCallback((sessionId: string | null) => {
    setSelectedSessionId(sessionId);
    if (typeof window === "undefined") {
      return;
    }
    if (sessionId) {
      window.sessionStorage.setItem(SESSION_KEY, sessionId);
    } else {
      window.sessionStorage.removeItem(SESSION_KEY);
    }
  }, []);

  const value = useMemo(
    () => ({
      selectedSessionId,
      setSelectedSessionId: persistSelectedSessionId,
      clearSelectedSession: () => {
        persistSelectedSessionId(null);
      },
      connectionState: runtime.connectionState,
      lastCommand: runtime.lastCommand,
      clearCommand: () => {
        setRuntime((current) => ({ ...current, lastCommand: null }));
      },
      sessionEndedAt: runtime.sessionEndedAt,
      clearSessionEnded: () => {
        setRuntime((current) => ({ ...current, sessionEndedAt: null }));
      },
      shopOpen: runtime.shopOpen,
      combatActive: runtime.combatActive,
      combatUiActive: runtime.combatActive,
      combatUiExpanded,
      combatModeVisible: runtime.combatActive && !combatUiExpanded,
      toggleCombatUiExpanded: () => {
        setCombatUiExpanded((current) => !current);
      },
      expandCombatUi: () => {
        setCombatUiExpanded(true);
      },
      collapseCombatUi: () => {
        setCombatUiExpanded(false);
      },
      restState: runtime.restState,
    }),
    [combatUiExpanded, persistSelectedSessionId, runtime, selectedSessionId]
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
};

export const useSession = () => {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error("useSession must be used within a SessionProvider");
  }
  return context;
};
