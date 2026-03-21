import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ActivityEvent } from "../../../shared/api/sessionsRepo";
import { sessionsRepo } from "../../../shared/api/sessionsRepo";
import { useLocale } from "../../../shared/hooks/useLocale";
import { SessionActivityRow } from "./SessionActivityRow";

type SessionActivityToggleProps = {
  refreshSignal?: string | number | null;
  sessionId?: string | null;
};

export const SessionActivityToggle = ({
  refreshSignal = null,
  sessionId = null,
}: SessionActivityToggleProps) => {
  const { t } = useLocale();
  const [open, setOpen] = useState(false);
  const [events, setEvents] = useState<ActivityEvent[] | null>(null);
  const [loading, setLoading] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const requestIdRef = useRef(0);

  const refreshActivity = useCallback(
    async ({ showLoader = false }: { showLoader?: boolean } = {}) => {
      if (!sessionId) {
        requestIdRef.current += 1;
        setEvents([]);
        setLoading(false);
        return;
      }
      const requestId = requestIdRef.current + 1;
      requestIdRef.current = requestId;
      if (showLoader) {
        setLoading(true);
      }
      try {
        const nextEvents = await sessionsRepo.getActivity(sessionId);
        if (requestIdRef.current !== requestId) {
          return;
        }
        setEvents(nextEvents);
      } catch {
        if (requestIdRef.current !== requestId) {
          return;
        }
        setEvents([]);
      } finally {
        if (showLoader && requestIdRef.current === requestId) {
          setLoading(false);
        }
      }
    },
    [sessionId]
  );

  useEffect(() => {
    requestIdRef.current += 1;
    setOpen(false);
    setEvents(null);
    setLoading(false);
    if (intervalRef.current) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, [sessionId]);

  useEffect(() => {
    if (!open || !sessionId) {
      if (intervalRef.current) {
        window.clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    void refreshActivity({ showLoader: events === null });
    intervalRef.current = window.setInterval(() => {
      void refreshActivity();
    }, 10_000);

    return () => {
      if (intervalRef.current) {
        window.clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [open, refreshActivity, sessionId]);

  useEffect(() => {
    if (!open || !sessionId || !refreshSignal) {
      return;
    }
    void refreshActivity();
  }, [open, refreshActivity, refreshSignal, sessionId]);

  const orderedEvents = useMemo(
    () => (events ? [...events].reverse() : []),
    [events]
  );

  if (!sessionId) {
    return null;
  }

  return (
    <section className="rounded-[32px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] shadow-[0_18px_60px_rgba(2,6,23,0.2)]">
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        className="flex w-full items-center justify-between gap-3 px-6 py-5 text-left"
        aria-expanded={open}
      >
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-slate-400">
            {t("playerBoard.sessionCommandCenter")}
          </p>
          <span className="mt-2 block text-lg font-semibold text-white">
            {t("sessionActivity.title")}
          </span>
        </div>
        <span className={`text-xs text-slate-500 transition-transform ${open ? "rotate-180" : ""}`}>
          ▼
        </span>
      </button>

      {open && (
        <div className="border-t border-white/8 px-6 py-5">
          {loading ? (
            <p className="text-sm text-slate-400">{t("sessionActivity.loading")}</p>
          ) : orderedEvents.length === 0 ? (
            <div className="rounded-[24px] border border-dashed border-white/10 bg-white/[0.03] px-4 py-5 text-sm text-slate-400">
              {t("sessionActivity.empty")}
            </div>
          ) : (
            <div className="max-h-72 space-y-2 overflow-y-auto pr-1">
              {orderedEvents.map((event, index) => (
                <SessionActivityRow key={`${event.type}-${event.timestamp}-${index}`} event={event} />
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
};
