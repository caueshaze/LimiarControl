import { useCallback, useEffect, useRef, useState } from "react";
import {
  sessionsRepo,
  type RollRequestActivityEvent,
} from "../../shared/api/sessionsRepo";
import type { LocaleKey } from "../../shared/i18n";
import type { ToastState } from "../../shared/ui/Toast";
import {
  buildRollRequestKey,
  type PendingRoll,
  readHandledRollRequestKey,
  writeHandledRollRequestKey,
} from "./playerBoard.types";
import {
  buildActivityRollRequestKey,
  findLatestPendingRollRequest,
  findMatchingRollRequestByKey,
  isActivityRequestAlreadyResolved,
} from "./playerBoard.rollRequests";

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

  const rememberHandledRequest = useCallback((requestKey: string) => {
    handledRollRequestKeyRef.current = requestKey;
    writeHandledRollRequestKey(activeSessionId, requestKey);
  }, [activeSessionId]);

  const markRequestHandled = useCallback((requestKey: string) => {
    rememberHandledRequest(requestKey);
    clearCommand();
  }, [clearCommand, rememberHandledRequest]);

  const resetPromptState = useCallback(() => {
    setPendingRoll(null);
    setRollMode(null);
    setManualValue("");
  }, []);

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

  const reconcileAndShowRollPrompt = useCallback(async (
    nextRoll: PendingRoll,
    requestActivity: RollRequestActivityEvent,
  ) => {
    if (nextRoll.requestKey === handledRollRequestKeyRef.current || nextRoll.requestKey === shownRollRequestKeyRef.current) {
      return;
    }

    // Wait for the active session to hydrate before showing restored prompts.
    // This avoids a flash/toast on reload for requests that activity already resolved.
    if (!activeSessionId) {
      return;
    }

    try {
      const activity = await sessionsRepo.getActivity(activeSessionId);
      if (isActivityRequestAlreadyResolved(activity, requestActivity, userId)) {
        rememberHandledRequest(nextRoll.requestKey);
        return;
      }
    } catch {
      // Ignore reconciliation errors and fall back to realtime/UI state.
    }

    if (nextRoll.requestKey === handledRollRequestKeyRef.current || nextRoll.requestKey === shownRollRequestKeyRef.current) {
      return;
    }

    showRollPrompt(nextRoll);
  }, [activeSessionId, rememberHandledRequest, showRollPrompt, userId]);

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
    const requestActivity: RollRequestActivityEvent = {
      type: "roll_request",
      expression,
      reason,
      mode,
      rollType,
      ability,
      skill,
      dc,
      targetUserId: targetUserId ?? null,
      timestamp: String(lastCommand.issuedAt ?? new Date().toISOString()),
      sessionOffsetSeconds: 0,
    };
    void reconcileAndShowRollPrompt({
      requestKey,
      expression,
      issuedBy: lastCommand.issuedBy,
      reason,
      mode,
      rollType: rollType as PendingRoll["rollType"],
      ability,
      skill,
      dc,
    }, requestActivity);
  }, [activeSessionId, lastCommand, reconcileAndShowRollPrompt, userId]);

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
    const requestActivity: RollRequestActivityEvent = {
      type: "roll_request",
      expression,
      reason,
      mode,
      rollType,
      ability,
      skill,
      dc,
      targetUserId,
      timestamp: String(lastEvent.payload.issuedAt ?? ""),
      sessionOffsetSeconds: 0,
    };
    void reconcileAndShowRollPrompt({
      requestKey,
      expression,
      issuedBy: typeof lastEvent.payload.issuedBy === "string" ? lastEvent.payload.issuedBy : undefined,
      reason,
      mode,
      rollType: rollType as PendingRoll["rollType"],
      ability,
      skill,
      dc,
    }, requestActivity);
  }, [activeSessionId, lastEvent, reconcileAndShowRollPrompt, userId]);

  const syncLatestRollRequest = useCallback(async () => {
    if (!activeSessionId) {
      return;
    }

    try {
      const activity = await sessionsRepo.getActivity(activeSessionId);
      if (pendingRoll) {
        const matchingRequest = findMatchingRollRequestByKey(
          activity,
          activeSessionId,
          pendingRoll.requestKey,
          userId,
        );
        if (
          matchingRequest
          && isActivityRequestAlreadyResolved(activity, matchingRequest, userId)
        ) {
          rememberHandledRequest(pendingRoll.requestKey);
          resetPromptState();
        }
      }

      const latestRequest = findLatestPendingRollRequest(activity, userId);

      if (!latestRequest) {
        return;
      }

      const requestKey = buildActivityRollRequestKey(latestRequest, activeSessionId);

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
  }, [activeSessionId, pendingRoll, rememberHandledRequest, resetPromptState, showRollPrompt, userId]);

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
    resetPromptState();
  }, [resetPromptState]);

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
