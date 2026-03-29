import { useMemo } from "react";
import type {
  AbilityName,
  AdvantageMode,
  RollType,
  SkillName,
} from "../../../entities/roll/rollResolution.types";
import { AuthoritativeRollDialog } from "../../../features/rolls/components/AuthoritativeRollDialog";
import { useLocale } from "../../../shared/hooks/useLocale";
import { CombatLogPanel } from "../components/CombatLogPanel";
import { CombatModeBar } from "../components/CombatModeBar";
import { CombatParticipantRoster } from "../components/CombatParticipantRoster";
import { buildCombatParticipantViews, getCombatEffectLabel, getCombatStatusLabel } from "../combatUi.helpers";
import { PlayerAttackRollDialog } from "../../../pages/PlayerBoardPage/player-combat-debug/PlayerAttackRollDialog";
import { PlayerSpellCastDialog } from "../../../pages/PlayerBoardPage/player-combat-debug/PlayerSpellCastDialog";
import { PlayerBoardRollDialog } from "../../../pages/PlayerBoardPage/PlayerBoardRollDialog";
import type { CharacterSheet } from "../../../features/character-sheet/model/characterSheet.types";
import type { InventoryItem } from "../../../entities/inventory";
import type { Item } from "../../../entities/item";
import type { Locale } from "../../../shared/i18n";
import type {
  PendingRoll,
  PlayerBoardStatusSummary,
} from "../../../pages/PlayerBoardPage/playerBoard.types";
import { usePlayerCombatMode } from "./usePlayerCombatMode";
import { PlayerTurnPanel } from "./PlayerTurnPanel";

type Props = {
  campaignId?: string | null;
  expanded: boolean;
  inventory: InventoryItem[] | null;
  itemsById: Record<string, Item>;
  locale: Locale;
  manualValue: string;
  onAuthoritativeRollResolved: () => void;
  onClearPendingRoll: () => void;
  onInventoryChanged?: () => void | Promise<void>;
  onManualValueChange: (value: string) => void;
  onRollModeChange: (mode: "virtual" | "manual" | null) => void;
  onSubmitManualRoll: () => Promise<void>;
  onToggleExpanded: () => void;
  onVirtualRoll: () => void;
  pendingRoll: PendingRoll | null;
  playerSheet?: CharacterSheet | null;
  playerStatus?: PlayerBoardStatusSummary | null;
  rollMode: "virtual" | "manual" | null;
  sessionId: string;
  userId?: string | null;
};

