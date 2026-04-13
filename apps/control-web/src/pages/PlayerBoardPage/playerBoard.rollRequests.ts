import type {
  ActivityEvent,
  RollRequestActivityEvent,
  RollResolvedActivityEvent,
} from "../../shared/api/sessionsRepo";
import { buildRollRequestKey } from "./playerBoard.types";

export const matchesResolvedRollRequest = (
  request: RollRequestActivityEvent,
  resolved: RollResolvedActivityEvent,
  userId?: string | null,
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
};

export const isActivityRequestAlreadyResolved = (
  activity: ActivityEvent[],
  request: RollRequestActivityEvent,
  userId?: string | null,
) => {
  if (request.rollType) {
    return activity.some((entry): boolean => {
      if (entry.type !== "roll_resolved") {
        return false;
      }
      return matchesResolvedRollRequest(request, entry, userId);
    });
  }

  const targetId = request.targetUserId ?? userId;
  if (!targetId) {
    return false;
  }
  const requestTime = Date.parse(request.timestamp);
  if (!Number.isFinite(requestTime)) {
    return false;
  }
  return activity.some((entry): boolean => {
    if (entry.type !== "roll") {
      return false;
    }
    if (entry.userId !== targetId) {
      return false;
    }
    const rollTime = Date.parse(entry.timestamp);
    return Number.isFinite(rollTime) && rollTime >= requestTime;
  });
};

const isRelevantRollRequest = (
  entry: ActivityEvent,
  userId?: string | null,
): entry is RollRequestActivityEvent => {
  if (entry.type !== "roll_request") {
    return false;
  }
  if (entry.targetUserId && entry.targetUserId !== userId) {
    return false;
  }
  return true;
};

export const findLatestPendingRollRequest = (
  activity: ActivityEvent[],
  userId?: string | null,
) =>
  [...activity]
    .reverse()
    .find((entry): entry is RollRequestActivityEvent => {
      if (!isRelevantRollRequest(entry, userId)) {
        return false;
      }
      return !isActivityRequestAlreadyResolved(activity, entry, userId);
    }) ?? null;

export const findMatchingRollRequestByKey = (
  activity: ActivityEvent[],
  sessionId: string,
  requestKey: string,
  userId?: string | null,
) =>
  activity.find((entry): entry is RollRequestActivityEvent => {
    if (!isRelevantRollRequest(entry, userId)) {
      return false;
    }
    return buildActivityRollRequestKey(entry, sessionId) === requestKey;
  }) ?? null;

export const buildActivityRollRequestKey = (
  request: RollRequestActivityEvent,
  sessionId: string,
) =>
  buildRollRequestKey({
    expression: request.expression,
    mode: request.mode ?? null,
    reason: request.reason ?? undefined,
    sessionId,
    targetUserId: request.targetUserId ?? null,
    timestamp: request.timestamp,
  });
