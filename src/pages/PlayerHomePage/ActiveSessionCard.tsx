import { useLocale } from "../../shared/hooks/useLocale";

type Props = {
  partyName: string;
  campaignName?: string;
  sessionTitle: string;
  sessionNumber?: number;
  sessionStatus: "LOBBY" | "ACTIVE";
  onEnter: () => void;
};

export const ActiveSessionCard = ({
  partyName,
  campaignName,
  sessionTitle,
  sessionNumber,
  sessionStatus,
  onEnter,
}: Props) => {
  const { t } = useLocale();
  const isLobby = sessionStatus === "LOBBY";

  return (
    <div
      onClick={onEnter}
      className="group relative cursor-pointer overflow-hidden rounded-[32px] border border-emerald-500/25 bg-[linear-gradient(180deg,rgba(7,28,21,0.92),rgba(2,10,14,0.96))] p-6 shadow-[0_24px_70px_rgba(0,0,0,0.28)] transition-all hover:border-emerald-500/45 hover:translate-y-[-1px] hover:shadow-[0_0_60px_rgba(34,197,94,0.14)]"
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(34,197,94,0.12),transparent_34%),linear-gradient(90deg,rgba(255,255,255,0.04)_1px,transparent_1px),linear-gradient(rgba(255,255,255,0.04)_1px,transparent_1px)] [background-size:auto,42px_42px,42px_42px]" />

      <div className="relative flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
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
                {isLobby ? t("home.player.lobbyLabel") : t("home.player.activeSessionLabel")}
              </p>
              {sessionNumber ? (
                <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-200">
                  #{sessionNumber}
                </span>
              ) : null}
            </div>

            <div className="space-y-1">
              <h2 className="text-2xl font-semibold text-white">{sessionTitle}</h2>
              <p className="text-sm text-slate-300">{partyName}</p>
            </div>

            <div className="flex flex-wrap gap-2">
              {campaignName && (
                <span className="rounded-full border border-white/10 bg-white/[0.05] px-3 py-1.5 text-xs font-semibold text-slate-100">
                  {campaignName}
                </span>
              )}
              <span className="rounded-full border border-emerald-300/15 bg-emerald-400/10 px-3 py-1.5 text-xs font-semibold text-emerald-100">
                {isLobby ? t("home.player.statusLobby") : t("home.player.statusLive")}
              </span>
            </div>
          </div>
        </div>

        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            onEnter();
          }}
          className="shrink-0 rounded-full bg-emerald-500 px-7 py-3 text-sm font-bold uppercase tracking-[0.22em] text-white shadow-[0_0_20px_rgba(34,197,94,0.35)] transition-all hover:bg-emerald-400 hover:shadow-[0_0_30px_rgba(34,197,94,0.44)] active:scale-95"
        >
          {isLobby ? t("home.player.joinLobbyAction") : t("home.player.enterSession")} →
        </button>
      </div>
    </div>
  );
};
