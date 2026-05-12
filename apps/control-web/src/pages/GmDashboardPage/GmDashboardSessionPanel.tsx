import { SessionTimer } from "../../shared/ui/SessionTimer";
import { useState } from "react";
import type { ActiveSession, LobbyStatus } from "../../shared/api/sessionsRepo";
import type { PartyMemberSummary } from "../../shared/api/partiesRepo";
import type { CampaignMapConfig } from "../../entities/campaign";
import type { CommandFeedback } from "./gmDashboard.types";
import { GmDashboardRestControlCard } from "./GmDashboardRestControlCard";
import { GmDashboardLobbyStatus } from "./GmDashboardLobbyStatus";
import { GmDashboardRollRequestCard } from "./GmDashboardRollRequestCard";
import { GmDashboardCombatControlCard } from "./GmDashboardCombatControlCard";
import type { CombatParticipantPreview } from "./CombatStartModal";
import { useLocale } from "../../shared/hooks/useLocale";

type Props = {
  activeSession: ActiveSession | null;
  campaignMaps: CampaignMapConfig[];
  combatUiActive: boolean;
  commandFeedback: CommandFeedback | null;
  commandSending: boolean;
  creating: boolean;
  forceStarting: boolean;
  loading: boolean;
  lobbyStatus: LobbyStatus | null;
  onlineUsers: Record<string, string>;
  partyPlayers: PartyMemberSummary[];
  restState: "exploration" | "short_rest" | "long_rest";
  gameTimeSeconds: number;
  rollAbility: string | null;
  rollAdvantage: "normal" | "advantage" | "disadvantage";
  rollDc: string;
  rollExpression: string;
  rollOptions: string[];
  rollReason: string;
  rollSkill: string | null;
  rollTargetUserId: string | null;
  rollType: string | null;
  shopUiOpen: boolean;
  onActivateClick: () => void;
  onCommand: (
    type:
      | "open_shop"
      | "close_shop"
      | "request_roll"
      | "start_combat"
      | "end_combat"
      | "start_short_rest"
      | "start_long_rest"
      | "end_rest"
      | "advance_game_time",
    payload?: Record<string, unknown>,
  ) => void;
  onEndSession: () => void;
  onForceStart: () => void;
  onRequestInitiativeRoll: (userId: string) => Promise<void>;
  onClearGmInitiativeQueue: () => void;
  onSetGmInitiativeQueue: (participants: CombatParticipantPreview[]) => void;
  setRollAbility: (value: string | null) => void;
  setRollAdvantage: (value: "normal" | "advantage" | "disadvantage") => void;
  setRollDc: (value: string) => void;
  setRollExpression: (value: string) => void;
  setRollReason: (value: string) => void;
  setRollSkill: (value: string | null) => void;
  setRollTargetUserId: (value: string | null) => void;
  setRollType: (value: string | null) => void;
};

