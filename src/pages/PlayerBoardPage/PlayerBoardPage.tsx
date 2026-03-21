import { useCallback } from "react";
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
import type { InventoryItem } from "../../entities/inventory";
import { PlayerEntityList } from "../../features/session-entities";
import { PlayerBoardHero } from "./PlayerBoardHero";
import { PlayerBoardRestBanner } from "./PlayerBoardRestBanner";
import { PlayerBoardRollDialog } from "./PlayerBoardRollDialog";
import { usePlayerBoardRestActions } from "./usePlayerBoardRestActions";
import { PlayerBoardStatusPanel } from "./PlayerBoardStatusPanel";
import { usePlayerBoardLoadout } from "./usePlayerBoardLoadout";
import { usePlayerBoardRestFeedback } from "./usePlayerBoardRestFeedback";
import { usePlayerBoardRealtime } from "./usePlayerBoardRealtime";
import { usePlayerBoardResources } from "./usePlayerBoardResources";
import { usePlayerBoardSummary } from "./usePlayerBoardSummary";

export const PlayerBoardPage = () => {
  const { t } = useLocale();
  const { user } = useAuth();
  const { partyId } = useParams<{ partyId: string }>();
  const { selectedCampaign, selectedCampaignId, setSelectedCampaignLocal } = useCampaigns();
  const { toast, showToast, clearToast } = useToast();
  const navigate = useNavigate();
  const {
    activeSession,
    catalogItems,
    clearCommand,
    clearSessionEnded,
    combatActive,
    effectiveCampaignId,
    lastCommand,
    lastEvent,
    myInventory,
    playerSheet,
    playerWallet,
    refresh,
    refreshInventoryData,
    refreshPlayerWallet,
    restState,
    roll,
    rollEvents,
    sessionEndedAt,
    setMyInventory,
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
  const {
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

  const {
    boardDescription,
    campaignTitle,
    inventoryTotal,
    playerStatus,
    sessionStatusLabel,
    sessionStatusTone,
  } = usePlayerBoardSummary({
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

  usePlayerBoardRestFeedback({
    lastEvent,
    restState,
    showToast,
    t,
    userId: user?.userId,
  });

  const handleOpenSheet = useCallback(() => {
    if (!partyId) {
      return;
    }
    navigate(
      `${routes.characterSheetParty.replace(":partyId", partyId)}?${new URLSearchParams({
        mode: "play",
        returnTo: "board",
      }).toString()}`,
    );
  }, [navigate, partyId]);

  const upsertInventoryEntry = useCallback((nextEntry: InventoryItem) => {
    setMyInventory((current) => {
      const source = current ?? [];
      const existing = source.find((entry) => entry.id === nextEntry.id);
      if (existing) {
        return source.map((entry) => (entry.id === nextEntry.id ? nextEntry : entry));
      }
      const sameItem = source.find((entry) => entry.itemId === nextEntry.itemId);
      if (sameItem) {
        return source.map((entry) =>
          entry.itemId === nextEntry.itemId
            ? { ...entry, quantity: nextEntry.quantity, isEquipped: nextEntry.isEquipped, notes: nextEntry.notes }
            : entry,
        );
      }
      return [nextEntry, ...source];
    });
  }, []);

  const applySoldInventoryEntry = useCallback((soldInventoryItemId: string, nextEntry: InventoryItem | null) => {
    setMyInventory((current) => {
      const source = current ?? [];
      if (nextEntry) {
        return source.map((entry) => (entry.id === soldInventoryItemId ? nextEntry : entry));
      }
      return source.filter((entry) => entry.id !== soldInventoryItemId);
    });
  }, []);

  return (
    <section className="space-y-6">
      <Toast toast={toast} onClose={clearToast} />
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
          navigate(
            partyId
              ? routes.playerPartyDetails.replace(":partyId", partyId)
              : routes.home,
          )
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

      <PlayerBoardRestBanner restState={restState} />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.08fr)_minmax(320px,0.92fr)]">
        <div className="space-y-6">
          <PlayerBoardStatusPanel
            combatActive={combatActive}
            pendingRoll={pendingRoll}
            playerStatus={playerStatus}
            restState={restState}
            shopAvailable={shopAvailable}
            shopOpen={shopOpen}
            usingHitDie={usingHitDie}
            onUseHitDie={handleUseHitDie}
            onOpenShop={handleOpenShop}
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
              refreshSignal={lastEvent ? `${lastEvent.type}:${lastEvent.version ?? ""}` : null}
              sessionId={activeSession.id}
            />
          )}
        </div>

        <div className="space-y-6">
          <SessionInventoryPanel
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
                onBuy={(item, inventoryItem) => {
                  upsertInventoryEntry(inventoryItem);
                  void refreshInventoryData();
                  void refreshPlayerWallet();
                  setInventoryOpen(true);
                  setInventoryFlash(true);
                  window.setTimeout(() => setInventoryFlash(false), 1800);
                  showToast({
                    variant: "success",
                    title: t("shop.buyTitle"),
                    description: `${item.name} ${t("shop.buyDescription")}`,
                  });
                }}
                onBuyError={(message) =>
                  showToast({
                    variant: "error",
                    title: t("shop.buyErrorTitle"),
                    description: message ?? t("shop.buyErrorDescription"),
                  })
                }
                onSell={(item, result) => {
                  const soldEntry = (myInventory ?? []).find((entry) => entry.itemId === result.itemId);
                  if (soldEntry) {
                    applySoldInventoryEntry(soldEntry.id, result.inventoryItem);
                  }
                  setPlayerWallet(result.currentCurrency);
                  setInventoryOpen(true);
                  showToast({
                    variant: "success",
                    title: t("shop.sellSuccessTitle"),
                    description: `${item.name} ${t("shop.sellSuccessDescription")} ${result.refundLabel}.`,
                  });
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

      {pendingRoll && (
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
      )}
      <DiceVisualizer events={rollEvents} />
    </section>
  );
};
