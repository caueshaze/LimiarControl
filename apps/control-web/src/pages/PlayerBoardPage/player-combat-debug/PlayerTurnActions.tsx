import { useState } from "react";
import type { AbilityName } from "../../../entities/roll/rollResolution.types";
import type { DragonbornBreathWeaponAction } from "../../../features/combat-ui/player/dragonbornBreathWeapon";
import {
  isCombatSpellActionCostAvailable,
  resolveCombatSpellActionCost,
  spellModeNeedsDamageType,
  spellModeNeedsEffectInputs,
  spellModeNeedsSaveAbility,
} from "../../../features/combat-ui/spellAutomation";
import { getAbilityLabel } from "../../../features/character-sheet/utils/abilityLabels";
import type { CombatSpellMode, StandardActionType } from "../../../shared/api/combatRepo";
import type { CombatParticipant } from "../../../shared/api/combatRepo";
import { useLocale } from "../../../shared/hooks/useLocale";
import { localizeDamageType } from "../../../shared/i18n/domainLabels";
import type { PlayerBoardWeaponSummary } from "../playerBoard.types";
import type { CombatSpellOption } from "./types";

const STD_BTN = "rounded border px-3 py-2 text-xs font-bold disabled:opacity-40 disabled:cursor-not-allowed";

const StandardActionButtons = ({
  actionUsed,
  dragonbornBreathWeaponAction,
  loading,
  participants,
  myParticipantId,
  onStandardAction,
  targetParticipantId,
}: {
  actionUsed: boolean;
  dragonbornBreathWeaponAction: DragonbornBreathWeaponAction | null;
  loading: boolean;
  participants: CombatParticipant[];
  myParticipantId: string;
  onStandardAction: (action: StandardActionType, targetParticipantId?: string, description?: string) => void;
  targetParticipantId?: string | null;
}) => {
  const { locale, t } = useLocale();
  const [helpTarget, setHelpTarget] = useState("");
  const [useObjectDesc, setUseObjectDesc] = useState("");
  const disabled = actionUsed || loading;
  const allies = participants.filter((p) => p.id !== myParticipantId);
  const dragonbornDamageLabel = localizeDamageType(
    dragonbornBreathWeaponAction?.damageType ?? null,
    locale,
  );

  return (
    <div className="space-y-2">
      {dragonbornBreathWeaponAction ? (
        <div className="rounded border border-emerald-500/40 bg-emerald-500/10 p-3">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-widest text-emerald-200">
                {t("combatUi.dragonbornBreathWeapon")}
                {dragonbornDamageLabel ? ` (${dragonbornDamageLabel})` : ""}
              </p>
              <p className="mt-1 text-xs text-slate-200">
                {dragonbornBreathWeaponAction.damageDice} · {t("combatUi.saveDcShort")}{" "}
                {dragonbornBreathWeaponAction.dc} ·{" "}
                {getAbilityLabel(dragonbornBreathWeaponAction.saveAbility, t)}
              </p>
              <p className="mt-1 text-[11px] text-slate-300">
                {t("combatUi.usesRemaining")}: {dragonbornBreathWeaponAction.usesRemaining}/
                {dragonbornBreathWeaponAction.usesMax}
              </p>
            </div>
            <button
              disabled={
                disabled
                || !targetParticipantId
                || dragonbornBreathWeaponAction.usesRemaining <= 0
              }
              onClick={() => onStandardAction("dragonborn_breath_weapon", targetParticipantId ?? undefined)}
              className={`${STD_BTN} border-emerald-500/40 text-emerald-200 hover:bg-emerald-500/10`}
            >
              {t("combatUi.useDragonbornBreathWeapon")}
            </button>
          </div>
        </div>
      ) : null}
      <div className="grid grid-cols-3 gap-2">
        <button
          disabled={disabled}
          onClick={() => onStandardAction("dodge")}
          className={`${STD_BTN} border-sky-500/40 text-sky-300 hover:bg-sky-500/10`}
        >
          {t("combatUi.dodge")}
        </button>
        <button
          disabled={disabled}
          onClick={() => onStandardAction("dash")}
          className={`${STD_BTN} border-slate-600 text-slate-300 hover:bg-slate-700`}
        >
          {t("combatUi.dash")}
        </button>
        <button
          disabled={disabled}
          onClick={() => onStandardAction("disengage")}
          className={`${STD_BTN} border-slate-600 text-slate-300 hover:bg-slate-700`}
        >
          {t("combatUi.disengage")}
        </button>
        <button
          disabled={disabled}
          onClick={() => onStandardAction("hide")}
          className={`${STD_BTN} border-violet-500/40 text-violet-300 hover:bg-violet-500/10`}
        >
          {t("combatUi.hide")}
        </button>
        <button
          disabled={disabled || !helpTarget}
          onClick={() => { onStandardAction("help", helpTarget); setHelpTarget(""); }}
          className={`${STD_BTN} border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/10`}
        >{t("combatUi.help")}</button>
        <button
          disabled={disabled}
          onClick={() => { onStandardAction("use_object", undefined, useObjectDesc || undefined); setUseObjectDesc(""); }}
          className={`${STD_BTN} border-amber-500/40 text-amber-300 hover:bg-amber-500/10`}
        >{t("combatUi.useObject")}</button>
      </div>

      {/* Help target selector */}
      {!actionUsed && allies.length > 0 && (
        <select
          value={helpTarget}
          onChange={(e) => setHelpTarget(e.target.value)}
          className="w-full rounded border border-slate-700 bg-slate-900 p-1.5 text-xs text-white"
        >
          <option value="">{t("combatUi.helpTargetPlaceholder")}</option>
          {allies.map((p) => (
            <option key={p.id} value={p.id}>{p.display_name}</option>
          ))}
        </select>
      )}

      {/* Use Object description */}
      {!actionUsed && (
        <input
          type="text"
          value={useObjectDesc}
          onChange={(e) => setUseObjectDesc(e.target.value)}
          placeholder={t("combatUi.objectDescriptionPlaceholder")}
          className="w-full rounded border border-slate-700 bg-slate-900 p-1.5 text-xs text-white"
        />
      )}
    </div>
  );
};

