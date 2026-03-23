import { SessionTimer } from "../../shared/ui/SessionTimer";
import type { ActiveSession, LobbyStatus } from "../../shared/api/sessionsRepo";
import type { PartyMemberSummary } from "../../shared/api/partiesRepo";
import type { SessionEntity } from "../../entities/session-entity/sessionEntity.types";
import type { CommandFeedback } from "./gmDashboard.types";
import { GmDashboardRestControlCard } from "./GmDashboardRestControlCard";
import { GmCombatDebugPanel } from "./GmCombatDebugPanel";
import { CombatStartModal, type CombatParticipantPreview } from "./CombatStartModal";
import { AuthoritativeRollDialog } from "../../features/rolls/components/AuthoritativeRollDialog";
import { useState } from "react";
import { combatRepo } from "../../shared/api/combatRepo";
import { sessionEntitiesRepo } from "../../shared/api/sessionEntitiesRepo";
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
  const [combatLoading, setCombatLoading] = useState(false);
  const [combatError, setCombatError] = useState<string | null>(null);
  const [combatModalOpen, setCombatModalOpen] = useState(false);
  const [combatModalEntities, setCombatModalEntities] = useState<SessionEntity[]>([]);
  const [gmInitiativeQueue, setGmInitiativeQueue] = useState<CombatParticipantPreview[]>([]);

  const handleOpenCombatModal = async () => {
    if (!activeSession?.id) return;
    let entities: SessionEntity[] = [];
    try {
      entities = await sessionEntitiesRepo.list(activeSession.id);
    } catch { /* no entities is fine */ }
    setCombatModalEntities(entities);
    setCombatModalOpen(true);
  };

  const handleConfirmCombatStart = async (included: CombatParticipantPreview[]) => {
    if (!activeSession?.id || combatLoading) return;
    setCombatLoading(true);
    setCombatError(null);
    try {
      const parts = included.map((p) =>
        p.kind === "player"
          ? {
              id: "p_" + p.id,
              ref_id: p.id,
              kind: "player" as const,
              display_name: p.displayName,
              initiative: null,
              status: "active" as const,
              team: "players" as const,
              visible: true,
              actor_user_id: p.id,
            }
          : {
              id: "e_" + p.id,
              ref_id: p.id,
              kind: "session_entity" as const,
              display_name: p.displayName,
              initiative: null,
              status: "active" as const,
              team: "enemies" as const,
              visible: combatModalEntities.find((e) => e.id === p.id)?.visibleToPlayers ?? true,
              actor_user_id: null as any,
            },
      );

      await combatRepo.startCombat(activeSession.id, { participants: parts as any });
      onCommand("start_combat");
      setCombatModalOpen(false);

      // Request initiative rolls from all included players
      const playerIds = included.filter((p) => p.kind === "player").map((p) => p.id);
      await Promise.allSettled(playerIds.map((userId) => onRequestInitiativeRoll(userId)));
      setGmInitiativeQueue(included.filter((p) => p.kind === "session_entity"));
    } catch (err: any) {
      setCombatError(err?.response?.data?.detail || err.message || "Failed to start combat");
    } finally {
      setCombatLoading(false);
    }
  };

  const handleEndCombat = async () => {
    if (commandSending || combatLoading || !activeSession?.id) return;
    setCombatLoading(true);
    setCombatError(null);
    try {
      await combatRepo.endCombat(activeSession.id);
      onCommand("end_combat");
      setGmInitiativeQueue([]);
      if (rollType === "attack" || rollType === "initiative") setRollType(null);
    } catch (err: any) {
      setCombatError(err?.response?.data?.detail || err.message || "Failed to end combat");
    } finally {
      setCombatLoading(false);
    }
  };

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
              {activeSession.status === "LOBBY" ? t("gm.dashboard.cancelLobby") : t("gm.dashboard.endSession")}
            </button>
            <span
              className={`rounded-full border px-3 py-1 text-xs font-semibold ${
                activeSession.status === "LOBBY"
                  ? "border-amber-500/20 bg-amber-500/10 text-amber-400"
                  : "border-emerald-500/20 bg-emerald-500/10 text-emerald-400"
              }`}
            >
              {activeSession.status === "LOBBY" ? t("gm.dashboard.statusLobby") : t("gm.dashboard.statusLive")}
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
                  <span className="text-xs font-bold uppercase tracking-widest text-amber-400">{t("gm.dashboard.lobbyLabel")}</span>
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

            {lobbyStatus && lobbyStatus.expected.length > 0 ? (
              <div className="space-y-2">
                <p className="text-[10px] font-bold uppercase tracking-[0.25em] text-slate-500">
                  {t("gm.dashboard.playersCount")} ({lobbyStatus.ready.length}/{lobbyStatus.expected.length})
                </p>
                <div className="grid grid-cols-2 gap-2">
                  {lobbyStatus.expected.map((player) => {
                    const isReady = lobbyStatus.ready.includes(player.userId);
                    const isOnline = Boolean(onlineUsers[player.userId]);
                    return (
                      <div
                        key={player.userId}
                        className={`flex items-center gap-3 rounded-xl border px-4 py-3 transition-all ${
                          isReady
                            ? "border-emerald-500/20 bg-emerald-500/10"
                            : "border-slate-800/40 bg-slate-900/40"
                        }`}
                      >
                        <div className="relative shrink-0">
                          <div
                            className={`flex h-8 w-8 items-center justify-center rounded-full border text-sm font-bold ${
                              isReady
                                ? "border-emerald-500/40 bg-emerald-500/20 text-emerald-300"
                                : "border-slate-700 bg-slate-800 text-slate-400"
                            }`}
                          >
                            {player.displayName.charAt(0).toUpperCase()}
                          </div>
                          <span
                            className={`absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-slate-950 ${
                              isOnline ? "bg-emerald-400" : "bg-slate-600"
                            }`}
                          />
                        </div>
                        <div className="min-w-0">
                          <p className={`truncate text-sm font-medium ${isReady ? "text-emerald-300" : "text-slate-300"}`}>
                            {player.displayName}
                          </p>
                          <p className={`text-[10px] ${isReady ? "text-emerald-500" : isOnline ? "text-sky-400" : "text-slate-600"}`}>
                            {isReady ? t("gm.dashboard.playerReady") : isOnline ? t("gm.dashboard.playerOnline") : t("gm.dashboard.playerOffline")}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : (
              <p className="py-4 text-center text-sm text-slate-500">{t("gm.dashboard.noPlayersToWait")}</p>
            )}
          </div>
        ) : activeSession ? (
          <div className="flex flex-col items-center justify-center space-y-4 py-10">
            <h3 className="text-2xl font-bold text-white">{activeSession.title || t("gm.dashboard.untitledSession")}</h3>
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
          <div className="rounded-2xl border border-slate-800 bg-linear-to-br from-slate-950/60 to-slate-900/40 p-4">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-[10px] font-semibold uppercase tracking-[0.35em] text-slate-500">
                  {t("gm.dashboard.shopControl")}
                </label>
                <p className="mt-1 text-xs text-slate-400">{t("gm.dashboard.shopControlDescription")}</p>
              </div>
              <span className={`rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] ${shopUiOpen ? "border-emerald-500/40 text-emerald-300" : "border-slate-700 text-slate-400"}`}>
                {shopUiOpen ? t("gm.dashboard.shopLive") : t("gm.dashboard.shopClosed")}
              </span>
            </div>
            <button
              onClick={() => onCommand(shopUiOpen ? "close_shop" : "open_shop")}
              disabled={commandSending}
              className={`mt-4 w-full rounded-2xl px-4 py-3 text-xs font-semibold uppercase tracking-[0.25em] transition-colors ${shopUiOpen ? "bg-rose-900/40 text-rose-200 hover:bg-rose-900/60" : "bg-limiar-500/80 text-white hover:bg-limiar-500"}`}
            >
              {shopUiOpen ? t("gm.dashboard.closeShop") : t("gm.dashboard.openShop")}
            </button>
            {commandFeedback && (commandFeedback.type === "open_shop" || commandFeedback.type === "close_shop") && (
              <div className={`mt-3 rounded-2xl border px-3 py-2 text-[11px] ${commandFeedback.tone === "success" ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-300" : "border-rose-500/20 bg-rose-500/10 text-rose-200"}`}>
                {commandFeedback.message}
              </div>
            )}
          </div>

          <div className="rounded-2xl border border-slate-800 bg-linear-to-br from-slate-950/60 to-slate-900/40 p-4">
            <div>
              <label className="text-[10px] font-semibold uppercase tracking-[0.35em] text-slate-500">
                {t("gm.dashboard.diceRequest")}
              </label>
              <p className="mt-1 text-xs text-slate-400">{t("gm.dashboard.diceRequestDescription")}</p>
            </div>
            <div className="mt-4 space-y-3">
              {/* Roll type selector */}
              <select
                value={rollType ?? ""}
                onChange={(event) => {
                  const val = event.target.value || null;
                  setRollType(val);
                  setRollAbility(null);
                  setRollSkill(null);
                  if (val) setRollExpression("d20");
                }}
                className="w-full rounded-2xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-limiar-500 focus:outline-none"
              >
                <option value="">{t("gm.dashboard.freeRollLegacy")}</option>
                <option value="ability">{t("rolls.abilityCheck")}</option>
                <option value="save">{t("rolls.savingThrow")}</option>
                <option value="skill">{t("rolls.skillCheck")}</option>
                {combatUiActive && (
                  <>
                    <option value="initiative">{t("rolls.initiative")}</option>
                    <option value="attack">{t("rolls.attackRoll")}</option>
                  </>
                )}
              </select>

              {/* Ability/skill selector when roll type requires it */}
              {(rollType === "ability" || rollType === "save") && (
                <select
                  value={rollAbility ?? ""}
                  onChange={(event) => setRollAbility(event.target.value || null)}
                  className="w-full rounded-2xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-limiar-500 focus:outline-none"
                >
                  <option value="">{t("gm.dashboard.selectAbility")}</option>
                  <option value="strength">{t("rolls.ability.strength")}</option>
                  <option value="dexterity">{t("rolls.ability.dexterity")}</option>
                  <option value="constitution">{t("rolls.ability.constitution")}</option>
                  <option value="intelligence">{t("rolls.ability.intelligence")}</option>
                  <option value="wisdom">{t("rolls.ability.wisdom")}</option>
                  <option value="charisma">{t("rolls.ability.charisma")}</option>
                </select>
              )}
              {rollType === "skill" && (
                <select
                  value={rollSkill ?? ""}
                  onChange={(event) => setRollSkill(event.target.value || null)}
                  className="w-full rounded-2xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-limiar-500 focus:outline-none"
                >
                  <option value="">{t("gm.dashboard.selectSkill")}</option>
                  <option value="acrobatics">{t("rolls.skill.acrobatics")}</option>
                  <option value="animalHandling">{t("rolls.skill.animalHandling")}</option>
                  <option value="arcana">{t("rolls.skill.arcana")}</option>
                  <option value="athletics">{t("rolls.skill.athletics")}</option>
                  <option value="deception">{t("rolls.skill.deception")}</option>
                  <option value="history">{t("rolls.skill.history")}</option>
                  <option value="insight">{t("rolls.skill.insight")}</option>
                  <option value="intimidation">{t("rolls.skill.intimidation")}</option>
                  <option value="investigation">{t("rolls.skill.investigation")}</option>
                  <option value="medicine">{t("rolls.skill.medicine")}</option>
                  <option value="nature">{t("rolls.skill.nature")}</option>
                  <option value="perception">{t("rolls.skill.perception")}</option>
                  <option value="performance">{t("rolls.skill.performance")}</option>
                  <option value="persuasion">{t("rolls.skill.persuasion")}</option>
                  <option value="religion">{t("rolls.skill.religion")}</option>
                  <option value="sleightOfHand">{t("rolls.skill.sleightOfHand")}</option>
                  <option value="stealth">{t("rolls.skill.stealth")}</option>
                  <option value="survival">{t("rolls.skill.survival")}</option>
                </select>
              )}

              {/* DC input for authoritative rolls */}
              {rollType && rollType !== "initiative" && (
                <input
                  type="number"
                  min={1}
                  value={rollDc}
                  onChange={(event) => setRollDc(event.target.value)}
                  placeholder={t("gm.dashboard.dcPlaceholder")}
                  className="w-full rounded-2xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white placeholder:text-slate-600 focus:border-limiar-500 focus:outline-none"
                />
              )}

              {/* Die selector (only for legacy/free rolls) */}
              {!rollType && (
                <select
                  value={rollExpression}
                  onChange={(event) => setRollExpression(event.target.value)}
                  className="w-full rounded-2xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-white focus:border-limiar-500 focus:outline-none"
                >
                  {rollOptions.map((option) => (
                    <option key={option} value={option} className="text-slate-900">
                      {option.toUpperCase()}
                    </option>
                  ))}
                </select>
              )}

              {/* Target player */}
              <select
                value={rollTargetUserId ?? ""}
                onChange={(event) => setRollTargetUserId(event.target.value || null)}
                className="w-full rounded-2xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-limiar-500 focus:outline-none"
              >
                <option value="">{t("gm.dashboard.allPlayers")}</option>
                {partyPlayers.map((player) => (
                  <option key={player.userId} value={player.userId}>
                    {player.displayName || player.username || "Player"}
                  </option>
                ))}
              </select>

              <input
                type="text"
                value={rollReason}
                onChange={(event) => setRollReason(event.target.value)}
                placeholder={t("gm.dashboard.reasonPlaceholder")}
                className="w-full rounded-2xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white placeholder:text-slate-600 focus:border-limiar-500 focus:outline-none"
              />
              <div className="flex overflow-hidden rounded-2xl border border-slate-700 text-[10px] font-bold uppercase tracking-widest">
                {(["normal", "advantage", "disadvantage"] as const).map((option) => (
                  <button
                    key={option}
                    type="button"
                    onClick={() => setRollAdvantage(option)}
                    className={`flex-1 py-2 transition-colors ${rollAdvantage === option ? option === "advantage" ? "bg-emerald-500/20 text-emerald-400" : option === "disadvantage" ? "bg-red-500/20 text-red-400" : "bg-slate-700 text-white" : "bg-slate-900 text-slate-500 hover:bg-slate-800"}`}
                  >
                    {option === "normal" ? t("gm.dashboard.advantageNormal") : option === "advantage" ? t("gm.dashboard.advantageAdv") : t("gm.dashboard.advantageDisadv")}
                  </button>
                ))}
              </div>
              <button
                onClick={() => onCommand("request_roll", { expression: rollExpression })}
                disabled={commandSending || (rollType === "ability" && !rollAbility) || (rollType === "save" && !rollAbility) || (rollType === "skill" && !rollSkill)}
                className="w-full rounded-2xl bg-slate-800 px-4 py-2 text-xs font-semibold uppercase tracking-[0.25em] text-slate-200 hover:bg-slate-700 disabled:opacity-50"
              >
                {t("gm.dashboard.requestRollTo")}{rollTargetUserId ? ` → ${partyPlayers.find((player) => player.userId === rollTargetUserId)?.displayName ?? ""}` : ""}
              </button>
              {commandFeedback?.type === "request_roll" && (
                <div className={`rounded-2xl border px-3 py-2 text-[11px] ${commandFeedback.tone === "success" ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-300" : "border-rose-500/20 bg-rose-500/10 text-rose-200"}`}>
                  {commandFeedback.message}
                </div>
              )}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-linear-to-br from-slate-950/60 to-slate-900/40 p-4">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-[10px] font-semibold uppercase tracking-[0.35em] text-slate-500">
                  {t("gm.dashboard.combatControl")}
                </label>
                <p className="mt-1 text-xs text-slate-400">
                  {t("gm.dashboard.combatControlDescription")}
                </p>
              </div>
              <span className={`rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] ${combatUiActive ? "border-rose-500/40 text-rose-300" : "border-slate-700 text-slate-400"}`}>
                {combatUiActive ? t("gm.dashboard.combatLive") : t("gm.dashboard.combatStandby")}
              </span>
            </div>
            {combatError && (
              <div className="mt-3 rounded border border-rose-500/50 bg-rose-500/10 px-3 py-2 text-[10px] font-semibold text-rose-300">
                {combatError}
              </div>
            )}
            <button
              onClick={() => { combatUiActive ? void handleEndCombat() : void handleOpenCombatModal(); }}
              disabled={commandSending || combatLoading}
              className={`mt-4 w-full rounded-2xl px-4 py-3 text-xs font-semibold uppercase tracking-[0.25em] transition-colors ${combatUiActive ? "bg-slate-800 text-slate-200 hover:bg-slate-700" : "bg-rose-900/50 text-rose-100 hover:bg-rose-900/70"} disabled:opacity-50`}
            >
              {combatLoading ? t("gm.dashboard.combatSyncing") : combatUiActive ? t("gm.dashboard.endCombat") : t("gm.dashboard.startCombat")}
            </button>
            {commandFeedback && (commandFeedback.type === "start_combat" || commandFeedback.type === "end_combat") && (
              <div className={`mt-3 rounded-2xl border px-3 py-2 text-[11px] ${commandFeedback.tone === "success" ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-300" : "border-rose-500/20 bg-rose-500/10 text-rose-200"}`}>
                {commandFeedback.message}
              </div>
            )}
          </div>

          <GmDashboardRestControlCard
            combatUiActive={combatUiActive}
            commandFeedback={commandFeedback}
            commandSending={commandSending}
            restState={restState}
            onCommand={onCommand}
          />
        </div>
      )}
      {activeSession?.status === "ACTIVE" && combatUiActive && (
        <GmCombatDebugPanel
          sessionId={activeSession.id!}
          campaignId={activeSession.campaignId!}
          partyPlayers={partyPlayers}
        />
      )}
    </div>

    <CombatStartModal
      isOpen={combatModalOpen}
      loading={combatLoading}
      partyPlayers={partyPlayers}
      sessionEntities={combatModalEntities}
      onClose={() => setCombatModalOpen(false)}
      onConfirm={(participants) => { void handleConfirmCombatStart(participants); }}
    />
    {activeSession?.id && gmInitiativeQueue[0] && (
      <AuthoritativeRollDialog
        key={`gm-initiative:${gmInitiativeQueue[0].id}`}
        request={{
          rollType: "initiative",
          advantageMode: "normal",
          reason: gmInitiativeQueue[0].displayName,
        }}
        sessionId={activeSession.id}
        actorKind="session_entity"
        actorRefId={gmInitiativeQueue[0].id}
        onResolved={() => {
          setGmInitiativeQueue((current) => current.slice(1));
        }}
        onClose={() => {
          setGmInitiativeQueue((current) => current.slice(1));
        }}
      />
    )}
  </div>
  );
};
