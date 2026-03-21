import { useNavigate, useParams } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { useCampaigns } from "../../features/campaign-select";
import { useLocale } from "../../shared/hooks/useLocale";
import {
    useSession,
} from "../../features/sessions";
import { StartSessionModal } from "../../features/sessions/components/StartSessionModal";
import { DiceVisualizer } from "../../features/dice-roller/components/DiceVisualizer";
import { SessionEntityPanel } from "../../features/session-entities";
import { GmDashboardActivityCard } from "./GmDashboardActivityCard";
import { GmDashboardHeader } from "./GmDashboardHeader";
import { GmDashboardMissingSheetsBanner } from "./GmDashboardMissingSheetsBanner";
import { GmDashboardPartyInventories } from "./GmDashboardPartyInventories";
import { GmDashboardSessionPanel } from "./GmDashboardSessionPanel";
import { useGmDashboardActions } from "./useGmDashboardActions";
import { useGmDashboardData } from "./useGmDashboardData";

export const GmDashboardPage = () => {
    const { campaignId } = useParams<{ campaignId: string }>();
    const navigate = useNavigate();
    const { selectedCampaign, selectedCampaignId, selectCampaign } = useCampaigns();
    const { t } = useLocale();
    const effectiveCampaignId = campaignId ?? selectedCampaignId ?? null;
    const { setSelectedSessionId } = useSession();
    const {
        activate,
        activeSession,
        activityFeed,
        catalogItems,
        combatUiActive,
        endSession,
        lastEvent,
        loading,
        lobbyStatus,
        memberIdByUserId,
        onlineUsers,
        overviewName,
        overviewSystem,
        partyPlayers,
        refreshPlayerInventory,
        refreshPlayerSheet,
        refreshPlayerWallet,
        restUiState,
        rollEvents,
        setCombatUiActive,
        setInventoryByMemberId,
        setRestUiState,
        setShopUiOpen,
        setWalletByUserId,
        shopUiOpen,
        sortedCatalogItems,
        walletByUserId,
        inventoryByMemberId,
        playerSheetByUserId,
    } = useGmDashboardData({
        effectiveCampaignId,
        selectCampaign,
        selectedCampaignId,
    });
    const {
        commandFeedback,
        commandSending,
        creating,
        currencyDraftByUserId,
        forceStarting,
        grantFeedbackByUserId,
        grantingCurrencyForUserId,
        grantingItemForUserId,
        grantingXpForUserId,
        handleActivateClick,
        handleDamagePlayer,
        handleApproveLevelUp,
        handleCommand,
        handleConfirmStart,
        handleDenyLevelUp,
        handleEndSession,
        handleForceStart,
        handleGrantCurrency,
        handleGrantItem,
        handleGrantXp,
        handleHealPlayer,
        hpActionState,
        hpDraftByUserId,
        handleOpenInventory,
        inventoryOpenForUserId,
        itemDraftByUserId,
        levelUpActionState,
        missingSheetsPlayers,
        rollAdvantage,
        rollExpression,
        rollOptions,
        rollReason,
        rollTargetUserId,
        setCurrencyDraftByUserId,
        setHpDraftByUserId,
        setItemDraftByUserId,
        setMissingSheetsPlayers,
        setRollAdvantage,
        setRollExpression,
        setRollReason,
        setRollTargetUserId,
        setShowStartModal,
        setXpDraftByUserId,
        showStartModal,
        xpDraftByUserId,
    } = useGmDashboardActions({
        activate,
        activeSession,
        endSession,
        memberIdByUserId,
        navigate,
        partyPlayers,
        playerSheetByUserId,
        refreshPlayerInventory,
        refreshPlayerSheet,
        refreshPlayerWallet,
        setRestUiState,
        setCombatUiActive,
        setInventoryByMemberId,
        setSelectedSessionId,
        setShopUiOpen,
        setWalletByUserId,
        sortedCatalogItems,
        t,
    });
    const dashboardBackHref = activeSession?.partyId
        ? routes.partyDetails.replace(":partyId", activeSession.partyId)
        : routes.home;

    return (
        <section className="space-y-8">
            <GmDashboardHeader
                backHref={dashboardBackHref}
                backLabel={t("gm.dashboard.backToParty")}
                overviewName={overviewName}
                overviewSystem={overviewSystem}
                selectedCampaignName={selectedCampaign?.name}
            />

            <GmDashboardMissingSheetsBanner
                players={missingSheetsPlayers}
                onClose={() => setMissingSheetsPlayers([])}
            />

            <GmDashboardSessionPanel
                activeSession={activeSession}
                combatUiActive={combatUiActive}
                commandFeedback={commandFeedback}
                commandSending={commandSending}
                creating={creating}
                forceStarting={forceStarting}
                loading={loading}
                lobbyStatus={lobbyStatus}
                onlineUsers={onlineUsers}
                partyPlayers={partyPlayers}
                restState={restUiState}
                rollAdvantage={rollAdvantage}
                rollExpression={rollExpression}
                rollOptions={rollOptions}
                rollReason={rollReason}
                rollTargetUserId={rollTargetUserId}
                shopUiOpen={shopUiOpen}
                onActivateClick={handleActivateClick}
                onCommand={handleCommand}
                onEndSession={handleEndSession}
                onForceStart={handleForceStart}
                setRollAdvantage={setRollAdvantage}
                setRollExpression={setRollExpression}
                setRollReason={setRollReason}
                setRollTargetUserId={setRollTargetUserId}
            />

            {activeSession?.status === "ACTIVE" && effectiveCampaignId && (
                <SessionEntityPanel
                    sessionId={activeSession.id}
                    campaignId={effectiveCampaignId}
                    combatActive={combatUiActive}
                    lastEvent={lastEvent}
                />
            )}

            {activeSession?.status === "ACTIVE" && (
                <GmDashboardPartyInventories
                    activeSessionPartyId={activeSession.partyId ?? null}
                    catalogItems={catalogItems}
                    currencyDraftByUserId={currencyDraftByUserId}
                    effectiveCampaignId={effectiveCampaignId}
                    grantFeedbackByUserId={grantFeedbackByUserId}
                    grantingCurrencyForUserId={grantingCurrencyForUserId}
                    grantingItemForUserId={grantingItemForUserId}
                    grantingXpForUserId={grantingXpForUserId}
                    hpActionState={hpActionState}
                    hpDraftByUserId={hpDraftByUserId}
                    inventoryByMemberId={inventoryByMemberId}
                    inventoryOpenForUserId={inventoryOpenForUserId}
                    itemDraftByUserId={itemDraftByUserId}
                    levelUpActionState={levelUpActionState}
                    memberIdByUserId={memberIdByUserId}
                    navigate={navigate}
                    onlineUsers={onlineUsers}
                    partyPlayers={partyPlayers}
                    playerSheetByUserId={playerSheetByUserId}
                    sortedCatalogItems={sortedCatalogItems}
                    walletByUserId={walletByUserId}
                    xpDraftByUserId={xpDraftByUserId}
                    onDamagePlayer={handleDamagePlayer}
                    onApproveLevelUp={handleApproveLevelUp}
                    onGrantCurrency={handleGrantCurrency}
                    onGrantItem={handleGrantItem}
                    onGrantXp={handleGrantXp}
                    onHealPlayer={handleHealPlayer}
                    onDenyLevelUp={handleDenyLevelUp}
                    onOpenInventory={handleOpenInventory}
                    setCurrencyDraftByUserId={setCurrencyDraftByUserId}
                    setHpDraftByUserId={setHpDraftByUserId}
                    setItemDraftByUserId={setItemDraftByUserId}
                    setXpDraftByUserId={setXpDraftByUserId}
                />
            )}

            {activeSession?.status === "ACTIVE" && <GmDashboardActivityCard activityFeed={activityFeed} />}

            <StartSessionModal
                isOpen={showStartModal}
                onClose={() => setShowStartModal(false)}
                onConfirm={handleConfirmStart}
                loading={creating}
            />

            <DiceVisualizer events={rollEvents} />
        </section>
    );
};
