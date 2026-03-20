import type { PartyActiveSession } from "../../../shared/api/partiesRepo";
import type { LobbyStatus } from "../../../shared/api/sessionsRepo";
import { useLocale } from "../../../shared/hooks/useLocale";

type Props = {
  activeSession: PartyActiveSession | null;
  lobbyStatus: LobbyStatus | null;
  alreadyInLobby: boolean;
  joiningLobby: boolean;
  onJoinLobby: () => void;
  onEnterBoard: () => void;
};

export const PlayerPartySessionCard = ({
  activeSession,
  lobbyStatus,
  alreadyInLobby,
  joiningLobby,
  onJoinLobby,
  onEnterBoard,
}: Props) => {
  const { t } = useLocale();

  if (!activeSession) {
    return (
      <section className="rounded-[30px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] px-6 py-5 shadow-[0_18px_60px_rgba(2,6,23,0.22)]">
        <div className="flex items-start gap-4">
          <div className="mt-1 h-3 w-3 shrink-0 rounded-full bg-slate-700" />
          <div className="space-y-2">
            <p className="text-[10px] font-bold uppercase tracking-[0.25em] text-slate-500">
              {t("playerParty.statusIdle")}
            </p>
            <h2 className="text-xl font-semibold text-white">
              {t("playerParty.idleTitle")}
            </h2>
            <p className="max-w-2xl text-sm leading-7 text-slate-400">
              {t("playerParty.idleBody")}
            </p>
          </div>
        </div>
      </section>
    );
  }

  if (activeSession.status === "ACTIVE") {
    return (
      <section className="group relative overflow-hidden rounded-[32px] border border-emerald-500/25 bg-[linear-gradient(180deg,rgba(8,37,29,0.92),rgba(2,10,14,0.96))] px-6 py-6 shadow-[0_24px_70px_rgba(0,0,0,0.28)]">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(34,197,94,0.12),transparent_34%),linear-gradient(90deg,rgba(255,255,255,0.04)_1px,transparent_1px),linear-gradient(rgba(255,255,255,0.04)_1px,transparent_1px)] [background-size:auto,42px_42px,42px_42px]" />
        <div className="relative flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-start gap-4">
            <div className="mt-1 shrink-0">
              <span className="relative flex h-3 w-3">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
                <span className="relative inline-flex h-3 w-3 rounded-full bg-emerald-500" />
              </span>
            </div>

            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-[10px] font-bold uppercase tracking-[0.25em] text-emerald-300">
                  {t("playerParty.statusActive")}
                </p>
                <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-200">
                  #{activeSession.number}
                </span>
              </div>

              <div className="space-y-1">
                <h2 className="text-2xl font-semibold text-white">{activeSession.title}</h2>
                <p className="text-sm leading-7 text-slate-300">
                  {t("playerParty.activeBody")}
                </p>
              </div>
            </div>
          </div>

          <button
            type="button"
            onClick={onEnterBoard}
            className="shrink-0 rounded-full bg-emerald-500 px-7 py-3 text-sm font-bold uppercase tracking-[0.22em] text-white shadow-[0_0_20px_rgba(34,197,94,0.35)] transition-all hover:bg-emerald-400 hover:shadow-[0_0_30px_rgba(34,197,94,0.44)] active:scale-95"
          >
            {t("playerParty.openBoard")} →
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="relative overflow-hidden rounded-[32px] border border-amber-500/25 bg-[linear-gradient(180deg,rgba(49,29,7,0.82),rgba(2,6,23,0.95))] px-6 py-6 shadow-[0_24px_70px_rgba(0,0,0,0.22)]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(251,191,36,0.12),transparent_34%),linear-gradient(90deg,rgba(255,255,255,0.04)_1px,transparent_1px),linear-gradient(rgba(255,255,255,0.04)_1px,transparent_1px)] [background-size:auto,42px_42px,42px_42px]" />
      <div className="relative flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex items-start gap-4">
          <div className="mt-1 shrink-0">
            <span className="relative flex h-3 w-3">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400 opacity-60" />
              <span className="relative inline-flex h-3 w-3 rounded-full bg-amber-500" />
            </span>
          </div>

          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-[10px] font-bold uppercase tracking-[0.25em] text-amber-300">
                {t("playerParty.statusLobby")}
              </p>
              <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-200">
                #{activeSession.number}
              </span>
            </div>

            <div className="space-y-1">
              <h2 className="text-2xl font-semibold text-white">{activeSession.title}</h2>
              <p className="max-w-2xl text-sm leading-7 text-slate-300">
                {alreadyInLobby
                  ? t("playerParty.lobbyWaiting")
                  : t("playerParty.lobbyBody")}
              </p>
            </div>

            {lobbyStatus && lobbyStatus.expected.length > 0 ? (
              <div className="space-y-2">
                <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-500">
                  {lobbyStatus.ready.length}/{lobbyStatus.expected.length} {t("playerParty.lobbyProgress")}
                </p>
                <div className="flex flex-wrap gap-2">
                  {lobbyStatus.expected.map((player) => {
                    const isReady = lobbyStatus.ready.includes(player.userId);
                    return (
                      <span
                        key={player.userId}
                        className={`rounded-full border px-3 py-1 text-[11px] font-semibold ${
                          isReady
                            ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-200"
                            : "border-white/10 bg-white/[0.04] text-slate-300"
                        }`}
                      >
                        {player.displayName}
                      </span>
                    );
                  })}
                </div>
              </div>
            ) : null}
          </div>
        </div>

        <div className="flex shrink-0 flex-col gap-3">
          {alreadyInLobby ? (
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/25 bg-emerald-500/10 px-5 py-2.5">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
              <span className="text-sm font-semibold text-emerald-300">
                {t("playerParty.lobbyConfirmed")}
              </span>
            </div>
          ) : (
            <button
              type="button"
              onClick={onJoinLobby}
              disabled={joiningLobby}
              className="rounded-full bg-amber-500 px-7 py-3 text-sm font-bold uppercase tracking-[0.22em] text-slate-950 shadow-[0_0_20px_rgba(251,191,36,0.3)] transition-all hover:bg-amber-400 active:scale-95 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {joiningLobby ? t("playerParty.lobbyJoining") : `${t("playerParty.lobbyJoin")} →`}
            </button>
          )}
        </div>
      </div>
    </section>
  );
};
