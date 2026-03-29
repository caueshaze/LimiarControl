import { useState } from "react";
import { combatRepo } from "../../shared/api/combatRepo";
import { sessionEntitiesRepo } from "../../shared/api/sessionEntitiesRepo";
import type { SessionEntity } from "../../entities/session-entity/sessionEntity.types";
import type { CommandFeedback } from "./gmDashboard.types";
import { CombatStartModal, type CombatParticipantPreview } from "./CombatStartModal";
import type { PartyMemberSummary } from "../../shared/api/partiesRepo";
import { useLocale } from "../../shared/hooks/useLocale";

type Props = {
  activeSessionId: string;
  combatUiActive: boolean;
  commandFeedback: CommandFeedback | null;
  commandSending: boolean;
  partyPlayers: PartyMemberSummary[];
  rollType: string | null;
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
  onRequestInitiativeRoll: (userId: string) => Promise<void>;
  onClearGmInitiativeQueue: () => void;
  onSetGmInitiativeQueue: (participants: CombatParticipantPreview[]) => void;
  setRollType: (value: string | null) => void;
};

export const GmDashboardCombatControlCard = ({
  activeSessionId,
  combatUiActive,
  commandFeedback,
  commandSending,
  partyPlayers,
  rollType,
  onCommand,
  onRequestInitiativeRoll,
  onClearGmInitiativeQueue,
  onSetGmInitiativeQueue,
  setRollType,
}: Props) => {
  const { t } = useLocale();
  const [combatLoading, setCombatLoading] = useState(false);
  const [combatError, setCombatError] = useState<string | null>(null);
  const [combatModalOpen, setCombatModalOpen] = useState(false);
  const [combatModalEntities, setCombatModalEntities] = useState<SessionEntity[]>([]);

  const handleOpenCombatModal = async () => {
    let entities: SessionEntity[] = [];
    try {
      entities = await sessionEntitiesRepo.list(activeSessionId);
    } catch { /* no entities is fine */ }
    setCombatModalEntities(entities);
    setCombatModalOpen(true);
  };

  const handleConfirmCombatStart = async (included: CombatParticipantPreview[]) => {
    if (combatLoading) return;
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

      await combatRepo.startCombat(activeSessionId, { participants: parts as any });
      onCommand("start_combat");
      setCombatModalOpen(false);

      // Request initiative rolls from all included players
      const playerIds = included.filter((p) => p.kind === "player").map((p) => p.id);
      await Promise.allSettled(playerIds.map((userId) => onRequestInitiativeRoll(userId)));
      onSetGmInitiativeQueue(included.filter((p) => p.kind === "session_entity"));
    } catch (err: any) {
      setCombatError(err?.response?.data?.detail || err.message || "Failed to start combat");
    } finally {
      setCombatLoading(false);
    }
  };

  const handleEndCombat = async () => {
    if (commandSending || combatLoading) return;
    setCombatLoading(true);
    setCombatError(null);
    try {
      await combatRepo.endCombat(activeSessionId);
      onCommand("end_combat");
      onClearGmInitiativeQueue();
      if (rollType === "attack" || rollType === "initiative") setRollType(null);
    } catch (err: any) {
      setCombatError(err?.response?.data?.detail || err.message || "Failed to end combat");
    } finally {
      setCombatLoading(false);
    }
  };

  return (
    <>
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
          <span
            className={`rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] ${
              combatUiActive
                ? "border-rose-500/40 text-rose-300"
                : "border-slate-700 text-slate-400"
            }`}
          >
            {combatUiActive ? t("gm.dashboard.combatLive") : t("gm.dashboard.combatStandby")}
          </span>
        </div>
        {combatError && (
          <div className="mt-3 rounded border border-rose-500/50 bg-rose-500/10 px-3 py-2 text-[10px] font-semibold text-rose-300">
            {combatError}
          </div>
        )}
        <button
          onClick={() => {
            combatUiActive ? void handleEndCombat() : void handleOpenCombatModal();
          }}
          disabled={commandSending || combatLoading}
          className={`mt-4 w-full rounded-2xl px-4 py-3 text-xs font-semibold uppercase tracking-[0.25em] transition-colors ${
            combatUiActive
              ? "bg-slate-800 text-slate-200 hover:bg-slate-700"
              : "bg-rose-900/50 text-rose-100 hover:bg-rose-900/70"
          } disabled:opacity-50`}
        >
          {combatLoading
            ? t("gm.dashboard.combatSyncing")
            : combatUiActive
            ? t("gm.dashboard.endCombat")
            : t("gm.dashboard.startCombat")}
        </button>
        {commandFeedback &&
          (commandFeedback.type === "start_combat" || commandFeedback.type === "end_combat") && (
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

      <CombatStartModal
        isOpen={combatModalOpen}
        loading={combatLoading}
        partyPlayers={partyPlayers}
        sessionEntities={combatModalEntities}
        onClose={() => setCombatModalOpen(false)}
        onConfirm={(participants) => {
          void handleConfirmCombatStart(participants);
        }}
      />
    </>
  );
};
