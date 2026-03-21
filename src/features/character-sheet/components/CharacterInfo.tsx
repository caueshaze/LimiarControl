import type { CharacterSheet, CharacterSheetMode } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import { Section } from "./Section";
import { input, fieldLabel, chk } from "./styles";
import { ALIGNMENTS } from "../data/alignments";
import { RACES, getRace } from "../data/races";
import { CLASSES, FIGHTING_STYLES, getClass, getSubclassConfigFields, hasFightingStyleAtCreation, isSubclassUnlocked } from "../data/classes";
import { BACKGROUNDS, getBackground } from "../data/backgrounds";
import { ClassSkillPicker } from "./ClassSkillPicker";
import { ClassToolProficiencyPicker } from "./ClassToolProficiencyPicker";
import { RaceToolProficiencyPicker } from "./RaceToolProficiencyPicker";
import { ClassEquipmentChoices } from "./ClassEquipmentChoices";
import { ClassExpertisePicker } from "./ClassExpertisePicker";
import { LanguageChoicePicker } from "./LanguageChoicePicker";
import { CharacterProgressPanel } from "./CharacterProgressPanel";
import { RaceConfigPicker } from "./RaceConfigPicker";
import { RacePreviewCard } from "./RacePreviewCard";
import { useLocale } from "../../../shared/hooks/useLocale";
import type { RequiredField } from "../utils/creationValidation";
import { canonicalizeStarterItemName } from "../utils/creationEquipment";

type Props = {
  sheet: CharacterSheet;
  mode: CharacterSheetMode;
  readOnly?: boolean;
  missingRequiredFields?: RequiredField[];
  set: SheetActions["set"];
  selectClass: SheetActions["selectClass"];
  selectSubclass: SheetActions["selectSubclass"];
  canRequestLevelUp: boolean;
  requestingLevelUp: boolean;
  requestLevelUpError: string | null;
  onRequestLevelUp: () => void;
  showProgressPanel?: boolean;
  selectBackground: SheetActions["selectBackground"];
  selectRace: SheetActions["selectRace"];
  selectClassEquipment: SheetActions["selectClassEquipment"];
  pickClassSkill: SheetActions["pickClassSkill"];
  pickExpertise: SheetActions["pickExpertise"];
  pickRaceToolProficiency: SheetActions["pickRaceToolProficiency"];
  pickClassToolProficiency: SheetActions["pickClassToolProficiency"];
  selectLanguageChoice: SheetActions["selectLanguageChoice"];
  selectRaceConfig: SheetActions["selectRaceConfig"];
  selectSubclassConfig: SheetActions["selectSubclassConfig"];
};

