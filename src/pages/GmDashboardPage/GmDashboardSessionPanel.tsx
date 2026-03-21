import { SessionTimer } from "../../shared/ui/SessionTimer";
import type { ActiveSession, LobbyStatus } from "../../shared/api/sessionsRepo";
import type { PartyMemberSummary } from "../../shared/api/partiesRepo";
import type { CommandFeedback } from "./gmDashboard.types";

type Props = {
  activeSession: ActiveSession | null;
  combatUiActive: boolean;
  commandFeedback: CommandFeedback | null;
  commandSending: boolean;
  creating: boolean;
  forceStarting: boolean;
  loading: boolean;
  lobbyStatus: LobbyStatus | null;
  onlineUsers: Record<string, string>;
  partyPlayers: PartyMemberSummary[];
  rollAdvantage: "normal" | "advantage" | "disadvantage";
  rollExpression: string;
  rollOptions: string[];
  rollReason: string;
  rollTargetUserId: string | null;
  shopUiOpen: boolean;
  onActivateClick: () => void;
  onCommand: (
    type: "open_shop" | "close_shop" | "request_roll" | "start_combat" | "end_combat",
    payload?: Record<string, unknown>,
  ) => void;
  onEndSession: () => void;
  onForceStart: () => void;
  setRollAdvantage: (value: "normal" | "advantage" | "disadvantage") => void;
  setRollExpression: (value: string) => void;
  setRollReason: (value: string) => void;
  setRollTargetUserId: (value: string | null) => void;
};

