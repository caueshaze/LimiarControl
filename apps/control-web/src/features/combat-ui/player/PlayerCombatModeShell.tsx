import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
  AbilityName,
  AdvantageMode,
  RollType,
  SkillName,
} from "../../../entities/roll/rollResolution.types";
import { AuthoritativeRollDialog } from "../../../features/rolls/components/AuthoritativeRollDialog";
import { deriveCheckModifierPreviewSources } from "../../../features/rolls/checkModifierSources";
import { useLocale } from "../../../shared/hooks/useLocale";
import { SpellSlotSummary } from "../../../shared/ui/SpellSlotSummary";
import { CombatLogPanel } from "../components/CombatLogPanel";
import { CombatModeBar } from "../components/CombatModeBar";
import { CombatParticipantRoster } from "../components/CombatParticipantRoster";
import { ActiveEffectDebugPanel } from "../components/ActiveEffectDebugPanel";
import { buildCombatParticipantViews, getCombatEffectLabel, getCombatStatusLabel } from "../combatUi.helpers";
import { computePassiveSkillBonus, computePassiveSkillBonusSources } from "../../../features/character-sheet/utils/calculations";
import { PlayerAttackRollDialog } from "../../../pages/PlayerBoardPage/player-combat-debug/PlayerAttackRollDialog";
import { PlayerSpellCastDialog } from "../../../pages/PlayerBoardPage/player-combat-debug/PlayerSpellCastDialog";
import { PlayerBoardRollDialog } from "../../../pages/PlayerBoardPage/PlayerBoardRollDialog";
import {
  requiresAreaTargetingSelection,
  spellRequiresExternalTarget,
} from "../../../pages/PlayerBoardPage/player-combat-debug/areaTargetingUi";
import type { CharacterSheet } from "../../../features/character-sheet/model/characterSheet.types";
import type { InventoryItem } from "../../../entities/inventory";
import type { Item } from "../../../entities/item";
import type { SessionInventorySelectOption } from "../../inventory/components/sessionInventoryPanel.utils";
import type { Locale } from "../../../shared/i18n";
import type {
  PendingRoll,
  PlayerBoardStatusSummary,
} from "../../../pages/PlayerBoardPage/playerBoard.types";
import { usePlayerCombatMode } from "./usePlayerCombatMode";
import { PlayerTurnPanel } from "./PlayerTurnPanel";
import { CombatMapFrame, toCombatMapFrameAreaEffects, type SpellMapHighlight } from "../map/CombatMapFrame";
import {
  formatMovementMeters,
  getMovementPreviewReasonLabel,
  pathCostUnitsToMeters,
  resolveMovementCellSelection,
  useMovementPreview,
} from "../map/useMovementPreview";
import { combatRepo, type PendingSave } from "../../../shared/api/combatRepo";
import { buildPendingSaveReason, resolveTargetVariantLabel } from "../spellVariantUi";

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
  onWeaponChange?: (inventoryItemId: string | null) => void;
  pendingRoll: PendingRoll | null;
  playerSheet?: CharacterSheet | null;
  playerStatus?: PlayerBoardStatusSummary | null;
  rollMode: "virtual" | "manual" | null;
  sessionId: string;
  selectedWeaponId?: string | null;
  weaponOptions?: SessionInventorySelectOption[];
  isSavingLoadout?: boolean;
  loadoutStatus?: string | null;
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
  onWeaponChange,
  pendingRoll,
  playerSheet,
  playerStatus,
  rollMode,
  sessionId,
  selectedWeaponId = null,
  weaponOptions = [],
  isSavingLoadout = false,
  loadoutStatus = null,
  userId = null,
}: Props) => {
  const { locale: currentLocale, t } = useLocale();
  const [activeActionPanel, setActiveActionPanel] = useState<
    "attack" | "spell" | "standard" | "object"
  >("attack");
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
  const enrichedPlayerStatus = useMemo(() => {
    if (!playerStatus) return null;
    const activeEffects = myParticipant?.active_effects ?? [];
    const bonus = computePassiveSkillBonus(activeEffects, "perception");
    if (!bonus) return playerStatus;
    return {
      ...playerStatus,
      passivePerception: playerStatus.passivePerception + bonus,
      passivePerceptionBonus: bonus,
      passivePerceptionBonusSources: computePassiveSkillBonusSources(activeEffects, "perception"),
    };
  }, [playerStatus, myParticipant?.active_effects]);

  const selectedSpellIsArea = requiresAreaTargetingSelection(selectedSpell?.selectionType, selectedSpell?.areaShape);
  const selectedSpellNeedsTarget = spellRequiresExternalTarget(selectedSpell?.selectionType, selectedSpell?.areaShape);
  const [spellMapHighlights, setSpellMapHighlights] = useState<SpellMapHighlight[]>([]);
  const handleMapPreviewChange = useCallback((highlights: SpellMapHighlight[]) => {
    setSpellMapHighlights(highlights);
  }, []);
  const [movementMode, setMovementMode] = useState(false);
  const [movementSelectedCell, setMovementSelectedCell] = useState<{ x: number; y: number } | null>(null);
  const [movementSubmitting, setMovementSubmitting] = useState(false);
  const [movementRejectionReason, setMovementRejectionReason] = useState<string | null>(null);
  const [activePendingSave, setActivePendingSave] = useState<(
    PendingSave & { participantId: string; participantRefId: string; participantName: string }
  ) | null>(null);
  const pendingRollDebugModifiers = useMemo(() => {
    if (!pendingRoll || !myParticipant) {
      return pendingRoll?.debugModifiers ?? undefined;
    }
    if (pendingRoll.debugModifiers?.length) {
      return pendingRoll.debugModifiers;
    }
    if (pendingRoll.rollType !== "ability" && pendingRoll.rollType !== "skill") {
      return undefined;
    }
    const preview = deriveCheckModifierPreviewSources(myParticipant.active_effects, {
      rollType: pendingRoll.rollType,
      ability: (pendingRoll.ability ?? null) as AbilityName | null,
      skill: (pendingRoll.skill ?? null) as SkillName | null,
      targetParticipantId: pendingRoll.targetParticipantId ?? null,
    });
    return preview.length > 0 ? preview : undefined;
  }, [myParticipant, pendingRoll]);
  const movementEnabled =
    movementMode &&
    combat.state?.use_map !== false &&
    combat.state?.phase === "active" &&
    combat.isMyTurn &&
    myParticipant?.status === "active";
  const movementPreview = useMovementPreview({
    sessionId,
    actorParticipantId: myParticipant?.id,
    actorRefId: myParticipant?.ref_id,
    destinationCell: movementEnabled ? movementSelectedCell : null,
    enabled: movementEnabled,
  });

  useEffect(() => {
    if (movementEnabled) {
      return;
    }
    setMovementMode(false);
    setMovementSelectedCell(null);
    setMovementRejectionReason(null);
  }, [movementEnabled]);

  useEffect(() => {
    if (myParticipant?.pending_save?.status === "pending") {
      setActivePendingSave({
        ...myParticipant.pending_save,
        participantId: myParticipant.id,
        participantName: myParticipant.display_name,
        participantRefId: myParticipant.ref_id,
      });
    }
  }, [myParticipant]);

  const clearMovementMode = () => {
    setMovementMode(false);
    setMovementSelectedCell(null);
    setMovementRejectionReason(null);
  };

  const submitMovement = (cell: { x: number; y: number }) => {
    if (!myParticipant?.id || movementSubmitting) return;
    const actorParticipantId = myParticipant.id;
    setMovementSubmitting(true);
    setMovementSelectedCell(cell);
    setMovementRejectionReason(null);
    combatRepo
      .confirmMovement(sessionId, {
        actor_participant_id: actorParticipantId,
        destination_cell: cell,
      })
      .then((response) => {
        if (!response.is_valid) {
          setMovementRejectionReason(getMovementPreviewReasonLabel(response.reason));
          return;
        }
        clearMovementMode();
        return combat.refreshState();
      })
      .catch((error) => {
        setMovementRejectionReason(
          error?.data?.detail || error?.message || "Falha ao confirmar movimento.",
        );
      })
      .finally(() => setMovementSubmitting(false));
  };

  const canMoveNow =
    combat.state?.phase === "active" &&
    combat.isMyTurn &&
    myParticipant?.status === "active" &&
    combat.state?.use_map !== false;
  const isTargetingAction =
    activeActionPanel === "attack" ||
    (activeActionPanel === "spell" && Boolean(selectedSpell) && selectedSpellNeedsTarget);

  const mapSelectionMode =
    movementEnabled
      ? "select-cell"
      : canMoveNow || isTargetingAction
      ? "select-token"
      : "none";
  const movementPreviewMessage =
    movementPreview.preview != null && movementSelectedCell != null
      ? t("combatUi.mapHintMoveLocked")
          .replace(
            "{cost}",
            formatMovementMeters(
              pathCostUnitsToMeters(movementPreview.preview.path_cost_units),
              currentLocale,
            ),
          )
          .replace(
            "{remaining}",
            formatMovementMeters(
              pathCostUnitsToMeters(movementPreview.preview.remaining_budget),
              currentLocale,
            ),
          )
      : null;
  const encumbranceMovementWarning =
    movementPreview.preview != null &&
    enrichedPlayerStatus &&
    enrichedPlayerStatus.baseSpeedMeters > 0 &&
    pathCostUnitsToMeters(movementPreview.preview.path_cost_units) > enrichedPlayerStatus.effectiveSpeedMeters
      ? t("playerBoard.encumbranceMovementExceed")
      : null;
  const movementHintMessage = movementRejectionReason ?? movementPreview.error;
  const mapHint =
    movementEnabled && movementHintMessage
      ? movementHintMessage
      : movementEnabled && movementPreview.loading && movementSelectedCell
      ? t("combatUi.movementChecking")
      : movementEnabled && movementPreviewMessage
      ? encumbranceMovementWarning
        ? `${movementPreviewMessage}\n${encumbranceMovementWarning}`
        : movementPreviewMessage
      : movementEnabled
      ? t("combatUi.mapHintMove")
      : activeActionPanel === "attack"
      ? t("combatUi.mapHintAttack")
      : activeActionPanel === "spell" && selectedSpellIsArea
        ? t("combatUi.mapHintAreaSpell")
        : activeActionPanel === "spell"
          ? t("combatUi.mapHintSpell")
          : t("combatUi.mapHintIdle");

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

      <div className="space-y-6">
        <CombatMapFrame
          sessionId={sessionId}
          title={t("combatUi.mapTitle")}
          hint={mapHint}
          combatPhase={combat.state?.phase ?? null}
          actor={userId ? { actorId: userId, actorType: "player" } : null}
          selectionMode={mapSelectionMode}
          previewCells={[]}
          activeAreaEffects={toCombatMapFrameAreaEffects(combat.state?.active_area_effects)}
          selectedCell={movementEnabled ? movementSelectedCell : null}
          selectedTargetRefId={movementEnabled ? null : (targetId || null)}
          spellHighlights={spellMapHighlights}
          frameClassName="h-[420px] w-full border-0 bg-slate-950 md:h-[560px] xl:h-[720px]"
          onCellSelected={(selection) => {
            if (!movementEnabled) {
              return;
            }
            if (selection.combatantId && selection.combatantId === myParticipant?.ref_id) {
              clearMovementMode();
              return;
            }
            const nextAction = resolveMovementCellSelection({
              currentSelectedCell: movementSelectedCell,
              nextCell: selection.cell,
              preview: movementPreview.preview,
              loading: movementPreview.loading,
            });
            if (nextAction === "confirm") {
              submitMovement(selection.cell);
              return;
            }
            setMovementSelectedCell(selection.cell);
            setMovementRejectionReason(null);
          }}
          onTokenSelected={(selection) => {
            if (movementEnabled) {
              if (selection.combatantId && selection.combatantId === myParticipant?.ref_id) {
                clearMovementMode();
              }
              return;
            }
            const isOwnToken =
              selection.combatantId != null && selection.combatantId === myParticipant?.ref_id;
            if (isOwnToken && canMoveNow) {
              setMovementMode(true);
              setMovementSelectedCell(null);
              return;
            }
            if (selection.combatantId) {
              setTargetId(selection.combatantId);
            }
          }}
        />

        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.02fr)_minmax(340px,0.98fr)]">
          <div className="space-y-6">
          <PlayerTurnPanel
            activeActionPanel={activeActionPanel}
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
            playerStatus={enrichedPlayerStatus}
            selectedConsumable={selectedConsumable}
            selectedSpell={selectedSpell}
            selectedSpellId={selectedSpellId}
            selectedTarget={selectedTarget}
            sessionId={sessionId}
            setActiveActionPanel={setActiveActionPanel}
            setConsumableItemId={setConsumableItemId}
            setSelectedSpellId={setSelectedSpellId}
            setTargetId={setTargetId}
            setUseObjectManualRolls={setUseObjectManualRolls}
            setUseObjectNote={setUseObjectNote}
            setUseObjectRollMode={setUseObjectRollMode}
            setUseObjectTargetParticipantId={setUseObjectTargetParticipantId}
            selectedWeaponId={selectedWeaponId ?? ""}
            spellOptions={spellOptions}
            targetId={targetId}
            useObjectManualRolls={useObjectManualRolls}
            useObjectNote={useObjectNote}
            useObjectRollMode={useObjectRollMode}
            useObjectTargetOptions={useObjectTargetOptions}
            useObjectTargetParticipantId={useObjectTargetParticipantId}
            weaponOptions={weaponOptions}
            isSavingLoadout={isSavingLoadout}
            loadoutStatus={loadoutStatus}
            onWeaponChange={onWeaponChange}
          />
        </div>

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
                    {enrichedPlayerStatus ? `${enrichedPlayerStatus.currentHp}/${enrichedPlayerStatus.maxHp}` : "-"}
                  </p>
                </div>
                <div className="rounded-3xl border border-white/8 bg-white/4 px-4 py-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">{t("combatUi.armorClass")}</p>
                  <p className="mt-2 text-xl font-semibold text-white">{enrichedPlayerStatus?.ac ?? "-"}</p>
                </div>
                <div className="rounded-3xl border border-white/8 bg-white/4 px-4 py-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">{t("playerBoard.speedLabel")}</p>
                  <p className="mt-2 text-xl font-semibold text-white">
                    {enrichedPlayerStatus && enrichedPlayerStatus.baseSpeedMeters > 0
                      ? `${enrichedPlayerStatus.effectiveSpeedMeters} m`
                      : "-"}
                  </p>
                  {enrichedPlayerStatus && enrichedPlayerStatus.effectiveSpeedMeters < enrichedPlayerStatus.baseSpeedMeters ? (
                    <p className="mt-1 text-[10px] text-amber-400">
                      {`${t("playerBoard.speedPenaltyHint")} (base ${enrichedPlayerStatus.baseSpeedMeters} m)`}
                    </p>
                  ) : null}
                </div>
                <div className="rounded-3xl border border-white/8 bg-white/4 px-4 py-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">{t("sheet.skills.passivePerception")}</p>
                  <p className="mt-2 text-xl font-semibold text-white">{enrichedPlayerStatus?.passivePerception ?? "-"}</p>
                  {enrichedPlayerStatus?.passivePerceptionBonus && enrichedPlayerStatus.passivePerceptionBonusSources?.length ? (
                    <p className="mt-1 text-[10px] text-sky-300">
                      {`Base ${enrichedPlayerStatus.passivePerception - enrichedPlayerStatus.passivePerceptionBonus}${enrichedPlayerStatus.passivePerceptionBonusSources.map((s) => ` + ${s.label} ${s.value}`).join("")}`}
                    </p>
                  ) : null}
                </div>
                <div className="rounded-3xl border border-white/8 bg-white/4 px-4 py-4 sm:col-span-2">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">{t("combatUi.currentWeapon")}</p>
                  <p className="mt-2 text-sm font-semibold text-white">
                    {enrichedPlayerStatus?.currentWeapon?.name ?? t("combatUi.noWeapon")}
                  </p>
                  {enrichedPlayerStatus?.currentWeapon ? (
                    <p className="mt-2 text-xs text-slate-300">
                      {enrichedPlayerStatus.currentWeapon.damageLabel}
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
                  <>
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
                    <ActiveEffectDebugPanel
                      effects={myParticipant.active_effects}
                      targetDisplayName={myParticipant.display_name}
                    />
                  </>
                ) : (
                  <p className="mt-3 text-sm text-slate-400">{t("combatUi.noEffects")}</p>
                )}
              </div>

              {playerSheet?.spellcasting ? (
                <div className="mt-4 rounded-3xl border border-white/8 bg-white/4 px-4 py-4">
                  <SpellSlotSummary
                    slots={playerSheet.spellcasting.slots}
                    title={t("playerBoard.spellResourcesTitle")}
                    emptyLabel={t("playerBoard.noSpellSlots")}
                  />
                </div>
              ) : null}
            </section>

            <CombatParticipantRoster
              participants={rosterParticipants}
              subtitle={t("combatUi.participantsDescription")}
              title={t("combatUi.participants")}
            />

            <CombatLogPanel logs={combat.logs} />
          </div>
        </div>
      </div>

      {attackDialogOpen && combat.state?.phase === "active" && combat.currentParticipant && selectedTarget ? (
        <PlayerAttackRollDialog
          actorParticipantId={combat.currentParticipant.id}
          actorRefId={combat.currentParticipant.ref_id}
          onClose={closeAttackDialog}
          onResolved={(result) => {
            setLastAttackResult(result);
          }}
          sessionId={sessionId}
          target={selectedTarget}
          weapon={playerStatus?.currentWeapon ?? null}
        />
      ) : null}

      {spellDialogOpen && combat.state?.phase === "active" && combat.currentParticipant && selectedSpell && (!selectedSpellNeedsTarget || selectedTarget || selectedSpellIsArea) ? (
        <PlayerSpellCastDialog
          actor={combat.currentParticipant}
          actorParticipantId={combat.currentParticipant.id}
          onClose={closeSpellDialog}
          onMapPreviewChange={handleMapPreviewChange}
          onResolved={(result) => {
            setLastSpellResult(result);
            if (result.inventory_refresh_required) {
              void onInventoryChanged?.();
            }
          }}
          participants={combat.state.participants}
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
            targetParticipantId: pendingRoll.targetParticipantId ?? undefined,
            reason: pendingRoll.reason,
            issuedBy: pendingRoll.issuedBy,
            debugModifiers: pendingRollDebugModifiers,
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

      {!pendingRoll && activePendingSave ? (
        <AuthoritativeRollDialog
          request={{
            rollType: "save",
            ability: activePendingSave.save_ability as AbilityName,
            advantageMode: "normal",
            dc: activePendingSave.save_dc,
            reason: buildPendingSaveReason({
              spellName: activePendingSave.spell_name,
              saveAbility: activePendingSave.save_ability,
              variantLabel: resolveTargetVariantLabel({
                targetVariantAssignments: activePendingSave.target_variant_assignments,
                manualNotesByTarget: activePendingSave.manual_notes_by_target,
                selectedVariantKey: activePendingSave.selected_variant_key,
                selectedVariantLabel: activePendingSave.selected_variant_label,
                targetParticipantId: activePendingSave.participantId,
                targetRefId: activePendingSave.participantRefId,
              }),
            }),
            targetParticipantId: activePendingSave.participantId,
            issuedBy: activePendingSave.attacker_display_name ?? undefined,
            issuedByLabel: t("combatUi.castBy"),
          }}
          sessionId={sessionId}
          actorKind="player"
          actorRefId={activePendingSave.participantRefId}
          onClose={() => setActivePendingSave(null)}
          onSubmitRoll={async ({ rollSource, manualRoll, manualRolls }) => {
            const resolved = await combatRepo.resolvePendingSave(sessionId, {
              target_participant_id: activePendingSave.participantId,
              pending_save_id: activePendingSave.id,
              roll_source: rollSource,
              manual_roll: rollSource === "manual" ? manualRoll ?? null : null,
              manual_rolls: rollSource === "manual" ? manualRolls ?? null : null,
            });
            await combat.refreshState();
            return resolved.roll_result ?? null;
          }}
        />
      ) : null}
    </section>
  );
};
