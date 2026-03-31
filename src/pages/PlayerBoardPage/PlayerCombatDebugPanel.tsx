import { RollResultCard } from "../../features/rolls/components/RollResultCard";
import { PlayerAttackRollDialog } from "./player-combat-debug/PlayerAttackRollDialog";
import { PlayerCombatParticipants } from "./player-combat-debug/PlayerCombatParticipants";
import { PlayerDeathSaveFeedbackCard } from "./player-combat-debug/PlayerDeathSaveFeedbackCard";
import { PlayerSpellCastDialog } from "./player-combat-debug/PlayerSpellCastDialog";
import { PlayerTurnActions } from "./player-combat-debug/PlayerTurnActions";
import type { PlayerCombatDebugPanelProps } from "./player-combat-debug/types";
import { usePlayerCombatDebugState } from "./player-combat-debug/usePlayerCombatDebugState";

export const PlayerCombatDebugPanel = ({
  campaignId,
  playerSheet,
  playerStatus,
  sessionId,
  userId,
}: PlayerCombatDebugPanelProps) => {
  const {
    activeTab,
    attackDialogOpen,
    closeAttackDialog,
    closeSpellDialog,
    deathSaveFeedback,
    dragonbornBreathWeaponAction,
    error,
    handleAttack,
    handleAttackResolved,
    handleCast,
    handleDeathSave,
    handleEndTurn,
    handleSpellResolved,
    handleStandardAction,
    lastAttackResult,
    lastSpellResult,
    loading,
    selectedSpell,
    selectedSpellId,
    setActiveTab,
    setSelectedSpellId,
    setSpellDamageType,
    setSpellEffectBonus,
    setSpellEffectDice,
    setSpellMode,
    setSpellSaveAbility,
    setTargetId,
    spellDamageType,
    spellDialogOpen,
    spellEffectBonus,
    spellEffectDice,
    spellMode,
    spellOptions,
    spellSaveAbility,
    state,
    targetId,
  } = usePlayerCombatDebugState({ campaignId, playerSheet, playerStatus, sessionId });

  if (!state || state.phase === "ended" || !userId) return null;

  const currentParticipant = state.participants[state.current_turn_index];
  const myParticipant =
    state.participants.find((participant) => participant.actor_user_id === userId) ?? null;
  const isMyTurn = state.phase === "active" && currentParticipant?.id === myParticipant?.id;
  const canRollDeathSave = myParticipant?.status === "downed" && isMyTurn;
  const isActive = isMyTurn && myParticipant?.status === "active";
  const otherParticipants = state.participants.filter(
    (participant) => participant.id !== myParticipant?.id,
  );
  const livingTargets = otherParticipants.filter(
    (participant) => participant.status !== "dead" && participant.status !== "defeated",
  );
  const defeatedTargets = otherParticipants.filter(
    (participant) => participant.status === "dead" || participant.status === "defeated",
  );
  const selectedTarget =
    livingTargets.find((participant) => participant.ref_id === targetId) ??
    defeatedTargets.find((participant) => participant.ref_id === targetId) ??
    null;

  return (
    <div className="rounded-xl border border-sky-500/30 bg-sky-950/20 p-4 shadow-xl">
      <h3 className="text-lg font-bold text-sky-300">Combat Feed (Phase 1)</h3>

      {error && (
        <div className="mt-4 rounded border border-rose-500 bg-rose-500/10 p-2 text-sm text-rose-200">
          <strong>Error:</strong> {error}
        </div>
      )}

      <div className="mt-4 space-y-4 text-sm text-slate-300">
        <div className="flex items-center justify-between rounded border border-sky-500/20 bg-sky-900/10 p-2">
          <span>
            Phase: <strong className="uppercase text-sky-400">{state.phase}</strong>
          </span>
          <span>
            Round: <strong className="text-white">{state.round}</strong>
          </span>
        </div>

        <PlayerCombatParticipants state={state} userId={userId} />

        {deathSaveFeedback && <PlayerDeathSaveFeedbackCard feedback={deathSaveFeedback} />}

        <PlayerTurnActions
          activeTab={activeTab}
          canRollDeathSave={canRollDeathSave}
          currentWeapon={playerStatus?.currentWeapon ?? null}
          deathSaveVisible={myParticipant?.status === "downed"}
          defeatedTargets={defeatedTargets}
          dragonbornBreathWeaponAction={dragonbornBreathWeaponAction}
          isActive={isActive}
          isMyTurn={isMyTurn}
          loading={loading}
          livingTargets={livingTargets}
          myParticipant={myParticipant}
          onAttack={handleAttack}
          onCast={handleCast}
          onDeathSave={handleDeathSave}
          onEndTurn={handleEndTurn}
          onStandardAction={handleStandardAction}
          selectedSpell={selectedSpell}
          selectedSpellId={selectedSpellId}
          setActiveTab={setActiveTab}
          setSelectedSpellId={setSelectedSpellId}
          setSpellDamageType={setSpellDamageType}
          setSpellEffectBonus={setSpellEffectBonus}
          setSpellEffectDice={setSpellEffectDice}
          setSpellMode={setSpellMode}
          setSpellSaveAbility={setSpellSaveAbility}
          setTargetId={setTargetId}
          spellDamageType={spellDamageType}
          spellEffectBonus={spellEffectBonus}
          spellEffectDice={spellEffectDice}
          spellMode={spellMode}
          spellOptions={spellOptions}
          spellSaveAbility={spellSaveAbility}
          targetId={targetId}
        />

        {lastAttackResult && (
          <div className="rounded-xl border border-rose-500/20 bg-rose-950/20 p-4">
            <h4 className="text-sm font-bold uppercase tracking-widest text-rose-200">
              Ultimo ataque
            </h4>
            <div className="mt-3">
              <RollResultCard result={lastAttackResult.roll_result} hideDc />
            </div>
            <p className="mt-3 text-sm text-slate-200">
              {lastAttackResult.is_hit
                ? `${lastAttackResult.weapon_name} acertou ${lastAttackResult.target_display_name} e causou ${lastAttackResult.damage} de dano.`
                : `${lastAttackResult.weapon_name} errou ${lastAttackResult.target_display_name}.`}
            </p>
          </div>
        )}

        {lastSpellResult && (
          <div className="rounded-xl border border-fuchsia-500/20 bg-fuchsia-950/20 p-4">
            <h4 className="text-sm font-bold uppercase tracking-widest text-fuchsia-200">
              Ultima magia
            </h4>
            {lastSpellResult.roll_result ? (
              <div className="mt-3">
                <RollResultCard result={lastSpellResult.roll_result} hideDc />
              </div>
            ) : null}
            <p className="mt-3 text-sm text-slate-200">
              {lastSpellResult.effect_kind === "healing"
                ? `${lastSpellResult.spell_name} restaurou ${lastSpellResult.healing} HP em ${lastSpellResult.target_display_name}.`
                : `${lastSpellResult.spell_name} ${lastSpellResult.is_hit === false ? "nao acertou" : lastSpellResult.is_saved ? "foi resistida por" : "atingiu"} ${lastSpellResult.target_display_name}${lastSpellResult.damage > 0 ? ` e causou ${lastSpellResult.damage} de dano.` : "."}`}
            </p>
          </div>
        )}
      </div>

      {attackDialogOpen && state.phase === "active" && currentParticipant && selectedTarget ? (
        <PlayerAttackRollDialog
          actorParticipantId={currentParticipant.id}
          sessionId={sessionId}
          target={selectedTarget}
          weapon={playerStatus?.currentWeapon ?? null}
          onClose={closeAttackDialog}
          onResolved={handleAttackResolved}
        />
      ) : null}

      {spellDialogOpen && state.phase === "active" && currentParticipant && selectedTarget && selectedSpell ? (
        <PlayerSpellCastDialog
          actorParticipantId={currentParticipant.id}
          onClose={closeSpellDialog}
          onResolved={handleSpellResolved}
          sessionId={sessionId}
          spell={selectedSpell}
          spellDamageType={spellDamageType}
          spellEffectBonus={spellEffectBonus}
          spellEffectDice={spellEffectDice}
          spellMode={spellMode}
          spellSaveAbility={spellSaveAbility}
          target={selectedTarget}
        />
      ) : null}
    </div>
  );
};
