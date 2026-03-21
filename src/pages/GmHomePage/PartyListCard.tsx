import { useLocale } from "../../shared/hooks/useLocale";
import type { PartySummary } from "../../shared/api/partiesRepo";

type Props = {
  party: PartySummary;
  campaignName?: string;
  systemLabel?: string;
  onOpen: () => void;
  featured?: boolean;
};

export const PartyListCard = ({
  party,
  campaignName,
  systemLabel,
  onOpen,
  featured = false,
}: Props) => {
  const { t, locale } = useLocale();

  const createdLabel = new Intl.DateTimeFormat(locale === "pt" ? "pt-BR" : "en-US", {
    day: "2-digit",
    month: "short",
  }).format(new Date(party.createdAt));

  return (
    <article
      onClick={onOpen}
      className={`group cursor-pointer rounded-[28px] border p-5 transition hover:translate-y-[-1px] ${
        featured
          ? "border-limiar-300/20 bg-[linear-gradient(145deg,rgba(34,197,94,0.08),rgba(15,23,42,0.88)_35%,rgba(2,6,23,0.96))] shadow-[0_20px_60px_rgba(15,23,42,0.3)] hover:border-limiar-300/30"
          : "border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] shadow-[0_18px_50px_rgba(2,6,23,0.22)] hover:border-white/14 hover:bg-[linear-gradient(180deg,rgba(24,32,54,0.88),rgba(2,6,23,0.94))]"
      }`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          {featured && (
            <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-limiar-100/80">
              {t("gm.home.continuePartyLabel")}
            </p>
          )}
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

        <span
          className={`flex-shrink-0 rounded-full px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.22em] transition ${
            featured
              ? "border border-limiar-300/15 bg-limiar-400/10 text-limiar-50 group-hover:border-limiar-300/30"
              : "border border-white/8 bg-white/[0.04] text-slate-400 group-hover:border-limiar-300/20 group-hover:text-limiar-100"
          }`}
        >
          {t("gm.home.openAction")} →
        </span>
      </div>
    </article>
  );
};
