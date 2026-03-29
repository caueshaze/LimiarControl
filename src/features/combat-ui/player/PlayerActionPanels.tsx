import { useLocale } from "../../../shared/hooks/useLocale";
import { localizeDamageType } from "../../../shared/i18n/domainLabels";
import type { PlayerBoardStatusSummary } from "../../../pages/PlayerBoardPage/playerBoard.types";
import type { StandardActionType, TurnResources } from "../../../shared/api/combatRepo";
import { getAbilityLabel } from "../../character-sheet/utils/abilityLabels";
import { isCombatSpellActionCostAvailable } from "../spellAutomation";
import type {
  ConsumableOption,
  DragonbornBreathWeaponOption,
  SelectedConsumable,
  SpellOption,
  UseObjectTargetOption,
} from "./playerCombatShell.types";
import { PlayerUseObjectPanel } from "./PlayerUseObjectPanel";

type Props = {
  activeActionPanel: "attack" | "spell" | "standard" | "object";
  actionUsed: boolean;
  canAct: boolean;
  consumableItemId: string;
  consumableOptions: ConsumableOption[];
  dragonbornBreathWeaponAction: DragonbornBreathWeaponOption | null;
  handleAttack: () => Promise<void>;
  handleCast: () => Promise<void>;
  handleDragonbornBreathWeapon: () => Promise<void>;
  handleStandardAction: (action: StandardActionType, targetId?: string) => Promise<void>;
  handleUseObject: () => Promise<void>;
  myParticipantId?: string | null;
  playerStatus?: PlayerBoardStatusSummary | null;
  selectedConsumable: SelectedConsumable | null;
  selectedTarget: { id: string } | null;
  selectedSpell: SpellOption | null;
  selectedSpellId: string;
  turnResources?: TurnResources | null;
  setActiveActionPanel: (panel: "attack" | "spell" | "standard" | "object") => void;
  setConsumableItemId: (id: string) => void;
  setSelectedSpellId: (id: string) => void;
  setUseObjectManualRolls: (updater: (current: number[]) => number[]) => void;
  setUseObjectNote: (note: string) => void;
  setUseObjectRollMode: (mode: "system" | "manual") => void;
  setUseObjectTargetParticipantId: (id: string) => void;
  spellOptions: SpellOption[];
  targetId: string;
  useObjectActionDisabled: boolean;
  useObjectManualRolls: number[];
  useObjectNote: string;
  useObjectRollMode: "system" | "manual";
  useObjectTargetOptions: UseObjectTargetOption[];
  useObjectTargetParticipantId: string;
};

export const PlayerActionPanels = ({
  activeActionPanel,
  actionUsed,
  canAct,
  consumableItemId,
  consumableOptions,
  dragonbornBreathWeaponAction,
  handleAttack,
  handleCast,
  handleDragonbornBreathWeapon,
  handleStandardAction,
  handleUseObject,
  myParticipantId,
  playerStatus,
  selectedConsumable,
  selectedTarget,
  selectedSpell,
  selectedSpellId,
  turnResources,
  setActiveActionPanel,
  setConsumableItemId,
  setSelectedSpellId,
  setUseObjectManualRolls,
  setUseObjectNote,
  setUseObjectRollMode,
  setUseObjectTargetParticipantId,
  spellOptions,
  targetId,
  useObjectActionDisabled,
  useObjectManualRolls,
  useObjectNote,
  useObjectRollMode,
  useObjectTargetOptions,
  useObjectTargetParticipantId,
}: Props) => {
  const { locale, t } = useLocale();
  const selectedSpellActionCost = selectedSpell?.actionCost ?? null;
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
    { key: "attack" as const, label: t("combatUi.attack") },
    { key: "spell" as const, label: t("combatUi.castSpell") },
    { key: "standard" as const, label: t("combatUi.standardActions") },
    { key: "object" as const, label: t("combatUi.useObject") },
  ];
  const dragonbornDamageLabel = localizeDamageType(
    dragonbornBreathWeaponAction?.damageType ?? null,
    locale,
  );

  return (
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
              {selectedSpell && !canSpendSpellActionCost ? (
                <p className="mt-2 text-xs text-rose-200">
                  {t("combatUi.spellActionUnavailable")}
                </p>
              ) : null}
            </div>
            <button
              type="button"
              disabled={!canAct || !canSpendSpellActionCost || !targetId || !selectedSpell}
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
                    {spell.name}
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
        </article>
      ) : null}

      {activeActionPanel === "standard" ? (
        <article className="min-w-0 rounded-3xl border border-white/8 bg-white/4 p-5">
          <h3 className="text-lg font-semibold text-white">{t("combatUi.standardActions")}</h3>
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
  );
};
