import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  type RealtimeHistoryPublication,
  getHistory,
  subscribe,
} from "../../shared/realtime/centrifugoClient";
import { combatRepo, type CombatState } from "../../shared/api/combatRepo";
import {
  appendCombatLogEntries,
  toCombatLogEntry,
} from "./combatUi.helpers";
import type { CombatLogEntry } from "./types";

type Props = {
  enabled?: boolean;
  historyLimit?: number;
  pollMs?: number;
  sessionId: string;
  userId?: string | null;
};

export const useCombatUiState = ({
  enabled = true,
  historyLimit = 8,
  pollMs = 4_000,
  sessionId,
  userId = null,
}: Props) => {
  const [state, setState] = useState<CombatState | null>(null);
  const [logs, setLogs] = useState<CombatLogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const logSequenceRef = useRef(0);

  const refreshState = useCallback(async () => {
    if (!enabled || !sessionId) {
      setState(null);
      return;
    }
    setLoading(true);
    try {
      const nextState = await combatRepo.getState(sessionId);
      setState(nextState);
      setError(null);
    } catch (err: any) {
      setState(null);
      setError(err?.data?.detail || err?.message || null);
    } finally {
      setLoading(false);
    }
  }, [enabled, sessionId]);

  const appendLogs = useCallback((entries: CombatLogEntry[]) => {
    setLogs((current) => appendCombatLogEntries(current, entries, historyLimit));
  }, [historyLimit]);

  const processRealtimeMessage = useCallback((message: unknown, offset?: string) => {
    if (!message || typeof message !== "object") {
      return;
    }
    const data = message as { payload?: Record<string, unknown>; type?: string };
    if (data.type === "combat_state_updated") {
      setState(data.payload as CombatState);
      setError(null);
      return;
    }
    if (data.type === "combat_log_added" && data.payload) {
      const logId = offset ?? `live:${++logSequenceRef.current}`;
      appendLogs([toCombatLogEntry(data.payload, logId)]);
    }
  }, [appendLogs]);

  useEffect(() => {
    setState(null);
    setLogs([]);
    setError(null);
    logSequenceRef.current = 0;
  }, [sessionId]);

  useEffect(() => {
    if (!enabled || !sessionId) {
      return;
    }

    let active = true;
    const channel = `session:${sessionId}`;
    const replayHistory = (publications: RealtimeHistoryPublication[]) => {
      const combatLogEntries: CombatLogEntry[] = [];
      [...publications]
        .sort((left, right) => {
          const leftOffset = left.offset ? Number(left.offset) : 0;
          const rightOffset = right.offset ? Number(right.offset) : 0;
          return leftOffset - rightOffset;
        })
        .forEach((publication) => {
          const data = publication.data as { payload?: Record<string, unknown>; type?: string };
          if (data.type === "combat_state_updated") {
            setState(data.payload as CombatState);
            return;
          }
          if (data.type === "combat_log_added" && data.payload) {
            combatLogEntries.push(
              toCombatLogEntry(data.payload, publication.offset ?? `history:${++logSequenceRef.current}`),
            );
          }
        });
      appendLogs(combatLogEntries);
    };

    void refreshState();
    const intervalId = window.setInterval(() => {
      void refreshState();
    }, pollMs);
    const unsubscribe = subscribe(channel, {
      onSubscribed: () => {
        void getHistory(channel, Math.max(historyLimit * 3, 20))
          .then((publications) => {
            if (active) {
              replayHistory(publications);
            }
          })
          .catch(() => {});
      },
      onPublication: (message, context) => {
        processRealtimeMessage(
          message,
          typeof context.offset === "number" ? String(context.offset) : context.offset,
        );
      },
    });

    return () => {
      active = false;
      window.clearInterval(intervalId);
      unsubscribe();
    };
  }, [appendLogs, enabled, historyLimit, pollMs, processRealtimeMessage, refreshState, sessionId]);

  const currentParticipant = useMemo(
    () => state?.participants[state.current_turn_index] ?? null,
    [state],
  );

  const myParticipant = useMemo(
    () =>
      userId
        ? state?.participants.find(
            (participant) =>
              participant.actor_user_id === userId || participant.ref_id === userId,
          ) ?? null
        : null,
    [state, userId],
  );

  const livingParticipants = useMemo(
    () =>
      state?.participants.filter(
        (participant) => participant.status !== "dead" && participant.status !== "defeated",
      ) ?? [],
    [state],
  );

  const defeatedParticipants = useMemo(
    () =>
      state?.participants.filter(
        (participant) => participant.status === "dead" || participant.status === "defeated",
      ) ?? [],
    [state],
  );

  const isMyTurn = Boolean(
    state?.phase === "active" &&
      currentParticipant &&
      myParticipant &&
      currentParticipant.id === myParticipant.id,
  );

  return {
    currentParticipant,
    defeatedParticipants,
    error,
    isMyTurn,
    livingParticipants,
    loading,
    logs,
    myParticipant,
    refreshState,
    state,
  };
};