const DAMAGE_TYPE_OPTIONS = [
  "acid",
  "bludgeoning",
  "cold",
  "fire",
  "force",
  "lightning",
  "necrotic",
  "piercing",
  "poison",
  "psychic",
  "radiant",
  "slashing",
  "thunder",
];

const parseEffectBonus = (value: string) => {
  const parsed = Number.parseInt(value.trim(), 10);
  return Number.isFinite(parsed) ? parsed : 0;
};

type Props = {
  activeTab: "attack" | "cast";
  canRollDeathSave: boolean;
  currentWeapon: PlayerBoardWeaponSummary | null;
  deathSaveVisible: boolean;
  defeatedTargets: CombatParticipant[];
  dragonbornBreathWeaponAction: DragonbornBreathWeaponAction | null;
  isActive: boolean;
  isMyTurn: boolean;
  loading: boolean;
  livingTargets: CombatParticipant[];
  myParticipant: CombatParticipant | null;
  onAttack: () => void;
  onCast: () => void;
  onDeathSave: () => void;
  onEndTurn: () => void;
  onStandardAction: (action: StandardActionType, targetParticipantId?: string, description?: string) => void;
  selectedSpell: CombatSpellOption | null;
  selectedSpellId: string;
  setActiveTab: (value: "attack" | "cast") => void;
  setSelectedSpellId: (value: string) => void;
  setSpellDamageType: (value: string) => void;
  setSpellEffectBonus: (value: string) => void;
  setSpellEffectDice: (value: string) => void;
  setSpellMode: (value: CombatSpellMode) => void;
  setSpellSaveAbility: (value: AbilityName | "") => void;
  setTargetId: (value: string) => void;
  spellDamageType: string;
  spellEffectBonus: string;
  spellEffectDice: string;
  spellMode: CombatSpellMode;
  spellOptions: CombatSpellOption[];
  spellSaveAbility: AbilityName | "";
  targetId: string;
};

