import { useState } from "react";
import { useCharacterSheet } from "../hooks/useCharacterSheet";
import type { CharacterSheetMode } from "../model/characterSheet.types";
import { CharacterHeader } from "./CharacterHeader";
import { CharacterInfo } from "./CharacterInfo";
import { AbilityScores } from "./AbilityScores";
import { SavingThrows } from "./SavingThrows";
import { Skills } from "./Skills";
import { CombatStats } from "./CombatStats";
import { HitPoints } from "./HitPoints";
import { HitDiceSection } from "./HitDiceSection";
import { Weapons } from "./Weapons";
import { Equipment } from "./Equipment";
import { Currency } from "./Currency";
import { Spellcasting } from "./Spellcasting";
import { Proficiencies } from "./Proficiencies";
import { Conditions } from "./Conditions";
import { FeaturesTraits } from "./FeaturesTraits";
import { CharacterSheetCreationConfirmDialog } from "./CharacterSheetCreationConfirmDialog";
import { CharacterSheetStateScreen } from "./CharacterSheetStateScreen";
import { CharacterSheetStatusBanners } from "./CharacterSheetStatusBanners";
import { validateCreationSheet } from "../utils/creationValidation";
import { useLocale } from "../../../shared/hooks/useLocale";
import { useCharacterSheetDerived } from "../hooks/useCharacterSheetDerived";

type Props = {
  partyId?: string | null;
  campaignId?: string | null;
  mode?: CharacterSheetMode;
  playPlayerUserId?: string | null;
  canEditPlay?: boolean;
  backHref?: string | null;
  backLabel?: string | null;
  playContextLabel?: string | null;
};

