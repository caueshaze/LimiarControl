import type { NavigateFunction } from "react-router-dom";
import type { LocaleKey } from "../../shared/i18n";
import type { ToastState } from "../../shared/ui/Toast";

export type ActiveSessionLike = {
  id: string;
};

export type SessionCommandLike = {
  command: string;
  data?: Record<string, unknown> | null;
  issuedAt?: string;
  issuedBy?: string;
};

export type CampaignEventLike = {
  type: string;
  payload: Record<string, unknown>;
  version?: number;
};

export type UsePlayerBoardRealtimeProps = {
  activeSession: ActiveSessionLike | null;
  clearCommand: () => void;
  clearSessionEnded: () => void;
  effectiveCampaignId: string | null;
  lastCommand: SessionCommandLike | null;
  lastEvent: CampaignEventLike | null;
  navigate: NavigateFunction;
  partyId: string | undefined;
  refresh: () => Promise<unknown>;
  refreshInventoryData: () => Promise<void>;
  roll: (
    expression: string,
    label?: string,
    mode?: "advantage" | "disadvantage" | null,
  ) => void;
  selectedCampaignId: string | null;
  sessionEndedAt: string | null;
  setSelectedCampaignLocal: (campaignId: string) => void;
  setSelectedSessionId: (sessionId: string | null) => void;
  showToast: (toast: ToastState) => void;
  shopAvailable: boolean;
  t: (key: LocaleKey) => string;
  userId?: string | null;
};
