import { describeCombatAction } from "../../../entities/campaign-entity/describeCombatAction";
import type { CombatAction } from "../../../entities/campaign-entity/campaignEntity.types";
import type { CombatParticipant, CombatEntityActionResult, StandardActionType } from "../../../shared/api/combatRepo";
import { useLocale } from "../../../shared/hooks/useLocale";
import { getCombatStatusLabel } from "../combatUi.helpers";
import { RollResultCard } from "../../rolls/components/RollResultCard";

const ENTITY_STANDARD_ACTIONS: StandardActionType[] = [
  "dodge",
  "help",
  "hide",
  "use_object",
  "dash",
  "disengage",
];

type Props = {
  currentParticipant: CombatParticipant;
  npcCombatActions: CombatAction[];
  attackCombatActions: CombatAction[];
  spellCombatActions: CombatAction[];
  utilityCombatActions: CombatAction[];
  activeStructuredActions: CombatAction[];
  availableTargets: CombatParticipant[];
  availableStandardTargets: CombatParticipant[];
  entityActionPanel: "attack" | "spell" | "standard";
  attackPanelEnabled: boolean;
  spellPanelEnabled: boolean;
  selectedCombatActionId: string;
  selectedCombatAction: CombatAction | null;
  selectedTargetRefId: string;
  selectedUtilityActionId: string;
  selectedUtilityAction: CombatAction | null;
  selectedStandardAction: StandardActionType;
  selectedStandardTargetId: string;
  standardActionNote: string;
  submitting: boolean;
  lastEntityActionResult: CombatEntityActionResult | null;
  onSetEntityActionPanel: (panel: "attack" | "spell" | "standard") => void;
  onSetSelectedCombatActionId: (id: string) => void;
  onSetSelectedTargetRefId: (id: string) => void;
  onSetSelectedUtilityActionId: (id: string) => void;
  onSetSelectedStandardAction: (action: StandardActionType) => void;
  onSetSelectedStandardTargetId: (id: string) => void;
  onSetStandardActionNote: (note: string) => void;
  onEntityAction: () => void;
  onNpcStandardAction: () => void;
  onEntityUtilityAction: () => void;
};

