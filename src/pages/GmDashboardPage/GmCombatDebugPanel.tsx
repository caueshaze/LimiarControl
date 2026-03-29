import type { PartyMemberSummary } from "../../shared/api/partiesRepo";
import { describeCombatAction } from "../../entities/campaign-entity/describeCombatAction";
import { RollResultCard } from "../../features/rolls/components/RollResultCard";
import { GmEntityActionRollDialog } from "./GmEntityActionRollDialog";
import { GmStandardActionControls } from "./GmStandardActionControls";
import { ApplyEffectForm } from "./ApplyEffectForm";
import { GmCombatParticipantList } from "./GmCombatParticipantList";
import { GmCombatNpcActions } from "./GmCombatNpcActions";
import { useGmCombatDebug } from "./useGmCombatDebug";

export const GmCombatDebugPanel = ({
  sessionId,
  campaignId,
  partyPlayers,
}: {
  sessionId: string;
  campaignId: string;
  partyPlayers: PartyMemberSummary[];
}) => {
  const {
    state,
    loading,
    setLoading,
    error,
    initiatives,
    setInitiatives,
    selectedCombatActionId,
    setSelectedCombatActionId,
    targetId,
    setTargetId,
    actionResult,
    entityActionDialogOpen,
    setEntityActionDialogOpen,
    lastEntityActionResult,
    currentParticipant,
    canActForNpc,
    npcCombatActions,
    selectedCombatAction,
    availableTargets,
    selectedTarget,
    handleSetInitiative,
    handleNextTurn,
    handleMarkReaction,
    handleEntityAction,
    handleEntityActionResolved,
  } = useGmCombatDebug(sessionId);

  return (
    <div className="rounded-xl border border-rose-500/30 bg-rose-950/20 p-4 mt-6">
      <div className="flex items-center justify-between">
         <h3 className="text-lg font-bold text-rose-300">Phase 2 Turn Controller (Debug)</h3>
      </div>

      {error && (
        <div className="mt-4 rounded border border-rose-500 bg-rose-500/10 p-2 text-rose-200 text-sm">
          <strong>Error:</strong> {error}
        </div>
      )}

      {actionResult && (
        <div className="mt-4 rounded border border-emerald-500/40 bg-emerald-500/10 p-2 text-sm text-emerald-200">
          <strong>Result:</strong> {actionResult}
        </div>
      )}

      {lastEntityActionResult?.roll_result && (
        <div className="mt-4 rounded border border-amber-500/30 bg-amber-500/10 p-3">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-amber-200">
            Last NPC Attack
          </p>
          <div className="mt-3">
            <RollResultCard result={lastEntityActionResult.roll_result} />
          </div>
        </div>
      )}

      {!state || state.phase === "ended" ? (
        <div className="mt-4 text-slate-400 text-sm italic">
          Fetching backend state or no combat currently tracked...
        </div>
      ) : (
        <div className="mt-4 space-y-4 text-sm text-slate-300">
          <div className="flex justify-between items-center rounded border border-rose-500/20 bg-rose-900/10 p-2">
             <span>Phase: <strong className="uppercase text-rose-400">{state.phase}</strong></span>
             <span>Round: <strong className="text-white">{state.round}</strong></span>
          </div>

          <GmCombatParticipantList
            state={state}
            initiatives={initiatives}
            setInitiatives={setInitiatives}
            sessionId={sessionId}
          />

          <div className="flex gap-2">
            {state.phase === "initiative" && (
                <button
                    disabled={loading}
                    onClick={handleSetInitiative}
                    className="flex-1 rounded bg-amber-600 px-4 py-2 font-bold text-white hover:bg-amber-500 disabled:opacity-50"
                  >
                    Confirm Initiatives
                </button>
            )}

            {state.phase === "active" && (
                <>
                  <button
                      disabled={loading}
                      onClick={handleNextTurn}
                      className="flex-1 rounded bg-sky-600 px-4 py-2 font-bold text-white hover:bg-sky-500 disabled:opacity-50"
                    >
                      Next Turn (Bypass)
                  </button>
                  <button
                      disabled={loading}
                      onClick={handleMarkReaction}
                      className="rounded border border-orange-500/50 bg-transparent px-3 py-2 text-xs font-bold text-orange-400 hover:bg-orange-500/10 disabled:opacity-50"
                      title="Mark the active participant's reaction as used"
                    >
                      Mark Reaction
                  </button>
                  <GmStandardActionControls
                    loading={loading}
                    participants={state.participants}
                    currentParticipantId={state.participants[state.current_turn_index]?.id ?? null}
                    sessionId={sessionId}
                    setLoading={setLoading}
                  />
                </>
            )}
          </div>

          {state.phase === "active" && (
            <ApplyEffectForm
              participants={state.participants}
              sessionId={sessionId}
            />
          )}

          {canActForNpc && currentParticipant && (
            <GmCombatNpcActions
              currentParticipant={currentParticipant}
              npcCombatActions={npcCombatActions}
              selectedCombatActionId={selectedCombatActionId}
              setSelectedCombatActionId={setSelectedCombatActionId}
              selectedCombatAction={selectedCombatAction}
              availableTargets={availableTargets}
              targetId={targetId}
              setTargetId={setTargetId}
              loading={loading}
              onExecuteAction={handleEntityAction}
            />
          )}
        </div>
      )}

      {entityActionDialogOpen &&
      currentParticipant &&
      selectedCombatAction &&
      selectedTarget &&
      (selectedCombatAction.kind === "weapon_attack" || selectedCombatAction.kind === "spell_attack") ? (
        <GmEntityActionRollDialog
          actorParticipantId={currentParticipant.id}
          actionDescription={describeCombatAction(selectedCombatAction)}
          actionId={selectedCombatAction.id}
          actionKind={selectedCombatAction.kind}
          actionName={selectedCombatAction.name}
          sessionId={sessionId}
          target={selectedTarget}
          onClose={() => setEntityActionDialogOpen(false)}
          onResolved={handleEntityActionResolved}
        />
      ) : null}
    </div>
  );
};
