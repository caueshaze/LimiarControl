import { Link } from "react-router-dom";
import { routes } from "../../../app/routes/routes";
import { useLocale } from "../../../shared/hooks/useLocale";
import type { PartyActiveSession } from "../../../shared/api/partiesRepo";
import {
  formatPartyDate,
  getPlayerPartyStatusKey,
} from "../playerParty.utils";

type Props = {
  partyName: string;
  memberCount: number;
  sessionsCount: number;
  createdAt: string;
  hasCharacterSheet: boolean | null;
  sessionStatus: PartyActiveSession["status"] | null;
};

export const PlayerPartyHeader = ({
  partyName,
  memberCount,
  sessionsCount,
  createdAt,
  hasCharacterSheet,
  sessionStatus,
}: Props) => {
  const { t, locale } = useLocale();

  const sessionStatusLabel = t(getPlayerPartyStatusKey(sessionStatus));
  const sheetValue =
    hasCharacterSheet === true
      ? t("playerParty.sheetStatReady")
      : hasCharacterSheet === false
        ? t("playerParty.sheetStatMissing")
        : "--";

  const sessionTone =
    sessionStatus === "ACTIVE"
      ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-200"
      : sessionStatus === "LOBBY"
        ? "border-amber-500/25 bg-amber-500/10 text-amber-200"
        : "border-white/10 bg-white/[0.04] text-slate-200";

  return (
    <header className="relative overflow-hidden rounded-[34px] border border-white/10 bg-[linear-gradient(180deg,rgba(17,24,39,0.94),rgba(2,6,23,0.98))] px-6 py-6 shadow-[0_24px_80px_rgba(2,6,23,0.34)] sm:px-7">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(125,211,252,0.08),transparent_30%),radial-gradient(circle_at_bottom_right,rgba(99,102,241,0.12),transparent_34%),linear-gradient(90deg,rgba(255,255,255,0.04)_1px,transparent_1px),linear-gradient(rgba(255,255,255,0.04)_1px,transparent_1px)] [background-size:auto,auto,42px_42px,42px_42px]" />

      <div className="relative space-y-6">
        <Link
          to={routes.home}
          className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-300 transition hover:border-white/16 hover:text-white"
        >
          <span aria-hidden>←</span>
          {t("playerParty.backHome")}
        </Link>

        <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-2xl space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-limiar-300/20 bg-limiar-300/10 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.25em] text-limiar-200">
                {t("playerParty.eyebrow")}
              </span>
              <span
                className={`rounded-full border px-3 py-1 text-[10px] font-bold uppercase tracking-[0.25em] ${sessionTone}`}
              >
                {sessionStatusLabel}
              </span>
            </div>

            <div className="space-y-2">
              <h1 className="text-3xl font-semibold tracking-tight text-white sm:text-4xl">
                {partyName}
              </h1>
              <p className="max-w-xl text-sm leading-7 text-slate-300 sm:text-[15px]">
                {t("playerParty.description")}
              </p>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 xl:min-w-[360px] xl:max-w-[420px]">
            <div className="rounded-[24px] border border-white/8 bg-white/[0.04] px-4 py-4">
              <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-500">
                {t("playerParty.membersStat")}
              </p>
              <p className="mt-2 text-2xl font-semibold text-white">{memberCount}</p>
            </div>
            <div className="rounded-[24px] border border-white/8 bg-white/[0.04] px-4 py-4">
              <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-500">
                {t("playerParty.sessionsStat")}
              </p>
              <p className="mt-2 text-2xl font-semibold text-white">{sessionsCount}</p>
            </div>
            <div className="rounded-[24px] border border-white/8 bg-white/[0.04] px-4 py-4">
              <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-500">
                {t("playerParty.createdStat")}
              </p>
              <p className="mt-2 text-sm font-semibold text-white">
                {formatPartyDate(createdAt, locale)}
              </p>
            </div>
            <div className="rounded-[24px] border border-white/8 bg-white/[0.04] px-4 py-4">
              <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-500">
                {t("playerParty.sheetStat")}
              </p>
              <p className="mt-2 text-sm font-semibold text-white">{sheetValue}</p>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
