import { useLocale } from "../../shared/hooks/useLocale";
import { SessionActivityFeed } from "../../features/sessions/components/SessionActivityFeed";
import type { ActivityEvent } from "../../shared/api/sessionsRepo";

type Props = {
  activityFeed: ActivityEvent[];
  sessionId: string;
};

export const GmDashboardActivityCard = ({ activityFeed, sessionId }: Props) => {
  const { t } = useLocale();

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6">
      <h2 className="mb-4 text-lg font-semibold text-white">{t("sessionActivity.title")}</h2>
      {activityFeed.length === 0 ? (
        <p className="text-sm text-slate-500">{t("sessionActivity.empty")}</p>
      ) : (
        <div className="max-h-96 overflow-y-auto pr-1">
          <SessionActivityFeed events={activityFeed} sessionId={sessionId} />
        </div>
      )}
    </div>
  );
};
