import { useCallback, useEffect, useState } from "react";
import { sessionsRepo, type ActiveSession } from "../../../shared/api/sessionsRepo";
import { useCampaigns } from "../../campaign-select";

export const useActiveSession = (campaignId?: string | null) => {
  const { selectedCampaignId } = useCampaigns();
  const effectiveCampaignId = campaignId ?? selectedCampaignId ?? null;
  const [activeSession, setActiveSession] = useState<ActiveSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    if (!effectiveCampaignId) {
      setActiveSession(null);
      setError(null);
      return Promise.resolve(null);
    }
    setLoading(true);
    return sessionsRepo
      .getActive(effectiveCampaignId)
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
  }, [effectiveCampaignId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const activate = useCallback(
    (title: string) => {
      if (!effectiveCampaignId) {
        return Promise.resolve(null);
      }
      return sessionsRepo
        .activate(effectiveCampaignId, { title })
        .then((data) => {
          setActiveSession(data);
          setError(null);
          return data;
        })
        .catch((err: { message?: string }) => {
          setError(err?.message ?? "Failed to activate session");
          return null;
        });
    },
    [effectiveCampaignId]
  );

  const endSession = useCallback(() => {
    if (!activeSession?.id) return Promise.resolve(null);
    return sessionsRepo
      .end(activeSession.id)
      .then(() => {
        setActiveSession(null);
        setError(null);
        return true;
      })
      .catch((err: { message?: string }) => {
        setError(err?.message ?? "Failed to end session");
        return false;
      });
  }, [activeSession?.id]);

  return {
    activeSession,
    loading,
    error,
    refresh,
    activate,
    endSession,
  };
};
