import { useEffect, useState } from "react";
import { sessionsRepo, type ActivityEvent } from "../../shared/api/sessionsRepo";
import { SessionActivityRow } from "../../features/sessions";

export const PartyDetailsSessionActivityLog = ({ sessionId }: { sessionId: string }) => {
  const [events, setEvents] = useState<ActivityEvent[] | null>(null);

  useEffect(() => {
    sessionsRepo.getActivity(sessionId).then(setEvents).catch(() => setEvents([]));
  }, [sessionId]);

  if (events === null) return <p className="py-2 text-xs text-slate-500">Loading activity...</p>;
  if (events.length === 0) return <p className="py-2 text-xs text-slate-500">No activity recorded.</p>;

  return (
    <div className="mt-3 space-y-1.5">
      {events.map((event, index) => (
        <SessionActivityRow key={`${event.type}-${index}`} event={event} />
      ))}
    </div>
  );
};
