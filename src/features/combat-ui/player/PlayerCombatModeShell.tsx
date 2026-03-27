import { useMemo, useState } from "react";
import type {
  AbilityName,
  AdvantageMode,
  RollType,
  SkillName,
} from "../../../entities/roll/rollResolution.types";
import { AuthoritativeRollDialog } from "../../../features/rolls/components/AuthoritativeRollDialog";
import { RollResultCard } from "../../../features/rolls/components/RollResultCard";
import { useVisibleEntities } from "../../../features/session-entities/hooks/useVisibleEntities";
import { useLocale } from "../../../shared/hooks/useLocale";
import { getCombatEffectLabel, getCombatStatusLabel } from "../combatUi.helpers";
import { CombatLogPanel } from "../components/CombatLogPanel";
import { CombatModeBar } from "../components/CombatModeBar";
import { CombatParticipantRoster } from "../components/CombatParticipantRoster";
import { buildCombatParticipantViews } from "../combatUi.helpers";
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

type Props = {
  campaignId?: string | null;
  expanded: boolean;
  inventory: InventoryItem[] | null;
  itemsById: Record<string, Item>;
  locale: Locale;
  manualValue: string;
  onAuthoritativeRollResolved: () => void;
  onClearPendingRoll: () => void;
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

export const PlayerCombatModeShell = ({
  campaignId,
  expanded,
  inventory,
  itemsById,
  locale,
  manualValue,
  onAuthoritativeRollResolved,
  onClearPendingRoll,
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
  const [activeActionPanel, setActiveActionPanel] = useState<
    "attack" | "spell" | "standard" | "object"
  >("attack");
  const visibleEntities = useVisibleEntities(sessionId);
  const {
    attackDialogOpen,
    closeAttackDialog,
    closeSpellDialog,
    combat,
    consumableItemId,
    consumableOptions,
    deathSaveFeedback,
    handleAttack,
    handleRequestReaction,
    handleDeathSave,
    handleEndTurn,
    handleStandardAction,
    handleUseObject,
    handleCast,
    lastAttackResult,
    lastSpellResult,
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
    setUseObjectNote,
    spellDamageType,
    spellDialogOpen,
    spellEffectBonus,
    spellEffectDice,
    spellMode,
    spellOptions,
    spellSaveAbility,
    targetId,
    useObjectNote,
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

  const entityVitalsByRefId = useMemo(
    () =>
      Object.fromEntries(
        visibleEntities.entities.map((entity) => [
          entity.id,
          {
            currentHp: entity.currentHp ?? null,
            maxHp: entity.entity?.maxHp ?? null,
          },
        ]),
      ),
    [visibleEntities.entities],
  );

  const rosterParticipants = useMemo(
    () =>
      buildCombatParticipantViews({
        currentTurnIndex: combat.state?.current_turn_index ?? -1,
        entityVitalsByRefId,
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
    [combat.state?.current_turn_index, entityVitalsByRefId, playerStatus?.currentHp, playerStatus?.maxHp, userId, visibleParticipants],
  );

  const myParticipant = combat.myParticipant;
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
  const actionPanels = [
    { key: "attack" as const, label: t("combatUi.attack") },
    { key: "spell" as const, label: t("combatUi.castSpell") },
    { key: "standard" as const, label: t("combatUi.standardActions") },
    { key: "object" as const, label: t("combatUi.useObject") },
  ];

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

                <div className="space-y-4">
                  <div className="overflow-x-auto">
                    <div className="inline-flex min-w-full gap-2 rounded-3xl border border-white/8 bg-white/4 p-2">
                      {actionPanels.map((panel) => {
                        const isActive = activeActionPanel === panel.key;
                        return (
                          <button
                            key={panel.key}
                            type="button"
                            onClick={() => setActiveActionPanel(panel.key)}
                            className={`min-w-0 flex-1 rounded-2xl px-4 py-3 text-sm font-semibold transition-colors ${
                              isActive
                                ? "bg-white text-slate-950"
                                : "bg-slate-950/40 text-slate-200 hover:bg-slate-900/70"
                            }`}
                          >
                            <span className="block whitespace-normal break-words leading-5">
                              {panel.label}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {activeActionPanel === "attack" ? (
                    <article className="rounded-3xl border border-amber-500/15 bg-amber-500/8 p-5">
                      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                        <div>
                          <h3 className="text-lg font-semibold text-white">{t("combatUi.attack")}</h3>
                          <p className="mt-2 text-sm text-slate-300">
                            {playerStatus?.currentWeapon?.name ?? t("combatUi.noWeapon")}
                          </p>
                          {playerStatus?.currentWeapon ? (
                            <p className="mt-3 text-sm leading-6 text-slate-300">
                              {playerStatus.currentWeapon.damageLabel}
                            </p>
                          ) : null}
                        </div>
                        <button
                          type="button"
                          disabled={!canAct || actionUsed || !targetId}
                          onClick={() => {
                            void handleAttack();
                          }}
                          className="rounded-full bg-amber-500 px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-slate-950 transition-colors hover:bg-amber-400 disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          {t("combatUi.attack")}
                        </button>
                      </div>
                    </article>
                  ) : null}

                  {activeActionPanel === "spell" ? (
                    <article className="rounded-3xl border border-fuchsia-500/15 bg-fuchsia-500/8 p-5">
                      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                        <div className="min-w-0">
                          <h3 className="text-lg font-semibold text-white">{t("combatUi.castSpell")}</h3>
                          <p className="mt-2 text-sm text-slate-300">
                            {selectedSpell?.name ?? t("combatUi.noSpellcasting")}
                          </p>
                        </div>
                        <button
                          type="button"
                          disabled={!canAct || actionUsed || !targetId || !selectedSpell}
                          onClick={() => {
                            void handleCast();
                          }}
                          className="rounded-full bg-fuchsia-500 px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-white transition-colors hover:bg-fuchsia-400 disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          {t("combatUi.castSpell")}
                        </button>
                      </div>
                      <label className="mt-4 block space-y-2">
                        <span className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                          {t("combatUi.selectSpell")}
                        </span>
                        <select
                          value={selectedSpellId}
                          onChange={(event) => setSelectedSpellId(event.target.value)}
                          className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-fuchsia-400"
                        >
                          {spellOptions.length === 0 ? (
                            <option value="">{t("combatUi.noSpellsPrepared")}</option>
                          ) : (
                            spellOptions.map((spell) => (
                              <option key={spell.id} value={spell.id}>
                                {spell.name} · {spell.range || t("combatUi.rangeUnknown")}
                              </option>
                            ))
                          )}
                        </select>
                      </label>
                    </article>
                  ) : null}

                  {activeActionPanel === "standard" ? (
                    <article className="min-w-0 rounded-3xl border border-white/8 bg-white/4 p-5">
                      <h3 className="text-lg font-semibold text-white">{t("combatUi.standardActions")}</h3>
                      <div className="mt-4 grid min-w-0 auto-rows-fr gap-2 sm:grid-cols-2">
                        {([
                          ["dodge", t("combatUi.dodge")],
                          ["help", t("combatUi.help")],
                          ["hide", t("combatUi.hide")],
                          ["dash", t("combatUi.dash")],
                          ["disengage", t("combatUi.disengage")],
                        ] as const).map(([action, label]) => (
                          <button
                            key={action}
                            type="button"
                            disabled={!canAct || actionUsed || (action === "help" && !targetId)}
                            onClick={() => {
                              void handleStandardAction(
                                action,
                                action === "help" && selectedTarget ? selectedTarget.id : undefined,
                              );
                            }}
                            className="min-w-0 rounded-2xl border border-white/10 bg-slate-950/65 px-4 py-3 text-left text-sm font-semibold leading-5 text-white transition-colors hover:bg-slate-900 whitespace-normal break-words disabled:cursor-not-allowed disabled:opacity-40"
                          >
                            {label}
                          </button>
                        ))}
                      </div>
                    </article>
                  ) : null}

                  {activeActionPanel === "object" ? (
                    <article className="rounded-3xl border border-emerald-500/15 bg-emerald-500/8 p-5">
                      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                        <div>
                          <h3 className="text-lg font-semibold text-white">{t("combatUi.useObject")}</h3>
                          <p className="mt-2 text-sm leading-6 text-slate-300">
                            {t("combatUi.useObjectHint")}
                          </p>
                        </div>
                        <button
                          type="button"
                          disabled={!canAct || actionUsed}
                          onClick={() => {
                            void handleUseObject();
                          }}
                          className="rounded-full bg-emerald-500 px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-slate-950 transition-colors hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          {t("combatUi.useObject")}
                        </button>
                      </div>
                      <label className="mt-4 block space-y-2">
                        <span className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                          {t("combatUi.usableConsumable")}
                        </span>
                        <select
                          value={consumableItemId}
                          onChange={(event) => setConsumableItemId(event.target.value)}
                          className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-emerald-400"
                        >
                          {consumableOptions.length === 0 ? (
                            <option value="">{t("combatUi.noConsumables")}</option>
                          ) : (
                            consumableOptions.map((option) => (
                              <option key={option.id} value={option.id}>
                                {option.label}
                              </option>
                            ))
                          )}
                        </select>
                      </label>
                      <label className="mt-4 block space-y-2">
                        <span className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                          {t("combatUi.useObjectManualNote")}
                        </span>
                        <input
                          type="text"
                          value={useObjectNote}
                          onChange={(event) => setUseObjectNote(event.target.value)}
                          placeholder={t("combatUi.useObjectPlaceholder")}
                          className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none transition-colors placeholder:text-slate-500 focus:border-emerald-400"
                        />
                      </label>
                    </article>
                  ) : null}
                </div>

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
                <RollResultCard result={lastAttackResult.roll_result} />
              </div>
            </section>
          ) : null}

          {lastSpellResult?.roll_result ? (
            <section className="rounded-4xl border border-fuchsia-500/15 bg-fuchsia-500/8 p-5">
              <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-fuchsia-100">
                {t("combatUi.lastSpell")}
              </p>
              <div className="mt-4">
                <RollResultCard result={lastSpellResult.roll_result} />
              </div>
            </section>
          ) : null}
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
