import { useCallback, useEffect, useRef, useState } from "react";
import {
  sessionsRepo,
  type ActivityEvent,
  type RollRequestActivityEvent,
  type RollResolvedActivityEvent,
} from "../../shared/api/sessionsRepo";
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

  const markRequestHandled = useCallback((requestKey: string) => {
    handledRollRequestKeyRef.current = requestKey;
    writeHandledRollRequestKey(activeSessionId, requestKey);
    clearCommand();
  }, [activeSessionId, clearCommand]);

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

  const matchesResolvedRoll = useCallback((
    request: RollRequestActivityEvent,
    resolved: RollResolvedActivityEvent,
  ) => {
    if (request.rollType && resolved.rollType !== request.rollType) {
      return false;
    }
    if ((request.ability ?? null) !== (resolved.ability ?? null)) {
      return false;
    }
    if ((request.skill ?? null) !== (resolved.skill ?? null)) {
      return false;
    }
    const requestTime = Date.parse(request.timestamp);
    const resolvedTime = Date.parse(resolved.timestamp);
    if (Number.isFinite(requestTime) && Number.isFinite(resolvedTime) && resolvedTime < requestTime) {
      return false;
    }
    if (userId && resolved.userId !== userId) {
      return false;
    }
    return true;
  }, [userId]);

  const isActivityRequestAlreadyResolved = useCallback((
    activity: ActivityEvent[],
    request: RollRequestActivityEvent,
  ) => {
    if (!request.rollType) {
      return false;
    }

    return activity.some((entry): boolean => {
      if (entry.type !== "roll_resolved") {
        return false;
      }
      return matchesResolvedRoll(request, entry);
    });
  }, [matchesResolvedRoll]);

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
    const rollType = (lastCommand.data?.rollType as string | undefined) ?? null;
    const ability = (lastCommand.data?.ability as string | undefined) ?? null;
    const skill = (lastCommand.data?.skill as string | undefined) ?? null;
    const dc = typeof lastCommand.data?.dc === "number" ? lastCommand.data.dc : null;
    showRollPrompt({
      requestKey,
      expression,
      issuedBy: lastCommand.issuedBy,
      reason,
      mode,
      rollType: rollType as PendingRoll["rollType"],
      ability,
      skill,
      dc,
    });
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
    const rollType = (typeof lastEvent.payload.rollType === "string" ? lastEvent.payload.rollType : null);
    const ability = (typeof lastEvent.payload.ability === "string" ? lastEvent.payload.ability : null);
    const skill = (typeof lastEvent.payload.skill === "string" ? lastEvent.payload.skill : null);
    const dc = typeof lastEvent.payload.dc === "number" ? lastEvent.payload.dc : null;
    showRollPrompt({
      requestKey,
      expression,
      issuedBy: typeof lastEvent.payload.issuedBy === "string" ? lastEvent.payload.issuedBy : undefined,
      reason,
      mode,
      rollType: rollType as PendingRoll["rollType"],
      ability,
      skill,
      dc,
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
          if (entry.targetUserId && entry.targetUserId !== userId) {
            return false;
          }
          return !isActivityRequestAlreadyResolved(activity, entry);
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
        rollType: (latestRequest.rollType ?? null) as PendingRoll["rollType"],
        ability: latestRequest.ability ?? null,
        skill: latestRequest.skill ?? null,
        dc: latestRequest.dc ?? null,
      });
    } catch {
      // Ignore fallback polling errors; realtime remains the primary path.
    }
  }, [activeSessionId, isActivityRequestAlreadyResolved, showRollPrompt, userId]);

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
    markRequestHandled(pendingRoll.requestKey);
    roll(pendingRoll.expression, pendingRoll.reason, pendingRoll.mode);
    setPendingRoll(null);
  }, [markRequestHandled, pendingRoll, roll]);

  const handleManualRoll = useCallback(async () => {
    if (!activeSessionId || !pendingRoll || !manualValue) {
      return;
    }
    await sessionsRepo.manualRoll(activeSessionId, {
      expression: pendingRoll.expression,
      result: Number(manualValue),
      label: pendingRoll.reason ?? null,
    });
    markRequestHandled(pendingRoll.requestKey);
    setPendingRoll(null);
    setRollMode(null);
    setManualValue("");
  }, [activeSessionId, manualValue, markRequestHandled, pendingRoll]);

  const handleAuthoritativeRollResolved = useCallback(() => {
    if (!pendingRoll) {
      return;
    }
    markRequestHandled(pendingRoll.requestKey);
  }, [markRequestHandled, pendingRoll]);

  const clearPendingRoll = useCallback(() => {
    setPendingRoll(null);
    setRollMode(null);
    setManualValue("");
  }, []);

  return {
    clearPendingRoll,
    handleAuthoritativeRollResolved,
    handleManualRoll,
    handleRoll,
    manualValue,
    pendingRoll,
    rollMode,
    setManualValue,
    setRollMode,
  };
};
