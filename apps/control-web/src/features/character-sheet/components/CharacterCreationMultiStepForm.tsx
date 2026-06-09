import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { AbilityScores } from "./AbilityScores";
import { ClassExpertisePicker } from "./ClassExpertisePicker";
import { ClassSkillPicker } from "./ClassSkillPicker";
import { ClassToolProficiencyPicker } from "./ClassToolProficiencyPicker";
import { CombatStats } from "./CombatStats";
import { Currency } from "./Currency";
import { Equipment } from "./Equipment";
import { HitDiceSection } from "./HitDiceSection";
import { HitPoints } from "./HitPoints";
import { LanguageChoicePicker } from "./LanguageChoicePicker";
import { Proficiencies } from "./Proficiencies";
import { RaceConfigPicker } from "./RaceConfigPicker";
import { RacePreviewCard } from "./RacePreviewCard";
import { RaceToolProficiencyPicker } from "./RaceToolProficiencyPicker";
import { SavingThrows } from "./SavingThrows";
import { Section } from "./Section";
import { Skills } from "./Skills";
import { Spellcasting } from "./Spellcasting";
import { btnOutline, btnPrimary, fieldLabel, input } from "./styles";
import type { SheetActions } from "../hooks/useCharacterSheet";
import type { CharacterSheet } from "../model/characterSheet.types";
import { formatClassDisplayName, FIGHTING_STYLES, getClass, getSubclassConfigFields, hasFightingStyleAtCreation, isSubclassUnlocked } from "../data/classes";
import { getBackground } from "../data/backgrounds";
import { ALIGNMENTS } from "../data/alignments";
import { getRace, RACES } from "../data/races";
import { BACKGROUNDS } from "../data/backgrounds";
import { CLASSES } from "../data/classes";
import {
  DRACONIC_ANCESTRY_SUBCLASS_CONFIG_KEY,
  getDraconicLineageState,
  resolveElementalAffinityEligibility,
} from "../data/draconicAncestry";
import { getFixedFightingStyleForClassLevel, getFixedSubclassForClassLevel } from "../data/classFeatures";
import type { CreationValidationResult, RequiredField } from "../utils/creationValidation";
import { REQUIRED_FIELD_LABEL_KEY } from "../utils/creationFieldLabels";
import {
  canNavigateToStep,
  CREATION_STEP_ORDER,
  type CreationFlowContext,
  type CreationStepId,
  getNextCreationStepId,
  getPreviousCreationStepId,
  getStepMissingFields,
  getStepStatus,
  isStepComplete,
  parseCreationStepId,
  resolveReachableCreationStep,
} from "../utils/creationSteps";
import { canonicalizeStarterItemName } from "../utils/creationEquipment";
import { getAbilityLabel } from "../utils/abilityLabels";
import { safeParseInt, type PassiveSkillBonusSource } from "../utils/calculations";
import {
  composeCreationPersonalityFields,
  parseCreationPersonalityFields,
} from "../utils/creationPersonality";
import {
  hasBackgroundRandomOptions,
  rollBackgroundRandomOption,
  type CreationRandomizableField,
} from "../utils/creationBackgroundRandomizer";
import { useLocale } from "../../../shared/hooks/useLocale";
import type { LocaleKey } from "../../../shared/i18n";
import { navigateBackOrFallback } from "../../../shared/lib/navigation";
import { useAuth } from "../../auth";
import { AvatarUploadInput } from "./AvatarUploadInput";

type Props = {
  campaignId: string | null;
  sheet: CharacterSheet;
  actions: SheetActions;
  creationValidation: CreationValidationResult;
  creationContext: CreationFlowContext;
  isSheetLocked: boolean;
  isEditableCreationDraft: boolean;
  saveBlockedReason: string | null;
  draftProficiencyCatalogOptions?: Partial<
    Record<"toolProficiencies" | "weaponProficiencies" | "armorProficiencies", string[]>
  >;
  ac: number;
  acBreakdown: { label: string; value: number }[];
  effectiveSpeedMeters: number;
  hpColor: string;
  hpPercent: number;
  initiative: number;
  movementSpeedBonus: number;
  movementSpeedBonusSources: Array<{ label: string; value: number }>;
  passivePerceptionBonus: number;
  passivePerceptionBonusSources: PassiveSkillBonusSource[];
  spellAttack: number | null;
  spellSaveDC: number | null;
  backHref?: string | null;
  backLabel?: string | null;
  onSave: () => void;
  onSelectClass: (value: string) => void;
  onSelectBackground: (value: string) => void;
  onSelectRace: (value: string) => void;
};

type StepMeta = {
  titleKey: LocaleKey;
  descriptionKey: LocaleKey;
};

const STEP_META: Record<CreationStepId, StepMeta> = {
  identity: {
    titleKey: "sheet.creation.step.identity.title",
    descriptionKey: "sheet.creation.step.identity.description",
  },
  class: {
    titleKey: "sheet.creation.step.class.title",
    descriptionKey: "sheet.creation.step.class.description",
  },
  origin: {
    titleKey: "sheet.creation.step.origin.title",
    descriptionKey: "sheet.creation.step.origin.description",
  },
  abilities: {
    titleKey: "sheet.creation.step.abilities.title",
    descriptionKey: "sheet.creation.step.abilities.description",
  },
  loadout: {
    titleKey: "sheet.creation.step.loadout.title",
    descriptionKey: "sheet.creation.step.loadout.description",
  },
  review: {
    titleKey: "sheet.creation.step.review.title",
    descriptionKey: "sheet.creation.step.review.description",
  },
};

