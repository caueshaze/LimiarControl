import type { ActiveConcentration } from "../../entities/character";
import type { ActiveEffect } from "../../shared/api/combatRepo";
import type { CharacterSheet } from "../../features/character-sheet/model/characterSheet.types";
import { useLocale } from "../../shared/hooks/useLocale";
import { SpellSlotSummary } from "../../shared/ui/SpellSlotSummary";
import { formatPassiveBonusBreakdown } from "../../features/character-sheet/utils/passiveSkillBonusDisplay";
import { formatActiveConcentrationLabel } from "./concentrationLabel";
import { formatActiveEffectLabel, getActiveEffectLifecycleBadges } from "../../features/active-effects";
import type { PendingRoll, PlayerBoardStatusSummary } from "./playerBoard.types";
import {
  DeathSaveCard,
  getHpBarToneClass,
  getHpToneClass,
  ProgressCard,
  RestCard,
  StatCard,
  WeaponCard,
} from "./player-board-status/PlayerBoardStatusCards";

const encumbranceAccentMap: Record<PlayerBoardStatusSummary["encumbranceTier"], string> = {
  normal: "text-slate-300",
  encumbered: "text-amber-400",
  heavily_encumbered: "text-red-400",
  overloaded: "text-red-600",
};

type Props = {
  activeConcentration?: ActiveConcentration | null;
  activeSpellEffects?: ActiveEffect[] | null;
  clearingConcentration?: boolean;
  combatActive: boolean;
  onClearConcentration: () => void;
  onRemoveEffect: (effectId: string) => void;
  pendingRoll: PendingRoll | null;
  playerSheet?: CharacterSheet | null;
  playerStatus: PlayerBoardStatusSummary | null;
  removingEffectId?: string | null;
  restState: "exploration" | "short_rest" | "long_rest";
  usingHitDie: boolean;
  onUseHitDie: () => void;
};

