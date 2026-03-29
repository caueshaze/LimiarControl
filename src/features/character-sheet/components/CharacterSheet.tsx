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
import { Equipment } from "./Equipment";
import { Currency } from "./Currency";
import { Spellcasting } from "./Spellcasting";
import { Proficiencies } from "./Proficiencies";
import { Conditions } from "./Conditions";
import { FeaturesTraits } from "./FeaturesTraits";
import { CharacterSheetCreationConfirmDialog } from "./CharacterSheetCreationConfirmDialog";
import { CharacterSheetInventoryResetConfirmDialog } from "./CharacterSheetInventoryResetConfirmDialog";
import { CharacterSheetStateScreen } from "./CharacterSheetStateScreen";
import { CharacterSheetStatusBanners } from "./CharacterSheetStatusBanners";
import { validateCreationSheet } from "../utils/creationValidation";
import { hasCustomCreationInventoryItems } from "../utils/creationEquipment";
import {
  getDraftArmorProficiencyOptions,
  getDraftToolProficiencyOptions,
  getDraftWeaponProficiencyOptions,
} from "../utils/proficiencyCatalog";
import { useLocale } from "../../../shared/hooks/useLocale";
import { useCharacterSheetDerived } from "../hooks/useCharacterSheetDerived";

type Props = {
  partyId?: string | null;
  campaignId?: string | null;
  mode?: CharacterSheetMode;
  playPlayerUserId?: string | null;
  creationPlayerUserId?: string | null;
  creationDraftId?: string | null;
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
  creationPlayerUserId = null,
  creationDraftId = null,
  canEditPlay = false,
  backHref = null,
  backLabel = null,
  playContextLabel = null,
}: Props) => {
  const actions = useCharacterSheet(partyId, mode, {
    playPlayerUserId,
    creationPlayerUserId,
    creationDraftId,
    canEditPlay,
    campaignId,
  });
  const { sheet } = actions;
  const { t } = useLocale();
  const isCreation = mode === "creation";
  const isPlay = mode === "play";
  const isGmPlayView = isPlay && canEditPlay;
  const isRuntimeReadOnly = isPlay && !canEditPlay;
  const isPlayReadOnly = isPlay;
  const isDraftEditor = isCreation && !!creationDraftId;
  const isOwnCreationSheet = isCreation && !creationPlayerUserId && !creationDraftId;
  const isPendingAcceptance =
    isOwnCreationSheet &&
    !!actions.characterRecord?.sourceDraftId &&
    !actions.characterRecord?.acceptedAt;
  const canEditExistingCreation =
    isDraftEditor
      ? actions.draftRecord?.status === "active"
      : isOwnCreationSheet
        ? !actions.characterRecord || actions.characterRecord.acceptedAt == null
        : false;
  const isSheetLocked = isCreation && !!actions.remoteId && !canEditExistingCreation;
  const canSaveCreation = isCreation && (!actions.remoteId || canEditExistingCreation);
  const isDraftArchived = isDraftEditor && actions.draftRecord?.status === "archived";
  const isEditableCreationDraft = isDraftEditor && !isSheetLocked;
  const showAcceptPendingSheetAction = isPendingAcceptance && isOwnCreationSheet;
  const canAcceptPendingSheet =
    showAcceptPendingSheetAction && !actions.isDirty && !actions.saving;
  const shouldValidateCreationProgress =
    isCreation &&
    !creationDraftId &&
    !actions.characterRecord?.sourceDraftId;

  const [showConfirm, setShowConfirm] = useState(false);
  const [pendingInventoryResetChange, setPendingInventoryResetChange] = useState<{
    field: "class" | "background" | "race";
    value: string;
  } | null>(null);
  const creationValidation = shouldValidateCreationProgress ? validateCreationSheet(sheet) : null;
  const saveBlockedReason = creationValidation && !creationValidation.isValid
    ? t("sheet.creation.saveBlocked")
    : null;
  const shouldConfirmInventoryReset = isCreation && hasCustomCreationInventoryItems(sheet.inventory);
  const draftProficiencyCatalogOptions = isEditableCreationDraft
    ? {
        toolProficiencies: getDraftToolProficiencyOptions(),
        weaponProficiencies: getDraftWeaponProficiencyOptions(),
        armorProficiencies: getDraftArmorProficiencyOptions(),
      }
    : undefined;

  const requestCreationIdentityChange = (
    field: "class" | "background" | "race",
    currentValue: string,
    nextValue: string,
  ) => {
    if (nextValue === currentValue) {
      return;
    }

    if (!shouldConfirmInventoryReset) {
      if (field === "class") {
        actions.selectClass(nextValue);
        return;
      }
      if (field === "background") {
        actions.selectBackground(nextValue);
        return;
      }
      actions.selectRace(nextValue);
      return;
    }

    setPendingInventoryResetChange({ field, value: nextValue });
  };

  const applyPendingInventoryResetChange = () => {
    if (!pendingInventoryResetChange) {
      return;
    }

    if (pendingInventoryResetChange.field === "class") {
      actions.selectClass(pendingInventoryResetChange.value);
    } else if (pendingInventoryResetChange.field === "background") {
      actions.selectBackground(pendingInventoryResetChange.value);
    } else {
      actions.selectRace(pendingInventoryResetChange.value, { resetInventory: true });
    }

    setPendingInventoryResetChange(null);
  };

  const pendingInventoryResetFieldLabel =
    pendingInventoryResetChange?.field === "class"
      ? t("sheet.basicInfo.class")
      : pendingInventoryResetChange?.field === "background"
        ? t("sheet.basicInfo.background")
        : pendingInventoryResetChange?.field === "race"
          ? t("sheet.basicInfo.race")
          : "";

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
        canSave={canSaveCreation || canEditPlay}
        showResetImport={isCreation && (!actions.remoteId || canEditExistingCreation)}
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

      <CharacterSheetInventoryResetConfirmDialog
        open={!!pendingInventoryResetChange}
        fieldLabel={pendingInventoryResetFieldLabel}
        onCancel={() => setPendingInventoryResetChange(null)}
        onConfirm={applyPendingInventoryResetChange}
      />

      <div className="relative mx-auto max-w-352 space-y-3 px-4 py-8 lg:px-6">
        <CharacterSheetStatusBanners
          isPlay={isPlay}
          isSheetLocked={isSheetLocked}
          isDraftArchived={isDraftArchived}
          isPendingAcceptance={isPendingAcceptance}
          showAcceptPendingSheetAction={showAcceptPendingSheetAction}
          canAcceptPendingSheet={canAcceptPendingSheet}
          acceptingPendingSheet={actions.acceptingSheet}
          acceptPendingSheetError={actions.acceptSheetError}
          onAcceptPendingSheet={() => void actions.acceptPendingSheet()}
          playContextLabel={playContextLabel}
        />

        <CharacterInfo
          sheet={sheet}
          mode={mode}
          readOnly={isPlayReadOnly || isSheetLocked}
          allowLevelEditing={isEditableCreationDraft}
          missingRequiredFields={creationValidation?.missingRequiredFields ?? []}
          set={actions.set}
          selectClass={(value) => requestCreationIdentityChange("class", sheet.class, value)}
          selectSubclass={actions.selectSubclass}
          canRequestLevelUp={isPlay && !canEditPlay && !!partyId}
          requestingLevelUp={actions.requestingLevelUp}
          requestLevelUpError={actions.requestLevelUpError}
          onRequestLevelUp={actions.requestLevelUp}
          showProgressPanel={!isGmPlayView}
          selectBackground={(value) => requestCreationIdentityChange("background", sheet.background, value)}
          selectRace={(value) => requestCreationIdentityChange("race", sheet.race, value)}
          selectClassEquipment={actions.selectClassEquipment}
          pickClassSkill={actions.pickClassSkill}
          pickExpertise={actions.pickExpertise}
          pickRaceToolProficiency={actions.pickRaceToolProficiency}
          pickClassToolProficiency={actions.pickClassToolProficiency}
          selectLanguageChoice={actions.selectLanguageChoice}
          selectRaceConfig={actions.selectRaceConfig}
          selectSubclassConfig={actions.selectSubclassConfig}
        />

        <div className="grid gap-3 xl:grid-cols-12 xl:items-start">
          <div className="space-y-3 xl:col-span-8">
            <div className="grid gap-3 lg:grid-cols-[minmax(0,1.55fr)_minmax(0,0.95fr)] lg:items-start">
              <AbilityScores
                className={sheet.class}
                abilities={sheet.abilities}
                race={sheet.race}
                raceConfig={sheet.raceConfig}
                level={sheet.level}
                mode={mode}
                readOnly={isPlayReadOnly || isSheetLocked}
                allowFreeformCreationEditing={isEditableCreationDraft}
                setAbility={actions.setAbility}
              />
              <SavingThrows
                abilities={sheet.abilities}
                savingThrowProficiencies={sheet.savingThrowProficiencies}
                level={sheet.level}
                onToggle={actions.toggleSaveProf}
                readOnly={isCreation ? !isEditableCreationDraft : isPlayReadOnly || isSheetLocked}
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
                inventoryBackedArmorSelection={isCreation}
                readOnly={isCreation ? !isEditableCreationDraft : isPlayReadOnly || isSheetLocked}
              />
              <div className="space-y-3">
                {!isGmPlayView ? (
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
                ) : null}
                <HitDiceSection
                  sheet={sheet}
                  set={actions.set}
                  useHitDie={actions.useHitDie}
                  longRest={actions.longRest}
                  setDeathSave={actions.setDeathSave}
                  mode={mode}
                  showRestActions={!isPlay}
                  readOnly={isRuntimeReadOnly || isSheetLocked}
                />
              </div>
            </div>
            {isCreation && (
              <>
                <div className="grid gap-3 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)] lg:items-start">
                  <Proficiencies
                    languages={sheet.languages}
                    toolProficiencies={sheet.toolProficiencies}
                    weaponProficiencies={sheet.weaponProficiencies}
                    armorProficiencies={sheet.armorProficiencies}
                    onAddTag={actions.addTag}
                    onRemoveTag={actions.removeTag}
                    readOnly={!isEditableCreationDraft}
                    catalogOptions={draftProficiencyCatalogOptions}
                  />
                  <Spellcasting
                    campaignId={campaignId}
                    className={sheet.class}
                    spellcasting={sheet.spellcasting}
                    abilities={sheet.abilities}
                    level={sheet.level}
                    readOnly={!isEditableCreationDraft}
                    missingRequiredFields={creationValidation?.missingRequiredFields ?? []}
                    onEnable={actions.enableSpellcasting}
                    onDisable={actions.disableSpellcasting}
                    onSetAbility={actions.setSpellAbility}
                    onSetSlot={actions.setSpellSlot}
                    onAddSpell={actions.addSpell}
                    onSelectCatalogSpell={actions.selectCatalogSpell}
                    onRemoveSpell={actions.removeSpell}
                    onUpdateSpell={actions.updateSpell}
                    onToggleCreationSpell={actions.toggleCreationSpellSelection}
                    catalogBackedSelection={isEditableCreationDraft}
                  />
                </div>
                <div className="space-y-3">
                  <Equipment
                    inventory={sheet.inventory}
                    currency={sheet.currency}
                    onAdd={actions.addItem}
                    onRemove={actions.removeItem}
                    onUpdate={actions.updateItem}
                    onSelectCatalogItem={actions.selectInventoryCatalogItem}
                    creationCatalogBacked
                    readOnly={!isEditableCreationDraft}
                  />
                  {isEditableCreationDraft ? (
                    <Currency
                      currency={sheet.currency}
                      setCurrency={actions.setCurrency}
                      readOnly={false}
                    />
                  ) : null}
                </div>
              </>
            )}
          </div>
          <div className="space-y-3 xl:col-span-4">
              <Skills
                abilities={sheet.abilities}
                skillProficiencies={sheet.skillProficiencies}
                level={sheet.level}
                onCycleProf={actions.cycleSkillProf}
                readOnly={isCreation ? !isEditableCreationDraft : isPlayReadOnly || isSheetLocked}
              />
          </div>
        </div>

        {!isCreation && (
          <div className="grid gap-3 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <Equipment
                inventory={sheet.inventory}
                currency={sheet.currency}
                onAdd={actions.addItem}
                onRemove={actions.removeItem}
                onUpdate={actions.updateItem}
                onSelectCatalogItem={actions.selectInventoryCatalogItem}
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
              onSelectCatalogSpell={actions.selectCatalogSpell}
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
          classFeatures={sheet.classFeatures}
          featuresAndTraits={sheet.featuresAndTraits}
          notes={sheet.notes}
          set={actions.set}
          readOnly={isPlayReadOnly || isSheetLocked}
        />
      </div>
    </div>
  );
};
