import { Link } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { formatClassDisplayName } from "../../features/character-sheet/data/classes";
import { useLocale } from "../../shared/hooks/useLocale";
import type { PartyDetailsPlayerResource } from "./usePartyDetailsResources";

type PlayerSheetsCardProps = {
  activeSessionPartyId: string | null;
  campaignId: string;
  players: PartyDetailsPlayerResource[];
  loading: boolean;
  partyId: string;
};

export const PartyDetailsPlayerSheetsCard = ({
  activeSessionPartyId,
  campaignId,
  loading,
  partyId,
  players,
}: PlayerSheetsCardProps) => {
  const { t } = useLocale();

  return (
    <div className="rounded-[30px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.95))] p-6">
      <div className="border-b border-white/8 pb-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-cyan-300">
          {t("gm.party.sheetsTitle")}
        </p>
        <p className="mt-3 text-sm leading-7 text-slate-300">
          {t("gm.party.sheetsDescription")}
        </p>
      </div>

      <div className="mt-5 space-y-3">
        {loading ? (
          <p className="text-sm text-slate-400">{t("gm.party.loadingResources")}</p>
        ) : players.length === 0 ? (
          <p className="text-sm text-slate-500">{t("gm.party.noPlayersYet")}</p>
        ) : (
          players.map((player) => {
            const sheetHref = player.hasSheet
              ? `${routes.characterSheetParty.replace(":partyId", partyId)}?${new URLSearchParams({
                  mode: "creation",
                  playerId: player.userId,
                  playerName: player.displayName,
                }).toString()}`
              : null;
            const playSheetHref = activeSessionPartyId
              ? `${routes.characterSheetParty.replace(":partyId", activeSessionPartyId)}?${new URLSearchParams({
                  campaignId,
                  mode: "play",
                  playerId: player.userId,
                  playerName: player.displayName,
                }).toString()}`
              : null;

            return (
              <article
                key={player.userId}
                className="rounded-3xl border border-white/8 bg-white/3 p-4"
              >
                <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                  <div>
                    <p className="text-base font-semibold text-white">{player.displayName}</p>
                    <p className="mt-1 text-xs text-slate-500">
                      {player.sheet
                        ? `${player.sheet.name || "Sem nome"} · ${player.sheet.class ? formatClassDisplayName(player.sheet.class, player.sheet.subclass, player.sheet.subclassConfig) : "Classe?"} Lv${player.sheet.level}`
                        : player.sheetStatus === "pending_acceptance"
                          ? t("gm.party.sheetPendingAcceptance")
                          : t("gm.party.sheetMissing")}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <span
                      className={`rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] ${
                        player.sheetStatus === "accepted"
                          ? "border border-emerald-400/20 bg-emerald-400/10 text-emerald-200"
                          : player.sheetStatus === "pending_acceptance"
                            ? "border border-sky-400/20 bg-sky-400/10 text-sky-200"
                            : "border border-amber-400/20 bg-amber-400/10 text-amber-200"
                      }`}
                    >
                      {player.sheetStatus === "accepted"
                        ? t("gm.party.sheetAccepted")
                        : player.sheetStatus === "pending_acceptance"
                          ? t("gm.party.sheetPendingAcceptance")
                          : t("gm.party.sheetMissing")}
                    </span>
                    {sheetHref ? (
                      <Link
                        to={sheetHref}
                        className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-cyan-100 transition hover:bg-cyan-400/20"
                      >
                        {t("gm.party.inspectSheet")}
                      </Link>
                    ) : null}
                    {playSheetHref ? (
                      <Link
                        to={playSheetHref}
                        className="rounded-full border border-limiar-400/20 bg-limiar-400/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-limiar-100 transition hover:bg-limiar-400/20"
                      >
                        {t("gm.party.openPlaySheet")}
                      </Link>
                    ) : null}
                  </div>
                </div>
              </article>
            );
          })
        )}
      </div>
    </div>
  );
};
