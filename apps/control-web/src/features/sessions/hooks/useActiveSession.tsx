import { useCallback, useEffect, useRef, useState } from "react";
import { sessionsRepo } from "../../../shared/api/sessionsRepo";
import { useCampaigns } from "../../campaign-select";
import {
  beginActiveSessionRefresh,
  createInitialActiveSessionQueryState,
  resolveActiveSessionView,
} from "./useActiveSession.state";

export const useActiveSession = (campaignId?: string | null) => {
  const { selectedCampaignId } = useCampaigns();
  const effectiveCampaignId = campaignId ?? selectedCampaignId ?? null;
  const [state, setState] = useState(() =>
    createInitialActiveSessionQueryState(effectiveCampaignId),
  );
  const requestIdRef = useRef(0);

  const view = resolveActiveSessionView(state, effectiveCampaignId);

  const refresh = useCallback(() => {
    if (!effectiveCampaignId) {
      requestIdRef.current += 1;
      setState(createInitialActiveSessionQueryState(null));
      return Promise.resolve(null);
    }
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    setState((current) => beginActiveSessionRefresh(current, effectiveCampaignId));
    return sessionsRepo
      .getActive(effectiveCampaignId)
      .then((data) => {
        if (requestIdRef.current !== requestId) {
          return null;
        }
        setState({
          campaignId: effectiveCampaignId,
          activeSession: data,
          loading: false,
          error: null,
        });
        return data;
      })
      .catch((err: { status?: number; message?: string }) => {
        if (requestIdRef.current !== requestId) {
          return null;
        }
        if (err?.status === 404) {
          setState({
            campaignId: effectiveCampaignId,
            activeSession: null,
            loading: false,
            error: null,
          });
          return null;
        }
        setState({
          campaignId: effectiveCampaignId,
          activeSession: null,
          loading: false,
          error: err?.message ?? "Failed to load active session",
        });
        return null;
      });
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
          setState({
            campaignId: effectiveCampaignId,
            activeSession: data,
            loading: false,
            error: null,
          });
          return data;
        })
        .catch((err: { message?: string }) => {
          setState((current) => ({
            ...current,
            error: err?.message ?? "Failed to activate session",
          }));
          throw err; // re-throw so callers can inspect the full error
        });
    },
    [effectiveCampaignId]
  );

  const endSession = useCallback(() => {
    if (!view.activeSession?.id) return Promise.resolve(null);
    return sessionsRepo
      .end(view.activeSession.id)
      .then(() => {
        setState((current) => ({
          ...current,
          activeSession: null,
          error: null,
        }));
        return true;
      })
      .catch((err: { message?: string }) => {
        setState((current) => ({
          ...current,
          error: err?.message ?? "Failed to end session",
        }));
        return false;
      });
  }, [view.activeSession?.id]);

  return {
    activeSession: view.activeSession,
    loading: view.loading,
    error: view.error,
    refresh,
    activate,
    endSession,
  };
};