export const PlayerTurnActions = ({
  activeTab,
  canRollDeathSave,
  currentWeapon,
  deathSaveVisible,
  defeatedTargets,
  dragonbornBreathWeaponAction,
  isActive,
  isMyTurn,
  loading,
  livingTargets,
  myParticipant,
  onAttack,
  onCast,
  onDeathSave,
  onEndTurn,
  onStandardAction,
  selectedSpell,
  selectedSpellId,
  setActiveTab,
  setSelectedSpellId,
  setSpellDamageType,
  setSpellEffectBonus,
  setSpellEffectDice,
  setSpellMode,
  setSpellSaveAbility,
  setTargetId,
  spellDamageType,
  spellEffectBonus,
  spellEffectDice,
  spellMode,
  spellOptions,
  spellSaveAbility,
  targetId,
}: Props) => {
  const { t } = useLocale();
  const selectedSpellActionCost =
    selectedSpell?.actionCost ?? resolveCombatSpellActionCost("action");
  const canSpendSpellActionCost = isCombatSpellActionCostAvailable(
    selectedSpellActionCost,
    myParticipant?.turn_resources,
  );
  const spellActionCostLabel =
    selectedSpellActionCost === "bonus_action"
      ? t("combatUi.bonusAction")
      : selectedSpellActionCost === "reaction"
        ? t("combatUi.reaction")
        : t("combatUi.action");
  const canSubmitSpell =
    Boolean(targetId) &&
    Boolean(selectedSpell?.canonicalKey) &&
    canSpendSpellActionCost &&
    (!spellModeNeedsDamageType(spellMode) || Boolean(spellDamageType)) &&
    (!spellModeNeedsSaveAbility(spellMode) || Boolean(spellSaveAbility)) &&
    (!spellModeNeedsEffectInputs(spellMode)
      || spellEffectDice.trim().length > 0
      || parseEffectBonus(spellEffectBonus) > 0);

  if (deathSaveVisible) {
    return (
      <div className="mt-4 rounded border border-rose-500/40 bg-rose-950/40 p-4">
        <h4 className="text-sm font-bold uppercase tracking-widest text-rose-300">{t("combatUi.downedTitle")}</h4>
        <p className="mt-2 text-sm text-rose-100">
          {canRollDeathSave
            ? t("combatUi.downedYourTurn")
            : t("combatUi.downedWaiting")}
        </p>
        <button
          disabled={loading || !canRollDeathSave}
          onClick={onDeathSave}
          className="mt-4 w-full rounded bg-rose-600 px-4 py-4 text-lg font-bold uppercase tracking-widest text-white hover:bg-rose-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {t("combatUi.rollDeathSave")}
        </button>
      </div>
    );
  }

  if (!isMyTurn || !myParticipant) {
    return null;
  }

  return (
    <div className="mt-4 border-t border-sky-500/20 pt-4">
      <h4 className="mb-2 font-bold text-sky-300">{t("combatUi.turnActionsDebug")}</h4>

      {isActive ? (
        <>
          {(() => {
            const tr = myParticipant.turn_resources;
            if (!tr) return null;
            return (
              <div className="mb-3 flex gap-3 text-[10px] font-bold uppercase tracking-wider">
                <span className={tr.action_used ? "text-slate-600 line-through" : "text-emerald-400"}>
                  {t("combatUi.turnActionState")}
                </span>
                <span className={tr.bonus_action_used ? "text-slate-600 line-through" : "text-amber-400"}>
                  {t("combatUi.turnBonusState")}
                </span>
                <span className={tr.reaction_used ? "text-slate-600 line-through" : "text-sky-400"}>
                  {t("combatUi.turnReactionState")}
                </span>
              </div>
            );
          })()}

          <div className="mb-4 flex gap-2">
            <select
              className="flex-1 rounded border border-slate-700 bg-slate-900 p-2 text-white"
              value={targetId}
              onChange={(e) => setTargetId(e.target.value)}
            >
              <option value="">{t("combatUi.selectTarget")}</option>
              {livingTargets.length > 0 && (
                <optgroup label="Vivos / em combate">
                  {livingTargets.map((participant) => (
                    <option key={participant.id} value={participant.ref_id}>
                      {participant.display_name} [{participant.status}]
                    </option>
                  ))}
                </optgroup>
              )}
              {defeatedTargets.length > 0 && (
                <optgroup label="Mortos / derrotados">
                  {defeatedTargets.map((participant) => (
                    <option key={participant.id} value={participant.ref_id} disabled>
                      {participant.display_name} [{participant.status}]
                    </option>
                  ))}
                </optgroup>
              )}
            </select>
          </div>
          <p className="mb-4 text-xs text-slate-400">
            Alvos vivos aparecem primeiro. Mortos/derrotados continuam visíveis, mas ficam bloqueados.
          </p>

          <div className="mb-4 flex font-mono text-xs font-bold">
            <button
              onClick={() => setActiveTab("attack")}
              className={`flex-1 rounded-l border p-2 ${
                activeTab === "attack"
                  ? "border-amber-500 bg-amber-600 text-white"
                  : "border-slate-700 bg-slate-800 text-slate-400"
              }`}
            >
              {t("combatUi.attack")}
            </button>
            <button
              onClick={() => setActiveTab("cast")}
              className={`flex-1 rounded-r border-b border-r border-t p-2 ${
                activeTab === "cast"
                  ? "border-fuchsia-500 bg-fuchsia-600 text-white"
                  : "border-slate-700 bg-slate-800 text-slate-400"
              }`}
            >
              {t("combatUi.castSpell")}
            </button>
          </div>

          {activeTab === "attack" && (
            <div className="space-y-3">
              <div className="rounded border border-amber-500/20 bg-amber-500/10 p-3">
                <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-amber-200">
                  Ataque atual
                </p>
                <p className="mt-2 text-base font-semibold text-white">
                  {currentWeapon?.name ?? t("combatUi.unarmedStrikeName")}
                </p>
                <p className="mt-1 text-xs text-slate-300">
                  Bônus de ataque: {currentWeapon ? `${currentWeapon.attackBonus >= 0 ? "+" : ""}${currentWeapon.attackBonus}` : "FOR + proficiência"}
                </p>
                <p className="mt-1 text-xs text-slate-400">
                  Dano: {currentWeapon?.damageLabel ?? "1 + modificador de Força"}
                </p>
              </div>

              <button
                disabled={loading || !targetId || !!myParticipant.turn_resources?.action_used}
                onClick={onAttack}
                className="w-full rounded bg-rose-600 px-4 py-3 font-bold text-white hover:bg-rose-500 disabled:opacity-50"
              >
                Rolar ataque
              </button>
            </div>
          )}

          {activeTab === "cast" && (
            <div className="space-y-3">
              <select
                className="w-full rounded border border-slate-700 bg-slate-900 p-2 text-white"
                value={selectedSpellId}
                onChange={(e) => setSelectedSpellId(e.target.value)}
              >
                <option value="">{t("combatUi.selectSpellPlaceholder")}</option>
                {spellOptions.map((spell) => (
                  <option key={spell.id} value={spell.id}>
                    {spell.name} {spell.level > 0 ? `(Lv ${spell.level})` : "(Cantrip)"}
                  </option>
                ))}
              </select>

              {selectedSpell ? (
                <div className="rounded border border-fuchsia-500/20 bg-fuchsia-500/10 p-3">
                  <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-fuchsia-200">
                    Magia atual
                  </p>
                  <p className="mt-2 text-base font-semibold text-white">{selectedSpell.name}</p>
                  <p className="mt-1 text-xs text-slate-300">
                    Sugestao do catalogo: {selectedSpell.suggestedMode?.replace(/_/g, " ") ?? "nenhuma"}
                  </p>
                  <p className="mt-1 text-xs text-slate-300">
                    {t("combatUi.actionCost")}: {spellActionCostLabel}
                  </p>
                  <p className="mt-1 text-xs text-slate-400">
                    Tipo de dano: {selectedSpell.damageType ?? "nao estruturado"} · Save: {selectedSpell.savingThrow ?? "nao estruturado"}
                  </p>
                  {!canSpendSpellActionCost ? (
                    <p className="mt-1 text-xs text-rose-200">
                      Esse custo de ação já foi gasto neste turno.
                    </p>
                  ) : null}
                </div>
              ) : null}

              <select
                className="w-full rounded border border-slate-700 bg-slate-900 p-2 text-white"
                value={spellMode}
                onChange={(e) => setSpellMode(e.target.value as CombatSpellMode)}
              >
                <option value="spell_attack">{t("combatUi.spellMode.spell_attack")}</option>
                <option value="saving_throw">{t("combatUi.spellMode.saving_throw")}</option>
                <option value="direct_damage">{t("combatUi.spellMode.direct_damage")}</option>
                <option value="heal">{t("combatUi.spellMode.heal")}</option>
                <option value="utility">{t("combatUi.spellMode.utility")}</option>
              </select>

              {spellMode === "direct_damage" ? (
                <p className="text-[11px] text-amber-200">
                  Use apenas para magias desta fase que causam dano direto sem attack roll nem saving throw.
                </p>
              ) : null}

              {spellModeNeedsEffectInputs(spellMode) ? (
                <>
                  <input
                    type="text"
                    value={spellEffectDice}
                    onChange={(e) => setSpellEffectDice(e.target.value)}
                    placeholder={
                      spellMode === "heal"
                        ? t("combatUi.healDicePlaceholder")
                        : t("combatUi.damageDicePlaceholder")
                    }
                    className="w-full rounded border border-slate-700 bg-slate-900 p-2 font-mono text-white"
                  />

                  <input
                    type="number"
                    value={spellEffectBonus}
                    onChange={(e) => setSpellEffectBonus(e.target.value)}
                    placeholder={t("combatUi.bonusPlaceholder")}
                    className="w-full rounded border border-slate-700 bg-slate-900 p-2 font-mono text-white"
                  />
                </>
              ) : null}

              {spellModeNeedsDamageType(spellMode) ? (
                <select
                  value={spellDamageType}
                  onChange={(e) => setSpellDamageType(e.target.value)}
                  className="w-full rounded border border-slate-700 bg-slate-900 p-2 text-white"
                >
                  <option value="">{t("combatUi.damageTypePlaceholder")}</option>
                  {DAMAGE_TYPE_OPTIONS.map((damageType) => (
                    <option key={damageType} value={damageType}>
                      {damageType}
                    </option>
                  ))}
                </select>
              ) : null}

              {spellModeNeedsSaveAbility(spellMode) ? (
                <select
                  value={spellSaveAbility}
                  onChange={(e) => setSpellSaveAbility(e.target.value as AbilityName | "")}
                  className="w-full rounded border border-slate-700 bg-slate-900 p-2 text-white"
                >
                  <option value="">{t("combatUi.saveAbilityPlaceholder")}</option>
                  <option value="strength">{getAbilityLabel("strength", t)}</option>
                  <option value="dexterity">{getAbilityLabel("dexterity", t)}</option>
                  <option value="constitution">{getAbilityLabel("constitution", t)}</option>
                  <option value="intelligence">{getAbilityLabel("intelligence", t)}</option>
                  <option value="wisdom">{getAbilityLabel("wisdom", t)}</option>
                  <option value="charisma">{getAbilityLabel("charisma", t)}</option>
                </select>
              ) : null}

              <button
                disabled={loading || !canSubmitSpell}
                onClick={onCast}
                className="w-full rounded bg-fuchsia-600 px-4 py-3 font-bold text-white hover:bg-fuchsia-500 disabled:opacity-50"
              >
                {t("combatUi.castSpell")}
              </button>
            </div>
          )}

          {/* Standard Actions */}
          {(() => {
            const actionUsed = !!myParticipant.turn_resources?.action_used;
            return (
              <div className="mt-3 border-t border-slate-700/50 pt-3">
                <p className="mb-2 text-[10px] font-bold uppercase tracking-widest text-slate-500">{t("combatUi.standardActions")}</p>
                <StandardActionButtons
                  actionUsed={actionUsed}
                  dragonbornBreathWeaponAction={dragonbornBreathWeaponAction}
                  loading={loading}
                  participants={livingTargets}
                  myParticipantId={myParticipant.id}
                  onStandardAction={onStandardAction}
                  targetParticipantId={
                    [...livingTargets, ...defeatedTargets].find((participant) => participant.ref_id === targetId)?.id
                    ?? null
                  }
                />
              </div>
            );
          })()}

          <button
            disabled={loading}
            onClick={onEndTurn}
            className="mt-4 w-full rounded border border-sky-500/50 bg-transparent px-4 py-3 font-bold text-sky-400 hover:bg-sky-500/10 disabled:opacity-50"
          >
            {t("combatUi.endTurnLabel")}
          </button>
        </>
      ) : (
        <div className="rounded border border-slate-700 bg-slate-800 p-4 text-center text-slate-400">
          You cannot act right now due to your status: {myParticipant.status}.
        </div>
      )}
    </div>
  );
};