export const PlayerBoardStatusPanel = ({
  activeConcentration,
  activeSpellEffects,
  clearingConcentration,
  combatActive,
  onClearConcentration,
  onRemoveEffect,
  pendingRoll,
  playerSheet,
  playerStatus,
  removingEffectId,
  restState,
  usingHitDie,
  onUseHitDie,
}: Props) => {
  const { t } = useLocale();

  return (
    <section className="rounded-4xl border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] p-6 shadow-[0_18px_60px_rgba(2,6,23,0.2)]">
      <div className="border-b border-white/8 pb-5">
        <div className="max-w-2xl">
          <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-slate-400">
            {t("playerBoard.statusPanelTitle")}
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-white">
            {t("playerBoard.statusPanelHeading")}
          </h2>
          <p className="mt-3 text-sm leading-7 text-slate-300">
            {t("playerBoard.statusPanelDescription")}
          </p>
        </div>
      </div>

      {!playerStatus ? (
        <p className="mt-5 text-sm leading-7 text-slate-300">
          {t("playerBoard.waitingSheetState")}
        </p>
      ) : (
        <>
          <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard label={t("sheet.basicInfo.level")} value={String(playerStatus.level)} />
            <StatCard
              label={t("playerBoard.currentHpLabel")}
              value={`${playerStatus.currentHp}/${playerStatus.maxHp}`}
              accent={getHpToneClass(playerStatus.hpPercent)}
              helper={
                playerStatus.tempHp > 0
                  ? `${t("playerBoard.tempHpLabel")}: ${playerStatus.tempHp}`
                  : null
              }
            />
            <StatCard
              label={t("playerBoard.xpProgressLabel")}
              value={`${playerStatus.xpPercent}%`}
              accent="text-sky-300"
              helper={
                playerStatus.nextLevelThreshold === null
                  ? t("sheet.progress.maxLevel")
                  : `${playerStatus.experiencePoints}/${playerStatus.nextLevelThreshold} XP`
              }
            />
            <StatCard
              label={t("playerBoard.armorClassLabel")}
              value={String(playerStatus.ac)}
              accent="text-amber-200"
            />
          </div>

          <div className="mt-5 grid gap-3 lg:grid-cols-2">
            <ProgressCard
              label={t("playerBoard.hpTrackLabel")}
              value={`${playerStatus.currentHp}/${playerStatus.maxHp}`}
              percent={playerStatus.hpPercent}
              toneClass={getHpBarToneClass(playerStatus.hpPercent)}
            />
            <ProgressCard
              label={t("playerBoard.xpTrackLabel")}
              value={`${playerStatus.xpPercent}%`}
              percent={playerStatus.xpPercent}
              toneClass="bg-linear-to-r from-sky-500 via-limiar-500 to-emerald-400"
            />
          </div>

          <DeathSaveCard combatActive={combatActive} playerStatus={playerStatus} />

          <div className="mt-5 grid gap-3 xl:grid-cols-[minmax(0,0.68fr)_minmax(0,0.68fr)_minmax(0,0.68fr)_minmax(0,0.68fr)_minmax(0,0.68fr)_minmax(0,1.64fr)]">
            <StatCard
              label={t("playerBoard.initiativeLabel")}
              value={`${playerStatus.initiative >= 0 ? "+" : ""}${playerStatus.initiative}`}
            />
            <StatCard
              label={t("playerBoard.speedLabel")}
              value={playerStatus.baseSpeedMeters > 0 ? `${playerStatus.effectiveSpeedMeters} m` : "-"}
              accent={playerStatus.effectiveSpeedMeters < playerStatus.baseSpeedMeters
                ? encumbranceAccentMap[playerStatus.encumbranceTier]
                : undefined}
              helper={
                playerStatus.effectiveSpeedMeters < playerStatus.baseSpeedMeters
                  ? `${t("playerBoard.speedPenaltyHint")} (base ${playerStatus.baseSpeedMeters} m)`
                  : null
              }
            />
            <StatCard
              label={t("sheet.skills.passivePerception")}
              value={String(playerStatus.passivePerception)}
              helper={
                playerStatus.passivePerceptionBonus && playerStatus.passivePerceptionBonusSources?.length
                  ? formatPassiveBonusBreakdown(
                      playerStatus.passivePerception - playerStatus.passivePerceptionBonus,
                      playerStatus.passivePerceptionBonusSources,
                    )
                  : null
              }
            />
            <StatCard
              label={t("playerBoard.carryingCapacityLabel")}
              value={`${playerStatus.carryingCapacityKg} kg`}
              helper={
                playerStatus.carryingCapacitySources?.length
                  ? `${t("playerBoard.carryingCapacityBase")}: ${playerStatus.baseCarryingCapacityKg} kg\u2003${playerStatus.carryingCapacitySources.map((s) => `${s.label} ×${s.multiplier}`).join(", ")}`
                  : null
              }
            />
            <StatCard
              label={t("playerBoard.encumbranceTierLabel")}
              value={`${playerStatus.totalWeightKg} kg`}
              accent={encumbranceAccentMap[playerStatus.encumbranceTier]}
              helper={
                playerStatus.encumbranceTier !== "normal"
                  ? `${playerStatus.encumbranceNormalMaxKg} kg`
                  : null
              }
            />
            <StatCard
              label={t("playerBoard.pushDragLiftLabel")}
              value={`${playerStatus.pushDragLiftKg} kg`}
            />
            <WeaponCard
              combatActive={combatActive}
              pendingRoll={pendingRoll}
              playerStatus={playerStatus}
            />
          </div>

          {playerSheet?.spellcasting ? (
            <div className="mt-5 rounded-3xl border border-white/8 bg-white/4 px-4 py-4">
              <SpellSlotSummary
                slots={playerSheet.spellcasting.slots}
                title={t("playerBoard.spellResourcesTitle")}
                emptyLabel={t("playerBoard.noSpellSlots")}
              />
            </div>
          ) : null}

          {activeConcentration ? (
            <div className="mt-5 rounded-3xl border border-violet-500/20 bg-violet-500/8 px-4 py-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-400">
                    {t("playerBoard.activeConcentrationLabel")}
                  </p>
                  <h3 className="mt-2 text-lg font-semibold text-white">
                    {formatActiveConcentrationLabel(activeConcentration) ?? t("playerBoard.activeConcentrationLabel")}
                  </h3>
                </div>
              </div>
              <div className="mt-3">
                <button
                  type="button"
                  onClick={onClearConcentration}
                  disabled={clearingConcentration}
                  className="rounded-full bg-violet-200 px-4 py-2 text-xs font-bold uppercase tracking-[0.22em] text-slate-950 transition hover:bg-violet-100 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {clearingConcentration ? t("playerBoard.clearingConcentration") : t("playerBoard.clearConcentration")}
                </button>
              </div>
            </div>
          ) : null}

          {activeSpellEffects?.length ? (
            <div className="mt-5 rounded-3xl border border-white/8 bg-white/4 px-4 py-4">
              <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-400">
                {t("playerBoard.activeEffectsLabel")}
              </p>
              <ul className="mt-3 space-y-2">
                {activeSpellEffects.map((effect) => {
                  const label = formatActiveEffectLabel(effect) ?? t("playerBoard.activeEffectFallback");
                  const lifecycleBadges = getActiveEffectLifecycleBadges(effect);
                  const isRemoving = removingEffectId === effect.id;
                  return (
                    <li key={effect.id} className="flex items-center justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-white">{label}</p>
                        {lifecycleBadges.length > 0 ? (
                          <p className="mt-0.5 flex flex-wrap gap-x-1.5 gap-y-0.5">
                            {lifecycleBadges.map((badge, index) => (
                              <span key={badge.key} className="inline-flex items-center gap-x-1.5">
                                {index > 0 ? (
                                  <span className="text-[10px] text-slate-600">{"\u00B7"}</span>
                                ) : null}
                                <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-violet-400">
                                  {badge.params
                                    ? t(badge.i18nKey).replace("{count}", String(badge.params.count))
                                    : t(badge.i18nKey)}
                                </span>
                              </span>
                            ))}
                          </p>
                        ) : null}
                      </div>
                      <button
                        type="button"
                        onClick={() => onRemoveEffect(effect.id)}
                        disabled={isRemoving}
                        className="shrink-0 rounded-full bg-white/8 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.22em] text-slate-300 transition hover:bg-red-500/20 hover:text-red-300 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {isRemoving ? t("playerBoard.removingEffect") : t("playerBoard.removeEffect")}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          ) : null}

          <RestCard
            playerStatus={playerStatus}
            restState={restState}
            usingHitDie={usingHitDie}
            onUseHitDie={onUseHitDie}
          />
        </>
      )}
    </section>
  );
};
