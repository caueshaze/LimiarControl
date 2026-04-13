import { describeCombatAction } from "../../entities/campaign-entity/describeCombatAction";
import type { CombatState } from "../../shared/api/combatRepo";
import type { SessionEntity } from "../../entities/session-entity";

type CombatAction = NonNullable<SessionEntity["entity"]>["combatActions"][number];

export const GmCombatNpcActions = ({
  currentParticipant,
  npcCombatActions,
  selectedCombatActionId,
  setSelectedCombatActionId,
  selectedCombatAction,
  availableTargets,
  targetId,
  setTargetId,
  loading,
  onExecuteAction,
}: {
  currentParticipant: CombatState["participants"][number];
  npcCombatActions: CombatAction[];
  selectedCombatActionId: string;
  setSelectedCombatActionId: (id: string) => void;
  selectedCombatAction: CombatAction | null;
  availableTargets: CombatState["participants"];
  targetId: string;
  setTargetId: (id: string) => void;
  loading: boolean;
  onExecuteAction: () => void;
}) => {
  return (
    <div className="rounded border border-rose-500/20 bg-slate-950/60 p-4">
      <h4 className="mb-2 font-bold text-rose-300">
        NPC Active Actions: {currentParticipant.display_name}
      </h4>
      {npcCombatActions.length === 0 ? (
        <div className="rounded border border-slate-800 bg-slate-900/60 p-3 text-xs text-slate-400">
          This entity has no structured combat actions configured yet.
        </div>
      ) : (
        <div className="space-y-3">
          <select
            className="w-full rounded border border-slate-700 bg-slate-900 p-2 text-white"
            value={selectedCombatActionId}
            onChange={(e) => setSelectedCombatActionId(e.target.value)}
          >
            {npcCombatActions.map((action) => (
              <option key={action.id} value={action.id}>
                {action.name} [{action.kind}]
              </option>
            ))}
          </select>

          {selectedCombatAction && (
            <div className="rounded border border-slate-800 bg-slate-900/70 p-3 text-xs text-slate-300">
              <p className="font-semibold text-slate-100">{selectedCombatAction.name}</p>
              {describeCombatAction(selectedCombatAction) && (
                <p className="mt-1 text-slate-400">{describeCombatAction(selectedCombatAction)}</p>
              )}
              {selectedCombatAction.description && (
                <p className="mt-2 text-slate-500">{selectedCombatAction.description}</p>
              )}
            </div>
          )}

          {selectedCombatAction?.kind !== "utility" && (
            <select
              className="w-full rounded bg-slate-900 p-2 text-white border border-slate-700"
              value={targetId}
              onChange={(e) => setTargetId(e.target.value)}
            >
              <option value="">Select Target...</option>
              {availableTargets.map((participant) => (
                <option key={participant.id} value={participant.ref_id}>
                  {participant.display_name}
                  {participant.id === currentParticipant.id ? " (self)" : ""}
                  {" "}
                  [{participant.status}]
                </option>
              ))}
            </select>
          )}

          <button
            disabled={loading || !selectedCombatActionId || (selectedCombatAction?.kind !== "utility" && !targetId)}
            onClick={onExecuteAction}
            className="w-full rounded bg-rose-600 px-4 py-3 font-bold text-white hover:bg-rose-500 disabled:opacity-50"
          >
            {selectedCombatAction?.kind === "weapon_attack" || selectedCombatAction?.kind === "spell_attack"
              ? "Abrir rolagem da acao"
              : "Execute Structured Action"}
          </button>
        </div>
      )}
    </div>
  );
};
