import { useCallback, useEffect, useRef, useState } from "react";
import { sessionsRepo, type RollRequestActivityEvent } from "../../shared/api/sessionsRepo";
import type { LocaleKey } from "../../shared/i18n";
import type { ToastState } from "../../shared/ui/Toast";
import {
  buildRollRequestKey,
  type PendingRoll,
  readHandledRollRequestKey,
  writeHandledRollRequestKey,
} from "./playerBoard.types";

type SessionCommandLike = {
  command: string;
  data?: Record<string, unknown> | null;
  issuedAt?: string;
  issuedBy?: string;
};

type CampaignEventLike = {
  type: string;
  payload: Record<string, unknown>;
};

type Props = {
  activeSessionId: string | null;
  clearCommand: () => void;
  lastCommand: SessionCommandLike | null;
  lastEvent: CampaignEventLike | null;
  roll: (
    expression: string,
    label?: string,
    mode?: "advantage" | "disadvantage" | null,
  ) => void;
  showToast: (toast: ToastState) => void;
  t: (key: LocaleKey) => string;
  userId?: string | null;
};

export const usePlayerBoardRollRequests = ({
  activeSessionId,
  clearCommand,
  lastCommand,
  lastEvent,
  roll,
  showToast,
  t,
  userId = null,
}: Props) => {
  const [pendingRoll, setPendingRoll] = useState<PendingRoll | null>(null);
  const [rollMode, setRollMode] = useState<"virtual" | "manual" | null>(null);
  const [manualValue, setManualValue] = useState("");
  const handledRollRequestKeyRef = useRef<string | null>(readHandledRollRequestKey(activeSessionId));
  const shownRollRequestKeyRef = useRef<string | null>(null);

  useEffect(() => {
    handledRollRequestKeyRef.current = readHandledRollRequestKey(activeSessionId);
    shownRollRequestKeyRef.current = null;
  }, [activeSessionId]);

  const showRollPrompt = useCallback((nextRoll: PendingRoll) => {
    shownRollRequestKeyRef.current = nextRoll.requestKey;
    setPendingRoll(nextRoll);
    showToast({
      variant: "info",
      title: t("playerBoard.rollRequest"),
      description: nextRoll.reason ?? nextRoll.expression.toUpperCase(),
      duration: 3000,
    });
    setRollMode(null);
    setManualValue("");
  }, [showToast, t]);

  useEffect(() => {
    if (!lastCommand || lastCommand.command !== "request_roll") {
      return;
    }

    const targetUserId = lastCommand.data?.targetUserId as string | undefined;
    if (targetUserId && targetUserId !== userId) {
      return;
    }
    const expression = String(lastCommand.data?.expression ?? "d20");
    const reason = lastCommand.data?.reason as string | undefined;
    const mode = (lastCommand.data?.mode ?? null) as "advantage" | "disadvantage" | null;
    const requestKey = buildRollRequestKey({
      expression,
      mode,
      reason,
      sessionId: String(lastCommand.data?.sessionId ?? activeSessionId ?? ""),
      targetUserId: targetUserId ?? null,
      timestamp: String(lastCommand.issuedAt ?? new Date().toISOString()),
    });
    if (requestKey === handledRollRequestKeyRef.current || requestKey === shownRollRequestKeyRef.current) {
      return;
    }
    showRollPrompt({ requestKey, expression, issuedBy: lastCommand.issuedBy, reason, mode });
  }, [activeSessionId, lastCommand, showRollPrompt, userId]);

  useEffect(() => {
    if (!lastEvent || lastEvent.type !== "roll_requested") {
      return;
    }

    const targetUserId =
      typeof lastEvent.payload.targetUserId === "string" ? lastEvent.payload.targetUserId : null;
    if (targetUserId && targetUserId !== userId) {
      return;
    }
    const expression = String(lastEvent.payload.expression ?? "d20");
    const reason =
      typeof lastEvent.payload.reason === "string" ? lastEvent.payload.reason : undefined;
    const mode =
      lastEvent.payload.mode === "advantage" || lastEvent.payload.mode === "disadvantage"
        ? lastEvent.payload.mode
        : null;
    const requestKey = buildRollRequestKey({
      expression,
      mode,
      reason,
      sessionId: String(lastEvent.payload.sessionId ?? activeSessionId ?? ""),
      targetUserId,
      timestamp: String(lastEvent.payload.issuedAt ?? ""),
    });
    if (requestKey === handledRollRequestKeyRef.current || requestKey === shownRollRequestKeyRef.current) {
      return;
    }
    showRollPrompt({
      requestKey,
      expression,
      issuedBy: typeof lastEvent.payload.issuedBy === "string" ? lastEvent.payload.issuedBy : undefined,
      reason,
      mode,
    });
  }, [activeSessionId, lastEvent, showRollPrompt, userId]);

  const syncLatestRollRequest = useCallback(async () => {
    if (!activeSessionId) {
      return;
    }

    try {
      const activity = await sessionsRepo.getActivity(activeSessionId);
      const latestRequest = [...activity]
        .reverse()
        .find((entry): entry is RollRequestActivityEvent => {
          if (entry.type !== "roll_request") {
            return false;
          }
          return !entry.targetUserId || entry.targetUserId === userId;
        });

      if (!latestRequest) {
        return;
      }

      const requestKey = buildRollRequestKey({
        expression: latestRequest.expression,
        mode: latestRequest.mode ?? null,
        reason: latestRequest.reason ?? undefined,
        sessionId: activeSessionId,
        targetUserId: latestRequest.targetUserId ?? null,
        timestamp: latestRequest.timestamp,
      });

      if (requestKey === handledRollRequestKeyRef.current || requestKey === shownRollRequestKeyRef.current) {
        return;
      }

      showRollPrompt({
        requestKey,
        expression: latestRequest.expression,
        issuedBy: latestRequest.displayName ?? undefined,
        reason: latestRequest.reason ?? undefined,
        mode: latestRequest.mode ?? null,
      });
    } catch {
      // Ignore fallback polling errors; realtime remains the primary path.
    }
  }, [activeSessionId, showRollPrompt, userId]);

  useEffect(() => {
    if (!activeSessionId || !userId) {
      return;
    }

    void syncLatestRollRequest();
    const intervalId = window.setInterval(() => {
      void syncLatestRollRequest();
    }, 5000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [activeSessionId, syncLatestRollRequest, userId]);

  const handleRoll = useCallback(() => {
    if (!pendingRoll) {
      return;
    }
    handledRollRequestKeyRef.current = pendingRoll.requestKey;
    writeHandledRollRequestKey(activeSessionId, pendingRoll.requestKey);
    roll(pendingRoll.expression, pendingRoll.reason, pendingRoll.mode);
    setPendingRoll(null);
    clearCommand();
  }, [activeSessionId, clearCommand, pendingRoll, roll]);

  const handleManualRoll = useCallback(async () => {
    if (!activeSessionId || !pendingRoll || !manualValue) {
      return;
    }
    await sessionsRepo.manualRoll(activeSessionId, {
      expression: pendingRoll.expression,
      result: Number(manualValue),
      label: pendingRoll.reason ?? null,
    });
    handledRollRequestKeyRef.current = pendingRoll.requestKey;
    writeHandledRollRequestKey(activeSessionId, pendingRoll.requestKey);
    setPendingRoll(null);
    setRollMode(null);
    setManualValue("");
    clearCommand();
  }, [activeSessionId, clearCommand, manualValue, pendingRoll]);

  const clearPendingRoll = useCallback(() => {
    setPendingRoll(null);
    setRollMode(null);
    setManualValue("");
  }, []);

  return {
    clearPendingRoll,
    handleManualRoll,
    handleRoll,
    manualValue,
    pendingRoll,
    rollMode,
    setManualValue,
    setRollMode,
  };
};
