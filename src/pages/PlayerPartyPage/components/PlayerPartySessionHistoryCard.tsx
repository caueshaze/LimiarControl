import { useEffect, useState } from "react";
import { useLocale } from "../../../shared/hooks/useLocale";
import { sessionsRepo, type ActivityEvent } from "../../../shared/api/sessionsRepo";
import type { PartyActiveSession } from "../../../shared/api/partiesRepo";
import {
  formatOffset,
  formatPartyDateTime,
  getSessionStatusLabel,
} from "../playerParty.utils";

function SessionActivityLog({ sessionId }: { sessionId: string }) {
  const { t } = useLocale();
  const [events, setEvents] = useState<ActivityEvent[] | null>(null);

  useEffect(() => {
    sessionsRepo.getActivity(sessionId).then(setEvents).catch(() => setEvents([]));
  }, [sessionId]);

  if (events === null) {
    return <p className="py-3 text-xs text-slate-500">{t("playerParty.activityLoading")}</p>;
  }

  if (events.length === 0) {
    return <p className="py-3 text-xs text-slate-500">{t("playerParty.activityEmpty")}</p>;
  }

  return (
    <div className="mt-3 space-y-2">
      {events.map((event, index) => {
        const actor = event.displayName ?? event.username ?? "?";

        if (event.type === "roll") {
          return (
            <div
              key={`${event.type}-${index}`}
              className="flex items-start gap-3 rounded-2xl border border-white/8 bg-white/[0.03] px-3 py-3"
            >
              <span className="text-sm">🎲</span>
              <p className="flex-1 text-xs leading-6 text-slate-200">
                <span className="font-semibold text-white">{actor}</span>
                {" "}
                {t("playerParty.activityRolled")}
                {" "}
                <span className="font-mono text-limiar-200">{event.expression}</span>
                {" → "}
                <span className="font-bold text-limiar-100">{event.total}</span>
                {event.results.length > 1 ? (
                  <span className="ml-1 text-slate-500">({event.results.join(", ")})</span>
                ) : null}
                {event.label ? (
                  <span className="ml-1 italic text-slate-400">{event.label}</span>
                ) : null}
              </p>
              <span className="shrink-0 font-mono text-[10px] text-slate-500">
                {formatOffset(event.sessionOffsetSeconds)}
              </span>
            </div>
          );
        }

        if (event.type === "shop") {
          return (
            <div
              key={`${event.type}-${index}`}
              className="flex items-start gap-3 rounded-2xl border border-white/8 bg-white/[0.03] px-3 py-3"
            >
              <span className="text-sm">{event.action === "opened" ? "🏪" : "🔒"}</span>
              <p className="flex-1 text-xs leading-6 text-slate-200">
                <span className="font-semibold text-white">{actor}</span>
                {" "}
                {event.action === "opened"
                  ? t("playerParty.activityOpenedShop")
                  : t("playerParty.activityClosedShop")}
              </p>
              <span className="shrink-0 font-mono text-[10px] text-slate-500">
                {formatOffset(event.sessionOffsetSeconds)}
              </span>
            </div>
          );
        }

        return (
          <div
            key={`${event.type}-${index}`}
            className="flex items-start gap-3 rounded-2xl border border-white/8 bg-white/[0.03] px-3 py-3"
          >
            <span className="text-sm">🛒</span>
            <p className="flex-1 text-xs leading-6 text-slate-200">
              <span className="font-semibold text-white">{actor}</span>
              {" "}
              {t("playerParty.activityBought")}
              {" "}
              <span className="font-semibold text-amber-200">{event.itemName}</span>
              {event.quantity > 1 ? (
                <span className="text-slate-500"> ×{event.quantity}</span>
              ) : null}
            </p>
            <span className="shrink-0 font-mono text-[10px] text-slate-500">
              {formatOffset(event.sessionOffsetSeconds)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

type Props = {
  sessions: PartyActiveSession[];
  expandedSessionId: string | null;
  onToggleSession: (sessionId: string | null) => void;
};

export const PlayerPartySessionHistoryCard = ({
  sessions,
  expandedSessionId,
  onToggleSession,
}: Props) => {
  const { t, locale } = useLocale();

  return (
    <section className="rounded-[32px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] px-6 py-5 shadow-[0_18px_60px_rgba(2,6,23,0.2)]">
      <div className="space-y-1 border-b border-white/8 pb-4">
        <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-500">
          {t("playerParty.historyTitle")}
        </p>
        <h2 className="text-xl font-semibold text-white">
          {t("playerParty.historyHeading")}
        </h2>
        <p className="text-sm leading-7 text-slate-400">
          {t("playerParty.historyDescription")}
        </p>
      </div>

      {sessions.length === 0 ? (
        <p className="py-5 text-sm text-slate-400">{t("playerParty.historyEmpty")}</p>
      ) : (
        <div className="mt-4 space-y-3">
          {sessions.map((session) => {
            const isExpanded = expandedSessionId === session.id;
            const statusLabel = getSessionStatusLabel(session.status, t);

            return (
              <article
                key={session.id}
                className="overflow-hidden rounded-[24px] border border-white/8 bg-white/[0.03]"
              >
                <button
                  type="button"
                  onClick={() => onToggleSession(isExpanded ? null : session.id)}
                  className="flex w-full items-center justify-between gap-4 px-4 py-4 text-left transition hover:bg-white/[0.03]"
                >
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-semibold text-white">{session.title}</p>
                      <span
                        className={`rounded-full border px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-[0.22em] ${
                          session.status === "ACTIVE"
                            ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-200"
                            : session.status === "LOBBY"
                              ? "border-amber-500/20 bg-amber-500/10 text-amber-200"
                              : "border-white/10 bg-white/[0.04] text-slate-300"
                        }`}
                      >
                        {statusLabel}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-slate-500">
                      {formatPartyDateTime(session.createdAt, locale)}
                    </p>
                  </div>

                  <span
                    className={`text-xs text-slate-500 transition-transform ${
                      isExpanded ? "rotate-180" : ""
                    }`}
                  >
                    ▼
                  </span>
                </button>

                {isExpanded ? (
                  <div className="border-t border-white/8 px-4 pb-4">
                    <SessionActivityLog sessionId={session.id} />
                  </div>
                ) : null}
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
};
