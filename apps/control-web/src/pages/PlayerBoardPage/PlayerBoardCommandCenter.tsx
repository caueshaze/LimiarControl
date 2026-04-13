import { useLocale } from "../../shared/hooks/useLocale";
import type { PendingRoll } from "./playerBoard.types";

type Props = {
  activeSessionStatus: "ACTIVE" | "LOBBY" | "CLOSED" | null;
  canOpenSheet: boolean;
  combatActive: boolean;
  commandDescription: string;
  commandTitle: string;
  lastCommandType?: string;
  pendingRoll: PendingRoll | null;
  sessionStatusLabel: string;
  shopAvailable: boolean;
  shopOpen: boolean;
  onOpenSheet: () => void;
  onOpenShop: () => void;
  onToggleInventory: () => void;
};

export const PlayerBoardCommandCenter = ({
  activeSessionStatus,
  canOpenSheet,
  combatActive,
  commandDescription,
  commandTitle,
  lastCommandType,
  pendingRoll,
  sessionStatusLabel,
  shopAvailable,
  shopOpen,
  onOpenSheet,
  onOpenShop,
  onToggleInventory,
}: Props) => {
  const { t } = useLocale();

  return (
    <section className="rounded-4xl border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] p-6 shadow-[0_18px_60px_rgba(2,6,23,0.2)]">
      <div className="flex flex-col gap-5 border-b border-white/8 pb-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-2xl">
          <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-slate-400">
            {t("playerBoard.sessionCommandCenter")}
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-white">{commandTitle}</h2>
          <p className="mt-3 text-sm leading-7 text-slate-300">{commandDescription}</p>
        </div>

        <div className="flex flex-wrap gap-3">
          {(shopAvailable || lastCommandType === "open_shop") && !pendingRoll && !shopOpen && (
            <button
              type="button"
              onClick={onOpenShop}
              className="rounded-full bg-cyan-500 px-5 py-3 text-xs font-bold uppercase tracking-[0.22em] text-slate-950 transition hover:bg-cyan-400"
            >
              {t("playerBoard.goShop")}
            </button>
          )}
          <button
            type="button"
            onClick={onToggleInventory}
            className="rounded-full border border-white/10 bg-white/4 px-5 py-3 text-xs font-semibold uppercase tracking-[0.22em] text-slate-100 transition hover:border-white/20 hover:bg-white/8"
          >
            {t("playerBoard.toggleInventory")}
          </button>
          {canOpenSheet && (
            <button
              type="button"
              onClick={onOpenSheet}
              className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-5 py-3 text-xs font-semibold uppercase tracking-[0.22em] text-emerald-100 transition hover:border-emerald-300/30 hover:bg-emerald-400/15"
            >
              {t("playerBoard.openSheet")}
            </button>
          )}
        </div>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <div className="rounded-3xl border border-white/8 bg-white/4 px-4 py-4">
          <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-500">
            {t("playerBoard.sessionStateLabel")}
          </p>
          <p className="mt-3 text-lg font-semibold text-white">{sessionStatusLabel}</p>
        </div>
        <div className="rounded-3xl border border-white/8 bg-white/4 px-4 py-4">
          <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-500">
            {t("playerBoard.shopStateLabel")}
          </p>
          <p className="mt-3 text-lg font-semibold text-white">
            {shopAvailable || shopOpen ? t("playerBoard.shopOpenState") : t("playerBoard.shopClosedState")}
          </p>
        </div>
        <div className="rounded-3xl border border-white/8 bg-white/4 px-4 py-4">
          <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-500">
            {t("playerBoard.combatStateLabel")}
          </p>
          <p className="mt-3 text-lg font-semibold text-white">
            {combatActive ? t("playerBoard.combatOpenState") : t("playerBoard.combatClosedState")}
          </p>
        </div>
      </div>
    </section>
  );
};
