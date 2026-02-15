import type { RollEvent } from "../../../entities/roll";
import type { ConnectionState } from "../../../shared/realtime/wsClient";
import { useLocale } from "../../../shared/hooks/useLocale";

type RollFeedProps = {
  events: RollEvent[];
  connectionState: ConnectionState;
};

const stateLabelKey: Record<ConnectionState, string> = {
  connected: "rolls.state.connected",
  reconnecting: "rolls.state.reconnecting",
  offline: "rolls.state.offline",
};

export const RollFeed = ({ events, connectionState }: RollFeedProps) => {
  const { t } = useLocale();

  return (
    <div className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
      <div className="flex items-center justify-between text-xs uppercase tracking-[0.2em] text-slate-400">
        <span>{t("rolls.feed.title")}</span>
        <span className="rounded-full border border-slate-700 px-3 py-1 text-[10px] text-slate-200">
          {t(stateLabelKey[connectionState])}
        </span>
      </div>
      {events.length === 0 ? (
        <div className="text-sm text-slate-300">{t("rolls.feed.empty")}</div>
      ) : (
        <ul className="space-y-3">
          {events.map((event) => (
            <li
              key={event.id}
              className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-slate-100">
                    {event.authorName}
                  </p>
                  <p className="text-xs text-slate-400">
                    {event.label ? `${event.label} · ` : ""}
                    {event.expression}
                  </p>
                </div>
                <p className="text-xs text-slate-500">
                  {new Date(event.createdAt).toLocaleTimeString()}
                </p>
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-300">
                <span className="rounded-full border border-slate-700 px-2 py-1">
                  {t("rolls.feed.results")}: {event.results.join(", ")}
                </span>
                <span className="rounded-full border border-slate-700 px-2 py-1">
                  {t("rolls.feed.total")}: {event.total}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};
