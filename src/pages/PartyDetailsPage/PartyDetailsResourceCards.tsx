import { Link } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import type { PartyActiveSession } from "../../shared/api/partiesRepo";
import { useLocale } from "../../shared/hooks/useLocale";
import type { PartyDetailsPlayerResource } from "./usePartyDetailsResources";

export { PartyDetailsInventoryCard } from "./PartyDetailsInventoryCard";
export { PartyDetailsCharacterSheetDraftsCard } from "./PartyDetailsCharacterSheetDraftsCard";
export { PartyDetailsPlayerSheetsCard } from "./PartyDetailsPlayerSheetsCard";

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

// Re-exported for legacy consumers that import PartyDetailsPlayerResource via this module
export type { PartyDetailsPlayerResource };
