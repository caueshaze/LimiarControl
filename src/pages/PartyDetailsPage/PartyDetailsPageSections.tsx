import { routes } from "../../app/routes/routes";
import type { PartyActiveSession, PartyDetail } from "../../shared/api/partiesRepo";
import type { LobbyStatus } from "../../shared/api/sessionsRepo";
import { useLocale } from "../../shared/hooks/useLocale";
import { BackButton } from "../../shared/ui";
import { PartyDetailsSessionActivityLog } from "./PartyDetailsSessionActivityLog";

type HeaderProps = {
  party: PartyDetail;
  activeSession: PartyActiveSession | null;
  deletingParty: boolean;
  onStartSession: () => void;
  onEndSession: () => void;
  onDeleteParty: () => void;
};

export const PartyDetailsHeader = ({
  party,
  activeSession,
  deletingParty,
  onStartSession,
  onEndSession,
  onDeleteParty,
}: HeaderProps) => {
  const { t } = useLocale();

  return (
    <header className="flex flex-wrap items-start justify-between gap-4 rounded-3xl border border-slate-800 bg-linear-to-br from-void-950 via-slate-950/80 to-limiar-900/30 p-6">
      <div>
        <BackButton
          fallbackTo={routes.gmHome}
          label={`← ${t("campaignHome.back")}`}
          className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400 hover:text-slate-200"
        />
        <p className="mt-3 text-xs uppercase tracking-[0.3em] text-limiar-300">
          {t("gm.home.partyPanelTitle")}
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-white">{party.name}</h1>
        <p className="mt-3 text-sm text-slate-300">
          Manage the roster, inspect sheets, and keep inventory close before the next session goes live.
        </p>
      </div>
      <div className="flex flex-wrap justify-end gap-3">
        <button
          type="button"
          onClick={onDeleteParty}
          disabled={deletingParty}
          className="rounded-full border border-red-500/30 bg-red-500/10 px-4 py-2 text-xs font-semibold uppercase tracking-widest text-red-300 hover:bg-red-500/20 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {deletingParty ? "Deleting..." : "Delete Party"}
        </button>
        {activeSession?.status === "ACTIVE" ? (
          <>
            <button
              onClick={onEndSession}
              className="rounded-full border border-red-500/30 bg-red-500/10 px-4 py-2 text-xs font-semibold uppercase tracking-widest text-red-400 hover:bg-red-500/20"
            >
              End Session
            </button>
            <Link
              to={routes.campaignDashboard.replace(":campaignId", party.campaignId)}
              className="rounded-full border border-emerald-500/30 bg-emerald-500/20 px-4 py-2 text-xs font-semibold uppercase tracking-widest text-emerald-300 hover:bg-emerald-500/30"
            >
              Manage Session →
            </Link>
          </>
        ) : activeSession?.status === "LOBBY" ? (
          <button
            onClick={onEndSession}
            className="rounded-full border border-red-500/30 bg-red-500/10 px-4 py-2 text-xs font-semibold uppercase tracking-widest text-red-400 hover:bg-red-500/20"
          >
            Cancel Lobby
          </button>
        ) : (
          <button
            onClick={onStartSession}
            className="rounded-full bg-limiar-500 px-6 py-2.5 text-sm font-semibold uppercase tracking-wider text-white shadow-lg shadow-limiar-500/20 transition hover:bg-limiar-400"
          >
            Start New Session
          </button>
        )}
      </div>
    </header>
  );
};

type LobbyProps = {
  activeSession: PartyActiveSession;
  lobbyStatus: LobbyStatus | null;
  onlineUsers: Record<string, string>;
  forceStarting: boolean;
  onForceStart: () => void;
};

