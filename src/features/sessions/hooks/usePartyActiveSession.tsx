import { useCallback, useEffect, useRef, useState } from "react";
import { partiesRepo, type PartyActiveSession } from "../../../shared/api/partiesRepo";

export const usePartyActiveSession = (partyId?: string | null) => {
  const [activeSession, setActiveSession] = useState<PartyActiveSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestIdRef = useRef(0);

  const refresh = useCallback(() => {
    if (!partyId) {
      requestIdRef.current += 1;
      setActiveSession(null);
      setError(null);
      setLoading(false);
      return Promise.resolve(null);
    }
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    setLoading(true);
    return partiesRepo
      .getPartyActiveSession(partyId)
      .then((data) => {
        if (requestIdRef.current !== requestId) {
          return null;
        }
        setActiveSession(data);
        setError(null);
        return data;
      })
      .catch((err: { status?: number; message?: string }) => {
        if (requestIdRef.current !== requestId) {
          return null;
        }
        if (err?.status === 404) {
          setActiveSession(null);
          setError(null);
          return null;
        }
        setActiveSession(null);
        setError(err?.message ?? "Failed to load active session");
        return null;
      })
      .finally(() => {
        if (requestIdRef.current === requestId) {
          setLoading(false);
        }
      });
  }, [partyId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return {
    activeSession,
    loading,
    error,
    refresh,
  };
};
