import { useEffect, useState } from "react";
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
import { CombatModeBar } from "../../features/combat-ui/components/CombatModeBar";
import { GmCombatModeShell } from "../../features/combat-ui/gm/GmCombatModeShell";
import { useCombatUiState } from "../../features/combat-ui/useCombatUiState";
import { AuthoritativeRollDialog } from "../../features/rolls/components/AuthoritativeRollDialog";
import type { CombatParticipantPreview } from "./CombatStartModal";

export const GmDashboardPage = () => {
    const { campaignId } = useParams<{ campaignId: string }>();
    const navigate = useNavigate();
    const { selectedCampaign, selectedCampaignId, selectCampaign } = useCampaigns();
    const { t } = useLocale();
    const effectiveCampaignId = campaignId ?? selectedCampaignId ?? null;
    const {
        combatModeVisible,
        combatUiExpanded,
        combatUiActive,
        setSelectedSessionId,
        toggleCombatUiExpanded,
    } = useSession();
    const [gmInitiativeQueue, setGmInitiativeQueue] = useState<CombatParticipantPreview[]>([]);
    const {
        activate,
        activeSession,
        activityFeed,
        catalogItems,
        combatUiActive: gmCombatUiActive,
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
        handleRequestInitiativeRoll,
        inventoryOpenForUserId,
        itemDraftByUserId,
        levelUpActionState,
        missingSheetsPlayers,
        rollAbility,
        rollAdvantage,
        rollDc,
        rollExpression,
        rollOptions,
        rollReason,
        rollSkill,
        rollTargetUserId,
        rollType,
        setCurrencyDraftByUserId,
        setHpDraftByUserId,
        setItemDraftByUserId,
        setMissingSheetsPlayers,
        setRollAbility,
        setRollAdvantage,
        setRollDc,
        setRollExpression,
        setRollReason,
        setRollSkill,
        setRollTargetUserId,
        setRollType,
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
    const effectiveCombatUiActive = combatUiActive || gmCombatUiActive;
    const effectiveCombatModeVisible = effectiveCombatUiActive && !combatUiExpanded;
    const combatBarState = useCombatUiState({
        enabled: Boolean(activeSession?.id) && effectiveCombatUiActive && !effectiveCombatModeVisible,
        sessionId: activeSession?.id ?? "",
    });
    const dashboardBackHref = activeSession?.partyId
        ? routes.partyDetails.replace(":partyId", activeSession.partyId)
        : routes.home;

    useEffect(() => {
        if (!effectiveCombatUiActive || activeSession?.status !== "ACTIVE") {
            setGmInitiativeQueue([]);
        }
    }, [activeSession?.status, effectiveCombatUiActive]);

    useEffect(() => {
        setGmInitiativeQueue([]);
    }, [activeSession?.id]);

    return (
        <section className="space-y-8">
            {effectiveCombatModeVisible && activeSession?.status === "ACTIVE" && effectiveCampaignId ? (
                <GmCombatModeShell
                    campaignId={effectiveCampaignId}
                    expanded={combatUiExpanded}
                    onToggleExpanded={toggleCombatUiExpanded}
                    partyPlayers={partyPlayers}
                    playerSheetByUserId={playerSheetByUserId}
                    sessionId={activeSession.id}
                />
            ) : (
                <>
            <GmDashboardHeader
                backHref={dashboardBackHref}
                backLabel={t("gm.dashboard.backToParty")}
                overviewName={overviewName}
                overviewSystem={overviewSystem}
                selectedCampaignName={selectedCampaign?.name}
            />

            {effectiveCombatUiActive && activeSession?.status === "ACTIVE" ? (
                <CombatModeBar
                    currentParticipantName={combatBarState.currentParticipant?.display_name ?? null}
                    expanded={combatUiExpanded}
                    onToggleExpanded={toggleCombatUiExpanded}
                    phase={combatBarState.state?.phase ?? null}
                    round={combatBarState.state?.round ?? null}
                    turnResources={combatBarState.currentParticipant?.turn_resources ?? null}
                />
            ) : null}

            <GmDashboardMissingSheetsBanner
                players={missingSheetsPlayers}
                onClose={() => setMissingSheetsPlayers([])}
            />

            <GmDashboardSessionPanel
                activeSession={activeSession}
                combatUiActive={effectiveCombatUiActive}
                commandFeedback={commandFeedback}
                commandSending={commandSending}
                creating={creating}
                forceStarting={forceStarting}
                loading={loading}
                lobbyStatus={lobbyStatus}
                onlineUsers={onlineUsers}
                partyPlayers={partyPlayers}
                restState={restUiState}
                rollAbility={rollAbility}
                rollAdvantage={rollAdvantage}
                rollDc={rollDc}
                rollExpression={rollExpression}
                rollOptions={rollOptions}
                rollReason={rollReason}
                rollSkill={rollSkill}
                rollTargetUserId={rollTargetUserId}
                rollType={rollType}
                shopUiOpen={shopUiOpen}
                onActivateClick={handleActivateClick}
                onCommand={handleCommand}
                onEndSession={handleEndSession}
                onForceStart={handleForceStart}
                onRequestInitiativeRoll={handleRequestInitiativeRoll}
                onClearGmInitiativeQueue={() => setGmInitiativeQueue([])}
                onSetGmInitiativeQueue={setGmInitiativeQueue}
                setRollAbility={setRollAbility}
                setRollAdvantage={setRollAdvantage}
                setRollDc={setRollDc}
                setRollExpression={setRollExpression}
                setRollReason={setRollReason}
                setRollSkill={setRollSkill}
                setRollTargetUserId={setRollTargetUserId}
                setRollType={setRollType}
            />

            {activeSession?.status === "ACTIVE" && effectiveCampaignId && (
                <SessionEntityPanel
                    sessionId={activeSession.id}
                    campaignId={effectiveCampaignId}
                    combatActive={effectiveCombatUiActive}
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

            {activeSession?.status === "ACTIVE" && activeSession?.id ? (
                <GmDashboardActivityCard activityFeed={activityFeed} sessionId={activeSession.id} />
            ) : null}

            <StartSessionModal
                isOpen={showStartModal}
                onClose={() => setShowStartModal(false)}
                onConfirm={handleConfirmStart}
                loading={creating}
            />

            <DiceVisualizer events={rollEvents} />
                </>
            )}

            {activeSession?.id && gmInitiativeQueue[0] ? (
                <AuthoritativeRollDialog
                    key={`gm-initiative:${gmInitiativeQueue[0].id}`}
                    request={{
                        rollType: "initiative",
                        advantageMode: "normal",
                        reason: gmInitiativeQueue[0].displayName,
                    }}
                    sessionId={activeSession.id}
                    actorKind="session_entity"
                    actorRefId={gmInitiativeQueue[0].id}
                    onResolved={() => {
                        setGmInitiativeQueue((current) => current.slice(1));
                    }}
                    onClose={() => {
                        setGmInitiativeQueue((current) => current.slice(1));
                    }}
                />
            ) : null}
        </section>
    );
};
