import { useLocale } from "../../../shared/hooks/useLocale";
import { localizeDamageType } from "../../../shared/i18n/domainLabels";
import type { PlayerBoardStatusSummary } from "../../../pages/PlayerBoardPage/playerBoard.types";
import type { CombatParticipant, StandardActionType, TurnResources } from "../../../shared/api/combatRepo";
import { getAbilityLabel } from "../../character-sheet/utils/abilityLabels";
import { isCombatSpellActionCostAvailable } from "../spellAutomation";
import { requiresAreaTargetingSelection, spellRequiresExternalTarget } from "../../../pages/PlayerBoardPage/player-combat-debug/areaTargetingUi";
import { RangeStatusBadge } from "../components/RangeStatusBadge";
import type { TargetingPreviewState } from "../hooks/useTargetingPreview";
import { SpellSlotSummary } from "../../../shared/ui/SpellSlotSummary";
import type {
  ConsumableOption,
  DragonbornBreathWeaponOption,
  SelectedConsumable,
  SpellOption,
  UseObjectTargetOption,
  WeaponOption,
} from "./playerCombatShell.types";
import { PlayerUseObjectPanel } from "./PlayerUseObjectPanel";
import type {
  ActiveElementalResistance,
  DraconicElementalResistanceAction,
} from "./draconicElementalResistance";
import type { DraconicElementalResistanceResult } from "../../../shared/api/combatRepo";
import type { DragonWingsAction } from "./dragonWings";
import type { SpiritualWeaponFollowUpAction } from "./spiritualWeapon";
import type { CreatureSize } from "@limiarmap/shared-contracts";
import { formatSizeMeleeReachBonusSource, formatMetersCompact } from "../utils/formatSizeMeleeReachBonus";

type Props = {
  activeActionPanel: "attack" | "spell" | "standard" | "object";
  actionUsed: boolean;
  attackRangePreview: TargetingPreviewState;
  canAct: boolean;
  consumableItemId: string;
  consumableOptions: ConsumableOption[];
  dragonbornBreathWeaponAction: DragonbornBreathWeaponOption | null;
  draconicElementalResistanceAction?: DraconicElementalResistanceAction | null;
  activeElementalResistance?: ActiveElementalResistance | null;
  lastElementalResistanceResult?: DraconicElementalResistanceResult | null;
  dragonWingsAction?: DragonWingsAction | null;
  spiritualWeaponFollowUpAction: SpiritualWeaponFollowUpAction | null;
  handleAttack: () => Promise<void>;
  handleCast: () => Promise<void>;
  handleDragonbornBreathWeapon: () => Promise<void>;
  handleActivateDraconicElementalResistance?: () => Promise<void>;
  handleToggleDragonWings?: () => Promise<void>;
  onEnterSpiritualWeaponMode: () => void;
  handleStandardAction: (action: StandardActionType, targetId?: string) => Promise<void>;
  handleUseObject: () => Promise<void>;
  myParticipantId?: string | null;
  playerStatus?: PlayerBoardStatusSummary | null;
  selectedConsumable: SelectedConsumable | null;
  selectedTarget: { id: string } | null;
  selectedSpell: SpellOption | null;
  selectedSpellId: string;
  spellRangePreview: TargetingPreviewState;
  turnResources?: TurnResources | null;
  setActiveActionPanel: (panel: "attack" | "spell" | "standard" | "object") => void;
  setConsumableItemId: (id: string) => void;
  setSelectedSpellId: (id: string) => void;
  setUseObjectManualRolls: (updater: (current: number[]) => number[]) => void;
  setUseObjectNote: (note: string) => void;
  setUseObjectRollMode: (mode: "system" | "manual") => void;
  setUseObjectTargetParticipantId: (id: string) => void;
  selectedWeaponId: string;
  spellOptions: SpellOption[];
  targetId: string;
  useObjectActionDisabled: boolean;
  useObjectManualRolls: number[];
  useObjectNote: string;
  useObjectRollMode: "system" | "manual";
  useObjectTargetOptions: UseObjectTargetOption[];
  useObjectTargetParticipantId: string;
  weaponOptions: WeaponOption[];
  isSavingLoadout?: boolean;
  isMyTurn?: boolean;
  loadoutStatus?: string | null;
  participants?: CombatParticipant[];
  onWeaponChange?: (inventoryItemId: string | null) => void;
  effectiveSize?: CreatureSize;
};

