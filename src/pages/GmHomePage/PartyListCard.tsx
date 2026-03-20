import { useLocale } from "../../shared/hooks/useLocale";
import type { PartySummary } from "../../shared/api/partiesRepo";

type Props = {
  party: PartySummary;
  campaignName?: string;
  systemLabel?: string;
  onOpen: () => void;
};

export const PartyListCard = ({ party, campaignName, systemLabel, onOpen }: Props) => {
  const { t, locale } = useLocale();

  const createdLabel = new Intl.DateTimeFormat(locale === "pt" ? "pt-BR" : "en-US", {
    day: "2-digit",
    month: "short",
  }).format(new Date(party.createdAt));

  return (
    <article
      onClick={onOpen}
      className="group cursor-pointer rounded-[28px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] p-5 shadow-[0_18px_50px_rgba(2,6,23,0.22)] transition hover:translate-y-[-1px] hover:border-white/14 hover:bg-[linear-gradient(180deg,rgba(24,32,54,0.88),rgba(2,6,23,0.94))]"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-base font-semibold text-white">{party.name}</h3>

          <div className="mt-3 flex flex-wrap items-center gap-2">
            {campaignName && (
              <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-300">
                {campaignName}
              </span>
            )}
            {systemLabel && (
              <span className="rounded-full border border-sky-300/15 bg-sky-400/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-sky-100">
                {systemLabel}
              </span>
            )}
          </div>

          <p className="mt-4 text-xs uppercase tracking-[0.2em] text-slate-500">
            {t("gm.home.lastCreated")} {createdLabel}
          </p>
        </div>

        <span className="flex-shrink-0 rounded-full border border-white/8 bg-white/[0.04] px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-400 transition group-hover:border-limiar-300/20 group-hover:text-limiar-100">
          {t("gm.home.openAction")} →
        </span>
      </div>
    </article>
  );
};