export const PartyDetailsLobbyCard = ({
  activeSession,
  lobbyStatus,
  onlineUsers,
  forceStarting,
  onForceStart,
}: LobbyProps) => (
  <div className="space-y-5 rounded-3xl border border-amber-500/20 bg-amber-500/5 p-5">
    <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
      <div>
        <p className="text-xs uppercase tracking-widest text-amber-400">Lobby aberto</p>
        <p className="mt-1 text-lg font-semibold text-white">
          {activeSession.title || "Untitled Session"}
        </p>
        <p className="mt-1 text-sm text-slate-400">
          Aguardando os jogadores confirmarem entrada para iniciar a sessao.
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <span className="rounded-full border border-amber-500/20 bg-amber-500/10 px-3 py-1 text-xs font-semibold text-amber-300">
          {lobbyStatus
            ? `${lobbyStatus.ready.length}/${lobbyStatus.expected.length} prontos`
            : "Carregando lobby"}
        </span>
        <button
          onClick={onForceStart}
          disabled={forceStarting}
          className="rounded-full border border-limiar-500/30 bg-limiar-500/10 px-4 py-2 text-xs font-semibold uppercase tracking-widest text-limiar-300 hover:bg-limiar-500/20 disabled:opacity-50"
        >
          {forceStarting ? "Starting..." : "Force Start"}
        </button>
      </div>
    </div>

    {lobbyStatus ? (
      lobbyStatus.expected.length > 0 ? (
        <div className="grid gap-3 md:grid-cols-2">
          {lobbyStatus.expected.map((player) => {
            const isReady = lobbyStatus.ready.includes(player.userId);
            const isOnline = Boolean(onlineUsers[player.userId]);
            return (
              <div
                key={player.userId}
                className={`flex items-center gap-3 rounded-2xl border px-4 py-3 ${
                  isReady
                    ? "border-emerald-500/20 bg-emerald-500/10"
                    : "border-slate-800 bg-slate-900/40"
                }`}
              >
                <div className="relative">
                  <div
                    className={`flex h-9 w-9 items-center justify-center rounded-full border text-sm font-bold ${
                      isReady
                        ? "border-emerald-500/30 bg-emerald-500/20 text-emerald-200"
                        : "border-slate-700 bg-slate-800 text-slate-300"
                    }`}
                  >
                    {player.displayName.charAt(0).toUpperCase()}
                  </div>
                  <span
                    className={`absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-slate-950 ${
                      isOnline ? "bg-emerald-400" : "bg-slate-600"
                    }`}
                  />
                </div>
                <div className="min-w-0">
                  <p className={`truncate text-sm font-medium ${isReady ? "text-emerald-200" : "text-white"}`}>
                    {player.displayName}
                  </p>
                  <p className={`text-xs ${isReady ? "text-emerald-400" : isOnline ? "text-sky-400" : "text-slate-500"}`}>
                    {isReady ? "Entrou no lobby" : isOnline ? "Online" : "Offline"}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <p className="text-sm text-slate-400">Nenhum player confirmado para este lobby.</p>
      )
    ) : (
      <p className="text-sm text-slate-400">Carregando estado do lobby...</p>
    )}
  </div>
);

type MembersProps = {
  party: PartyDetail;
  searchQuery: string;
  searching: boolean;
  searchResults: { id: string; username: string; displayName?: string | null }[];
  onSearchChange: (value: string) => void;
  onInvite: (userId: string) => void;
};

export const PartyDetailsMembersCard = ({
  party,
  searchQuery,
  searching,
  searchResults,
  onSearchChange,
  onInvite,
}: MembersProps) => {
  const { t } = useLocale();

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-950/80 p-6">
      <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">
        Members & Invites
      </h2>
      <div className="mt-6 space-y-3">
        {party.members.length === 0 ? (
          <p className="text-sm text-slate-500">No members or invites yet.</p>
        ) : (
          party.members.map((member) => (
            <div
              key={member.userId}
              className="flex items-center justify-between rounded-xl border border-slate-800/60 bg-slate-900/40 p-3"
            >
              <div>
                <span className="block text-sm font-medium text-white">
                  {member.displayName || member.username || "Unknown Player"}
                </span>
                {member.username && (
                  <span className="block text-xs text-slate-500">@{member.username}</span>
                )}
              </div>
              <span
                className={`rounded-full px-2 py-1 text-xs font-semibold uppercase tracking-wider ${
                  member.status === "joined"
                    ? "bg-emerald-500/10 text-emerald-400"
                    : member.status === "invited"
                      ? "bg-amber-500/10 text-amber-400"
                      : "bg-red-500/10 text-red-400"
                }`}
              >
                {member.status}
              </span>
            </div>
          ))
        )}
      </div>

      <div className="mt-8 border-t border-slate-800 pt-6">
        <label className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
          {t("gm.home.partyUsersLabel")}
        </label>
        <p className="mb-4 mt-1 text-xs text-slate-400">{t("gm.home.partyUsersHint")}</p>

        <input
          value={searchQuery}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder={t("gm.home.partyUsersPlaceholder")}
          className="w-full rounded-xl border border-slate-800 bg-slate-900 px-4 py-3 text-sm text-white focus:border-limiar-500 focus:outline-none"
        />

        {searchQuery.length > 0 && searchQuery.length < 2 && (
          <p className="mt-2 text-xs text-slate-500">{t("gm.home.partySearchHint")}</p>
        )}

        {searching && (
          <p className="mt-2 text-xs text-slate-500">{t("gm.home.partySearchLoading")}</p>
        )}

        {!searching && searchQuery.length >= 2 && searchResults.length === 0 && (
          <p className="mt-2 text-xs text-slate-500">{t("gm.home.partySearchEmpty")}</p>
        )}

        <div className="mt-4 space-y-2">
          {searchResults.map((user) => {
            const alreadyInParty = party.members.some((member) => member.userId === user.id);
            return (
              <div key={user.id} className="flex items-center justify-between rounded-xl bg-slate-900 p-3">
                <div>
                  <p className="text-sm font-semibold text-white">{user.displayName || user.username}</p>
                  <p className="text-xs text-slate-500">@{user.username}</p>
                </div>
                <button
                  onClick={() => onInvite(user.id)}
                  disabled={alreadyInParty}
                  className="rounded-full bg-slate-800 px-4 py-1.5 text-xs font-semibold uppercase tracking-wider text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {alreadyInParty ? "Added" : t("gm.home.partyUserAdd")}
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

type TimelineProps = {
  sessions: PartyActiveSession[];
  expandedSessionId: string | null;
  onToggleSession: (sessionId: string | null) => void;
};

export const PartyDetailsTimelineCard = ({
  sessions,
  expandedSessionId,
  onToggleSession,
}: TimelineProps) => (
  <div className="rounded-3xl border border-slate-800 bg-slate-950/80 p-6">
    <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">
      Sessions Timeline
    </h2>
    <div className="mt-6 space-y-3">
      {sessions.length === 0 ? (
        <p className="text-sm text-slate-500">No sessions recorded. Start one above!</p>
      ) : (
        sessions.map((session, index) => {
          const isExpanded = expandedSessionId === session.id;
          return (
            <div
              key={session.id}
              className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-950/60"
            >
              <button
                onClick={() => onToggleSession(isExpanded ? null : session.id)}
                className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition-colors hover:bg-slate-900/40"
              >
                <div>
                  <p className="text-xs uppercase tracking-wider text-slate-500">
                    Session {index + 1} • {new Date(session.createdAt).toLocaleDateString()}
                  </p>
                  <p className="mt-0.5 text-sm font-semibold text-white">{session.title}</p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <span
                    className={`rounded-sm px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest ${
                      session.isActive
                        ? "bg-limiar-500/20 text-limiar-300"
                        : "bg-slate-800 text-slate-400"
                    }`}
                  >
                    {session.status}
                  </span>
                  <span className={`text-xs text-slate-500 transition-transform ${isExpanded ? "rotate-180" : ""}`}>
                    ▼
                  </span>
                </div>
              </button>
              {isExpanded && (
                <div className="border-t border-slate-800/60 px-4 pb-4">
                  <PartyDetailsSessionActivityLog sessionId={session.id} />
                </div>
              )}
            </div>
          );
        })
      )}
    </div>
  </div>
);
