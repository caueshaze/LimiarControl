import { useCallback, useEffect, useState } from "react";
import { partiesRepo, type PartyActiveSession } from "../../../shared/api/partiesRepo";

export const usePartyActiveSession = (partyId?: string | null) => {
  const [activeSession, setActiveSession] = useState<PartyActiveSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    if (!partyId) {
      setActiveSession(null);
      setError(null);
      return Promise.resolve(null);
    }
    setLoading(true);
    return partiesRepo
      .getPartyActiveSession(partyId)
      .then((data) => {
        setActiveSession(data);
        setError(null);
        return data;
      })
      .catch((err: { status?: number; message?: string }) => {
        if (err?.status === 404) {
          setActiveSession(null);
          setError(null);
          return null;
        }
        setActiveSession(null);
        setError(err?.message ?? "Failed to load active session");
        return null;
      })
      .finally(() => setLoading(false));
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