export const GmDashboardSessionPanel = ({
  activeSession,
  campaignMaps,
  combatUiActive,
  commandFeedback,
  commandSending,
  creating,
  forceStarting,
  loading,
  lobbyStatus,
  onlineUsers,
  partyPlayers,
  restState,
  gameTimeSeconds,
  rollAbility,
  rollAdvantage,
  rollDc,
  rollExpression,
  rollOptions,
  rollReason,
  rollSkill,
  rollTargetUserId,
  rollType,
  shopUiOpen,
  onActivateClick,
  onCommand,
  onEndSession,
  onForceStart,
  onRequestInitiativeRoll,
  onClearGmInitiativeQueue,
  onSetGmInitiativeQueue,
  setRollAbility,
  setRollAdvantage,
  setRollDc,
  setRollExpression,
  setRollReason,
  setRollSkill,
  setRollTargetUserId,
  setRollType,
}: Props) => {
  const { t } = useLocale();
  const [customHours, setCustomHours] = useState("1");
  const gameDay = Math.floor(gameTimeSeconds / 86400) + 1;
  const daySeconds = gameTimeSeconds % 86400;
  const gameTimeHours = Math.floor(daySeconds / 3600);
  const gameTimeMinutes = Math.floor((daySeconds % 3600) / 60);
  const gameTimeRemainderSeconds = daySeconds % 60;
  const gameClockLabel = `${String(gameTimeHours).padStart(2, "0")}:${String(gameTimeMinutes).padStart(2, "0")}:${String(
    gameTimeRemainderSeconds,
  ).padStart(2, "0")}`;
  const customHoursNumber = Number(customHours);
  const customHoursIsValid = Number.isFinite(customHoursNumber) && customHoursNumber > 0;
  const isAdvanceFeedback = commandFeedback?.type === "advance_game_time";

  /* ──── No session / loading ──────────────────────────────────────── */
  if (loading) {
    return (
      <div className="flex items-center justify-center rounded-[28px] border border-white/8 bg-white/[0.03] py-16">
        <span className="text-slate-400">{t("gm.dashboard.loadingSession")}</span>
      </div>
    );
  }

  if (!activeSession) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 rounded-[28px] border border-white/8 bg-white/[0.03] py-16">
        <p className="text-slate-400">{t("gm.dashboard.noActiveSession")}</p>
        <button
          onClick={onActivateClick}
          disabled={creating}
          className="rounded-full bg-limiar-500 px-8 py-3 text-sm font-bold uppercase tracking-widest text-white shadow-[0_0_24px_rgba(139,92,246,0.4)] transition-all hover:bg-limiar-400 hover:shadow-[0_0_36px_rgba(139,92,246,0.6)] active:scale-95 disabled:opacity-50 disabled:shadow-none"
        >
          {t("gm.dashboard.startSession")}
        </button>
      </div>
    );
  }

  /* ──── Lobby state ───────────────────────────────────────────────── */
  if (activeSession.status === "LOBBY") {
    return (
      <div className="overflow-hidden rounded-[28px] border border-white/8 bg-white/[0.03] backdrop-blur-xl">
        <div className="border-b border-white/6 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="h-2 w-2 animate-pulse rounded-full bg-amber-400" />
              <span className="text-xs font-bold uppercase tracking-widest text-amber-400">
                {t("gm.dashboard.lobbyLabel")}
              </span>
            </div>
            <button
              onClick={onEndSession}
              className="rounded-full border border-red-500/30 bg-red-500/10 px-3 py-1 text-xs font-semibold text-red-400 transition-all hover:bg-red-500/20 active:scale-95"
            >
              {t("gm.dashboard.cancelLobby")}
            </button>
          </div>
          <h3 className="mt-3 font-display text-2xl font-bold text-white">{activeSession.title}</h3>
          <p className="mt-1 text-xs text-slate-500">
            #{activeSession.number} · {t("gm.dashboard.waitingForPlayers")}
          </p>
        </div>
        <div className="space-y-4 p-6">
          <div className="flex justify-end">
            <button
              onClick={onForceStart}
              disabled={forceStarting}
              className="rounded-full border border-limiar-500/30 bg-limiar-500/10 px-4 py-2 text-xs font-bold uppercase tracking-widest text-limiar-400 transition-all hover:bg-limiar-500/20 active:scale-95 disabled:opacity-50"
            >
              {forceStarting ? t("gm.dashboard.forceStarting") : t("gm.dashboard.forceStart")}
            </button>
          </div>
          <GmDashboardLobbyStatus lobbyStatus={lobbyStatus} onlineUsers={onlineUsers} />
        </div>
      </div>
    );
  }

  /* ──── Active session ────────────────────────────────────────────── */
  return (
    <div className="space-y-4">
      {/* Row 1: Session hero ↔ Clock + Shop */}
      <div className="grid gap-4 lg:grid-cols-[1fr_300px]">

        {/* Session live hero */}
        <div className="relative flex flex-col items-center justify-center overflow-hidden rounded-[28px] border border-white/8 bg-white/[0.03] px-8 py-10 backdrop-blur-xl">
          {/* Radial glow behind timer */}
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_60%_50%_at_50%_55%,rgba(139,92,246,0.12),transparent)]"
          />
          {/* End session button top-right */}
          <button
            onClick={onEndSession}
            className="absolute top-4 right-4 rounded-full border border-red-500/30 bg-red-500/8 px-3 py-1 text-[11px] font-semibold text-red-400 transition-all hover:bg-red-500/18 active:scale-95"
          >
            {t("gm.dashboard.endSession")}
          </button>
          <div className="relative z-10 text-center">
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.32em] text-slate-500">
              {t("gm.dashboard.sessionStatus")}
            </p>
            <h3 className="font-display text-3xl font-bold text-white">
              {activeSession.title || t("gm.dashboard.untitledSession")}
            </h3>
            <div className="mt-4 font-mono text-[4.5rem] font-semibold leading-none tracking-[0.06em] text-limiar-300 drop-shadow-[0_0_32px_rgba(167,139,250,0.65)]">
              <SessionTimer startedAt={activeSession.startedAt ?? activeSession.createdAt} />
            </div>
            <div className="mt-5 flex items-center justify-center gap-3">
              <span className="text-xs text-slate-600">#{activeSession.number}</span>
              <span className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
                {t("gm.dashboard.statusActive")}
              </span>
            </div>
          </div>
        </div>

        {/* Clock + Shop stacked */}
        <div className="flex flex-col gap-4">

          {/* Clock card */}
          <div className="rounded-[24px] border border-white/8 bg-white/[0.04] p-5 backdrop-blur-xl">
            <div className="mb-1 flex items-center justify-between">
              <label className="text-[10px] font-semibold uppercase tracking-[0.35em] text-slate-400">
                {t("gm.dashboard.gameClock")}
              </label>
              <span className="rounded-full border border-limiar-500/25 bg-limiar-500/8 px-2 py-0.5 text-[9px] font-semibold uppercase tracking-[0.2em] text-limiar-400">
                {t("gm.dashboard.gameClockLive")}
              </span>
            </div>
            <div className="mt-3 rounded-2xl border border-white/6 bg-black/25 px-4 py-3">
              <p className="mb-0.5 text-[9px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                {t("gm.dashboard.gameClockDay").replace("{day}", String(gameDay))}
              </p>
              <p className="font-mono text-xl font-semibold tracking-[0.18em] text-limiar-200">{gameClockLabel}</p>
            </div>
            <div className="mt-3 grid grid-cols-3 gap-1.5">
              {([["1h", 3600], ["2h", 7200], ["8h", 28800]] as const).map(([label, secs]) => (
                <button
                  key={label}
                  type="button"
                  onClick={() => onCommand("advance_game_time", { seconds: secs })}
                  disabled={commandSending}
                  className="rounded-xl border border-white/10 bg-white/5 py-1.5 text-xs font-semibold text-slate-300 transition-all hover:border-white/20 hover:bg-white/10 active:scale-95 disabled:opacity-50"
                >
                  +{label}
                </button>
              ))}
            </div>
            <div className="mt-2 flex items-center gap-2">
              <input
                type="number"
                min={1}
                step={1}
                value={customHours}
                onChange={(e) => setCustomHours(e.target.value)}
                className="w-16 rounded-xl border border-white/10 bg-white/5 px-2 py-1.5 text-xs text-slate-100 focus:border-limiar-500 focus:outline-none"
                aria-label={t("gm.dashboard.gameClockCustomHours")}
              />
              <span className="text-[11px] text-slate-500">{t("gm.dashboard.gameClockHoursSuffix")}</span>
              <button
                type="button"
                onClick={() => onCommand("advance_game_time", { seconds: Math.round(customHoursNumber * 3600) })}
                disabled={commandSending || !customHoursIsValid}
                className="ml-auto rounded-xl bg-limiar-600 px-3 py-1.5 text-[11px] font-semibold text-white shadow-[0_0_12px_rgba(124,58,237,0.4)] transition-all hover:bg-limiar-500 hover:shadow-[0_0_20px_rgba(124,58,237,0.55)] active:scale-95 disabled:opacity-50 disabled:shadow-none"
              >
                {t("gm.dashboard.gameClockAdvance")}
              </button>
            </div>
            {isAdvanceFeedback && commandFeedback ? (
              <p className={`mt-2 text-[11px] ${commandFeedback.tone === "success" ? "text-emerald-400" : "text-rose-400"}`}>
                {commandFeedback.message}
              </p>
            ) : null}
          </div>

          {/* Shop card */}
          <div className="rounded-[24px] border border-white/8 bg-white/[0.04] p-5 backdrop-blur-xl">
            <div className="flex items-center justify-between">
              <label className="text-[10px] font-semibold uppercase tracking-[0.35em] text-slate-400">
                {t("gm.dashboard.shopControl")}
              </label>
              <span
                className={`flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[9px] font-semibold uppercase tracking-[0.2em] ${
                  shopUiOpen
                    ? "border-emerald-500/30 text-emerald-400"
                    : "border-white/10 text-slate-500"
                }`}
              >
                {shopUiOpen && <span className="h-1 w-1 animate-pulse rounded-full bg-emerald-400" />}
                {shopUiOpen ? t("gm.dashboard.shopLive") : t("gm.dashboard.shopClosed")}
              </span>
            </div>
            <p className="mt-1 text-[11px] text-slate-500">{t("gm.dashboard.shopControlDescription")}</p>
            <button
              onClick={() => onCommand(shopUiOpen ? "close_shop" : "open_shop")}
              disabled={commandSending}
              className={`mt-3 w-full rounded-2xl px-4 py-2.5 text-xs font-bold uppercase tracking-[0.22em] transition-all active:scale-95 ${
                shopUiOpen
                  ? "border border-white/8 bg-white/5 text-slate-200 hover:bg-white/10"
                  : "bg-limiar-600 text-white shadow-[0_0_16px_rgba(124,58,237,0.4)] hover:bg-limiar-500 hover:shadow-[0_0_24px_rgba(124,58,237,0.55)]"
              } disabled:opacity-50 disabled:shadow-none`}
            >
              {shopUiOpen ? t("gm.dashboard.closeShop") : t("gm.dashboard.openShop")}
            </button>
            {commandFeedback && (commandFeedback.type === "open_shop" || commandFeedback.type === "close_shop") ? (
              <p className={`mt-2 text-[11px] ${commandFeedback.tone === "success" ? "text-emerald-400" : "text-rose-400"}`}>
                {commandFeedback.message}
              </p>
            ) : null}
          </div>

        </div>
      </div>

      {/* Row 2: Roll Request + Combat + Rest */}
      <div className="grid gap-4 lg:grid-cols-[2fr_1fr_1fr]">
        <GmDashboardRollRequestCard
          combatUiActive={combatUiActive}
          commandFeedback={commandFeedback}
          commandSending={commandSending}
          partyPlayers={partyPlayers}
          rollAbility={rollAbility}
          rollAdvantage={rollAdvantage}
          rollDc={rollDc}
          rollExpression={rollExpression}
          rollOptions={rollOptions}
          rollReason={rollReason}
          rollSkill={rollSkill}
          rollTargetUserId={rollTargetUserId}
          rollType={rollType}
          onCommand={onCommand}
          setRollAbility={setRollAbility}
          setRollAdvantage={setRollAdvantage}
          setRollDc={setRollDc}
          setRollExpression={setRollExpression}
          setRollReason={setRollReason}
          setRollSkill={setRollSkill}
          setRollTargetUserId={setRollTargetUserId}
          setRollType={setRollType}
        />

        <GmDashboardCombatControlCard
          activeSessionId={activeSession.id}
          campaignMaps={campaignMaps}
          combatUiActive={combatUiActive}
          commandFeedback={commandFeedback}
          commandSending={commandSending}
          partyPlayers={partyPlayers}
          rollType={rollType}
          onCommand={onCommand}
          onRequestInitiativeRoll={onRequestInitiativeRoll}
          onClearGmInitiativeQueue={onClearGmInitiativeQueue}
          onSetGmInitiativeQueue={onSetGmInitiativeQueue}
          setRollType={setRollType}
        />

        <GmDashboardRestControlCard
          combatUiActive={combatUiActive}
          commandFeedback={commandFeedback}
          commandSending={commandSending}
          restState={restState}
          onCommand={onCommand}
        />
      </div>
    </div>
  );
};