export const PlayerCombatModeShell = ({
  campaignId,
  expanded,
  inventory,
  itemsById,
  locale,
  manualValue,
  onAuthoritativeRollResolved,
  onClearPendingRoll,
  onInventoryChanged,
  onManualValueChange,
  onRollModeChange,
  onSubmitManualRoll,
  onToggleExpanded,
  onVirtualRoll,
  pendingRoll,
  playerSheet,
  playerStatus,
  rollMode,
  sessionId,
  userId = null,
}: Props) => {
  const { t } = useLocale();
  const {
    attackDialogOpen,
    closeAttackDialog,
    closeSpellDialog,
    combat,
    consumableItemId,
    consumableOptions,
    deathSaveFeedback,
    dragonbornBreathWeaponAction,
    handleAttack,
    handleRequestReaction,
    handleDeathSave,
    handleDragonbornBreathWeapon,
    handleEndTurn,
    handleStandardAction,
    handleUseObject,
    handleCast,
    lastAttackResult,
    lastSpellResult,
    lastUseObjectResult,
    selectedConsumable,
    selectedSpell,
    selectedSpellId,
    selectedTarget,
    setConsumableItemId,
    setLastAttackResult,
    setLastSpellResult,
    setSelectedSpellId,
    setSpellDamageType,
    setSpellEffectBonus,
    setSpellEffectDice,
    setSpellMode,
    setSpellSaveAbility,
    setTargetId,
    setUseObjectManualRolls,
    setUseObjectNote,
    setUseObjectRollMode,
    setUseObjectTargetParticipantId,
    spellDamageType,
    spellDialogOpen,
    spellEffectBonus,
    spellEffectDice,
    spellMode,
    spellOptions,
    spellSaveAbility,
    targetId,
    useObjectNote,
    useObjectManualRolls,
    useObjectRollMode,
    useObjectTargetOptions,
    useObjectTargetParticipantId,
    visibleParticipants,
  } = usePlayerCombatMode({
    campaignId,
    inventory,
    itemsById,
    locale,
    playerSheet,
    playerStatus,
    sessionId,
    userId,
  });

  const rosterParticipants = useMemo(
    () =>
      buildCombatParticipantViews({
        currentTurnIndex: combat.state?.current_turn_index ?? -1,
        participants: visibleParticipants,
        playerVitalsByUserId: userId
          ? {
              [userId]: {
                currentHp: playerStatus?.currentHp ?? null,
                maxHp: playerStatus?.maxHp ?? null,
              },
            }
          : {},
        userId,
      }),
    [combat.state?.current_turn_index, playerStatus?.currentHp, playerStatus?.maxHp, userId, visibleParticipants],
  );

  const myParticipant = combat.myParticipant;

  return (
    <section className="space-y-6">
      <CombatModeBar
        currentParticipantName={combat.currentParticipant?.display_name ?? null}
        expanded={expanded}
        isMyTurn={combat.isMyTurn}
        onToggleExpanded={onToggleExpanded}
        phase={combat.state?.phase ?? null}
        round={combat.state?.round ?? null}
        turnResources={myParticipant?.turn_resources ?? null}
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.08fr)_minmax(340px,0.92fr)]">
        <PlayerTurnPanel
          combat={combat}
          consumableItemId={consumableItemId}
          consumableOptions={consumableOptions}
          deathSaveFeedback={deathSaveFeedback}
          dragonbornBreathWeaponAction={dragonbornBreathWeaponAction}
          handleAttack={handleAttack}
          handleCast={handleCast}
          handleDeathSave={handleDeathSave}
          handleDragonbornBreathWeapon={handleDragonbornBreathWeapon}
          handleEndTurn={handleEndTurn}
          handleRequestReaction={handleRequestReaction}
          handleStandardAction={handleStandardAction}
          handleUseObject={handleUseObject}
          lastAttackResult={lastAttackResult}
          lastSpellResult={lastSpellResult}
          lastUseObjectResult={lastUseObjectResult}
          myParticipant={myParticipant}
          pendingRoll={pendingRoll}
          playerStatus={playerStatus}
          selectedConsumable={selectedConsumable}
          selectedSpell={selectedSpell}
          selectedSpellId={selectedSpellId}
          selectedTarget={selectedTarget}
          setConsumableItemId={setConsumableItemId}
          setSelectedSpellId={setSelectedSpellId}
          setTargetId={setTargetId}
          setUseObjectManualRolls={setUseObjectManualRolls}
          setUseObjectNote={setUseObjectNote}
          setUseObjectRollMode={setUseObjectRollMode}
          setUseObjectTargetParticipantId={setUseObjectTargetParticipantId}
          spellOptions={spellOptions}
          targetId={targetId}
          useObjectManualRolls={useObjectManualRolls}
          useObjectNote={useObjectNote}
          useObjectRollMode={useObjectRollMode}
          useObjectTargetOptions={useObjectTargetOptions}
          useObjectTargetParticipantId={useObjectTargetParticipantId}
        />

        <div className="space-y-6">
          <section className="rounded-4xl border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.85),rgba(2,6,23,0.94))] p-5 shadow-[0_18px_60px_rgba(2,6,23,0.2)]">
            <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-slate-400">
              {t("combatUi.statusEyebrow")}
            </p>
            <h3 className="mt-2 text-lg font-semibold text-white">{t("combatUi.statusTitle")}</h3>

            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <div className="rounded-3xl border border-white/8 bg-white/4 px-4 py-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">{t("combatUi.hp")}</p>
                <p className="mt-2 text-xl font-semibold text-white">
                  {playerStatus ? `${playerStatus.currentHp}/${playerStatus.maxHp}` : "-"}
                </p>
              </div>
              <div className="rounded-3xl border border-white/8 bg-white/4 px-4 py-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">{t("combatUi.armorClass")}</p>
                <p className="mt-2 text-xl font-semibold text-white">{playerStatus?.ac ?? "-"}</p>
              </div>
              <div className="rounded-3xl border border-white/8 bg-white/4 px-4 py-4 sm:col-span-2">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">{t("combatUi.currentWeapon")}</p>
                <p className="mt-2 text-sm font-semibold text-white">
                  {playerStatus?.currentWeapon?.name ?? t("combatUi.noWeapon")}
                </p>
                {playerStatus?.currentWeapon ? (
                  <p className="mt-2 text-xs text-slate-300">
                    {playerStatus.currentWeapon.damageLabel}
                  </p>
                ) : null}
              </div>
            </div>

            <div className="mt-4 rounded-3xl border border-white/8 bg-white/4 px-4 py-4">
              <div className="flex items-center justify-between gap-3">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                  {t("combatUi.effects")}
                </p>
                <span className="text-xs text-slate-500">
                  {myParticipant ? getCombatStatusLabel(t, myParticipant.status) : "-"}
                </span>
              </div>
              {myParticipant?.active_effects?.length ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  {myParticipant.active_effects.map((effect) => (
                    <span
                      key={effect.id}
                      className="rounded-full border border-fuchsia-500/25 bg-fuchsia-500/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-fuchsia-100"
                    >
                      {getCombatEffectLabel(t, effect)}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="mt-3 text-sm text-slate-400">{t("combatUi.noEffects")}</p>
              )}
            </div>
          </section>

          <CombatParticipantRoster
            participants={rosterParticipants}
            subtitle={t("combatUi.participantsDescription")}
            title={t("combatUi.participants")}
          />

          <CombatLogPanel logs={combat.logs} />
        </div>
      </div>

      {attackDialogOpen && combat.state?.phase === "active" && combat.currentParticipant && selectedTarget ? (
        <PlayerAttackRollDialog
          actorParticipantId={combat.currentParticipant.id}
          onClose={closeAttackDialog}
          onResolved={(result) => {
            setLastAttackResult(result);
          }}
          sessionId={sessionId}
          target={selectedTarget}
          weapon={playerStatus?.currentWeapon ?? null}
        />
      ) : null}

      {spellDialogOpen && combat.state?.phase === "active" && combat.currentParticipant && selectedTarget && selectedSpell ? (
        <PlayerSpellCastDialog
          actorParticipantId={combat.currentParticipant.id}
          onClose={closeSpellDialog}
          onResolved={(result) => {
            setLastSpellResult(result);
            if (result.inventory_refresh_required) {
              void onInventoryChanged?.();
            }
          }}
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

      {pendingRoll && pendingRoll.rollType ? (
        <AuthoritativeRollDialog
          request={{
            rollType: pendingRoll.rollType as RollType,
            ability: (pendingRoll.ability ?? undefined) as AbilityName | undefined,
            skill: (pendingRoll.skill ?? undefined) as SkillName | undefined,
            advantageMode: (pendingRoll.mode ?? "normal") as AdvantageMode,
            dc: pendingRoll.dc,
            reason: pendingRoll.reason,
            issuedBy: pendingRoll.issuedBy,
          }}
          sessionId={sessionId}
          actorKind="player"
          actorRefId={userId ?? ""}
          onClose={onClearPendingRoll}
          onResolved={onAuthoritativeRollResolved}
        />
      ) : pendingRoll ? (
        <PlayerBoardRollDialog
          activeSessionId={sessionId}
          manualValue={manualValue}
          pendingRoll={pendingRoll}
          rollMode={rollMode}
          onManualValueChange={onManualValueChange}
          onRollModeChange={onRollModeChange}
          onSubmitManual={onSubmitManualRoll}
          onVirtualRoll={onVirtualRoll}
        />
      ) : null}
    </section>
  );
};
