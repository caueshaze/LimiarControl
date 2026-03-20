import type { PartyInvite } from "../../shared/api/partiesRepo";
import { useLocale } from "../../shared/hooks/useLocale";

type PendingInviteCardProps = {
  invite: PartyInvite;
  onJoin: () => void;
  onDecline: () => void;
};

export const PendingInviteCard = ({
  invite,
  onJoin,
  onDecline,
}: PendingInviteCardProps) => {
  const { t } = useLocale();

  const sessionStatus = invite.activeSession?.status ?? null;
  const sessionLabel =
    sessionStatus === "ACTIVE"
      ? t("home.player.statusLive")
      : sessionStatus === "LOBBY"
        ? t("home.player.statusLobby")
        : null;

  return (
    <article
      className={`rounded-[28px] border p-5 shadow-[0_18px_45px_rgba(2,6,23,0.28)] transition ${
        sessionStatus === "ACTIVE"
          ? "border-emerald-400/25 bg-[linear-gradient(180deg,rgba(6,22,18,0.95),rgba(4,12,16,0.95))]"
          : sessionStatus === "LOBBY"
            ? "border-amber-400/20 bg-[linear-gradient(180deg,rgba(28,20,7,0.95),rgba(15,10,4,0.95))]"
            : "border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.88),rgba(2,6,23,0.94))]"
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-2">
          <p className="text-lg font-semibold text-white">{invite.party.name}</p>
          <p className="text-sm text-slate-400">{invite.campaignName}</p>
        </div>
        {sessionLabel && (
          <span
            className={`rounded-full border px-3 py-1 text-[10px] font-bold uppercase tracking-[0.24em] ${
              sessionStatus === "ACTIVE"
                ? "border-emerald-300/20 bg-emerald-400/10 text-emerald-100"
                : "border-amber-300/20 bg-amber-400/10 text-amber-100"
            }`}
          >
            {sessionLabel}
          </span>
        )}
      </div>

      {invite.activeSession?.title && (
        <p className="mt-4 rounded-[18px] border border-white/8 bg-white/[0.04] px-4 py-3 text-sm text-slate-200">
          {invite.activeSession.title}
        </p>
      )}

      <div className="mt-5 flex flex-wrap gap-3">
        <button
          type="button"
          onClick={onDecline}
          className="rounded-full border border-white/10 bg-white/[0.04] px-4 py-2.5 text-xs font-semibold uppercase tracking-[0.2em] text-slate-200 transition hover:border-white/20 hover:bg-white/[0.08]"
        >
          {t("home.player.declineInvite")}
        </button>
        <button
          type="button"
          onClick={onJoin}
          className="rounded-full bg-limiar-500 px-4 py-2.5 text-xs font-bold uppercase tracking-[0.2em] text-white transition hover:bg-limiar-400"
        >
          {t("home.player.acceptInvite")}
        </button>
      </div>
    </article>
  );
};
