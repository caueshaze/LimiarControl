import type { LobbyStatus } from "../../shared/api/sessionsRepo";
import { useLocale } from "../../shared/hooks/useLocale";

type Props = {
  lobbyStatus: LobbyStatus | null;
  onlineUsers: Record<string, string>;
};

export const GmDashboardLobbyStatus = ({ lobbyStatus, onlineUsers }: Props) => {
  const { t } = useLocale();

  if (!lobbyStatus || lobbyStatus.expected.length === 0) {
    return (
      <p className="py-4 text-center text-sm text-slate-500">{t("gm.dashboard.noPlayersToWait")}</p>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-[10px] font-bold uppercase tracking-[0.25em] text-slate-500">
        {t("gm.dashboard.playersCount")} ({lobbyStatus.ready.length}/{lobbyStatus.expected.length})
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
                  {isReady
                    ? t("gm.dashboard.playerReady")
                    : isOnline
                    ? t("gm.dashboard.playerOnline")
                    : t("gm.dashboard.playerOffline")}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