export const CharacterCreationMultiStepForm = ({
  campaignId,
  sheet,
  actions,
  creationValidation,
  creationContext,
  isSheetLocked,
  isEditableCreationDraft,
  saveBlockedReason,
  draftProficiencyCatalogOptions,
  ac,
  acBreakdown,
  effectiveSpeedMeters,
  hpColor,
  hpPercent,
  initiative,
  movementSpeedBonus,
  movementSpeedBonusSources,
  passivePerceptionBonus,
  passivePerceptionBonusSources,
  spellAttack,
  spellSaveDC,
  backHref = null,
  backLabel = null,
  onSave,
  onSelectClass,
  onSelectBackground,
  onSelectRace,
}: Props) => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { t } = useLocale();
  const { user } = useAuth();
  const initialStep = resolveReachableCreationStep(
    parseCreationStepId(searchParams.get("step")),
    creationValidation,
  );
  const [currentStepId, setCurrentStepId] = useState<CreationStepId>(initialStep);
  const lastRawRequestedStepRef = useRef<string | null | undefined>(undefined);

  useEffect(() => {
    const rawRequestedStep = searchParams.get("step");
    if (rawRequestedStep === lastRawRequestedStepRef.current) {
      return;
    }

    lastRawRequestedStepRef.current = rawRequestedStep;
    const requestedStep = parseCreationStepId(rawRequestedStep);
    const resolvedStep = resolveReachableCreationStep(requestedStep, creationValidation);
    setCurrentStepId(resolvedStep);

    if (requestedStep !== resolvedStep) {
      const nextParams = new URLSearchParams(searchParams);
      nextParams.set("step", resolvedStep);
      setSearchParams(nextParams, { replace: true });
    }
  }, [creationValidation, searchParams, setSearchParams]);

  useEffect(() => {
    if (creationContext !== "player-creation") {
      return;
    }
    if (sheet.playerName.trim().length > 0) {
      return;
    }
    const profileName = user?.displayName?.trim() || user?.username?.trim();
    if (!profileName) {
      return;
    }
    actions.set("playerName", profileName);
  }, [actions, creationContext, sheet.playerName, user?.displayName, user?.username]);

  const currentStepMissingFields = getStepMissingFields(creationValidation, currentStepId);
  const nextStepId = getNextCreationStepId(currentStepId);
  const previousStepId = getPreviousCreationStepId(currentStepId);
  const isReviewStep = currentStepId === "review";
  const isCurrentStepComplete = isStepComplete(creationValidation, currentStepId);
  const isNavigationLocked = isSheetLocked;
  const canAdvance = !isReviewStep && isCurrentStepComplete && nextStepId !== null;
  const canSubmit = creationContext === "gm-draft" || !saveBlockedReason;
  const isDraftMode = creationContext === "gm-draft";

  const pendingByStep = useMemo(
    () =>
      CREATION_STEP_ORDER.filter((stepId) => stepId !== "review").map((stepId) => ({
        stepId,
        missingFields: getStepMissingFields(creationValidation, stepId),
      })),
    [creationValidation],
  );

  const navigateToStep = (stepId: CreationStepId, replace = false) => {
    setCurrentStepId(stepId);
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set("step", stepId);
    setSearchParams(nextParams, { replace });
  };

  const handleStepClick = (stepId: CreationStepId) => {
    if (isNavigationLocked) {
      return;
    }
    if (
      !canNavigateToStep({
        targetStepId: stepId,
        currentStepId,
        validation: creationValidation,
        context: creationContext,
      })
    ) {
      return;
    }
    navigateToStep(stepId);
  };

  const handleNext = () => {
    if (isNavigationLocked || !canAdvance || !nextStepId) {
      return;
    }
    navigateToStep(nextStepId);
  };

  const handleBackToPreviousMenu = () => {
    if (backHref) {
      navigate(backHref);
      return;
    }
    navigateBackOrFallback(navigate, { fallbackTo: backHref });
  };

  const stepTitle = t(STEP_META[currentStepId].titleKey);
  const stepDescription = t(STEP_META[currentStepId].descriptionKey);

  return (
    <div className="space-y-4">
      <div className="rounded-[28px] border border-white/8 bg-[linear-gradient(180deg,rgba(8,15,34,0.92),rgba(2,6,23,0.98))] p-4 shadow-[0_22px_70px_rgba(2,6,23,0.35)]">
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <div className="flex flex-wrap gap-2">
              {CREATION_STEP_ORDER.map((stepId, index) => {
                const status = getStepStatus({
                  stepId,
                  currentStepId,
                  validation: creationValidation,
                  context: creationContext,
                });
                const statusClass =
                  status === "current"
                    ? "border-limiar-400/40 bg-limiar-500/18 text-limiar-100"
                    : status === "done"
                      ? "border-emerald-400/30 bg-emerald-500/10 text-emerald-100"
                      : status === "error"
                        ? "border-amber-400/30 bg-amber-500/10 text-amber-100"
                        : status === "available"
                          ? "border-white/12 bg-white/4 text-slate-200 hover:border-white/20"
                          : "cursor-not-allowed border-white/6 bg-white/[0.02] text-slate-600";
                return (
                  <button
                  key={stepId}
                  type="button"
                  disabled={status === "locked" || isNavigationLocked}
                  onClick={() => handleStepClick(stepId)}
                  className={`flex items-center gap-3 rounded-full border px-4 py-2 text-left text-xs font-semibold uppercase tracking-[0.18em] transition-all ${statusClass}`}
                >
                    <span className="inline-flex h-6 w-6 items-center justify-center rounded-full border border-current/20 text-[11px]">
                      {index + 1}
                    </span>
                    <span>{t(STEP_META[stepId].titleKey)}</span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="rounded-[24px] border border-white/8 bg-white/[0.03] p-4">
            <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-500">
              {t("sheet.creation.currentStep")}
            </p>
            <h2 className="mt-2 text-2xl font-semibold text-white">{stepTitle}</h2>
            <p className="mt-2 max-w-3xl text-sm leading-7 text-slate-300">{stepDescription}</p>
          </div>

          {currentStepMissingFields.length > 0 ? (
            <div className="rounded-[22px] border border-amber-500/25 bg-amber-950/20 p-4">
              <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-amber-300">
                {t("sheet.creation.stepIncomplete")}
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {currentStepMissingFields.map((field) => (
                  <span
                    key={`${currentStepId}-${field}`}
                    className="rounded-full border border-amber-400/20 bg-amber-400/10 px-3 py-1 text-[11px] font-semibold text-amber-100"
                  >
                    {t(REQUIRED_FIELD_LABEL_KEY[field])}
                  </span>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </div>

      {currentStepId === "identity" ? (
        <CreationIdentityStep
          sheet={sheet}
          readOnly={isSheetLocked}
          set={actions.set}
          selectBackground={onSelectBackground}
        />
      ) : null}

      {currentStepId === "class" ? (
        <CreationClassStep
          sheet={sheet}
          readOnly={isSheetLocked}
          allowLevelEditing={isEditableCreationDraft}
          missingRequiredFields={creationValidation.missingRequiredFields}
          set={actions.set}
          selectClass={onSelectClass}
          selectSubclass={actions.selectSubclass}
          selectSubclassConfig={actions.selectSubclassConfig}
        />
      ) : null}

      {currentStepId === "origin" ? (
        <CreationOriginStep
          sheet={sheet}
          readOnly={isSheetLocked}
          missingRequiredFields={creationValidation.missingRequiredFields}
          set={actions.set}
          selectBackground={onSelectBackground}
          selectRace={onSelectRace}
          pickRaceToolProficiency={actions.pickRaceToolProficiency}
          selectLanguageChoice={actions.selectLanguageChoice}
          selectRaceConfig={actions.selectRaceConfig}
        />
      ) : null}

      {currentStepId === "abilities" ? (
        <div className="grid gap-3 xl:grid-cols-12 xl:items-start">
          <div className="space-y-3 xl:col-span-8">
            <div className="grid gap-3 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)] lg:items-start">
              <AbilityScores
                className={sheet.class}
                abilities={sheet.abilities}
                race={sheet.race}
                raceConfig={sheet.raceConfig}
                level={sheet.level}
                mode="creation"
                readOnly={isSheetLocked}
                allowFreeformCreationEditing={isEditableCreationDraft}
                setAbility={actions.setAbility}
              />
              <SavingThrows
                abilities={sheet.abilities}
                savingThrowProficiencies={sheet.savingThrowProficiencies}
                level={sheet.level}
                onToggle={actions.toggleSaveProf}
                readOnly={!isEditableCreationDraft || isSheetLocked}
              />
            </div>
            <ClassSkillPicker
              sheet={sheet}
              pickClassSkill={actions.pickClassSkill}
              missingRequiredFields={creationValidation.missingRequiredFields}
            />
            <ClassExpertisePicker
              sheet={sheet}
              pickExpertise={actions.pickExpertise}
              missingRequiredFields={creationValidation.missingRequiredFields}
            />
            <ClassToolProficiencyPicker
              sheet={sheet}
              pickClassToolProficiency={actions.pickClassToolProficiency}
              missingRequiredFields={creationValidation.missingRequiredFields}
            />
            <Proficiencies
              languages={sheet.languages}
              toolProficiencies={sheet.toolProficiencies}
              weaponProficiencies={sheet.weaponProficiencies}
              armorProficiencies={sheet.armorProficiencies}
              onAddTag={actions.addTag}
              onRemoveTag={actions.removeTag}
              readOnly={!isEditableCreationDraft || isSheetLocked}
              catalogOptions={draftProficiencyCatalogOptions}
            />
          </div>

          <div className="space-y-3 xl:col-span-4">
            <Skills
              abilities={sheet.abilities}
              className={sheet.class}
              skillProficiencies={sheet.skillProficiencies}
              level={sheet.level}
              onCycleProf={actions.cycleSkillProf}
              readOnly={!isEditableCreationDraft || isSheetLocked}
              passivePerceptionBonus={passivePerceptionBonus}
              passivePerceptionBonusSources={passivePerceptionBonusSources}
            />
          </div>
        </div>
      ) : null}

      {currentStepId === "loadout" ? (
        <div className="space-y-3">
          <CombatStats
            sheet={sheet}
            ac={ac}
            initiative={initiative}
            acBreakdown={acBreakdown}
            effectiveSpeedMeters={effectiveSpeedMeters}
            movementSpeedBonus={movementSpeedBonus}
            movementSpeedBonusSources={movementSpeedBonusSources}
            set={actions.set}
            selectArmor={actions.selectArmor}
            toggleShield={actions.toggleShield}
            inventoryBackedArmorSelection
            readOnly={!isEditableCreationDraft || isSheetLocked}
          />
          <Equipment
            inventory={sheet.inventory}
            currency={sheet.currency}
            strengthScore={sheet.abilities.strength}
            onAdd={actions.addItem}
            onRemove={actions.removeItem}
            onUpdate={actions.updateItem}
            onSelectCatalogItem={actions.selectInventoryCatalogItem}
            creationCatalogBacked
            readOnly={!isEditableCreationDraft || isSheetLocked}
          />
          {isEditableCreationDraft ? (
            <Currency
              currency={sheet.currency}
              setCurrency={actions.setCurrency}
              readOnly={false}
            />
          ) : null}
          <Spellcasting
            campaignId={campaignId}
            className={sheet.class}
            spellcasting={sheet.spellcasting}
            abilities={sheet.abilities}
            level={sheet.level}
            readOnly={!isEditableCreationDraft || isSheetLocked}
            missingRequiredFields={creationValidation.missingRequiredFields}
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
      ) : null}

      {currentStepId === "review" ? (
        <CreationReviewStep
          sheet={sheet}
          pendingByStep={pendingByStep}
          onNavigateToStep={(stepId) => navigateToStep(stepId)}
          readOnly={isSheetLocked}
          set={actions.set}
          hpPercent={hpPercent}
          hpColor={hpColor}
          setCurrentHP={actions.setCurrentHP}
          setMaxHP={actions.setMaxHP}
          adjustHP={actions.adjustHP}
          useHitDie={actions.useHitDie}
          longRest={actions.longRest}
          setDeathSave={actions.setDeathSave}
          ac={ac}
          initiative={initiative}
          spellSaveDC={spellSaveDC}
          spellAttack={spellAttack}
        />
      ) : null}

      <div className="rounded-[28px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={handleBackToPreviousMenu}
              disabled={isNavigationLocked}
              className={`${btnOutline} disabled:cursor-not-allowed disabled:opacity-50`}
            >
              {backLabel ?? t("campaignHome.back")}
            </button>
            {previousStepId ? (
              <button
                type="button"
                onClick={() => navigateToStep(previousStepId)}
                disabled={isNavigationLocked}
                className={`${btnOutline} disabled:cursor-not-allowed disabled:opacity-50`}
              >
                {t("sheet.creation.previousStep")}
              </button>
            ) : null}
          </div>

          <div className="flex flex-wrap gap-2">
            {isDraftMode ? (
              <button
                type="button"
                onClick={onSave}
                disabled={actions.saving}
                className={`${btnOutline} disabled:cursor-not-allowed disabled:opacity-60`}
              >
                {actions.saving ? t("sheet.header.saving") : t("sheet.creation.saveDraft")}
              </button>
            ) : null}

            {!isReviewStep ? (
              <button
                type="button"
                onClick={handleNext}
                disabled={isNavigationLocked || !canAdvance}
                className={`${btnPrimary} disabled:cursor-not-allowed disabled:opacity-50`}
              >
                {t("sheet.creation.next")}
              </button>
            ) : (
              <button
                type="button"
                onClick={onSave}
                disabled={isNavigationLocked || actions.saving || !canSubmit}
                className={`${btnPrimary} disabled:cursor-not-allowed disabled:opacity-50`}
              >
                {actions.saving
                  ? t("sheet.header.saving")
                  : isDraftMode
                    ? t("sheet.creation.saveDraft")
                    : t("sheet.creation.confirm")}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

const CreationIdentityStep = ({
  sheet,
  readOnly,
  set,
  selectBackground,
}: {
  sheet: CharacterSheet;
  readOnly: boolean;
  set: SheetActions["set"];
  selectBackground: (value: string) => void;
}) => {
  const { t } = useLocale();
  const backgroundData = getBackground(sheet.background);
  const personalityFields = useMemo(
    () => parseCreationPersonalityFields(sheet.featuresAndTraits),
    [sheet.featuresAndTraits],
  );

  const setPersonalityField = (
    field: CreationRandomizableField,
    value: string,
  ) => {
    set(
      "featuresAndTraits",
      composeCreationPersonalityFields({
        ...personalityFields,
        [field]: value,
      }),
    );
  };

  const randomizePersonalityField = (field: CreationRandomizableField) => {
    const rolledValue = rollBackgroundRandomOption(sheet.background, field);
    if (!rolledValue) {
      return;
    }
    setPersonalityField(field, rolledValue);
  };

  const canRandomizePersonalityTraits =
    !readOnly &&
    !!backgroundData &&
    hasBackgroundRandomOptions(backgroundData.id, "personalityTraits");
  const canRandomizeIdeals =
    !readOnly && !!backgroundData && hasBackgroundRandomOptions(backgroundData.id, "ideals");
  const canRandomizeBonds =
    !readOnly && !!backgroundData && hasBackgroundRandomOptions(backgroundData.id, "bonds");
  const canRandomizeFlaws =
    !readOnly && !!backgroundData && hasBackgroundRandomOptions(backgroundData.id, "flaws");

  return (
    <div className="space-y-3">
      <Section title={t("sheet.creation.step.identity.title")} color="bg-limiar-500">
        <div className="mb-4 border-b border-white/6 pb-4">
          <label className={fieldLabel}>{t("sheet.basicInfo.portrait")}</label>
          <AvatarUploadInput
            value={sheet.avatarUrl}
            onChange={(url) => set("avatarUrl", url)}
            label={t("sheet.basicInfo.portrait")}
            disabled={readOnly}
          />
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-12">
          <div className="xl:col-span-4">
            <label className={fieldLabel}>{t("sheet.basicInfo.characterName")}</label>
            <input
              type="text"
              value={sheet.name}
              disabled={readOnly}
              onChange={(event) => set("name", event.target.value)}
              className={input}
            />
          </div>
          <div className="xl:col-span-3">
            <label className={fieldLabel}>{t("sheet.basicInfo.playerName")}</label>
            <div className={`${input} flex items-center opacity-70`}>
              {sheet.playerName || "—"}
            </div>
          </div>
          <div className="md:col-span-1 xl:col-span-2">
            <label className={fieldLabel}>{t("sheet.basicInfo.alignment")}</label>
            <select
              value={sheet.alignment}
              disabled={readOnly}
              onChange={(event) => set("alignment", event.target.value)}
              className={input}
            >
              <option value="">{t("sheet.basicInfo.selectAlign")}</option>
              {ALIGNMENTS.map((alignment) => (
                <option key={alignment} value={alignment}>
                  {alignment}
                </option>
              ))}
            </select>
          </div>
          <div className="md:col-span-1 xl:col-span-3">
            <label className={fieldLabel}>{t("sheet.basicInfo.background")}</label>
            <select
              value={sheet.background}
              disabled={readOnly}
              onChange={(event) => selectBackground(event.target.value)}
              className={input}
            >
              <option value="">{t("sheet.basicInfo.selectBg")}</option>
              {BACKGROUNDS.map((background) => (
                <option key={background.id} value={background.id}>
                  {background.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </Section>

      {backgroundData ? (
        <Section title={t("sheet.basicInfo.bgPreview")} color="bg-slate-500">
          <div className="text-xs text-slate-400">
            <p className="text-sm font-semibold text-slate-100">{backgroundData.name}</p>
            <p className="mt-2 leading-6">
              {t("sheet.basicInfo.feature")}: {backgroundData.feature.label}
            </p>
            <p className="mt-1 leading-6">{backgroundData.feature.description}</p>
            <p className="mt-2 leading-6">
              {t("sheet.basicInfo.equipment")}:{" "}
              {backgroundData.startingEquipment
                .map((entry) => formatBackgroundEquipmentEntry(entry))
                .join(", ")}
            </p>
          </div>
        </Section>
      ) : null}

      <Section title={t("sheet.features.title")} color="bg-emerald-500">
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <div className="mb-2 inline-flex items-center gap-1.5 align-middle">
              <label className={`${fieldLabel} mb-0`}>
                {t("sheet.features.personalityTraits")}
              </label>
              {canRandomizePersonalityTraits ? (
                <button
                  type="button"
                  onClick={() => randomizePersonalityField("personalityTraits")}
                  className="inline-flex h-5 w-5 shrink-0 items-center justify-center self-center rounded-full text-slate-400 transition hover:bg-white/5 hover:text-slate-100"
                  title={t("sheet.creation.randomizeField")}
                  aria-label={t("sheet.creation.randomizeField")}
                >
                  <span aria-hidden="true" className="-translate-y-[4px] text-[13px] leading-none">
                    🎲
                  </span>
                </button>
              ) : null}
            </div>
            <textarea
              rows={4}
              value={personalityFields.personalityTraits}
              disabled={readOnly}
              onChange={(event) => setPersonalityField("personalityTraits", event.target.value)}
              className={`${input} min-h-28 resize-y py-3 ${readOnly ? "opacity-70" : ""}`}
            />
          </div>
          <div>
            <div className="mb-2 inline-flex items-center gap-1.5 align-middle">
              <label className={`${fieldLabel} mb-0`}>{t("sheet.features.ideals")}</label>
              {canRandomizeIdeals ? (
                <button
                  type="button"
                  onClick={() => randomizePersonalityField("ideals")}
                  className="inline-flex h-5 w-5 shrink-0 items-center justify-center self-center rounded-full text-slate-400 transition hover:bg-white/5 hover:text-slate-100"
                  title={t("sheet.creation.randomizeField")}
                  aria-label={t("sheet.creation.randomizeField")}
                >
                  <span aria-hidden="true" className="-translate-y-[4px] text-[13px] leading-none">
                    🎲
                  </span>
                </button>
              ) : null}
            </div>
            <textarea
              rows={4}
              value={personalityFields.ideals}
              disabled={readOnly}
              onChange={(event) => setPersonalityField("ideals", event.target.value)}
              className={`${input} min-h-28 resize-y py-3 ${readOnly ? "opacity-70" : ""}`}
            />
          </div>
          <div>
            <div className="mb-2 inline-flex items-center gap-1.5 align-middle">
              <label className={`${fieldLabel} mb-0`}>{t("sheet.features.bonds")}</label>
              {canRandomizeBonds ? (
                <button
                  type="button"
                  onClick={() => randomizePersonalityField("bonds")}
                  className="inline-flex h-5 w-5 shrink-0 items-center justify-center self-center rounded-full text-slate-400 transition hover:bg-white/5 hover:text-slate-100"
                  title={t("sheet.creation.randomizeField")}
                  aria-label={t("sheet.creation.randomizeField")}
                >
                  <span aria-hidden="true" className="-translate-y-[4px] text-[13px] leading-none">
                    🎲
                  </span>
                </button>
              ) : null}
            </div>
            <textarea
              rows={4}
              value={personalityFields.bonds}
              disabled={readOnly}
              onChange={(event) => setPersonalityField("bonds", event.target.value)}
              className={`${input} min-h-28 resize-y py-3 ${readOnly ? "opacity-70" : ""}`}
            />
          </div>
          <div>
            <div className="mb-2 inline-flex items-center gap-1.5 align-middle">
              <label className={`${fieldLabel} mb-0`}>{t("sheet.features.flaws")}</label>
              {canRandomizeFlaws ? (
                <button
                  type="button"
                  onClick={() => randomizePersonalityField("flaws")}
                  className="inline-flex h-5 w-5 shrink-0 items-center justify-center self-center rounded-full text-slate-400 transition hover:bg-white/5 hover:text-slate-100"
                  title={t("sheet.creation.randomizeField")}
                  aria-label={t("sheet.creation.randomizeField")}
                >
                  <span aria-hidden="true" className="-translate-y-[4px] text-[13px] leading-none">
                    🎲
                  </span>
                </button>
              ) : null}
            </div>
            <textarea
              rows={4}
              value={personalityFields.flaws}
              disabled={readOnly}
              onChange={(event) => setPersonalityField("flaws", event.target.value)}
              className={`${input} min-h-28 resize-y py-3 ${readOnly ? "opacity-70" : ""}`}
            />
          </div>
        </div>
      </Section>
    </div>
  );
};

const CreationClassStep = ({
  sheet,
  readOnly,
  allowLevelEditing,
  missingRequiredFields,
  set,
  selectClass,
  selectSubclass,
  selectSubclassConfig,
}: {
  sheet: CharacterSheet;
  readOnly: boolean;
  allowLevelEditing: boolean;
  missingRequiredFields: RequiredField[];
  set: SheetActions["set"];
  selectClass: (value: string) => void;
  selectSubclass: SheetActions["selectSubclass"];
  selectSubclassConfig: SheetActions["selectSubclassConfig"];
}) => {
  const { t } = useLocale();
  const classData = getClass(sheet.class);
  const unlockedClassData = classData && isSubclassUnlocked(classData, sheet.level) ? classData : null;
  const fixedSubclass = getFixedSubclassForClassLevel(sheet.class, sheet.level);
  const fixedFightingStyle = getFixedFightingStyleForClassLevel(sheet.class, sheet.level);
  const fixedSubclassName =
    unlockedClassData?.subclasses.find((subclass) => subclass.id === fixedSubclass)?.name ?? fixedSubclass;
  const fixedFightingStyleName =
    FIGHTING_STYLES.find((style) => style.id === fixedFightingStyle)?.name ?? fixedFightingStyle;
  const subclassConfigFields = getSubclassConfigFields(sheet.class, sheet.subclass);
  const showFightingStyle = !!classData && hasFightingStyleAtCreation(classData, sheet.level);
  const draconicLineage = getDraconicLineageState({
    classId: sheet.class,
    subclass: sheet.subclass,
    level: sheet.level,
    subclassConfig: sheet.subclassConfig,
  });
  const elementalAffinity = resolveElementalAffinityEligibility({
    classId: sheet.class,
    subclass: sheet.subclass,
    level: sheet.level,
    subclassConfig: sheet.subclassConfig,
    spellDamageType: draconicLineage.damageType,
    charismaScore: sheet.abilities.charisma,
  });
  const [levelInput, setLevelInput] = useState(() => String(sheet.level));

  useEffect(() => {
    setLevelInput(String(sheet.level));
  }, [sheet.level]);

  const commitLevelInput = (rawValue: string) => {
    const trimmedValue = rawValue.trim();
    if (!trimmedValue) {
      setLevelInput(String(sheet.level));
      return;
    }
    const nextLevel = Math.max(1, Math.min(20, safeParseInt(trimmedValue, sheet.level))) as CharacterSheet["level"];
    setLevelInput(String(nextLevel));
    if (nextLevel !== sheet.level) {
      set("level", nextLevel);
    }
  };

  return (
    <Section title={t("sheet.creation.step.class.title")} color="bg-limiar-500">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-12">
        <div className="xl:col-span-4">
          <label className={fieldLabel}>{t("sheet.basicInfo.class")}</label>
          <select
            value={sheet.class}
            disabled={readOnly}
            onChange={(event) => selectClass(event.target.value)}
            className={input}
          >
            <option value="">{t("sheet.basicInfo.selectClass")}</option>
            {CLASSES.map((classOption) => (
              <option key={classOption.id} value={classOption.id}>
                {classOption.name}
              </option>
            ))}
          </select>
        </div>

        <div className="xl:col-span-2">
          <label className={fieldLabel}>{t("sheet.basicInfo.level")}</label>
          <input
            type="number"
            min={1}
            max={20}
            value={allowLevelEditing ? levelInput : String(sheet.level)}
            disabled={readOnly || !allowLevelEditing}
            readOnly={!allowLevelEditing}
            onChange={(event) => {
              const rawValue = event.target.value;
              setLevelInput(rawValue);
              if (/^\d+$/.test(rawValue)) {
                commitLevelInput(rawValue);
              }
            }}
            onBlur={() => commitLevelInput(levelInput)}
            className={`${input} ${readOnly || !allowLevelEditing ? "opacity-70" : ""}`}
          />
        </div>

        {unlockedClassData ? (
          <div className="xl:col-span-3">
            <label className={fieldLabel}>{unlockedClassData.subclassLabel}</label>
            {fixedSubclass ? (
              <div className={`${input} flex min-h-11 items-center opacity-70`}>
                {fixedSubclassName}
              </div>
            ) : (
              <select
                value={sheet.subclass ?? ""}
                disabled={readOnly}
                onChange={(event) => selectSubclass(event.target.value)}
                className={input}
              >
                <option value="">{t("sheet.basicInfo.selectSubclass")}</option>
                {unlockedClassData.subclasses.map((subclass) => (
                  <option key={subclass.id} value={subclass.id}>
                    {subclass.name}
                  </option>
                ))}
              </select>
            )}
          </div>
        ) : null}

        {showFightingStyle ? (
          <div className="xl:col-span-3">
            <label className={fieldLabel}>{t("sheet.basicInfo.fightingStyle")}</label>
            {fixedFightingStyle ? (
              <div className={`${input} flex min-h-11 items-center opacity-70`}>
                {fixedFightingStyleName}
              </div>
            ) : (
              <select
                value={sheet.fightingStyle ?? ""}
                disabled={readOnly}
                onChange={(event) => set("fightingStyle", event.target.value || null)}
                className={input}
              >
                <option value="">{t("sheet.basicInfo.selectFightingStyle")}</option>
                {FIGHTING_STYLES.filter((style) => classData?.fightingStyleOptions.includes(style.id)).map((style) => (
                  <option key={style.id} value={style.id}>
                    {style.name}
                  </option>
                ))}
              </select>
            )}
          </div>
        ) : null}

        {subclassConfigFields.map((field) => (
          <div key={field.key} className="xl:col-span-3">
            <label className={fieldLabel}>{field.label}</label>
            <select
              value={sheet.subclassConfig?.[field.key] ?? ""}
              disabled={readOnly}
              onChange={(event) => selectSubclassConfig(field.key, event.target.value)}
              className={input}
            >
              <option value="">{t("sheet.raceConfig.select")}</option>
              {field.options.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.name}
                </option>
              ))}
            </select>
            {field.key === DRACONIC_ANCESTRY_SUBCLASS_CONFIG_KEY && draconicLineage.ancestryLabel ? (
              <p className="mt-2 text-[11px] text-slate-400">
                {t("sheet.basicInfo.draconicLineage")}:{" "}
                <span className="font-semibold text-slate-200">{draconicLineage.ancestryLabel}</span>
                {draconicLineage.damageType ? (
                  <>
                    {" "}· {t("sheet.basicInfo.draconicDamageType")}:{" "}
                    <span className="font-semibold text-slate-200">{draconicLineage.damageType}</span>
                  </>
                ) : null}
                {draconicLineage.hasElementalAffinity && elementalAffinity.bonus !== null ? (
                  <>
                    {" "}· {t("sheet.basicInfo.draconicElementalAffinity")}:{" "}
                    <span className="font-semibold text-slate-200">
                      +{elementalAffinity.bonus} {draconicLineage.damageType}
                    </span>
                  </>
                ) : null}
              </p>
            ) : null}
          </div>
        ))}
      </div>

      {classData ? (
        <div className="mt-5 rounded-3xl border border-white/8 bg-slate-950/55 p-4 text-xs text-slate-400 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
            {t("sheet.basicInfo.classPreview")}
          </p>
          <p className="mt-3 text-sm font-semibold text-slate-100">{classData.name}</p>
          <p className="mt-1 leading-6">{t("sheet.basicInfo.hitDie")} {classData.hitDice}</p>
          <p className="leading-6">
            {t("sheet.basicInfo.savingThrowsLabel")}: {classData.savingThrows.join(", ")}
          </p>
          <p className="leading-6">
            {t("sheet.basicInfo.chooseSkills").replace("{n}", String(classData.skillCount))}
          </p>
          {classData.spellcastingAbility ? (
            <p className="mt-2 font-semibold text-violet-300">
              {t("sheet.basicInfo.spellcasting")}: {getAbilityLabel(classData.spellcastingAbility, t)}
            </p>
          ) : null}
        </div>
      ) : null}
    </Section>
  );
};

const CreationOriginStep = ({
  sheet,
  readOnly,
  missingRequiredFields,
  set,
  selectBackground,
  selectRace,
  pickRaceToolProficiency,
  selectLanguageChoice,
  selectRaceConfig,
}: {
  sheet: CharacterSheet;
  readOnly: boolean;
  missingRequiredFields: RequiredField[];
  set: SheetActions["set"];
  selectBackground: (value: string) => void;
  selectRace: (value: string) => void;
  pickRaceToolProficiency: SheetActions["pickRaceToolProficiency"];
  selectLanguageChoice: SheetActions["selectLanguageChoice"];
  selectRaceConfig: SheetActions["selectRaceConfig"];
}) => {
  const { t } = useLocale();
  const raceData = getRace(sheet.race, sheet.raceConfig);
  return (
    <div className="space-y-3">
      <Section title={t("sheet.creation.step.origin.title")} color="bg-teal-500">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-12">
          <div className="xl:col-span-4">
            <label className={fieldLabel}>{t("sheet.basicInfo.race")}</label>
            <select
              value={sheet.race}
              disabled={readOnly}
              onChange={(event) => selectRace(event.target.value)}
              className={input}
            >
              <option value="">{t("sheet.basicInfo.selectRace")}</option>
              {RACES.map((race) => (
                <option key={race.id} value={race.id}>
                  {race.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="mt-5 grid gap-3 xl:grid-cols-2">
          {raceData ? <RacePreviewCard raceData={raceData} sheet={sheet} /> : null}
        </div>
      </Section>

      <RaceConfigPicker
        sheet={sheet}
        selectRaceConfig={selectRaceConfig}
        missingRequiredFields={missingRequiredFields}
        readOnly={readOnly}
      />
      <RaceToolProficiencyPicker
        sheet={sheet}
        pickRaceToolProficiency={pickRaceToolProficiency}
        missingRequiredFields={missingRequiredFields}
      />
      <LanguageChoicePicker
        sheet={sheet}
        onSelectLanguage={selectLanguageChoice}
        missingRequiredFields={missingRequiredFields}
      />
    </div>
  );
};

const CreationReviewStep = ({
  sheet,
  pendingByStep,
  onNavigateToStep,
  readOnly,
  set,
  hpPercent,
  hpColor,
  setCurrentHP,
  setMaxHP,
  adjustHP,
  useHitDie,
  longRest,
  setDeathSave,
  ac,
  initiative,
  spellSaveDC,
  spellAttack,
}: {
  sheet: CharacterSheet;
  pendingByStep: Array<{ stepId: CreationStepId; missingFields: RequiredField[] }>;
  onNavigateToStep: (stepId: CreationStepId) => void;
  readOnly: boolean;
  set: SheetActions["set"];
  hpPercent: number;
  hpColor: string;
  setCurrentHP: SheetActions["setCurrentHP"];
  setMaxHP: SheetActions["setMaxHP"];
  adjustHP: SheetActions["adjustHP"];
  useHitDie: SheetActions["useHitDie"];
  longRest: SheetActions["longRest"];
  setDeathSave: SheetActions["setDeathSave"];
  ac: number;
  initiative: number;
  spellSaveDC: number | null;
  spellAttack: number | null;
}) => {
  const { t } = useLocale();
  const classLabel = sheet.class
    ? formatClassDisplayName(sheet.class, sheet.subclass, sheet.subclassConfig)
    : "—";
  const raceLabel = getRace(sheet.race, sheet.raceConfig)?.name ?? "—";
  const backgroundLabel = getBackground(sheet.background)?.name ?? "—";

  return (
    <div className="space-y-3">
      <div className="grid gap-3 lg:grid-cols-3">
        <SummaryCard
          eyebrow={t("sheet.creation.review.identity")}
          title={sheet.name || t("sheet.header.unnamed")}
          detail={t("sheet.creation.review.identityReady")}
        />
        <SummaryCard
          eyebrow={t("sheet.creation.review.class")}
          title={classLabel}
          detail={`${t("sheet.basicInfo.level")} ${sheet.level}`}
        />
        <SummaryCard
          eyebrow={t("sheet.creation.review.origin")}
          title={`${raceLabel} · ${backgroundLabel}`}
          detail={sheet.alignment || "—"}
        />
      </div>

      <Section title={t("sheet.creation.review.pendingTitle")} color="bg-amber-500">
        <div className="space-y-3">
          {pendingByStep.map(({ stepId, missingFields }) => (
            <div
              key={`pending-${stepId}`}
              className="rounded-2xl border border-white/8 bg-white/[0.03] p-4"
            >
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                    {t(STEP_META[stepId].titleKey)}
                  </p>
                  {missingFields.length === 0 ? (
                    <p className="mt-1 text-sm text-emerald-300">
                      {t("sheet.creation.review.stepReady")}
                    </p>
                  ) : (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {missingFields.map((field) => (
                        <span
                          key={`${stepId}-${field}`}
                          className="rounded-full border border-amber-400/20 bg-amber-400/10 px-3 py-1 text-[11px] font-semibold text-amber-100"
                        >
                          {t(REQUIRED_FIELD_LABEL_KEY[field])}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <button type="button" onClick={() => onNavigateToStep(stepId)} className={btnOutline}>
                  {t("sheet.creation.review.fixStep")}
                </button>
              </div>
            </div>
          ))}
        </div>
      </Section>

      <div className="grid gap-3 xl:grid-cols-12 xl:items-start">
        <div className="space-y-3 xl:col-span-8">
          <div className="grid gap-3 lg:grid-cols-2">
            <HitPoints
              sheet={sheet}
              hpPercent={hpPercent}
              hpColor={hpColor}
              readOnly={readOnly}
              setCurrentHP={setCurrentHP}
              setMaxHP={setMaxHP}
              adjustHP={adjustHP}
              set={set}
              mode="creation"
            />
            <HitDiceSection
              sheet={sheet}
              set={set}
              useHitDie={useHitDie}
              longRest={longRest}
              setDeathSave={setDeathSave}
              mode="creation"
              showRestActions
              readOnly={readOnly}
            />
          </div>
        </div>

        <div className="space-y-3 xl:col-span-4">
          <Section title={t("sheet.creation.review.derivedTitle")} color="bg-cyan-500">
            <div className="grid grid-cols-2 gap-3">
              <DerivedChip label="AC" value={String(ac)} />
              <DerivedChip label="Init" value={initiative >= 0 ? `+${initiative}` : String(initiative)} />
              <DerivedChip label="HP" value={String(sheet.maxHP)} />
              <DerivedChip label="HD" value={`${sheet.hitDiceTotal}${sheet.hitDiceType ? ` ${sheet.hitDiceType}` : ""}`} />
              {spellSaveDC !== null ? <DerivedChip label="Spell DC" value={String(spellSaveDC)} /> : null}
              {spellAttack !== null ? <DerivedChip label="Spell Atk" value={spellAttack >= 0 ? `+${spellAttack}` : String(spellAttack)} /> : null}
            </div>
          </Section>
        </div>
      </div>
    </div>
  );
};

const SummaryCard = ({
  eyebrow,
  title,
  detail,
}: {
  eyebrow: string;
  title: string;
  detail: string;
}) => (
  <div className="rounded-[26px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] p-4">
    <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">{eyebrow}</p>
    <p className="mt-3 text-lg font-semibold text-white">{title}</p>
    <p className="mt-2 text-sm text-slate-400">{detail}</p>
  </div>
);

const DerivedChip = ({ label, value }: { label: string; value: string }) => (
  <div className="rounded-2xl border border-white/8 bg-white/[0.03] p-3 text-center">
    <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">{label}</p>
    <p className="mt-2 text-xl font-semibold text-white">{value || "—"}</p>
  </div>
);

const formatBackgroundEquipmentEntry = (entry: string) => {
  const quantityMatch = entry.trim().match(/^(.+?)\s*x(\d+)$/i);
  if (quantityMatch) {
    return `${canonicalizeStarterItemName(quantityMatch[1].trim())} x${quantityMatch[2]}`;
  }
  return canonicalizeStarterItemName(entry);
};