export const CharacterSheet = ({
  partyId,
  campaignId = null,
  mode = "play",
  playPlayerUserId = null,
  canEditPlay = false,
  backHref = null,
  backLabel = null,
  playContextLabel = null,
}: Props) => {
  const actions = useCharacterSheet(partyId, mode, { playPlayerUserId, canEditPlay, campaignId });
  const { sheet } = actions;
  const { t } = useLocale();
  const isCreation = mode === "creation";
  const isPlay = mode === "play";
  const isRuntimeReadOnly = isPlay && !canEditPlay;
  const isPlayReadOnly = isPlay;

  // Sheet is locked for players after the first save; only GM can edit afterwards
  const isSheetLocked = isCreation && !!actions.remoteId && !canEditPlay;

  const [showConfirm, setShowConfirm] = useState(false);
  const creationValidation = isCreation ? validateCreationSheet(sheet) : null;
  const saveBlockedReason = creationValidation && !creationValidation.isValid
    ? t("sheet.creation.saveBlocked")
    : null;

  const handleSave = () => {
    if (saveBlockedReason) return;
    // First-time creation save: require explicit confirmation
    if (isCreation && !actions.remoteId) {
      setShowConfirm(true);
      return;
    }
    void actions.save();
  };

  const {
    ac,
    acBreakdown,
    hpColor,
    hpPercent,
    hpTextColor,
    initiative,
    passivePerception,
    profBonus,
    spellAttack,
    spellSaveDC,
  } = useCharacterSheetDerived(sheet);

  if (actions.loading) {
    return <CharacterSheetStateScreen />;
  }

  if (actions.loadError) {
    return <CharacterSheetStateScreen error={actions.loadError} />;
  }

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-[radial-gradient(circle_at_top,rgba(56,189,248,0.08),transparent_24%),radial-gradient(circle_at_85%_15%,rgba(34,197,94,0.08),transparent_18%),linear-gradient(180deg,#020617_0%,#020617_45%,#030712_100%)] text-slate-100">
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(180deg,rgba(255,255,255,0.02),transparent_22%)]" />
      <CharacterHeader
        sheet={sheet}
        mode={mode}
        canSave={(isCreation && !isSheetLocked) || canEditPlay}
        showResetImport={isCreation && !isSheetLocked}
        ac={ac}
        initiative={initiative}
        profBonus={profBonus}
        passivePerception={passivePerception}
        spellSaveDC={spellSaveDC}
        spellAttack={spellAttack}
        hpTextColor={hpTextColor}
        partyId={partyId}
        backHref={backHref}
        backLabel={backLabel}
        isDirty={actions.isDirty}
        saving={actions.saving}
        saveError={actions.saveError}
        saveDisabledReason={saveBlockedReason}
        missingRequiredFields={creationValidation?.missingRequiredFields ?? []}
        onSave={handleSave}
        importRef={actions.importRef}
        importError={actions.importError}
        onExport={actions.handleExport}
        onImport={actions.handleImport}
        onReset={actions.resetSheet}
      />

      <CharacterSheetCreationConfirmDialog
        open={showConfirm}
        disabled={!!saveBlockedReason}
        onCancel={() => setShowConfirm(false)}
        onConfirm={() => {
          if (!saveBlockedReason) {
            setShowConfirm(false);
            void actions.save();
          }
        }}
      />

      <div className="relative mx-auto max-w-[88rem] space-y-3 px-4 py-8 lg:px-6">
        <CharacterSheetStatusBanners
          isPlay={isPlay}
          isSheetLocked={isSheetLocked}
          playContextLabel={playContextLabel}
        />

        <CharacterInfo
          sheet={sheet}
          mode={mode}
          readOnly={isPlayReadOnly || isSheetLocked}
          missingRequiredFields={creationValidation?.missingRequiredFields ?? []}
          set={actions.set}
          selectClass={actions.selectClass}
          selectSubclass={actions.selectSubclass}
          canRequestLevelUp={isPlay && !canEditPlay && !!partyId}
          requestingLevelUp={actions.requestingLevelUp}
          requestLevelUpError={actions.requestLevelUpError}
          onRequestLevelUp={actions.requestLevelUp}
          selectBackground={actions.selectBackground}
          selectRace={actions.selectRace}
          selectClassEquipment={actions.selectClassEquipment}
          pickClassSkill={actions.pickClassSkill}
          pickClassToolProficiency={actions.pickClassToolProficiency}
          selectLanguageChoice={actions.selectLanguageChoice}
        />

        <div className="grid gap-3 xl:grid-cols-12 xl:items-start">
          <div className="space-y-3 xl:col-span-8">
            <div className="grid gap-3 lg:grid-cols-[minmax(0,1.55fr)_minmax(0,0.95fr)] lg:items-start">
              <AbilityScores
                abilities={sheet.abilities}
                race={sheet.race}
                mode={mode}
                readOnly={isPlayReadOnly || isSheetLocked}
                setAbility={actions.setAbility}
              />
              <SavingThrows
                abilities={sheet.abilities}
                savingThrowProficiencies={sheet.savingThrowProficiencies}
                level={sheet.level}
                onToggle={actions.toggleSaveProf}
                readOnly={isCreation || isPlayReadOnly || isSheetLocked}
              />
            </div>
            <div className="grid gap-3 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)] lg:items-start">
              <CombatStats
                sheet={sheet}
                ac={ac}
                initiative={initiative}
                acBreakdown={acBreakdown}
                set={actions.set}
                selectArmor={actions.selectArmor}
                toggleShield={actions.toggleShield}
                readOnly={isCreation || isPlayReadOnly || isSheetLocked}
              />
              <div className="space-y-3">
                <HitPoints
                  sheet={sheet}
                  hpPercent={hpPercent}
                  hpColor={hpColor}
                  readOnly={isRuntimeReadOnly || isSheetLocked}
                  setCurrentHP={actions.setCurrentHP}
                  setMaxHP={actions.setMaxHP}
                  adjustHP={actions.adjustHP}
                  set={actions.set}
                  mode={mode}
                />
                <HitDiceSection
                  sheet={sheet}
                  set={actions.set}
                  useHitDie={actions.useHitDie}
                  longRest={actions.longRest}
                  setDeathSave={actions.setDeathSave}
                  mode={mode}
                  readOnly={isRuntimeReadOnly || isSheetLocked}
                />
              </div>
            </div>
            {isCreation && (
              <div className="grid gap-3 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)] lg:items-start">
                <Proficiencies
                  languages={sheet.languages}
                  toolProficiencies={sheet.toolProficiencies}
                  weaponProficiencies={sheet.weaponProficiencies}
                  armorProficiencies={sheet.armorProficiencies}
                  onAddTag={actions.addTag}
                  onRemoveTag={actions.removeTag}
                  readOnly
                />
                <Spellcasting
                  campaignId={campaignId}
                  className={sheet.class}
                  spellcasting={sheet.spellcasting}
                  abilities={sheet.abilities}
                  level={sheet.level}
                  readOnly
                  missingRequiredFields={creationValidation?.missingRequiredFields ?? []}
                  onEnable={actions.enableSpellcasting}
                  onDisable={actions.disableSpellcasting}
                  onSetAbility={actions.setSpellAbility}
                  onSetSlot={actions.setSpellSlot}
                  onAddSpell={actions.addSpell}
                  onRemoveSpell={actions.removeSpell}
                  onUpdateSpell={actions.updateSpell}
                  onToggleCreationSpell={actions.toggleCreationSpellSelection}
                />
              </div>
            )}
          </div>
          <div className="space-y-3 xl:col-span-4">
              <Skills
                abilities={sheet.abilities}
                skillProficiencies={sheet.skillProficiencies}
                level={sheet.level}
                onCycleProf={actions.cycleSkillProf}
                readOnly={isCreation || isPlayReadOnly || isSheetLocked}
              />
            {isCreation && (
              <Equipment
                inventory={sheet.inventory}
                currency={sheet.currency}
                onAdd={actions.addItem}
                onRemove={actions.removeItem}
                onUpdate={actions.updateItem}
                readOnly={true}
              />
            )}
          </div>
        </div>

        {!isCreation && (
          <Weapons
            weapons={sheet.weapons}
            abilities={sheet.abilities}
            level={sheet.level}
            readOnly={isPlayReadOnly}
            onAdd={actions.addWeapon}
            onRemove={actions.removeWeapon}
            onUpdate={actions.updateWeapon}
          />
        )}

        {!isCreation && (
          <div className="grid gap-3 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <Equipment
                inventory={sheet.inventory}
                currency={sheet.currency}
                onAdd={actions.addItem}
                onRemove={actions.removeItem}
                onUpdate={actions.updateItem}
                readOnly={isPlayReadOnly || isSheetLocked}
              />
            </div>
            <Currency
              currency={sheet.currency}
              setCurrency={actions.setCurrency}
              readOnly={isPlayReadOnly || isSheetLocked}
            />
          </div>
        )}

        {!isCreation && (
          <>
            <Spellcasting
              campaignId={campaignId}
              className={sheet.class}
              spellcasting={sheet.spellcasting}
              abilities={sheet.abilities}
              level={sheet.level}
              readOnly={isPlayReadOnly}
              onEnable={actions.enableSpellcasting}
              onDisable={actions.disableSpellcasting}
              onSetAbility={actions.setSpellAbility}
              onSetSlot={actions.setSpellSlot}
              onAddSpell={actions.addSpell}
              onRemoveSpell={actions.removeSpell}
              onUpdateSpell={actions.updateSpell}
              onToggleCreationSpell={actions.toggleCreationSpellSelection}
            />

            <Proficiencies
              languages={sheet.languages}
              toolProficiencies={sheet.toolProficiencies}
              weaponProficiencies={sheet.weaponProficiencies}
              armorProficiencies={sheet.armorProficiencies}
              onAddTag={actions.addTag}
              onRemoveTag={actions.removeTag}
              readOnly={isPlayReadOnly || isSheetLocked}
            />
          </>
        )}

        {!isCreation && (
          <Conditions
            conditions={sheet.conditions}
            onToggle={actions.toggleCondition}
            readOnly={isRuntimeReadOnly || isSheetLocked}
          />
        )}

        <FeaturesTraits
          featuresAndTraits={sheet.featuresAndTraits}
          notes={sheet.notes}
          set={actions.set}
          readOnly={isPlayReadOnly || isSheetLocked}
        />
      </div>
    </div>
  );
};
