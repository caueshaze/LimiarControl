import { Link } from "react-router-dom";
import { routes } from "../../../app/routes/routes";
import { useLocale } from "../../../shared/hooks/useLocale";

type Props = {
  partyId: string;
  isPlayer: boolean;
  hasCharacterSheet: boolean | null;
  isSessionActive: boolean;
};

export const PlayerPartySheetCard = ({
  partyId,
  isPlayer,
  hasCharacterSheet,
  isSessionActive,
}: Props) => {
  const { t } = useLocale();

  if (!isPlayer) {
    return null;
  }

  if (hasCharacterSheet === null) {
    return (
      <section className="rounded-[28px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] px-5 py-4">
        <p className="text-sm text-slate-400">{t("playerParty.sheetLoading")}</p>
      </section>
    );
  }

  if (hasCharacterSheet === false) {
    return (
      <section className="relative overflow-hidden rounded-[30px] border border-amber-500/25 bg-[linear-gradient(180deg,rgba(49,29,7,0.82),rgba(2,6,23,0.95))] px-5 py-5">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(251,191,36,0.08),transparent_34%)]" />
        <div className="relative flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-1">
            <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-amber-300">
              {t("playerParty.sheetMissingEyebrow")}
            </p>
            <h3 className="text-lg font-semibold text-white">
              {t("playerParty.sheetMissingTitle")}
            </h3>
            <p className="text-sm leading-7 text-slate-300">
              {t("playerParty.sheetMissingBody")}
            </p>
          </div>

          <Link
            to={routes.characterSheetParty.replace(":partyId", partyId)}
            className="shrink-0 rounded-full bg-amber-500 px-6 py-2.5 text-xs font-bold uppercase tracking-[0.22em] text-slate-950 transition hover:bg-amber-400"
          >
            {t("playerParty.createSheet")} →
          </Link>
        </div>
      </section>
    );
  }

  return (
    <section className="rounded-[30px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] px-5 py-5 shadow-[0_18px_60px_rgba(2,6,23,0.18)]">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="space-y-1">
          <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-emerald-300">
            {t("playerParty.sheetReadyEyebrow")}
          </p>
          <h3 className="text-lg font-semibold text-white">
            {t("playerParty.sheetReadyTitle")}
          </h3>
          <p className="text-sm leading-7 text-slate-300">
            {t("playerParty.sheetReadyBody")}
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <Link
            to={routes.characterSheetParty.replace(":partyId", partyId)}
            className="rounded-full border border-white/10 bg-white/[0.03] px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-slate-200 transition hover:border-white/20 hover:text-white"
          >
            {t("playerParty.viewSheet")}
          </Link>
          {isSessionActive ? (
            <Link
              to={`${routes.characterSheetParty.replace(":partyId", partyId)}?mode=play`}
              className="rounded-full border border-limiar-300/20 bg-limiar-300/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-limiar-100 transition hover:border-limiar-300/30 hover:bg-limiar-300/15"
            >
              {t("playerParty.playSheet")}
            </Link>
          ) : null}
        </div>
      </div>
    </section>
  );
};
