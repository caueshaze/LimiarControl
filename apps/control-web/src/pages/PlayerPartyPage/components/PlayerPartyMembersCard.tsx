import type { PartyMemberSummary } from "../../../shared/api/partiesRepo";
import { useLocale } from "../../../shared/hooks/useLocale";
import { getMemberBadgeLabel } from "../playerParty.utils";

type Props = {
  members: PartyMemberSummary[];
  currentUserId?: string;
  readyUserIds?: string[];
};

export const PlayerPartyMembersCard = ({
  members,
  currentUserId,
  readyUserIds = [],
}: Props) => {
  const { t } = useLocale();

  return (
    <section className="rounded-4xl border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] px-6 py-5 shadow-[0_18px_60px_rgba(2,6,23,0.2)]">
      <div className="flex items-start justify-between gap-4 border-b border-white/8 pb-4">
        <div className="space-y-1">
          <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-500">
            {t("playerParty.membersTitle")}
          </p>
          <h2 className="text-xl font-semibold text-white">
            {t("playerParty.membersHeading")}
          </h2>
          <p className="max-w-xl text-sm leading-7 text-slate-400">
            {t("playerParty.membersDescription")}
          </p>
        </div>

        <span className="rounded-full border border-white/8 bg-white/4 px-3 py-1.5 text-xs font-semibold text-slate-200">
          {members.length}
        </span>
      </div>

      <div className="mt-4 space-y-3">
        {members.map((member) => {
          const isReady = readyUserIds.includes(member.userId);
          const badgeLabel = getMemberBadgeLabel(member, t);
          const tone =
            member.role === "GM"
              ? "border-sky-400/20 bg-sky-400/10 text-sky-200"
              : member.status === "joined"
                ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-200"
                : member.status === "invited"
                  ? "border-amber-500/20 bg-amber-500/10 text-amber-200"
                  : "border-white/10 bg-white/4 text-slate-300";

          const name =
            member.displayName || member.username || t("playerParty.memberFallback");

          return (
            <article
              key={member.userId}
              className="flex items-center justify-between gap-4 rounded-3xl border border-white/8 bg-white/3 px-4 py-4"
            >
              <div className="flex min-w-0 items-center gap-3">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-white/10 bg-white/5 text-sm font-bold uppercase text-limiar-100">
                  {name.charAt(0)}
                </div>

                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="truncate text-sm font-semibold text-white">{name}</p>
                    {member.userId === currentUserId ? (
                      <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-300">
                        {t("playerParty.memberYou")}
                      </span>
                    ) : null}
                  </div>
                  {member.username ? (
                    <p className="truncate text-xs text-slate-500">@{member.username}</p>
                  ) : null}
                </div>
              </div>

              <div className="flex flex-wrap items-center justify-end gap-2">
                {isReady ? (
                  <span className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.22em] text-emerald-200">
                    {t("playerParty.memberReady")}
                  </span>
                ) : null}
                <span
                  className={`rounded-full border px-3 py-1 text-[10px] font-bold uppercase tracking-[0.22em] ${tone}`}
                >
                  {badgeLabel}
                </span>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
};
