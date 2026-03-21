import { SessionActivityRow } from "../../features/sessions";
import type { ActivityEvent } from "../../shared/api/sessionsRepo";

type Props = {
  activityFeed: ActivityEvent[];
};

export const GmDashboardActivityCard = ({ activityFeed }: Props) => (
  <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6">
    <h2 className="mb-4 text-lg font-semibold text-white">Session Activity</h2>
    {activityFeed.length === 0 ? (
      <p className="text-sm text-slate-500">No activity yet. Roll some dice or open the shop!</p>
    ) : (
      <div className="max-h-96 space-y-2 overflow-y-auto pr-1">
        {[...activityFeed].reverse().map((event, index) => (
          <SessionActivityRow key={index} event={event} />
        ))}
      </div>
    )}
  </div>
);
