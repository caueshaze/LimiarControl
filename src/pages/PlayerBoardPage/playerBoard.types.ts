export type PendingRoll = {
  requestKey: string;
  expression: string;
  issuedBy?: string;
  reason?: string;
  mode?: "advantage" | "disadvantage" | null;
};

export const buildRollRequestKey = (payload: {
  expression: string;
  mode?: "advantage" | "disadvantage" | null;
  reason?: string | null;
  sessionId: string;
  targetUserId?: string | null;
  timestamp: string;
}) =>
  [
    payload.sessionId,
    payload.timestamp,
    payload.expression.trim(),
    payload.reason?.trim() ?? "",
    payload.mode ?? "",
    payload.targetUserId ?? "",
  ].join(":");

export const readHandledRollRequestKey = (sessionId: string | null | undefined) => {
  if (!sessionId || typeof window === "undefined") {
    return null;
  }
  return window.sessionStorage.getItem(`limiar:handledRollRequest:${sessionId}`);
};

export const writeHandledRollRequestKey = (
  sessionId: string | null | undefined,
  requestKey: string,
) => {
  if (!sessionId || typeof window === "undefined") {
    return;
  }
  window.sessionStorage.setItem(`limiar:handledRollRequest:${sessionId}`, requestKey);
};