export const CharacterInfo = ({
  sheet,
  mode,
  readOnly = false,
  missingRequiredFields = [],
  set,
  selectClass,
  selectSubclass,
  canRequestLevelUp,
  requestingLevelUp,
  requestLevelUpError,
  onRequestLevelUp,
  showProgressPanel = true,
  selectBackground,
  selectRace,
  selectClassEquipment,
  pickClassSkill,
  pickExpertise,
  pickRaceToolProficiency,
  pickClassToolProficiency,
  selectLanguageChoice,
  selectRaceConfig,
  selectSubclassConfig,
}: Props) => {
  const { t } = useLocale();
  const isCreation = mode === "creation";
  const raceData = getRace(sheet.race, sheet.raceConfig);
  const classData = getClass(sheet.class);
  const backgroundData = getBackground(sheet.background);
  const unlockedClassData = classData && isSubclassUnlocked(classData, sheet.level) ? classData : null;
  const subclassConfigFields = getSubclassConfigFields(sheet.class, sheet.subclass);
  const showFightingStyle = !!classData && hasFightingStyleAtCreation(classData, sheet.level);

  const missing = new Set(missingRequiredFields);
  const hasAttempted = missingRequiredFields.length > 0;

  const errorInput = (field: RequiredField) => (hasAttempted && missing.has(field) ? "ring-1 ring-red-500/60 border-red-500/40" : "");

  const requiredMark = (field: RequiredField) =>
    isCreation && (
      <span
        className={`ml-0.5 ${missing.has(field) && hasAttempted ? "text-red-400" : "text-slate-500"}`}
      >
        *
      </span>
    );

  const formatBackgroundEquipmentEntry = (entry: string) => {
    const quantityMatch = entry.trim().match(/^(.+?)\s*x(\d+)$/i);
    if (quantityMatch) {
      return `${canonicalizeStarterItemName(quantityMatch[1].trim())} x${quantityMatch[2]}`;
    }
    return canonicalizeStarterItemName(entry);
  };

  const fieldError = (field: RequiredField) =>
    hasAttempted && missing.has(field) ? (
      <p className="mt-0.5 text-[10px] text-red-400">{t("sheet.validation.required")}</p>
    ) : null;

  return (
    <Section title={t("sheet.basicInfo.title")} color="bg-limiar-500">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-12">
        <div className="xl:col-span-5">
          <label className={fieldLabel}>
            {t("sheet.basicInfo.characterName")}{requiredMark("name")}
          </label>
          <input
            type="text"
            value={sheet.name}
            disabled={readOnly}
            required={isCreation}
            onChange={(e) => set("name", e.target.value)}
            className={`${input} ${errorInput("name")}`}
          />
          {fieldError("name")}
        </div>

        <div className="xl:col-span-3">
          <label className={fieldLabel}>
            {t("sheet.basicInfo.class")}{requiredMark("class")}
          </label>
          <select
            value={sheet.class}
            disabled={readOnly}
            required={isCreation}
            onChange={(e) => selectClass(e.target.value)}
            className={`${input} ${errorInput("class")}`}
          >
            <option value="">{t("sheet.basicInfo.selectClass")}</option>
            {CLASSES.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
          {fieldError("class")}
        </div>

        {unlockedClassData ? (
          <div className="xl:col-span-3">
            <label className={fieldLabel}>
              {unlockedClassData.subclassLabel}{requiredMark("subclass")}
            </label>
            <select
              value={sheet.subclass ?? ""}
              disabled={readOnly}
              onChange={(e) => selectSubclass(e.target.value)}
              className={`${input} ${errorInput("subclass")}`}
            >
              <option value="">{t("sheet.basicInfo.selectSubclass")}</option>
              {unlockedClassData.subclasses.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
            {fieldError("subclass")}
          </div>
        ) : null}

        {subclassConfigFields.map((field) => (
          <div key={field.key} className="xl:col-span-3">
            <label className={fieldLabel}>
              {field.label}{requiredMark("subclassConfig")}
            </label>
            <select
              value={sheet.subclassConfig?.[field.key] ?? ""}
              disabled={readOnly}
              onChange={(e) => selectSubclassConfig(field.key, e.target.value)}
              className={`${input} ${errorInput("subclassConfig")}`}
            >
              <option value="">Selecione...</option>
              {field.options.map((opt) => (
                <option key={opt.id} value={opt.id}>{opt.name}</option>
              ))}
            </select>
            {fieldError("subclassConfig")}
          </div>
        ))}

        {showFightingStyle && (
          <div className="xl:col-span-3">
            <label className={fieldLabel}>
              {t("sheet.basicInfo.fightingStyle")}{requiredMark("fightingStyle")}
            </label>
            <select
              value={sheet.fightingStyle ?? ""}
              disabled={readOnly}
              onChange={(e) => set("fightingStyle", e.target.value || null)}
              className={`${input} ${errorInput("fightingStyle")}`}
            >
              <option value="">{t("sheet.basicInfo.selectFightingStyle")}</option>
              {FIGHTING_STYLES.filter((s) => classData?.fightingStyleOptions.includes(s.id)).map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
            {fieldError("fightingStyle")}
          </div>
        )}

        <div className="xl:col-span-4">
          <label className={fieldLabel}>
            {t("sheet.basicInfo.race")}{requiredMark("race")}
          </label>
          <select
            value={sheet.race}
            disabled={readOnly}
            required={isCreation}
            onChange={(e) => selectRace(e.target.value)}
            className={`${input} ${errorInput("race")}`}
          >
            <option value="">{t("sheet.basicInfo.selectRace")}</option>
            {RACES.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
          {fieldError("race")}
        </div>

        <div className="xl:col-span-4">
          <label className={fieldLabel}>
            {t("sheet.basicInfo.background")}{requiredMark("background")}
          </label>
          <select
            value={sheet.background}
            disabled={readOnly}
            required={isCreation}
            onChange={(e) => selectBackground(e.target.value)}
            className={`${input} ${errorInput("background")}`}
          >
            <option value="">{t("sheet.basicInfo.selectBg")}</option>
            {BACKGROUNDS.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>
          {fieldError("background")}
        </div>

        <div className="xl:col-span-3">
          <label className={fieldLabel}>
            {t("sheet.basicInfo.alignment")}{requiredMark("alignment")}
          </label>
          <select
            value={sheet.alignment}
            disabled={readOnly}
            required={isCreation}
            onChange={(e) => set("alignment", e.target.value)}
            className={`${input} ${errorInput("alignment")}`}
          >
            <option value="">{t("sheet.basicInfo.selectAlign")}</option>
            {ALIGNMENTS.map((a) => <option key={a} value={a}>{a}</option>)}
          </select>
          {fieldError("alignment")}
        </div>

        <div className="xl:col-span-3">
          <label className={fieldLabel}>
            {t("sheet.basicInfo.playerName")}{requiredMark("playerName")}
          </label>
          <input
            type="text"
            value={sheet.playerName}
            disabled={readOnly}
            required={isCreation}
            onChange={(e) => set("playerName", e.target.value)}
            className={`${input} ${errorInput("playerName")}`}
          />
          {fieldError("playerName")}
        </div>

        <div className="xl:col-span-2">
          <label className={fieldLabel}>{t("sheet.basicInfo.level")}</label>
          <input
            type="number"
            min={1}
            max={20}
            value={sheet.level}
            disabled
            readOnly
            className={`${input} opacity-70`}
          />
        </div>

        {!isCreation && showProgressPanel ? (
          <CharacterProgressPanel
            level={sheet.level}
            experiencePoints={sheet.experiencePoints}
            pendingLevelUp={sheet.pendingLevelUp}
            canRequestLevelUp={canRequestLevelUp}
            requestingLevelUp={requestingLevelUp}
            requestLevelUpError={requestLevelUpError}
            onRequestLevelUp={onRequestLevelUp}
          />
        ) : null}
      </div>

      {/* Racial / class / background previews */}
      <div className="mt-5 grid gap-3 xl:grid-cols-3">
        {raceData ? <RacePreviewCard raceData={raceData} sheet={sheet} /> : null}

        {classData && (
          <div className="rounded-[24px] border border-white/8 bg-slate-950/55 p-4 text-xs text-slate-400 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
            <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">{t("sheet.basicInfo.classPreview")}</p>
            <p className="mt-3 text-sm font-semibold text-slate-100">{classData.name}</p>
            <p className="mt-1 leading-6">{t("sheet.basicInfo.hitDie")} {classData.hitDice}</p>
            <p className="leading-6">{t("sheet.basicInfo.savingThrowsLabel")}: {classData.savingThrows.join(", ")}</p>
            <p className="leading-6">{t("sheet.basicInfo.chooseSkills").replace("{n}", String(classData.skillCount))}</p>
            {classData.spellcastingAbility && (
              <p className="mt-2 font-semibold text-violet-300">
                {t("sheet.basicInfo.spellcasting")}: {classData.spellcastingAbility.toUpperCase()}
              </p>
            )}
          </div>
        )}

        {backgroundData && (
          <div className="rounded-[24px] border border-white/8 bg-slate-950/55 p-4 text-xs text-slate-400 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
            <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">{t("sheet.basicInfo.bgPreview")}</p>
            <p className="mt-3 text-sm font-semibold text-slate-100">{backgroundData.name}</p>
            <p className="mt-1 leading-6">
              {t("sheet.basicInfo.feature")}: {backgroundData.feature.label}
            </p>
            <p className="mt-1 leading-6">{backgroundData.feature.description}</p>
            <p className="mt-2 leading-6">
              {t("sheet.basicInfo.equipment")}:{" "}
              {backgroundData.startingEquipment.map(formatBackgroundEquipmentEntry).join(", ")}
            </p>
          </div>
        )}
      </div>

      {/* Class skill selection */}
      {isCreation && <ClassSkillPicker sheet={sheet} pickClassSkill={pickClassSkill} missingRequiredFields={missingRequiredFields} />}
      {isCreation && <ClassExpertisePicker sheet={sheet} pickExpertise={pickExpertise} missingRequiredFields={missingRequiredFields} />}
      {isCreation && <RaceToolProficiencyPicker sheet={sheet} pickRaceToolProficiency={pickRaceToolProficiency} missingRequiredFields={missingRequiredFields} />}
      {isCreation && <ClassToolProficiencyPicker sheet={sheet} pickClassToolProficiency={pickClassToolProficiency} missingRequiredFields={missingRequiredFields} />}
      {isCreation && (
        <RaceConfigPicker
          sheet={sheet}
          selectRaceConfig={selectRaceConfig}
          missingRequiredFields={missingRequiredFields}
          readOnly={readOnly}
        />
      )}
      {isCreation && (
        <ClassEquipmentChoices
          className={sheet.class}
          selections={sheet.classEquipmentSelections}
          onSelect={selectClassEquipment}
        />
      )}
      {isCreation && (
        <LanguageChoicePicker
          sheet={sheet}
          onSelectLanguage={selectLanguageChoice}
          missingRequiredFields={missingRequiredFields}
        />
      )}

      {!isCreation && !readOnly && (
        <label className="mt-4 flex items-center gap-3">
          <input type="checkbox" checked={sheet.inspiration} onChange={() => set("inspiration", !sheet.inspiration)} className={chk} />
          <span className="text-sm font-semibold text-amber-400">{t("sheet.basicInfo.inspiration")}</span>
        </label>
      )}
    </Section>
  );
};