export const GmNpcActionPanel = ({
  currentParticipant,
  npcCombatActions,
  attackCombatActions,
  spellCombatActions,
  utilityCombatActions,
  activeStructuredActions,
  availableTargets,
  availableStandardTargets,
  entityActionPanel,
  attackPanelEnabled,
  spellPanelEnabled,
  selectedCombatActionId,
  selectedCombatAction,
  selectedTargetRefId,
  selectedUtilityActionId,
  selectedUtilityAction,
  selectedStandardAction,
  selectedStandardTargetId,
  standardActionNote,
  submitting,
  lastEntityActionResult,
  onSetEntityActionPanel,
  onSetSelectedCombatActionId,
  onSetSelectedTargetRefId,
  onSetSelectedUtilityActionId,
  onSetSelectedStandardAction,
  onSetSelectedStandardTargetId,
  onSetStandardActionNote,
  onEntityAction,
  onNpcStandardAction,
  onEntityUtilityAction,
}: Props) => {
  const { t } = useLocale();

  return (
    <div className="mt-4 rounded-3xl border border-white/8 bg-white/4 px-4 py-4">
      <p className="text-sm text-slate-200">{t("combatUi.npcTurnHint")}</p>
      <p className="mt-2 text-xs text-slate-400">
        {t("combatUi.npcTurnDescription")}
      </p>
      <div className="mt-4 space-y-3">
        {npcCombatActions.length === 0 ? (
          <p className="rounded-2xl border border-white/8 bg-slate-950/40 px-3 py-3 text-xs text-slate-400">
            {t("combatUi.entityNoStructuredActions")}
          </p>
        ) : null}

        <div className="grid gap-2 sm:grid-cols-3">
          {(
            [
              ["attack", t("combatUi.attack")],
              ["spell", t("combatUi.castSpell")],
              ["standard", t("combatUi.standardActions")],
            ] as const
          ).map(([panel, label]) => {
            const isActive = entityActionPanel === panel;
            const isDisabled =
              panel === "attack" ? !attackPanelEnabled : panel === "spell" ? !spellPanelEnabled : false;
            return (
              <button
                key={panel}
                type="button"
                disabled={isDisabled}
                onClick={() => onSetEntityActionPanel(panel)}
                className={`rounded-2xl px-4 py-3 text-sm font-semibold transition-colors ${
                  isActive
                    ? "bg-white text-slate-950"
                    : isDisabled
                      ? "cursor-not-allowed bg-slate-950/30 text-slate-500 opacity-60"
                      : "bg-slate-950/50 text-slate-200 hover:bg-slate-900/70"
                }`}
              >
                <span className="block whitespace-normal wrap-break-word leading-5">{label}</span>
              </button>
            );
          })}
        </div>

        {entityActionPanel === "attack" || entityActionPanel === "spell" ? (
          activeStructuredActions.length === 0 ? (
            <p className="rounded-2xl border border-white/8 bg-slate-950/40 px-3 py-3 text-xs text-slate-400">
              {entityActionPanel === "attack"
                ? t("combatUi.entityNoAttackActions")
                : t("combatUi.entityNoSpellActions")}
            </p>
          ) : (
            <>
              <select
                value={selectedCombatActionId}
                onChange={(event) => onSetSelectedCombatActionId(event.target.value)}
                className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-rose-400"
              >
                {activeStructuredActions.map((action) => (
                  <option key={action.id} value={action.id}>
                    {action.name}
                  </option>
                ))}
              </select>

              {selectedCombatAction ? (
                <div className="rounded-2xl border border-white/8 bg-slate-950/40 px-3 py-3 text-xs text-slate-300">
                  <p className="font-semibold text-white">{selectedCombatAction.name}</p>
                  {describeCombatAction(selectedCombatAction) ? (
                    <p className="mt-1 text-slate-400">{describeCombatAction(selectedCombatAction)}</p>
                  ) : null}
                  {selectedCombatAction.description ? (
                    <p className="mt-2 text-slate-500">{selectedCombatAction.description}</p>
                  ) : null}
                </div>
              ) : null}

              <select
                value={selectedTargetRefId}
                onChange={(event) => onSetSelectedTargetRefId(event.target.value)}
                className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-rose-400"
              >
                <option value="">{t("combatUi.selectTarget")}</option>
                {availableTargets.map((participant) => (
                  <option key={participant.id} value={participant.ref_id}>
                    {participant.display_name}
                    {participant.id === currentParticipant.id ? ` (${t("combatUi.self")})` : ""}{" "}
                    [{getCombatStatusLabel(t, participant.status)}]
                  </option>
                ))}
              </select>

              <button
                type="button"
                disabled={submitting || !selectedCombatActionId || !selectedTargetRefId}
                onClick={onEntityAction}
                className="w-full rounded-3xl bg-rose-600 px-4 py-3 text-sm font-semibold uppercase tracking-[0.22em] text-white transition-colors hover:bg-rose-500 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {selectedCombatAction?.kind === "weapon_attack" || selectedCombatAction?.kind === "spell_attack"
                  ? t("combatUi.entityOpenActionRoll")
                  : t("combatUi.entityExecuteAction")}
              </button>
            </>
          )
        ) : null}

        {entityActionPanel === "standard" ? (
          <div className="space-y-4">
            <div className="space-y-3">
              <div className="grid gap-2 sm:grid-cols-2">
                {ENTITY_STANDARD_ACTIONS.map((action) => {
                  const isActive = selectedStandardAction === action;
                  const labelKey =
                    action === "use_object"
                      ? "combatUi.useObject"
                      : action === "dodge"
                        ? "combatUi.dodge"
                        : action === "help"
                          ? "combatUi.help"
                          : action === "hide"
                            ? "combatUi.hide"
                            : action === "dash"
                              ? "combatUi.dash"
                              : "combatUi.disengage";
                  return (
                    <button
                      key={action}
                      type="button"
                      onClick={() => onSetSelectedStandardAction(action)}
                      className={`rounded-2xl border px-4 py-3 text-left text-sm font-semibold transition-colors ${
                        isActive
                          ? "border-rose-400/50 bg-rose-500/20 text-white"
                          : "border-white/10 bg-slate-950/50 text-slate-200 hover:bg-slate-900/70"
                      }`}
                    >
                      <span className="block whitespace-normal wrap-break-word leading-5">{t(labelKey)}</span>
                    </button>
                  );
                })}
              </div>

              {selectedStandardAction === "help" ? (
                <select
                  value={selectedStandardTargetId}
                  onChange={(event) => onSetSelectedStandardTargetId(event.target.value)}
                  className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-rose-400"
                >
                  <option value="">{t("combatUi.selectTarget")}</option>
                  {availableStandardTargets.map((participant) => (
                    <option key={participant.id} value={participant.id}>
                      {participant.display_name} [{getCombatStatusLabel(t, participant.status)}]
                    </option>
                  ))}
                </select>
              ) : null}

              {selectedStandardAction === "use_object" ? (
                <input
                  type="text"
                  value={standardActionNote}
                  onChange={(event) => onSetStandardActionNote(event.target.value)}
                  placeholder={t("combatUi.useObjectPlaceholder")}
                  className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none transition-colors placeholder:text-slate-500 focus:border-rose-400"
                />
              ) : null}

              <button
                type="button"
                disabled={submitting || (selectedStandardAction === "help" && !selectedStandardTargetId)}
                onClick={onNpcStandardAction}
                className="w-full rounded-3xl bg-rose-600 px-4 py-3 text-sm font-semibold uppercase tracking-[0.22em] text-white transition-colors hover:bg-rose-500 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {t("combatUi.entityUseStandardAction")}
              </button>
            </div>

            {utilityCombatActions.length > 0 ? (
              <div className="space-y-3 rounded-3xl border border-white/8 bg-slate-950/35 px-4 py-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                  {t("combatUi.entityUtilityActions")}
                </p>

                <select
                  value={selectedUtilityActionId}
                  onChange={(event) => onSetSelectedUtilityActionId(event.target.value)}
                  className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-rose-400"
                >
                  {utilityCombatActions.map((action) => (
                    <option key={action.id} value={action.id}>
                      {action.name}
                    </option>
                  ))}
                </select>

                {selectedUtilityAction ? (
                  <div className="rounded-2xl border border-white/8 bg-slate-950/40 px-3 py-3 text-xs text-slate-300">
                    <p className="font-semibold text-white">{selectedUtilityAction.name}</p>
                    {describeCombatAction(selectedUtilityAction) ? (
                      <p className="mt-1 text-slate-400">{describeCombatAction(selectedUtilityAction)}</p>
                    ) : null}
                    {selectedUtilityAction.description ? (
                      <p className="mt-2 text-slate-500">{selectedUtilityAction.description}</p>
                    ) : null}
                  </div>
                ) : null}

                <button
                  type="button"
                  disabled={submitting || !selectedUtilityActionId}
                  onClick={onEntityUtilityAction}
                  className="w-full rounded-3xl border border-white/12 bg-white/6 px-4 py-3 text-sm font-semibold uppercase tracking-[0.22em] text-white transition-colors hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {t("combatUi.entityExecuteAction")}
                </button>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>

      {lastEntityActionResult?.roll_result ? (
        <div className="mt-4 rounded-3xl border border-amber-500/20 bg-amber-500/10 p-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-amber-200">
            {t("combatUi.lastEntityRoll")}
          </p>
          <div className="mt-3">
            <RollResultCard result={lastEntityActionResult.roll_result} />
          </div>
        </div>
      ) : null}
    </div>
  );
};
