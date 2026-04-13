import type { ConnectionState } from "../../../shared/realtime/centrifugoClient";

export type SessionCommand = {
  command:
    | "open_shop"
    | "close_shop"
    | "request_roll"
    | "start_short_rest"
    | "start_long_rest"
    | "end_rest";
  data?: Record<string, unknown>;
  issuedBy?: string;
  issuedAt?: string;
};

export type SessionRestState = "exploration" | "short_rest" | "long_rest";

export type SessionRuntimeState = {
  connectionState: ConnectionState;
  lastCommand: SessionCommand | null;
  sessionEndedAt: string | null;
  shopOpen: boolean;
  combatActive: boolean;
  restState: SessionRestState;
};

export const createInitialSessionRuntimeState = (): SessionRuntimeState => ({
  connectionState: "offline",
  lastCommand: null,
  sessionEndedAt: null,
  shopOpen: false,
  combatActive: false,
  restState: "exploration",
});
