import type { ActiveSession } from "../../../shared/api/sessionsRepo";

export type ActiveSessionQueryState = {
  campaignId: string | null;
  activeSession: ActiveSession | null;
  loading: boolean;
  error: string | null;
};

export const createInitialActiveSessionQueryState = (
  campaignId: string | null,
): ActiveSessionQueryState => ({
  campaignId,
  activeSession: null,
  loading: Boolean(campaignId),
  error: null,
});

export const beginActiveSessionRefresh = (
  current: ActiveSessionQueryState,
  campaignId: string,
): ActiveSessionQueryState => ({
  campaignId,
  activeSession: current.campaignId === campaignId ? current.activeSession : null,
  loading: true,
  error: null,
});

export const resolveActiveSessionView = (
  current: ActiveSessionQueryState,
  campaignId: string | null,
) => ({
  activeSession: current.campaignId === campaignId ? current.activeSession : null,
  loading: current.loading || (Boolean(campaignId) && current.campaignId !== campaignId),
  error: current.campaignId === campaignId ? current.error : null,
});