export const PlayerActionPanels = ({
  activeActionPanel,
  actionUsed,
  attackRangePreview,
  canAct,
  consumableItemId,
  consumableOptions,
  dragonbornBreathWeaponAction,
  draconicElementalResistanceAction = null,
  activeElementalResistance = null,
  lastElementalResistanceResult = null,
  dragonWingsAction = null,
  spiritualWeaponFollowUpAction,
  handleAttack,
  handleCast,
  handleDragonbornBreathWeapon,
  handleActivateDraconicElementalResistance,
  handleToggleDragonWings,
  onEnterSpiritualWeaponMode,
  handleStandardAction,
  handleUseObject,
  myParticipantId,
  playerStatus,
  selectedConsumable,
  selectedTarget,
  selectedSpell,
  selectedSpellId,
  spellRangePreview,
  turnResources,
  setActiveActionPanel,
  setConsumableItemId,
  setSelectedSpellId,
  setUseObjectManualRolls,
  setUseObjectNote,
  setUseObjectRollMode,
  setUseObjectTargetParticipantId,
  selectedWeaponId,
  spellOptions,
  targetId,
  useObjectActionDisabled,
  useObjectManualRolls,
  useObjectNote,
  useObjectRollMode,
  useObjectTargetOptions,
  useObjectTargetParticipantId,
  weaponOptions,
  isSavingLoadout = false,
  isMyTurn = false,
  loadoutStatus = null,
  participants = [],
  onWeaponChange,
  effectiveSize,
}: Props) => {
  const { locale, t } = useLocale();
  const myParticipant = participants.find((participant) => participant.id === myParticipantId) ?? null;
  const wildShapeActive = Boolean(myParticipant?.wild_shape_active);
  const selectedSpellActionCost = selectedSpell?.actionCost ?? null;
  const selectedSpellIsArea = requiresAreaTargetingSelection(selectedSpell?.selectionType, selectedSpell?.areaShape);
  const selectedSpellNeedsTarget = spellRequiresExternalTarget(selectedSpell?.selectionType, selectedSpell?.areaShape);
  const canSpendSpellActionCost = isCombatSpellActionCostAvailable(
    selectedSpellActionCost,
    turnResources,
  );
  const spellActionCostLabel =
    selectedSpellActionCost === "bonus_action"
      ? t("combatUi.bonusAction")
      : selectedSpellActionCost === "reaction"
        ? t("combatUi.reaction")
        : t("combatUi.action");

  const actionPanels = [
    { key: "attack" as const, label: t("combatUi.weaponAttack") },
    { key: "spell" as const, label: t("combatUi.castSpell") },
    { key: "standard" as const, label: t("combatUi.standardActions") },
    { key: "object" as const, label: t("combatUi.useObject") },
  ];
  const dragonbornDamageLabel = localizeDamageType(
    dragonbornBreathWeaponAction?.damageType ?? null,
    locale,
  );
  const elementalResistanceDamageLabel = localizeDamageType(
    draconicElementalResistanceAction?.damageType ?? null,
    locale,
  );
  const selectedWeaponOption =
    weaponOptions.find((option) => option.value === selectedWeaponId) ?? null;
  const selectedSpellHasSlots = (selectedSpell?.availableSlotLevels?.length ?? 0) > 0;
  const selectedSpellIsCantrip = selectedSpell?.level === 0;
  const spellCastUnavailableForSlots = Boolean(
    selectedSpell &&
      !selectedSpellIsCantrip &&
      selectedSpell.sourceType !== "magic_item" &&
      !selectedSpellHasSlots,
  );

  return (
    <>
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
                <span className="block whitespace-normal wrap-break-word leading-5">
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
            <div className="min-w-0">
              <h3 className="text-lg font-semibold text-white">{t("combatUi.attack")}</h3>
              <p className="mt-2 text-sm text-slate-300">
                {playerStatus?.currentWeapon?.name ?? t("combatUi.noWeapon")}
              </p>
              {playerStatus?.currentWeapon ? (
                <p className="mt-3 text-sm leading-6 text-slate-300">
                  {playerStatus.currentWeapon.damageLabel}
                </p>
              ) : null}
              <label className="mt-4 block">
                <span className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                  {t("combatUi.switchWeapon")}
                </span>
                <select
                  value={selectedWeaponId}
                  disabled={isSavingLoadout || weaponOptions.length === 0}
                  onChange={(event) => onWeaponChange?.(event.target.value || null)}
                  className="mt-2 w-full rounded-2xl border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-amber-400 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <option value="">{t("combatUi.switchWeaponPlaceholder")}</option>
                  {weaponOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.detail ? `${option.label} · ${option.detail}` : option.label}
                    </option>
                  ))}
                </select>
                <span className="mt-2 block text-xs text-slate-400">
                  {selectedWeaponOption?.detail
                    ? `${selectedWeaponOption.label} · ${selectedWeaponOption.detail}`
                    : selectedWeaponOption?.label ?? t("combatUi.switchWeaponHint")}
                </span>
              </label>
              {loadoutStatus ? (
                <p className="mt-2 text-xs font-medium text-amber-200">{loadoutStatus}</p>
              ) : null}
              {effectiveSize && !playerStatus?.currentWeapon?.isRanged ? (
                (() => {
                  const sizeBonus = formatSizeMeleeReachBonusSource(effectiveSize, t);
                  if (!sizeBonus) return null;
                  const baseReach = playerStatus?.currentWeapon?.rangeMeters ?? 1.5;
                  const totalReach = baseReach + sizeBonus.bonusMeters;
                  return (
                    <div className="mt-3 space-y-1">
                      <p className="text-xs text-amber-200">
                        {t("combatUi.meleeReachEffective")}: {formatMetersCompact(totalReach)}
                      </p>
                      <p className="text-[11px] text-slate-400">
                        {sizeBonus.label}
                      </p>
                    </div>
                  );
                })()
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
          {targetId ? (
            <div className="mt-4">
              <RangeStatusBadge preview={attackRangePreview} effectiveSize={effectiveSize} />
            </div>
          ) : null}
        </article>
      ) : null}

      {activeActionPanel === "spell" ? (
        <article className="rounded-3xl border border-fuchsia-500/15 bg-fuchsia-500/8 p-5">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <h3 className="text-lg font-semibold text-white">{t("combatUi.castSpell")}</h3>
              <p className="mt-2 text-sm text-slate-300">
                {((locale === "pt" && selectedSpell?.namePt) ? selectedSpell.namePt : selectedSpell?.name) ?? t("combatUi.noSpellcasting")}
              </p>
              {selectedSpell?.sourceType === "magic_item" && selectedSpell.sourceItemName ? (
                <p className="mt-2 text-xs text-slate-400">
                  {selectedSpell.sourceItemName}
                  {typeof selectedSpell.chargesCurrent === "number" && typeof selectedSpell.chargesMax === "number"
                    ? ` · ${selectedSpell.chargesCurrent}/${selectedSpell.chargesMax}`
                    : ""}
                </p>
              ) : null}
              {selectedSpell ? (
                <p className="mt-2 text-xs uppercase tracking-[0.2em] text-fuchsia-200/80">
                  {spellActionCostLabel}
                </p>
              ) : null}
              {selectedSpellIsCantrip ? (
                <p className="mt-2 text-xs text-emerald-200">Truque - sem custo de slot.</p>
              ) : null}
              {selectedSpell?.slotSummary?.length ? (
                <div className="mt-3">
                  <SpellSlotSummary compact entries={selectedSpell.slotSummary} />
                </div>
              ) : null}
              {spellCastUnavailableForSlots ? (
                <p className="mt-2 text-xs text-rose-200">Sem slots válidos disponíveis para esta magia.</p>
              ) : null}
              {selectedSpell && !canSpendSpellActionCost ? (
                <p className="mt-2 text-xs text-rose-200">
                  {t("combatUi.spellActionUnavailable")}
                </p>
              ) : null}
            </div>
            <button
              type="button"
              disabled={!canAct || !canSpendSpellActionCost || spellCastUnavailableForSlots || (selectedSpellNeedsTarget && !targetId) || !selectedSpell}
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
                    {(locale === "pt" && spell.namePt) ? spell.namePt : spell.name}
                    {spell.level === 0 ? ` · ${locale === "pt" ? "truque" : "cantrip"}` : ""}
                    {spell.level !== 0 && spell.sourceType !== "magic_item" && (spell.availableSlotLevels?.length ?? 0) === 0
                      ? " · sem slots"
                      : ""}
                    {spell.sourceType === "magic_item" && spell.sourceItemName ? ` · ${spell.sourceItemName}` : ""}
                    {typeof spell.chargesCurrent === "number" && typeof spell.chargesMax === "number"
                      ? ` · ${spell.chargesCurrent}/${spell.chargesMax}`
                      : ""}
                    {` · ${spell.range || t("combatUi.rangeUnknown")}`}
                  </option>
                ))
              )}
            </select>
          </label>
          {targetId && selectedSpell ? (
            <div className="mt-4">
              <RangeStatusBadge preview={spellRangePreview} />
            </div>
          ) : null}
        </article>
      ) : null}

      {activeActionPanel === "standard" ? (
        <article className="min-w-0 rounded-3xl border border-white/8 bg-white/4 p-5">
          <h3 className="text-lg font-semibold text-white">{t("combatUi.standardActions")}</h3>
          {spiritualWeaponFollowUpAction ? (
            <div className="mt-4 rounded-3xl border border-violet-500/20 bg-violet-500/8 p-4">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-white">
                    {t("combatUi.spiritualWeaponAction")}
                  </p>
                  <p className="mt-2 text-xs uppercase tracking-[0.2em] text-violet-100/80">
                    {t("combatUi.bonusAction")}
                  </p>
                  {spiritualWeaponFollowUpAction.remainingRounds != null && (
                    <p className="mt-2 text-xs text-slate-300">
                      {t("combatUi.spiritualWeaponRoundsLeft").replace(
                        "{rounds}",
                        String(spiritualWeaponFollowUpAction.remainingRounds),
                      )}
                    </p>
                  )}
                </div>
                <button
                  type="button"
                  disabled={!canAct || !isMyTurn || (turnResources?.bonus_action_used ?? false)}
                  onClick={onEnterSpiritualWeaponMode}
                  className="rounded-full bg-violet-600 px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-white transition-colors hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {t("combatUi.spiritualWeaponAction")}
                </button>
              </div>
            </div>
          ) : null}
          {dragonbornBreathWeaponAction ? (
            <div className="mt-4 rounded-3xl border border-emerald-500/20 bg-emerald-500/8 p-4">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-white">
                    {t("combatUi.dragonbornBreathWeapon")}
                    {dragonbornDamageLabel ? ` (${dragonbornDamageLabel})` : ""}
                  </p>
                  <p className="mt-2 text-xs uppercase tracking-[0.2em] text-emerald-100/80">
                    {t("combatUi.action")}
                  </p>
                  <p className="mt-3 text-sm leading-6 text-slate-300">
                    {dragonbornBreathWeaponAction.damageDice} · {t("combatUi.saveDcShort")}{" "}
                    {dragonbornBreathWeaponAction.dc} ·{" "}
                    {getAbilityLabel(dragonbornBreathWeaponAction.saveAbility, t)}
                  </p>
                  <p className="mt-2 text-xs text-slate-300">
                    {t("combatUi.usesRemaining")}: {dragonbornBreathWeaponAction.usesRemaining}/
                    {dragonbornBreathWeaponAction.usesMax}
                  </p>
                </div>
                <button
                  type="button"
                  disabled={
                    !canAct
                    || actionUsed
                    || wildShapeActive
                    || !targetId
                    || dragonbornBreathWeaponAction.usesRemaining <= 0
                  }
                  onClick={() => {
                    void handleDragonbornBreathWeapon();
                  }}
                  className="rounded-full bg-emerald-500 px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-slate-950 transition-colors hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {t("combatUi.useDragonbornBreathWeapon")}
                </button>
              </div>
            </div>
          ) : null}
          {draconicElementalResistanceAction ? (
            <div className="mt-4 rounded-3xl border border-amber-500/20 bg-amber-500/8 p-4">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-white">
                    {t("combatUi.elementalAffinityResistance")}
                    {elementalResistanceDamageLabel ? ` (${elementalResistanceDamageLabel})` : ""}
                  </p>
                  <p className="mt-2 text-xs uppercase tracking-[0.2em] text-amber-100/80">
                    {t("combatUi.elementalAffinityResistanceCost")}
                  </p>
                  <p className="mt-3 text-sm leading-6 text-slate-300">
                    {t("combatUi.sorceryPoints")}:{" "}
                    {draconicElementalResistanceAction.sorceryPointsRemaining}/
                    {draconicElementalResistanceAction.sorceryPointsMax}
                  </p>
                  {activeElementalResistance ? (
                    <p className="mt-2 text-xs text-amber-200">
                      {t("combatUi.elementalAffinityResistanceActive")}
                      {" · "}
                      {activeElementalResistance.secondsRemaining ?? 0}s
                    </p>
                  ) : lastElementalResistanceResult ? (
                    <p className="mt-2 text-xs text-amber-200">
                      {t("combatUi.elementalAffinityResistanceActive")}
                      {" · "}
                      {lastElementalResistanceResult.duration_seconds}s
                    </p>
                  ) : null}
                </div>
                <button
                  type="button"
                  disabled={
                    !canAct
                    || wildShapeActive
                    || draconicElementalResistanceAction.sorceryPointsRemaining <= 0
                  }
                  onClick={() => {
                    void handleActivateDraconicElementalResistance?.();
                  }}
                  className="rounded-full bg-amber-500 px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-slate-950 transition-colors hover:bg-amber-400 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {t("combatUi.useElementalAffinityResistance")}
                </button>
              </div>
            </div>
          ) : null}
          {dragonWingsAction ? (
            <div className="mt-4 rounded-3xl border border-indigo-500/20 bg-indigo-500/8 p-4">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-white">
                    {t("combatUi.dragonWings")}
                    {dragonWingsAction.active ? ` · ${t("combatUi.dragonWingsFlying")}` : ""}
                  </p>
                  <p className="mt-2 text-xs uppercase tracking-[0.2em] text-indigo-100/80">
                    {t("combatUi.bonusAction")}
                  </p>
                  {dragonWingsAction.active ? (
                    <p className="mt-3 text-sm leading-6 text-slate-300">
                      {t("combatUi.flySpeed")}: {dragonWingsAction.flySpeedMeters}m
                    </p>
                  ) : null}
                </div>
                <button
                  type="button"
                  disabled={!canAct || (turnResources?.bonus_action_used ?? false)}
                  onClick={() => {
                    void handleToggleDragonWings?.();
                  }}
                  className="rounded-full bg-indigo-500 px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-white transition-colors hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {dragonWingsAction.active
                    ? t("combatUi.dismissDragonWings")
                    : t("combatUi.useDragonWings")}
                </button>
              </div>
            </div>
          ) : null}
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
                className="min-w-0 rounded-2xl border border-white/10 bg-slate-950/65 px-4 py-3 text-left text-sm font-semibold leading-5 text-white transition-colors hover:bg-slate-900 whitespace-normal wrap-break-word ak-words disabled:cursor-not-allowed disabled:opacity-40"
              >
                {label}
              </button>
            ))}
          </div>
        </article>
      ) : null}

      {activeActionPanel === "object" ? (
        <PlayerUseObjectPanel
          consumableItemId={consumableItemId}
          consumableOptions={consumableOptions}
          handleUseObject={handleUseObject}
          myParticipantId={myParticipantId}
          selectedConsumable={selectedConsumable}
          setConsumableItemId={setConsumableItemId}
          setUseObjectManualRolls={setUseObjectManualRolls}
          setUseObjectNote={setUseObjectNote}
          setUseObjectRollMode={setUseObjectRollMode}
          setUseObjectTargetParticipantId={setUseObjectTargetParticipantId}
          useObjectActionDisabled={useObjectActionDisabled}
          useObjectManualRolls={useObjectManualRolls}
          useObjectNote={useObjectNote}
          useObjectRollMode={useObjectRollMode}
          useObjectTargetOptions={useObjectTargetOptions}
          useObjectTargetParticipantId={useObjectTargetParticipantId}
        />
      ) : null}
    </div>
    </>
  );
};
