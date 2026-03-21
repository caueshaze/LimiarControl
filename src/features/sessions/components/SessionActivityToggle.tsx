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

  const refreshActivity = useCallback(
    async ({ showLoader = false }: { showLoader?: boolean } = {}) => {
      if (!sessionId) {
        setEvents([]);
        return;
      }
      if (showLoader) {
        setLoading(true);
      }
      try {
        const nextEvents = await sessionsRepo.getActivity(sessionId);
        setEvents(nextEvents);
      } catch {
        setEvents([]);
      } finally {
        if (showLoader) {
          setLoading(false);
        }
      }
    },
    [sessionId]
  );

  useEffect(() => {
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
    <div className="rounded-2xl border border-slate-800 bg-slate-900/30">
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
        aria-expanded={open}
      >
        <span className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-300">
          {t("sessionActivity.title")}
        </span>
        <span
          className={`text-xs text-slate-500 transition-transform ${
            open ? "rotate-180" : ""
          }`}
        >
          ▼
        </span>
      </button>

      {open && (
        <div className="border-t border-slate-800/70 px-4 py-4">
          {loading ? (
            <p className="text-sm text-slate-500">{t("sessionActivity.loading")}</p>
          ) : orderedEvents.length === 0 ? (
            <p className="text-sm text-slate-500">{t("sessionActivity.empty")}</p>
          ) : (
            <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
              {orderedEvents.map((event, index) => (
                <SessionActivityRow key={`${event.type}-${event.timestamp}-${index}`} event={event} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
