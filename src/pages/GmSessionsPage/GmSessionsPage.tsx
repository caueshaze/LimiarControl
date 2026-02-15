import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { useCampaigns } from "../../features/campaign-select";
import { useActiveSession } from "../../features/sessions";
import { StartSessionModal } from "../../features/sessions/components/StartSessionModal";
import { sessionsRepo, type SessionSummary } from "../../shared/api/sessionsRepo";
import { SessionTimer } from "../../shared/ui/SessionTimer";

const formatDuration = (seconds: number) => {
  const mins = Math.floor(seconds / 60);
  const hrs = Math.floor(mins / 60);
  const minsLeft = mins % 60;
  if (hrs > 0) {
    return `${hrs}h ${minsLeft}m`;
  }
  return `${minsLeft}m`;
};

export const GmSessionsPage = () => {
  const { campaignId } = useParams<{ campaignId: string }>();
  const { selectedCampaignId, selectCampaign } = useCampaigns();
  const { activeSession, activate, endSession } = useActiveSession();
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showStartModal, setShowStartModal] = useState(false);
  const [creating, setCreating] = useState(false);

  const effectiveCampaignId = campaignId ?? selectedCampaignId ?? null;

  useEffect(() => {
    if (!effectiveCampaignId) {
      return;
    }
    if (selectedCampaignId !== effectiveCampaignId) {
      selectCampaign(effectiveCampaignId);
    }
  }, [effectiveCampaignId, selectedCampaignId, selectCampaign]);

  const refreshSessions = () => {
    if (!effectiveCampaignId) {
      setSessions([]);
      setError(null);
      return;
    }
    setLoading(true);
    sessionsRepo
      .list(effectiveCampaignId)
      .then((data) => {
        setSessions(Array.isArray(data) ? data : []);
        setError(null);
      })
      .catch((err: { message?: string }) => {
        setSessions([]);
        setError(err?.message ?? "Failed to load sessions");
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    refreshSessions();
  }, [effectiveCampaignId, activeSession?.id]);

  const handleConfirmStart = async (title: string, _date: string) => {
    if (!effectiveCampaignId || creating) {
      return;
    }
    setCreating(true);
    try {
      await activate(title.trim());
      setShowStartModal(false);
      refreshSessions();
    } finally {
      setCreating(false);
    }
  };

  const handleEnd = async () => {
    if (!effectiveCampaignId) return;
    await endSession();
    refreshSessions();
  };

  const activeJoinCode = activeSession?.joinCode;

  if (!effectiveCampaignId) {
    return (
      <section className="space-y-4">
        <h1 className="text-2xl font-semibold">Sessions</h1>
        <p className="text-sm text-slate-400">Select a campaign first.</p>
        <Link
          to={routes.gmHome}
          className="inline-flex rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-200"
        >
          Back to GM home
        </Link>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link
            to={routes.gmHome}
            className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-400 hover:text-slate-200"
          >
            <span>←</span>
            GM home
          </Link>
          <p className="mt-3 text-xs uppercase tracking-[0.3em] text-slate-400">Sessions</p>
          <h1 className="mt-2 text-2xl font-semibold">Campaign Sessions</h1>
          <p className="mt-2 text-sm text-slate-400">
            Each new session continues from the last saved state.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {!activeSession && (
            <button
              type="button"
              onClick={() => setShowStartModal(true)}
              className="rounded-full bg-limiar-500 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-white"
            >
              Start new session
            </button>
          )}
          {activeSession && (
            <Link
              to={routes.gmDashboard.replace(":campaignId", effectiveCampaignId)}
              className="rounded-full border border-slate-700 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-200 hover:border-slate-500"
            >
              GM dashboard
            </Link>
          )}
        </div>
      </header>

      <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Active</p>
            <h2 className="mt-2 text-xl font-semibold text-white">
              {activeSession ? activeSession.title : "No active session"}
            </h2>
            {activeSession?.startedAt && (
              <p className="mt-1 text-sm text-slate-300">
                Started: {new Date(activeSession.startedAt).toLocaleString()}
              </p>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em]">
            {activeJoinCode && (
              <span className="rounded-full border border-limiar-400/40 px-3 py-1 text-limiar-100">
                Join code {activeJoinCode}
              </span>
            )}
            {activeSession && activeSession.startedAt && (
              <span className="rounded-full border border-slate-700 px-3 py-1 text-slate-200">
                <SessionTimer startedAt={activeSession.startedAt ?? activeSession.createdAt} />
              </span>
            )}
            {activeSession && (
              <button
                type="button"
                onClick={handleEnd}
                className="rounded-full border border-rose-500/40 px-3 py-1 text-rose-200 hover:border-rose-400"
              >
                End session
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Session history</h2>
          <button
            type="button"
            onClick={refreshSessions}
            className="rounded-full border border-slate-700 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-slate-300 hover:border-slate-500"
          >
            Refresh
          </button>
        </div>

        <div className="mt-4 space-y-3">
          {loading && (
            <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-3 text-sm text-slate-400">
              Loading sessions...
            </div>
          )}
          {!loading && error && (
            <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-200">
              {error}
            </div>
          )}
          {!loading && !error && sessions.length === 0 && (
            <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-3 text-sm text-slate-400">
              No sessions yet.
            </div>
          )}
          {!loading &&
            !error &&
            sessions.map((session) => (
              <div
                key={session.id}
                className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-slate-100">
                      #{session.number} · {session.title}
                    </p>
                    <p className="mt-1 text-xs text-slate-400">
                      {session.startedAt
                        ? `Started ${new Date(session.startedAt).toLocaleString()}`
                        : "Not started yet"}
                    </p>
                    {session.endedAt && (
                      <p className="text-xs text-slate-500">
                        Ended {new Date(session.endedAt).toLocaleString()}
                      </p>
                    )}
                  </div>
                  <div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em]">
                    <span
                      className={`rounded-full border px-2 py-0.5 ${
                        session.status === "ACTIVE"
                          ? "border-emerald-500/30 text-emerald-300"
                          : "border-slate-600 text-slate-400"
                      }`}
                    >
                      {session.status}
                    </span>
                    <span className="rounded-full border border-slate-700 px-2 py-0.5 text-slate-300">
                      {formatDuration(session.durationSeconds ?? 0)}
                    </span>
                  </div>
                </div>
              </div>
            ))}
        </div>
      </div>

      <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-5">
        <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
          Campaign tools
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <Link
            to={routes.catalog}
            className="rounded-2xl border border-slate-800 bg-slate-950/70 px-4 py-3 text-sm font-semibold text-slate-100 transition-colors hover:border-slate-500"
          >
            Create items
          </Link>
          <Link
            to={routes.npcs}
            className="rounded-2xl border border-slate-800 bg-slate-950/70 px-4 py-3 text-sm font-semibold text-slate-100 transition-colors hover:border-slate-500"
          >
            Create NPCs
          </Link>
        </div>
      </div>

      <StartSessionModal
        isOpen={showStartModal}
        onClose={() => setShowStartModal(false)}
        onConfirm={handleConfirmStart}
        loading={creating}
      />
    </section>
  );
};
