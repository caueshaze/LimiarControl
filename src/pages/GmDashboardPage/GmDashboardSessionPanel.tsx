import { SessionTimer } from "../../shared/ui/SessionTimer";
import type { ActiveSession, LobbyStatus } from "../../shared/api/sessionsRepo";
import type { PartyMemberSummary } from "../../shared/api/partiesRepo";
import type { CommandFeedback } from "./gmDashboard.types";
import { GmDashboardRestControlCard } from "./GmDashboardRestControlCard";
import { GmDashboardLobbyStatus } from "./GmDashboardLobbyStatus";
import { GmDashboardRollRequestCard } from "./GmDashboardRollRequestCard";
import { GmDashboardCombatControlCard } from "./GmDashboardCombatControlCard";
import type { CombatParticipantPreview } from "./CombatStartModal";
import { useLocale } from "../../shared/hooks/useLocale";

type Props = {
  activeSession: ActiveSession | null;
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
      | "end_rest",
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

  return (
    <div className="grid gap-6">
      <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">{t("gm.dashboard.sessionStatus")}</h2>
          {activeSession && (
            <div className="flex items-center gap-3">
              <button
                onClick={onEndSession}
                className="rounded-full border border-red-500/30 bg-red-500/10 px-3 py-1 text-xs font-semibold text-red-400 hover:bg-red-500/20"
              >
                {activeSession.status === "LOBBY"
                  ? t("gm.dashboard.cancelLobby")
                  : t("gm.dashboard.endSession")}
              </button>
              <span
                className={`rounded-full border px-3 py-1 text-xs font-semibold ${
                  activeSession.status === "LOBBY"
                    ? "border-amber-500/20 bg-amber-500/10 text-amber-400"
                    : "border-emerald-500/20 bg-emerald-500/10 text-emerald-400"
                }`}
              >
                {activeSession.status === "LOBBY"
                  ? t("gm.dashboard.statusLobby")
                  : t("gm.dashboard.statusLive")}
              </span>
            </div>
          )}
        </div>

        <div className="mt-6 overflow-hidden rounded-2xl border border-slate-800/50 bg-slate-950/50">
          {loading ? (
            <div className="flex items-center justify-center py-10">
              <span className="text-slate-400">{t("gm.dashboard.loadingSession")}</span>
            </div>
          ) : activeSession?.status === "LOBBY" ? (
            <div className="space-y-6 p-6">
              <div className="flex items-center justify-between">
                <div>
                  <div className="mb-1 flex items-center gap-2">
                    <span className="h-2 w-2 animate-pulse rounded-full bg-amber-400" />
                    <span className="text-xs font-bold uppercase tracking-widest text-amber-400">
                      {t("gm.dashboard.lobbyLabel")}
                    </span>
                  </div>
                  <h3 className="text-xl font-bold text-white">{activeSession.title}</h3>
                  <p className="mt-0.5 text-xs text-slate-500">
                    #{activeSession.number} · {t("gm.dashboard.waitingForPlayers")}
                  </p>
                </div>
                <button
                  onClick={onForceStart}
                  disabled={forceStarting}
                  className="rounded-full border border-limiar-500/30 bg-limiar-500/10 px-4 py-2 text-xs font-bold uppercase tracking-widest text-limiar-400 hover:bg-limiar-500/20 disabled:opacity-50 transition-all"
                >
                  {forceStarting ? t("gm.dashboard.forceStarting") : t("gm.dashboard.forceStart")}
                </button>
              </div>

              <GmDashboardLobbyStatus
                lobbyStatus={lobbyStatus}
                onlineUsers={onlineUsers}
              />
            </div>
          ) : activeSession ? (
            <div className="flex flex-col items-center justify-center space-y-4 py-10">
              <h3 className="text-2xl font-bold text-white">
                {activeSession.title || t("gm.dashboard.untitledSession")}
              </h3>
              <div className="text-4xl font-mono text-limiar-400">
                <SessionTimer startedAt={activeSession.startedAt ?? activeSession.createdAt} />
              </div>
              <div className="flex gap-2 text-sm text-slate-500">
                <span>#{activeSession.number}</span>
                <span className="text-emerald-400">● {t("gm.dashboard.statusActive")}</span>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center space-y-4 py-10">
              <p className="mb-2 text-slate-400">{t("gm.dashboard.noActiveSession")}</p>
              <button
                onClick={onActivateClick}
                disabled={creating}
                className="rounded-full bg-limiar-500 px-8 py-3 text-sm font-bold uppercase tracking-widest text-white shadow-lg shadow-limiar-500/20 hover:bg-limiar-400 disabled:opacity-50 transition-all active:scale-95"
              >
                {t("gm.dashboard.startSession")}
              </button>
            </div>
          )}
        </div>

        {activeSession?.status === "ACTIVE" && (
          <div className="mt-6 grid gap-4 lg:grid-cols-2 xl:grid-cols-4">
            {/* Shop control card */}
            <div className="rounded-2xl border border-slate-800 bg-linear-to-br from-slate-950/60 to-slate-900/40 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <label className="text-[10px] font-semibold uppercase tracking-[0.35em] text-slate-500">
                    {t("gm.dashboard.shopControl")}
                  </label>
                  <p className="mt-1 text-xs text-slate-400">{t("gm.dashboard.shopControlDescription")}</p>
                </div>
                <span
                  className={`rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] ${
                    shopUiOpen
                      ? "border-emerald-500/40 text-emerald-300"
                      : "border-slate-700 text-slate-400"
                  }`}
                >
                  {shopUiOpen ? t("gm.dashboard.shopLive") : t("gm.dashboard.shopClosed")}
                </span>
              </div>
              <button
                onClick={() => onCommand(shopUiOpen ? "close_shop" : "open_shop")}
                disabled={commandSending}
                className={`mt-4 w-full rounded-2xl px-4 py-3 text-xs font-semibold uppercase tracking-[0.25em] transition-colors ${
                  shopUiOpen
                    ? "bg-rose-900/40 text-rose-200 hover:bg-rose-900/60"
                    : "bg-limiar-500/80 text-white hover:bg-limiar-500"
                }`}
              >
                {shopUiOpen ? t("gm.dashboard.closeShop") : t("gm.dashboard.openShop")}
              </button>
              {commandFeedback &&
                (commandFeedback.type === "open_shop" || commandFeedback.type === "close_shop") && (
                  <div
                    className={`mt-3 rounded-2xl border px-3 py-2 text-[11px] ${
                      commandFeedback.tone === "success"
                        ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-300"
                        : "border-rose-500/20 bg-rose-500/10 text-rose-200"
                    }`}
                  >
                    {commandFeedback.message}
                  </div>
                )}
            </div>

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
        )}
      </div>
    </div>
  );
};
