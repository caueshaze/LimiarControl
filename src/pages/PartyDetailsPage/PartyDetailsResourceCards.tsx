import { Link } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import type { PartyActiveSession } from "../../shared/api/partiesRepo";
import { useLocale } from "../../shared/hooks/useLocale";
import type { PartyDetailsPlayerResource } from "./usePartyDetailsResources";

type MissingSheetsBannerProps = {
  players: { displayName: string; userId: string }[];
};

export const PartyDetailsMissingSheetsBanner = ({ players }: MissingSheetsBannerProps) => (
  <div className="rounded-3xl border border-amber-500/30 bg-amber-500/10 p-5">
    <p className="text-sm font-semibold text-amber-300">
      Nao e possivel iniciar a sessao. Os seguintes jogadores ainda nao possuem ficha:
    </p>
    <p className="mt-2 text-sm text-amber-100">
      {players.map((player) => player.displayName).join(", ")}
    </p>
  </div>
);

type ActiveSessionBannerProps = {
  campaignId: string;
  session: PartyActiveSession;
};

export const PartyDetailsActiveSessionBanner = ({
  campaignId,
  session,
}: ActiveSessionBannerProps) => {
  const { t } = useLocale();

  return (
    <div className="flex flex-col gap-4 rounded-[28px] border border-emerald-500/20 bg-[linear-gradient(135deg,rgba(16,185,129,0.12),rgba(2,6,23,0.72))] p-5 md:flex-row md:items-center md:justify-between">
      <div>
        <p className="text-xs uppercase tracking-[0.3em] text-emerald-300">
          {t("gm.party.sessionActive")}
        </p>
        <p className="mt-2 text-lg font-semibold text-white">{session.title || "Untitled Session"}</p>
        <p className="mt-1 text-sm text-emerald-100/80">
          {t("gm.party.activeSessionDescription")}
        </p>
      </div>
      <div className="flex items-center gap-3">
        <span className="rounded-full border border-emerald-400/30 bg-emerald-400/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-emerald-200">
          Live
        </span>
        <Link
          to={routes.campaignDashboard.replace(":campaignId", campaignId)}
          className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-white transition hover:border-emerald-300/40 hover:bg-emerald-400/10"
        >
          {t("gm.party.manageSession")}
        </Link>
      </div>
    </div>
  );
};

type OverviewStripProps = {
  activeSessionStatus: PartyActiveSession["status"] | null;
  invitedPlayers: number;
  joinedPlayers: number;
  readySheets: number;
  totalInventoryItems: number;
  totalPlayers: number;
};

export const PartyDetailsOverviewStrip = ({
  activeSessionStatus,
  invitedPlayers,
  joinedPlayers,
  readySheets,
  totalInventoryItems,
  totalPlayers,
}: OverviewStripProps) => {
  const { t } = useLocale();

  const sessionStateLabel =
    activeSessionStatus === "ACTIVE"
      ? t("gm.party.sessionActive")
      : activeSessionStatus === "LOBBY"
        ? t("gm.party.sessionLobby")
        : t("gm.party.sessionIdle");

  const cards = [
    { label: t("gm.party.joinedPlayers"), value: String(joinedPlayers) },
    { label: t("gm.party.invitesOpen"), value: String(invitedPlayers) },
    { label: t("gm.party.sheetsReady"), value: `${readySheets}/${totalPlayers}` },
    { label: t("gm.party.inventoryItems"), value: totalInventoryItems.toLocaleString() },
    { label: t("gm.party.sessionStatus"), value: sessionStateLabel },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
      {cards.map((card) => (
        <article
          key={card.label}
          className="rounded-3xl border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] p-4 shadow-[0_16px_36px_rgba(2,6,23,0.22)]"
        >
          <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-500">
            {card.label}
          </p>
          <p className="mt-3 text-2xl font-semibold text-white">{card.value}</p>
        </article>
      ))}
    </div>
  );
};

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
                        ? `${player.sheet.name || "Sem nome"} · ${player.sheet.class || "Classe?"} Lv${player.sheet.level}`
                        : t("gm.party.sheetMissing")}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <span
                      className={`rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] ${
                        player.hasSheet
                          ? "border border-emerald-400/20 bg-emerald-400/10 text-emerald-200"
                          : "border border-amber-400/20 bg-amber-400/10 text-amber-200"
                      }`}
                    >
                      {player.hasSheet ? t("gm.party.sheetReady") : t("gm.party.sheetMissing")}
                    </span>
                    {sheetHref ? (
                      <Link
                        to={sheetHref}
                        className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-cyan-100 transition hover:bg-cyan-400/20"
                      >
                        {t("gm.party.openSheet")}
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

type InventoryCardProps = {
  loadError: string | null;
  loading: boolean;
  players: PartyDetailsPlayerResource[];
};

export const PartyDetailsInventoryCard = ({
  loadError,
  loading,
  players,
}: InventoryCardProps) => {
  const { t } = useLocale();

  return (
    <div className="rounded-[30px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.95))] p-6">
      <div className="border-b border-white/8 pb-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-amber-300">
          {t("gm.party.inventoryTitle")}
        </p>
        <p className="mt-3 text-sm leading-7 text-slate-300">
          {t("gm.party.inventoryDescription")}
        </p>
      </div>

      <div className="mt-5 space-y-3">
        {loadError ? (
          <p className="text-sm text-rose-300">{loadError}</p>
        ) : loading ? (
          <p className="text-sm text-slate-400">{t("gm.party.loadingResources")}</p>
        ) : players.length === 0 ? (
          <p className="text-sm text-slate-500">{t("gm.party.noPlayersYet")}</p>
        ) : (
          players.map((player) => (
            <article
              key={player.userId}
              className="rounded-3xl border border-white/8 bg-white/3 p-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-base font-semibold text-white">{player.displayName}</p>
                  <p className="mt-2 text-xs text-slate-400">
                    {t("gm.party.inventoryItemsCount").replace("{n}", String(player.totalItems))}
                    {" · "}
                    {t("gm.party.inventoryTypesCount").replace("{n}", String(player.distinctItems))}
                    {" · "}
                    {t("gm.party.inventoryEquippedCount").replace("{n}", String(player.equippedCount))}
                  </p>
                </div>
                <span className="rounded-full border border-white/10 bg-white/4 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-300">
                  {player.totalItems > 0 ? "Loaded" : "Empty"}
                </span>
              </div>

              <div className="mt-4 space-y-2">
                {player.previewItems.length === 0 ? (
                  <p className="text-sm text-slate-500">{t("gm.party.inventoryPreviewEmpty")}</p>
                ) : (
                  player.previewItems.map((item) => (
                    <div
                      key={item.id}
                      className="flex items-center justify-between rounded-2xl border border-white/6 bg-slate-950/60 px-3 py-2"
                    >
                      <span className="text-sm text-white">
                        {item.name} <span className="text-slate-500">x{item.quantity}</span>
                      </span>
                      {item.isEquipped ? (
                        <span className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-emerald-200">
                          Equipped
                        </span>
                      ) : null}
                    </div>
                  ))
                )}
              </div>
            </article>
          ))
        )}
      </div>
    </div>
  );
};
