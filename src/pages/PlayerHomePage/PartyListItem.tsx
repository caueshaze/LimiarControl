import { useLocale } from "../../shared/hooks/useLocale";

type SessionStatus = "ACTIVE" | "LOBBY" | null;

type Props = {
  partyName: string;
  campaignName?: string;
  sessionStatus: SessionStatus;
  sessionTitle?: string;
  onClick: () => void;
};

export const PartyListItem = ({
  partyName,
  campaignName,
  sessionStatus,
  sessionTitle,
  onClick,
}: Props) => {
  const { t } = useLocale();

  const statusLabel =
    sessionStatus === "ACTIVE"
      ? t("home.player.statusLive")
      : sessionStatus === "LOBBY"
        ? t("home.player.statusLobby")
        : null;

  return (
    <article
      onClick={onClick}
      className="group cursor-pointer rounded-[28px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] p-5 shadow-[0_18px_50px_rgba(2,6,23,0.22)] transition hover:translate-y-[-1px] hover:border-white/14 hover:bg-[linear-gradient(180deg,rgba(24,32,54,0.88),rgba(2,6,23,0.94))]"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            {statusLabel ? (
              <span
                className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-[10px] font-bold uppercase tracking-[0.22em] ${
                  sessionStatus === "ACTIVE"
                    ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-300"
                    : "border-amber-500/20 bg-amber-500/10 text-amber-300"
                }`}
              >
                <span
                  className={`h-1.5 w-1.5 animate-pulse rounded-full ${
                    sessionStatus === "ACTIVE" ? "bg-emerald-400" : "bg-amber-400"
                  }`}
                />
                {statusLabel}
              </span>
            ) : (
              <span className="h-2 w-2 shrink-0 rounded-full bg-slate-700" />
            )}
            <h3 className="truncate text-base font-semibold text-white">{partyName}</h3>
          </div>

          <div className="space-y-1">
            {campaignName && <p className="text-sm text-slate-300">{campaignName}</p>}
            {sessionTitle ? (
              <p className="text-xs uppercase tracking-[0.18em] text-slate-500">{sessionTitle}</p>
            ) : (
              <p className="text-xs uppercase tracking-[0.18em] text-slate-500">
                {t("home.player.sessionInactive")}
              </p>
            )}
          </div>
        </div>

        <span className="flex-shrink-0 rounded-full border border-white/8 bg-white/[0.04] px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-400 transition group-hover:border-limiar-300/20 group-hover:text-limiar-100">
          {t("home.player.openParty")} →
        </span>
      </div>
    </article>
  );
};
