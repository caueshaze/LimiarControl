import { useState } from "react";
import { RollResultCard } from "../../../features/rolls/components/RollResultCard";
import type { StandardActionType } from "../../../shared/api/combatRepo";
import { useLocale } from "../../../shared/hooks/useLocale";
import { getCombatStatusLabel } from "../combatUi.helpers";
import type { PlayerBoardStatusSummary } from "../../../pages/PlayerBoardPage/playerBoard.types";
import type { PendingRoll } from "../../../pages/PlayerBoardPage/playerBoard.types";
import type {
  AttackResult,
  CombatMyParticipant,
  CombatShellData,
  ConsumableOption,
  DragonbornBreathWeaponOption,
  SelectedConsumable,
  SpellOption,
  SpellResult,
  UseObjectResult,
  UseObjectTargetOption,
} from "./playerCombatShell.types";
import { PlayerActionPanels } from "./PlayerActionPanels";

type Props = {
  combat: CombatShellData;
  consumableItemId: string;
  consumableOptions: ConsumableOption[];
  deathSaveFeedback: { message?: string | null } | null;
  dragonbornBreathWeaponAction: DragonbornBreathWeaponOption | null;
  handleAttack: () => Promise<void>;
  handleCast: () => Promise<void>;
  handleDeathSave: () => Promise<void>;
  handleDragonbornBreathWeapon: () => Promise<void>;
  handleEndTurn: () => Promise<void>;
  handleRequestReaction: () => Promise<void>;
  handleStandardAction: (action: StandardActionType, targetId?: string) => Promise<void>;
  handleUseObject: () => Promise<void>;
  lastAttackResult: AttackResult | null;
  lastSpellResult: SpellResult | null;
  lastUseObjectResult: UseObjectResult | null;
  myParticipant: CombatMyParticipant | null | undefined;
  pendingRoll: PendingRoll | null;
  playerStatus?: PlayerBoardStatusSummary | null;
  selectedConsumable: SelectedConsumable | null;
  selectedSpell: SpellOption | null;
  selectedSpellId: string;
  selectedTarget: { id: string } | null;
  setConsumableItemId: (id: string) => void;
  setSelectedSpellId: (id: string) => void;
  setTargetId: (id: string) => void;
  setUseObjectManualRolls: (updater: (current: number[]) => number[]) => void;
  setUseObjectNote: (note: string) => void;
  setUseObjectRollMode: (mode: "system" | "manual") => void;
  setUseObjectTargetParticipantId: (id: string) => void;
  spellOptions: SpellOption[];
  targetId: string;
  useObjectManualRolls: number[];
  useObjectNote: string;
  useObjectRollMode: "system" | "manual";
  useObjectTargetOptions: UseObjectTargetOption[];
  useObjectTargetParticipantId: string;
};

const waitLabelByPhase = (
  phase: string | null | undefined,
  isMyTurn: boolean,
  t: (key: any) => string,
) => {
  if (isMyTurn) {
    return t("combatUi.readyForTurn");
  }
  if (phase === "initiative") {
    return t("combatUi.waitingInitiative");
  }
  return t("combatUi.waitingTurn");
};