export const GmDashboardSessionPanel = ({
  activeSession,
  combatUiActive,
  commandFeedback,
  commandSending,
  creating,
  forceStarting,
  loading,
  lobbyStatus,
  onlineUsers,
  partyPlayers,
  rollAdvantage,
  rollExpression,
  rollOptions,
  rollReason,
  rollTargetUserId,
  shopUiOpen,
  onActivateClick,
  onCommand,
  onEndSession,
  onForceStart,
  setRollAdvantage,
  setRollExpression,
  setRollReason,
  setRollTargetUserId,
}: Props) => (
  <div className="grid gap-6">
    <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Session Status</h2>
        {activeSession && (
          <div className="flex items-center gap-3">
            <button
              onClick={onEndSession}
              className="rounded-full border border-red-500/30 bg-red-500/10 px-3 py-1 text-xs font-semibold text-red-400 hover:bg-red-500/20"
            >
              {activeSession.status === "LOBBY" ? "Cancel Lobby" : "End Session"}
            </button>
            <span
              className={`rounded-full border px-3 py-1 text-xs font-semibold ${
                activeSession.status === "LOBBY"
                  ? "border-amber-500/20 bg-amber-500/10 text-amber-400"
                  : "border-emerald-500/20 bg-emerald-500/10 text-emerald-400"
              }`}
            >
              {activeSession.status === "LOBBY" ? "LOBBY" : "LIVE"}
            </span>
          </div>
        )}
      </div>

      <div className="mt-6 overflow-hidden rounded-2xl border border-slate-800/50 bg-slate-950/50">
        {loading ? (
          <div className="flex items-center justify-center py-10">
            <span className="text-slate-400">Loading session...</span>
          </div>
        ) : activeSession?.status === "LOBBY" ? (
          <div className="space-y-6 p-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="mb-1 flex items-center gap-2">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-amber-400" />
                  <span className="text-xs font-bold uppercase tracking-widest text-amber-400">Lobby</span>
                </div>
                <h3 className="text-xl font-bold text-white">{activeSession.title}</h3>
                <p className="mt-0.5 text-xs text-slate-500">
                  #{activeSession.number} · Waiting for players to join
                </p>
              </div>
              <button
                onClick={onForceStart}
                disabled={forceStarting}
                className="rounded-full border border-limiar-500/30 bg-limiar-500/10 px-4 py-2 text-xs font-bold uppercase tracking-widest text-limiar-400 hover:bg-limiar-500/20 disabled:opacity-50 transition-all"
              >
                {forceStarting ? "Starting..." : "Force Start"}
              </button>
            </div>

            {lobbyStatus && lobbyStatus.expected.length > 0 ? (
              <div className="space-y-2">
                <p className="text-[10px] font-bold uppercase tracking-[0.25em] text-slate-500">
                  Players ({lobbyStatus.ready.length}/{lobbyStatus.expected.length} ready)
                </p>
                <div className="grid grid-cols-2 gap-2">
                  {lobbyStatus.expected.map((player) => {
                    const isReady = lobbyStatus.ready.includes(player.userId);
                    const isOnline = Boolean(onlineUsers[player.userId]);
                    return (
                      <div
                        key={player.userId}
                        className={`flex items-center gap-3 rounded-xl border px-4 py-3 transition-all ${
                          isReady
                            ? "border-emerald-500/20 bg-emerald-500/10"
                            : "border-slate-800/40 bg-slate-900/40"
                        }`}
                      >
                        <div className="relative shrink-0">
                          <div
                            className={`flex h-8 w-8 items-center justify-center rounded-full border text-sm font-bold ${
                              isReady
                                ? "border-emerald-500/40 bg-emerald-500/20 text-emerald-300"
                                : "border-slate-700 bg-slate-800 text-slate-400"
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
                          <p className={`truncate text-sm font-medium ${isReady ? "text-emerald-300" : "text-slate-300"}`}>
                            {player.displayName}
                          </p>
                          <p className={`text-[10px] ${isReady ? "text-emerald-500" : isOnline ? "text-sky-400" : "text-slate-600"}`}>
                            {isReady ? "Ready" : isOnline ? "Online" : "Offline"}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : (
              <p className="py-4 text-center text-sm text-slate-500">No players to wait for.</p>
            )}
          </div>
        ) : activeSession ? (
          <div className="flex flex-col items-center justify-center space-y-4 py-10">
            <h3 className="text-2xl font-bold text-white">{activeSession.title || "Untitled Session"}</h3>
            <div className="text-4xl font-mono text-limiar-400">
              <SessionTimer startedAt={activeSession.startedAt ?? activeSession.createdAt} />
            </div>
            <div className="flex gap-2 text-sm text-slate-500">
              <span>#{activeSession.number}</span>
              <span className="text-emerald-400">● Active</span>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center space-y-4 py-10">
            <p className="mb-2 text-slate-400">No active session</p>
            <button
              onClick={onActivateClick}
              disabled={creating}
              className="rounded-full bg-limiar-500 px-8 py-3 text-sm font-bold uppercase tracking-widest text-white shadow-lg shadow-limiar-500/20 hover:bg-limiar-400 disabled:opacity-50 transition-all active:scale-95"
            >
              Start Session
            </button>
          </div>
        )}
      </div>

      {activeSession?.status === "ACTIVE" && (
        <div className="mt-6 grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
          <div className="rounded-2xl border border-slate-800 bg-linear-to-br from-slate-950/60 to-slate-900/40 p-4">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-[10px] font-semibold uppercase tracking-[0.35em] text-slate-500">
                  Shop Control
                </label>
                <p className="mt-1 text-xs text-slate-400">Broadcast the shop command to players.</p>
              </div>
              <span className={`rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] ${shopUiOpen ? "border-emerald-500/40 text-emerald-300" : "border-slate-700 text-slate-400"}`}>
                {shopUiOpen ? "Live" : "Closed"}
              </span>
            </div>
            <button
              onClick={() => onCommand(shopUiOpen ? "close_shop" : "open_shop")}
              disabled={commandSending}
              className={`mt-4 w-full rounded-2xl px-4 py-3 text-xs font-semibold uppercase tracking-[0.25em] transition-colors ${shopUiOpen ? "bg-rose-900/40 text-rose-200 hover:bg-rose-900/60" : "bg-limiar-500/80 text-white hover:bg-limiar-500"}`}
            >
              {shopUiOpen ? "Close Shop" : "Open Shop"}
            </button>
            {commandFeedback && (commandFeedback.type === "open_shop" || commandFeedback.type === "close_shop") && (
              <div className={`mt-3 rounded-2xl border px-3 py-2 text-[11px] ${commandFeedback.tone === "success" ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-300" : "border-rose-500/20 bg-rose-500/10 text-rose-200"}`}>
                {commandFeedback.message}
              </div>
            )}
          </div>

          <div className="rounded-2xl border border-slate-800 bg-linear-to-br from-slate-950/60 to-slate-900/40 p-4">
            <div>
              <label className="text-[10px] font-semibold uppercase tracking-[0.35em] text-slate-500">
                Dice Request
              </label>
              <p className="mt-1 text-xs text-slate-400">Choose a die, target player (optional) and request.</p>
            </div>
            <div className="mt-4 space-y-3">
              <div className="flex flex-wrap items-center gap-3">
                <select
                  value={rollExpression}
                  onChange={(event) => setRollExpression(event.target.value)}
                  className="flex-1 rounded-2xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-white focus:border-limiar-500 focus:outline-none"
                >
                  {rollOptions.map((option) => (
                    <option key={option} value={option} className="text-slate-900">
                      {option.toUpperCase()}
                    </option>
                  ))}
                </select>
                <select
                  value={rollTargetUserId ?? ""}
                  onChange={(event) => setRollTargetUserId(event.target.value || null)}
                  className="flex-1 rounded-2xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-limiar-500 focus:outline-none"
                >
                  <option value="">All players</option>
                  {partyPlayers.map((player) => (
                    <option key={player.userId} value={player.userId}>
                      {player.displayName || player.username || "Player"}
                    </option>
                  ))}
                </select>
              </div>
              <input
                type="text"
                value={rollReason}
                onChange={(event) => setRollReason(event.target.value)}
                placeholder="Reason (e.g. Perception check)"
                className="w-full rounded-2xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white placeholder:text-slate-600 focus:border-limiar-500 focus:outline-none"
              />
              <div className="flex overflow-hidden rounded-2xl border border-slate-700 text-[10px] font-bold uppercase tracking-widest">
                {(["normal", "advantage", "disadvantage"] as const).map((option) => (
                  <button
                    key={option}
                    type="button"
                    onClick={() => setRollAdvantage(option)}
                    className={`flex-1 py-2 transition-colors ${rollAdvantage === option ? option === "advantage" ? "bg-emerald-500/20 text-emerald-400" : option === "disadvantage" ? "bg-red-500/20 text-red-400" : "bg-slate-700 text-white" : "bg-slate-900 text-slate-500 hover:bg-slate-800"}`}
                  >
                    {option === "normal" ? "Normal" : option === "advantage" ? "Adv." : "Disadv."}
                  </button>
                ))}
              </div>
              <button
                onClick={() => onCommand("request_roll", { expression: rollExpression })}
                disabled={commandSending}
                className="w-full rounded-2xl bg-slate-800 px-4 py-2 text-xs font-semibold uppercase tracking-[0.25em] text-slate-200 hover:bg-slate-700"
              >
                Request Roll{rollTargetUserId ? ` → ${partyPlayers.find((player) => player.userId === rollTargetUserId)?.displayName ?? "Player"}` : ""}
              </button>
              {commandFeedback?.type === "request_roll" && (
                <div className={`rounded-2xl border px-3 py-2 text-[11px] ${commandFeedback.tone === "success" ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-300" : "border-rose-500/20 bg-rose-500/10 text-rose-200"}`}>
                  {commandFeedback.message}
                </div>
              )}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-linear-to-br from-slate-950/60 to-slate-900/40 p-4">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-[10px] font-semibold uppercase tracking-[0.35em] text-slate-500">
                  Combat Control
                </label>
                <p className="mt-1 text-xs text-slate-400">
                  Mark the session as in combat and keep entity sheets ready for players.
                </p>
              </div>
              <span className={`rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] ${combatUiActive ? "border-rose-500/40 text-rose-300" : "border-slate-700 text-slate-400"}`}>
                {combatUiActive ? "Live" : "Standby"}
              </span>
            </div>
            <button
              onClick={() => onCommand(combatUiActive ? "end_combat" : "start_combat")}
              disabled={commandSending}
              className={`mt-4 w-full rounded-2xl px-4 py-3 text-xs font-semibold uppercase tracking-[0.25em] transition-colors ${combatUiActive ? "bg-slate-800 text-slate-200 hover:bg-slate-700" : "bg-rose-900/50 text-rose-100 hover:bg-rose-900/70"}`}
            >
              {combatUiActive ? "End Combat" : "Start Combat"}
            </button>
            {commandFeedback && (commandFeedback.type === "start_combat" || commandFeedback.type === "end_combat") && (
              <div className={`mt-3 rounded-2xl border px-3 py-2 text-[11px] ${commandFeedback.tone === "success" ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-300" : "border-rose-500/20 bg-rose-500/10 text-rose-200"}`}>
                {commandFeedback.message}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  </div>
);
