import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useLocale } from "../../shared/hooks/useLocale";
import { useCampaigns } from "../../features/campaign-select";
import { ShopPanel } from "../../features/shop";
import { SessionInventoryPanel } from "../../features/inventory";
import { SessionActivityToggle } from "../../features/sessions";
import { routes } from "../../app/routes/routes";
import { DiceVisualizer } from "../../features/dice-roller/components/DiceVisualizer";
import { useToast } from "../../shared/hooks/useToast";
import { Toast } from "../../shared/ui/Toast";
import { useAuth } from "../../features/auth";
import { PlayerEntityList } from "../../features/session-entities";
import { PlayerBoardHero } from "./PlayerBoardHero";
import { PlayerBoardRestBanner } from "./PlayerBoardRestBanner";
import { AuthoritativeRollDialog } from "../../features/rolls/components/AuthoritativeRollDialog";
import type { AbilityName, AdvantageMode, RollType, SkillName } from "../../entities/roll/rollResolution.types";
import { PlayerBoardRollDialog } from "./PlayerBoardRollDialog";
import { usePlayerBoardCallbacks } from "./usePlayerBoardCallbacks";
import { usePlayerBoardRestActions } from "./usePlayerBoardRestActions";
import { PlayerBoardStatusPanel } from "./PlayerBoardStatusPanel";
import { SpellPreparationDialog } from "./SpellPreparationDialog";
import { parseCharacterSheet } from "../../features/character-sheet/model/characterSheet.schema";
import { usePlayerBoardLoadout } from "./usePlayerBoardLoadout";
import { usePlayerBoardRestFeedback } from "./usePlayerBoardRestFeedback";
import { usePlayerBoardRealtime } from "./usePlayerBoardRealtime";
import { sessionStatesRepo } from "../../shared/api/sessionStatesRepo";
import { usePlayerBoardResources } from "./usePlayerBoardResources";
import { usePlayerBoardSummary } from "./usePlayerBoardSummary";
import { getConcentrationReplacementNotice } from "./concentrationLabel";
import {
  getSpellPreparationCopyKeys,
  resolveSpellPreparationCopyMode,
} from "./spellPreparationCopy";
import { useSession } from "../../features/sessions";
import { CombatModeBar } from "../../features/combat-ui/components/CombatModeBar";
import { PlayerCombatModeShell } from "../../features/combat-ui/player/PlayerCombatModeShell";
import { useCombatUiState } from "../../features/combat-ui/useCombatUiState";
import { navigateBackOrFallback } from "../../shared/lib/navigation";