export const PlayerTurnPanel = ({
  combat,
  consumableItemId,
  consumableOptions,
  deathSaveFeedback,
  dragonbornBreathWeaponAction,
  handleAttack,
  handleCast,
  handleDeathSave,
  handleDragonbornBreathWeapon,
  handleEndTurn,
  handleRequestReaction,
  handleStandardAction,
  handleUseObject,
  lastAttackResult,
  lastSpellResult,
  lastUseObjectResult,
  myParticipant,
  pendingRoll,
  playerStatus,
  selectedConsumable,
  selectedSpell,
  selectedSpellId,
  selectedTarget,
  setConsumableItemId,
  setSelectedSpellId,
  setTargetId,
  setUseObjectManualRolls,
  setUseObjectNote,
  setUseObjectRollMode,
  setUseObjectTargetParticipantId,
  spellOptions,
  targetId,
  useObjectManualRolls,
  useObjectNote,
  useObjectRollMode,
  useObjectTargetOptions,
  useObjectTargetParticipantId,
}: Props) => {
  const { t } = useLocale();
  const [activeActionPanel, setActiveActionPanel] = useState<
    "attack" | "spell" | "standard" | "object"
  >("attack");

  const isDowned = myParticipant?.status === "downed";
  const canUseReaction = Boolean(
    combat.state?.phase === "active" &&
      myParticipant &&
      !myParticipant.turn_resources?.reaction_used,
  );
  const isReactionPending = myParticipant?.reaction_request?.status === "pending";
  const hasInitiativePending = pendingRoll?.rollType === "initiative";
  const actionUsed = Boolean(myParticipant?.turn_resources?.action_used);
  const canAct = Boolean(combat.isMyTurn && myParticipant?.status === "active");
  const turnSummaryLabel = waitLabelByPhase(combat.state?.phase, combat.isMyTurn, t);

  const selectedConsumableIsHealing = Boolean(selectedConsumable?.isHealingConsumable);
  const useObjectManualRollReady =
    !selectedConsumableIsHealing ||
    useObjectRollMode !== "manual" ||
    !selectedConsumable ||
    selectedConsumable.manualRollCount < 1 ||
    useObjectManualRolls.length === selectedConsumable.manualRollCount;
  const useObjectActionDisabled =
    !canAct ||
    actionUsed ||
    (selectedConsumableIsHealing &&
      (!useObjectTargetParticipantId || !useObjectManualRollReady));

  return (
    <div className="space-y-6">
      <section className="rounded-4xl border border-white/8 bg-[linear-gradient(180deg,rgba(30,41,59,0.9),rgba(2,6,23,0.96))] p-6 shadow-[0_18px_60px_rgba(2,6,23,0.25)]">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-slate-400">
              {t("combatUi.turnEyebrow")}
            </p>
            <h2 className="mt-2 text-2xl font-semibold text-white">{t("combatUi.playerTurnPanel")}</h2>
            <p className="mt-3 text-sm leading-7 text-slate-300">{turnSummaryLabel}</p>
          </div>
          {canUseReaction ? (
            isReactionPending ? (
              <button
                type="button"
                disabled
                className="rounded-full border border-sky-400/30 bg-sky-500/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-sky-100/50 cursor-not-allowed"
              >
                Aguardando Aprovação...
              </button>
            ) : (
              <button
                type="button"
                onClick={() => {
                  void handleRequestReaction();
                }}
                className="rounded-full border border-sky-400/30 bg-sky-500/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-sky-100 transition-colors hover:bg-sky-500/20"
              >
                Solicitar Reação
              </button>
            )
          ) : null}
        </div>

        {!combat.state ? (
          <div className="mt-5 rounded-3xl border border-dashed border-white/10 bg-white/3 px-4 py-5 text-sm text-slate-400">
            {combat.loading ? t("combatUi.loadingState") : combat.error ?? t("combatUi.noCombatState")}
          </div>
        ) : isDowned ? (
          <div className="mt-5 rounded-3xl border border-rose-500/25 bg-rose-950/30 p-5">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h3 className="text-lg font-semibold text-rose-100">{t("combatUi.downedTitle")}</h3>
                <p className="mt-2 text-sm text-rose-200">
                  {combat.isMyTurn ? t("combatUi.downedYourTurn") : t("combatUi.downedWaiting")}
                </p>
              </div>
              <button
                type="button"
                disabled={!combat.isMyTurn}
                onClick={() => {
                  void handleDeathSave();
                }}
                className="rounded-full bg-rose-600 px-5 py-3 text-sm font-semibold uppercase tracking-[0.24em] text-white transition-colors hover:bg-rose-500 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {t("combatUi.rollDeathSave")}
              </button>
            </div>
            {deathSaveFeedback?.message ? (
              <p className="mt-4 text-sm text-rose-100">{deathSaveFeedback.message}</p>
            ) : null}
          </div>
        ) : (
          <div className="mt-5 space-y-5">
            {hasInitiativePending ? (
              <div className="rounded-3xl border border-sky-400/25 bg-sky-500/10 px-4 py-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-sky-100">
                  {t("playerBoard.rollRequest")}
                </p>
                <p className="mt-2 text-sm text-slate-100">
                  {pendingRoll?.reason ?? pendingRoll?.expression.toUpperCase()}
                </p>
                <p className="mt-2 text-xs leading-6 text-slate-300">
                  {t("combatUi.waitingInitiative")}
                </p>
              </div>
            ) : null}

            <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(240px,0.8fr)]">
              <label className="space-y-2">
                <span className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                  {t("combatUi.target")}
                </span>
                <select
                  value={targetId}
                  onChange={(event) => setTargetId(event.target.value)}
                  className="w-full rounded-3xl border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-white outline-none transition-colors focus:border-limiar-400"
                >
                  <option value="">{t("combatUi.selectTarget")}</option>
                  {combat.livingParticipants
                    .filter((participant) => participant.kind === "player" || participant.visible !== false)
                    .map((participant) => (
                      <option key={participant.id} value={participant.ref_id}>
                        {participant.display_name}
                      </option>
                    ))}
                </select>
              </label>

              <div className="rounded-3xl border border-white/8 bg-white/4 px-4 py-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                  {t("combatUi.currentTurnState")}
                </p>
                <p className="mt-2 text-sm text-slate-200">
                  {combat.currentParticipant?.display_name ?? "-"}
                </p>
                <p className="mt-2 text-xs text-slate-400">
                  {combat.currentParticipant
                    ? getCombatStatusLabel(t, combat.currentParticipant.status)
                    : t("combatUi.waitingTurn")}
                </p>
              </div>
            </div>

            <PlayerActionPanels
              activeActionPanel={activeActionPanel}
              actionUsed={actionUsed}
              canAct={canAct}
              consumableItemId={consumableItemId}
              consumableOptions={consumableOptions}
              dragonbornBreathWeaponAction={dragonbornBreathWeaponAction}
              handleAttack={handleAttack}
              handleCast={handleCast}
              handleDragonbornBreathWeapon={handleDragonbornBreathWeapon}
              handleStandardAction={handleStandardAction}
              handleUseObject={handleUseObject}
              myParticipantId={myParticipant?.id}
              playerStatus={playerStatus}
              selectedConsumable={selectedConsumable}
              selectedTarget={selectedTarget}
              selectedSpell={selectedSpell}
              selectedSpellId={selectedSpellId}
              turnResources={myParticipant?.turn_resources ?? null}
              setActiveActionPanel={setActiveActionPanel}
              setConsumableItemId={setConsumableItemId}
              setSelectedSpellId={setSelectedSpellId}
              setUseObjectManualRolls={setUseObjectManualRolls}
              setUseObjectNote={setUseObjectNote}
              setUseObjectRollMode={setUseObjectRollMode}
              setUseObjectTargetParticipantId={setUseObjectTargetParticipantId}
              spellOptions={spellOptions}
              targetId={targetId}
              useObjectActionDisabled={useObjectActionDisabled}
              useObjectManualRolls={useObjectManualRolls}
              useObjectNote={useObjectNote}
              useObjectRollMode={useObjectRollMode}
              useObjectTargetOptions={useObjectTargetOptions}
              useObjectTargetParticipantId={useObjectTargetParticipantId}
            />

            <div className="flex justify-end">
              <button
                type="button"
                disabled={!combat.isMyTurn || combat.state?.phase !== "active"}
                onClick={() => {
                  void handleEndTurn();
                }}
                className="rounded-full border border-white/12 bg-white/6 px-5 py-3 text-xs font-semibold uppercase tracking-[0.24em] text-white transition-colors hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {t("combatUi.endTurn")}
              </button>
            </div>
          </div>
        )}
      </section>

      {lastAttackResult ? (
        <section className="rounded-4xl border border-amber-500/15 bg-amber-500/8 p-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-amber-100">
            {t("combatUi.lastAttack")}
          </p>
          <div className="mt-4">
            <RollResultCard result={lastAttackResult.roll_result} hideDc />
          </div>
        </section>
      ) : null}

      {lastSpellResult?.roll_result ? (
        <section className="rounded-4xl border border-fuchsia-500/15 bg-fuchsia-500/8 p-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-fuchsia-100">
            {t("combatUi.lastSpell")}
          </p>
          <div className="mt-4">
            <RollResultCard result={lastSpellResult.roll_result} hideDc />
          </div>
        </section>
      ) : null}

      {lastUseObjectResult ? (
        <section className="rounded-4xl border border-emerald-500/15 bg-emerald-500/8 p-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-emerald-100">
            {t("combatUi.lastConsumable")}
          </p>
          <div className="mt-4 rounded-3xl border border-emerald-400/15 bg-slate-950/35 px-4 py-4">
            <p className="text-sm leading-6 text-white">{lastUseObjectResult.message}</p>
            {lastUseObjectResult.target_display_name && lastUseObjectResult.new_hp != null ? (
              <p className="mt-2 text-xs text-slate-300">
                {lastUseObjectResult.target_display_name} · {t("combatUi.hp")} {lastUseObjectResult.new_hp}
              </p>
            ) : null}
          </div>
        </section>
      ) : null}
    </div>
  );
};
