import type { ReactNode } from "react";
import { createContext, useContext, useMemo, useState } from "react";

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
};

const SessionContext = createContext<SessionContextValue | null>(null);

export const SessionProvider = ({ children }: { children: ReactNode }) => {
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(
    readStoredSession
  );

  const value = useMemo(
    () => ({
      selectedSessionId,
      setSelectedSessionId: (sessionId: string | null) => {
        setSelectedSessionId(sessionId);
        if (typeof window === "undefined") {
          return;
        }
        if (sessionId) {
          window.sessionStorage.setItem(SESSION_KEY, sessionId);
        } else {
          window.sessionStorage.removeItem(SESSION_KEY);
        }
      },
      clearSelectedSession: () => {
        setSelectedSessionId(null);
        if (typeof window === "undefined") {
          return;
        }
        window.sessionStorage.removeItem(SESSION_KEY);
      },
    }),
    [selectedSessionId]
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