export const PlayerBoardPage = () => {
  const { locale, t } = useLocale();
  const { user } = useAuth();
  const {
    collapseCombatUi,
    combatModeVisible,
    combatUiExpanded,
    toggleCombatUiExpanded,
  } = useSession();
  const { partyId } = useParams<{ partyId: string }>();
  const { selectedCampaign, selectedCampaignId, setSelectedCampaignLocal } = useCampaigns();
  const { toast, showToast, clearToast } = useToast();
  const navigate = useNavigate();
  const {
    activeConcentration,
    activeSession,
    activeSpellEffects,
    catalogItems,
    clearCommand,
    clearSessionEnded,
    combatActive,
    effectiveCampaignId,
    lastCommand,
    lastEvent,
    myInventory,
    partyPlayers,
    pendingSpellPreparation,
    playerSheet,
    playerWallet,
    refresh,
    refreshInventoryData,
    refreshPlayerWallet,
    restState,
    roll,
    rollEvents,
    sessionEndedAt,
    setActiveConcentration,
    setActiveSpellEffects,
    setMyInventory,
    setPendingSpellPreparation,
    setPlayerSheet,
    setPlayerWallet,
    setSelectedSessionId,
    shopAvailable,
  } = usePlayerBoardResources({
    partyId,
    selectedCampaignId,
    setSelectedCampaignLocal,
    userId: user?.userId,
  });
  const spellPreparationCopyMode = resolveSpellPreparationCopyMode(
    pendingSpellPreparation,
    restState,
  );
  const spellPreparationCopyKeys = getSpellPreparationCopyKeys(
    spellPreparationCopyMode,
  );
  const {
    clearPendingRoll,
    handleAuthoritativeRollResolved,
    handleManualRoll,
    handleOpenShop,
    handleRoll,
    handleShopClose,
    inventoryFlash,
    inventoryOpen,
    manualValue,
    pendingRoll,
    rollMode,
    setInventoryFlash,
    setInventoryOpen,
    setManualValue,
    setRollMode,
    shopOpen,
  } = usePlayerBoardRealtime({
    activeSession,
    clearCommand,
    clearSessionEnded,
    effectiveCampaignId,
    lastCommand,
    lastEvent,
    navigate,
    partyId,
    refresh,
    refreshInventoryData,
    roll,
    selectedCampaignId,
    sessionEndedAt,
    setSelectedCampaignLocal,
    setSelectedSessionId,
    showToast,
    shopAvailable,
    t,
    userId: user?.userId,
  });

  const combatBarState = useCombatUiState({
    enabled: Boolean(activeSession?.id) && combatActive && !combatModeVisible,
    sessionId: activeSession?.id ?? "",
    userId: user?.userId,
  });

  const {
    boardDescription,
    campaignTitle,
    inventoryTotal,
    playerStatus,
    sessionStatusLabel,
    sessionStatusTone,
  } = usePlayerBoardSummary({
    activeEffects: combatBarState.myParticipant?.active_effects,
    activeSession,
    effectiveCampaignId,
    inventory: myInventory,
    itemsById: catalogItems,
    playerSheet,
    selectedCampaignName: selectedCampaign?.name,
    t,
  });
  const {
    armorOptions,
    handleArmorChange,
    handleWeaponChange,
    isSavingLoadout,
    loadoutStatus,
    selectedArmorId,
    selectedWeaponId,
    weaponOptions,
  } = usePlayerBoardLoadout({
    activeSessionId: activeSession?.id ?? null,
    inventory: myInventory,
    itemsById: catalogItems,
    locale,
    playerSheet,
    setPlayerSheet,
    showToast,
    t,
  });
  const { handleUseHitDie, usingHitDie } = usePlayerBoardRestActions({
    activeSessionId: activeSession?.id ?? null,
    setPlayerSheet,
    showToast,
    t,
  });
  const [clearingConcentration, setClearingConcentration] = useState(false);
  const [removingEffectId, setRemovingEffectId] = useState<string | null>(null);
  const [showPrepDialog, setShowPrepDialog] = useState(false);
  const [preparingSpells, setPreparingSpells] = useState(false);
  const [castableSpells, setCastableSpells] = useState<import("../../entities/character").OutOfCombatCastableSpell[]>([]);
  const [castingSpell, setCastingSpell] = useState(false);
  const previousConcentrationRef = useRef<import("../../entities/character").ActiveConcentration | null>(null);

  const handleClearConcentration = async () => {
    if (!activeSession?.id || clearingConcentration) return;
    setClearingConcentration(true);
    try {
      const record = await sessionStatesRepo.clearConcentration(activeSession.id);
      setPlayerSheet(parseCharacterSheet(record.state));
      setActiveConcentration(record.activeConcentration ?? null);
      setActiveSpellEffects(
        (record.activeSpellEffects as import("../../shared/api/combatRepo").ActiveEffect[] | null | undefined) ?? null,
      );
    } catch {
      showToast({
        variant: "error",
        title: t("playerBoard.clearConcentrationErrorTitle"),
        description: t("playerBoard.clearConcentrationErrorDescription"),
      });
    } finally {
      setClearingConcentration(false);
    }
  };

  const handleRemoveEffect = async (effectId: string) => {
    if (!activeSession?.id || removingEffectId) return;
    setRemovingEffectId(effectId);
    try {
      const record = await sessionStatesRepo.removePersistedEffect(activeSession.id, effectId);
      setPlayerSheet(parseCharacterSheet(record.state));
      setActiveConcentration(record.activeConcentration ?? null);
      setActiveSpellEffects(
        (record.activeSpellEffects as import("../../shared/api/combatRepo").ActiveEffect[] | null | undefined) ?? null,
      );
    } catch {
      showToast({
        variant: "error",
        title: t("playerBoard.removeEffectErrorTitle"),
        description: t("playerBoard.removeEffectErrorDescription"),
      });
    } finally {
      setRemovingEffectId(null);
    }
  };

  const handlePrepareSpells = async (preparedSpellIds: string[]) => {
    if (!activeSession?.id || preparingSpells) return;
    setPreparingSpells(true);
    try {
      const record = await sessionStatesRepo.prepareSpells(activeSession.id, preparedSpellIds);
      setPlayerSheet(parseCharacterSheet(record.state));
      setPendingSpellPreparation(
        (record.pendingSpellPreparation as import("../../shared/api/combatRepo").PendingSpellPreparation | null | undefined) ?? null,
      );
      setShowPrepDialog(false);
    } catch {
      showToast({
        variant: "error",
        title: t("playerBoard.prepareSpellsErrorTitle"),
        description: t("playerBoard.prepareSpellsErrorDescription"),
      });
    } finally {
      setPreparingSpells(false);
    }
  };

  useEffect(() => {
    if (!activeSession?.id || combatActive) return;
    void sessionStatesRepo.listCastableOutOfCombat(activeSession.id).then((spells) => {
      setCastableSpells(spells);
    }).catch(() => {
      setCastableSpells([]);
    });
  }, [activeSession?.id, combatActive]);

  const targetOptions = useMemo(
    () =>
      partyPlayers.map((m) => ({
        playerUserId: m.userId,
        label: m.displayName ?? m.username ?? m.userId,
      })),
    [partyPlayers],
  );

  const handleCastSpellOutOfCombat = async (
    spellId: string,
    slotLevel: number | null,
    variantKey: string | null,
    targetPlayerUserId: string | null,
  ) => {
    if (!activeSession?.id || castingSpell) return;
    setCastingSpell(true);
    try {
      const record = await sessionStatesRepo.castSpellOutOfCombat(activeSession.id, {
        spellId,
        slotLevel,
        variantKey,
        targetPlayerUserId,
      });
      setPlayerSheet(parseCharacterSheet(record.state));
      setActiveConcentration(record.activeConcentration ?? null);
      setActiveSpellEffects(
        (record.activeSpellEffects as import("../../shared/api/combatRepo").ActiveEffect[] | null | undefined) ?? null,
      );
      showToast({ variant: "success", title: t("playerBoard.castSpellSuccess") });
    } catch {
      showToast({
        variant: "error",
        title: t("playerBoard.castSpellErrorTitle"),
        description: t("playerBoard.castSpellErrorDescription"),
      });
    } finally {
      setCastingSpell(false);
    }
  };

  usePlayerBoardRestFeedback({
    lastEvent,
    restState,
    showToast,
    t,
    userId: user?.userId,
  });
  const {
    applySoldInventoryEntry,
    createBuySuccessToast,
    createSellSuccessToast,
    flashInventory,
    handleOpenSheet,
    translateShopErrorMessage,
    upsertInventoryEntry,
  } = usePlayerBoardCallbacks({
    locale,
    navigate,
    partyId,
    setInventoryFlash,
    setMyInventory,
    setPlayerWallet,
    showToast,
    t,
  });

  useEffect(() => {
    if (combatActive && combatUiExpanded && pendingRoll?.rollType === "initiative") {
      collapseCombatUi();
    }
  }, [collapseCombatUi, combatActive, combatUiExpanded, pendingRoll?.rollType]);

  useEffect(() => {
    const notice = getConcentrationReplacementNotice(
      previousConcentrationRef.current,
      activeConcentration,
    );
    previousConcentrationRef.current = activeConcentration ?? null;
    if (notice) {
      const prevLabel = notice.previousLabel ?? t("playerBoard.activeEffectFallback");
      const nextLabel = notice.nextLabel ?? t("playerBoard.activeEffectFallback");
      showToast({
        variant: "info",
        title: t("playerBoard.concentrationReplacedTitle"),
        description: t("playerBoard.concentrationReplacedDescription")
          .replace("{previous}", prevLabel)
          .replace("{next}", nextLabel),
      });
    }
  }, [activeConcentration, showToast, t]);

  return (
    <section className="space-y-6">
      <Toast toast={toast} onClose={clearToast} />
      {combatModeVisible && activeSession?.id ? (
        <PlayerCombatModeShell
          campaignId={effectiveCampaignId}
          expanded={combatUiExpanded}
          inventory={myInventory}
          isSavingLoadout={isSavingLoadout}
          itemsById={catalogItems}
          loadoutStatus={loadoutStatus}
          locale={locale}
          manualValue={manualValue}
          onAuthoritativeRollResolved={handleAuthoritativeRollResolved}
          onClearPendingRoll={clearPendingRoll}
          onInventoryChanged={() => {
            void refreshInventoryData();
          }}
          onManualValueChange={setManualValue}
          onRollModeChange={setRollMode}
          onSubmitManualRoll={handleManualRoll}
          onToggleExpanded={toggleCombatUiExpanded}
          onVirtualRoll={handleRoll}
          onWeaponChange={handleWeaponChange}
          pendingRoll={pendingRoll}
          playerSheet={playerSheet}
          playerStatus={playerStatus}
          rollMode={rollMode}
          selectedWeaponId={selectedWeaponId}
          sessionId={activeSession.id}
          userId={user?.userId}
          weaponOptions={weaponOptions}
        />
      ) : (
        <>
      <PlayerBoardHero
        campaignTitle={campaignTitle}
        sessionTitle={activeSession?.title ?? null}
        description={boardDescription}
        sessionNumber={activeSession?.number ?? null}
        startedAt={activeSession?.startedAt ?? null}
        sessionStatusLabel={sessionStatusLabel}
        sessionStatusTone={sessionStatusTone}
        shopOpen={shopOpen}
        combatActive={combatActive}
        inventoryTotal={inventoryTotal}
        onBack={() =>
          navigateBackOrFallback(navigate, {
            fallbackTo: partyId
              ? routes.playerPartyDetails.replace(":partyId", partyId)
              : routes.home,
          })
        }
        primaryActionLabel={activeSession?.status === "ACTIVE" && partyId ? t("playerBoard.openSheet") : null}
        onPrimaryAction={activeSession?.status === "ACTIVE" && partyId ? handleOpenSheet : undefined}
        secondaryActionLabel={effectiveCampaignId ? t("playerBoard.toggleInventory") : t("playerBoard.goJoin")}
        onSecondaryAction={
          effectiveCampaignId
            ? () => setInventoryOpen((value) => !value)
            : () => navigate(routes.join)
        }
      />

      {combatActive && activeSession?.id ? (
        <CombatModeBar
          currentParticipantName={combatBarState.currentParticipant?.display_name ?? null}
          expanded={combatUiExpanded}
          onToggleExpanded={toggleCombatUiExpanded}
          isMyTurn={combatBarState.isMyTurn}
          phase={combatBarState.state?.phase ?? null}
          round={combatBarState.state?.round ?? null}
          turnResources={combatBarState.myParticipant?.turn_resources ?? null}
        />
      ) : null}

      <PlayerBoardRestBanner restState={restState} />

      {pendingSpellPreparation && !combatActive && (
        <div className="mx-auto max-w-7xl px-4 sm:px-6">
          <div className="rounded-2xl border border-amber-700/30 bg-amber-900/20 px-4 py-3">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-semibold text-amber-200">
                  {t(spellPreparationCopyKeys.title)}
                </p>
                <p className="text-xs text-amber-300/70">
                  {t(spellPreparationCopyKeys.description)}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowPrepDialog(true)}
                className="shrink-0 rounded-full bg-amber-600/30 px-4 py-1.5 text-xs font-bold uppercase tracking-[0.2em] text-amber-200 transition hover:bg-amber-600/50"
              >
                {t("playerBoard.prepareSpellsButton")}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.08fr)_minmax(320px,0.92fr)]">
        <div className="space-y-6">
          <PlayerBoardStatusPanel
            activeConcentration={activeConcentration}
            activeSpellEffects={activeSpellEffects}
            castableSpells={castableSpells}
            castingSpell={castingSpell}
            clearingConcentration={clearingConcentration}
            combatActive={combatActive}
            onCastSpell={handleCastSpellOutOfCombat}
            onClearConcentration={handleClearConcentration}
            onRemoveEffect={handleRemoveEffect}
            pendingRoll={pendingRoll}
            participant={combatBarState.myParticipant ?? null}
            playerSheet={playerSheet}
            playerStatus={playerStatus}
            removingEffectId={removingEffectId}
            restState={restState}
            targetOptions={targetOptions}
            usingHitDie={usingHitDie}
            onUseHitDie={handleUseHitDie}
          />
          {activeSession?.id && (
            <PlayerEntityList
              sessionId={activeSession.id}
              combatActive={combatActive}
              lastEvent={lastEvent}
            />
          )}

          {activeSession?.id && (
            <SessionActivityToggle
              refreshSignal={lastEvent ? JSON.stringify(lastEvent) : null}
              sessionId={activeSession.id}
            />
          )}
        </div>

        <div className="space-y-6">
          <SessionInventoryPanel
            activeSessionId={activeSession?.id ?? null}
            combatActive={combatActive}
            flash={inventoryFlash}
            inventory={myInventory}
            itemsById={catalogItems}
            selectedArmorId={selectedArmorId}
            selectedWeaponId={selectedWeaponId}
            armorOptions={armorOptions}
            weaponOptions={weaponOptions}
            isSavingLoadout={isSavingLoadout}
            loadoutStatus={loadoutStatus}
            wallet={playerWallet}
            open={inventoryOpen}
            onArmorChange={handleArmorChange}
            onConsumableUsed={(result) => {
              void refreshInventoryData();
              flashInventory();
              if (result.targetPlayerUserId === user?.userId) {
                setPlayerSheet((current) =>
                  current
                    ? {
                        ...current,
                        currentHP: result.newHp,
                      }
                    : current,
                );
              }
              showToast({
                variant: "success",
                title: t("playerBoard.useConsumableTitle"),
                description: `${result.itemName} restored ${result.healingApplied} HP to ${result.targetDisplayName}.`,
              });
            }}
            onConsumableUseError={(message) =>
              showToast({
                variant: "error",
                title: t("playerBoard.consumableUseErrorTitle"),
                description: message ?? t("playerBoard.consumableUseErrorDescription"),
              })
            }
            onToggleOpen={() => setInventoryOpen((value) => !value)}
            onWeaponChange={handleWeaponChange}
          />

          {shopOpen && activeSession?.id && effectiveCampaignId && (
            <div className="xl:sticky xl:top-24">
              <ShopPanel
                open={shopOpen}
                onClose={handleShopClose}
                sessionId={activeSession.id}
                campaignId={effectiveCampaignId}
                inventoryItems={myInventory}
                wallet={playerWallet}
                strengthScore={playerSheet?.abilities?.strength}
                currentTotalWeightKg={playerStatus?.totalWeightKg}
                currentEncumbranceTier={playerStatus?.encumbranceTier}
                onBuy={(item, inventoryItem) => {
                  upsertInventoryEntry(inventoryItem);
                  void refreshInventoryData();
                  void refreshPlayerWallet();
                  flashInventory();
                  showToast(createBuySuccessToast(item));
                }}
                onBuyError={(message) =>
                  showToast({
                    variant: "error",
                    title: t("shop.buyErrorTitle"),
                    description: translateShopErrorMessage(message),
                  })
                }
                onSell={(item, result) => {
                  const soldEntry = (myInventory ?? []).find((entry) => entry.itemId === result.itemId);
                  if (soldEntry) {
                    applySoldInventoryEntry(soldEntry.id, result.inventoryItem);
                  }
                  setPlayerWallet(result.currentCurrency);
                  showToast(createSellSuccessToast(item, result.refundLabel));
                }}
                onSellError={(message) =>
                  showToast({
                    variant: "error",
                    title: t("shop.sellErrorTitle"),
                    description: message ?? t("shop.sellErrorDescription"),
                  })
                }
              />
            </div>
          )}
        </div>
      </div>

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
            debugModifiers: pendingRoll.debugModifiers ?? undefined,
          }}
          sessionId={activeSession?.id ?? ""}
          actorKind="player"
          actorRefId={user?.userId ?? ""}
          onClose={clearPendingRoll}
          onResolved={handleAuthoritativeRollResolved}
        />
      ) : pendingRoll ? (
        <PlayerBoardRollDialog
          activeSessionId={activeSession?.id ?? null}
          manualValue={manualValue}
          pendingRoll={pendingRoll}
          rollMode={rollMode}
          onManualValueChange={setManualValue}
          onRollModeChange={setRollMode}
          onSubmitManual={handleManualRoll}
          onVirtualRoll={handleRoll}
        />
      ) : null}
      <SpellPreparationDialog
        open={showPrepDialog}
        onClose={() => setShowPrepDialog(false)}
        spells={playerSheet?.spellcasting?.spells ?? []}
        preparedLimit={pendingSpellPreparation?.preparedLimit ?? 0}
        currentPreparedIds={pendingSpellPreparation?.currentPreparedSpellIds ?? []}
        onSubmit={handlePrepareSpells}
        isSubmitting={preparingSpells}
        copyMode={spellPreparationCopyMode}
      />
      <DiceVisualizer events={rollEvents} />
        </>
      )}
    </section>
  );
};
