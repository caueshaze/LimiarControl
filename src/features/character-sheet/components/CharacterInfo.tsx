import type { CharacterSheet, CharacterSheetMode } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import { Section } from "./Section";
import { input, fieldLabel, chk } from "./styles";
import { ALIGNMENTS } from "../data/alignments";
import { RACES, getRace } from "../data/races";
import { LANGUAGE_CHOICE_SLOT } from "../data/languages";
import { CLASSES, getClass } from "../data/classes";
import { BACKGROUNDS, getBackground } from "../data/backgrounds";
import { safeParseInt } from "../utils/calculations";
import { ClassSkillPicker } from "./ClassSkillPicker";
import { ClassToolProficiencyPicker } from "./ClassToolProficiencyPicker";
import { ClassEquipmentChoices } from "./ClassEquipmentChoices";
import { LanguageChoicePicker } from "./LanguageChoicePicker";
import { useLocale } from "../../../shared/hooks/useLocale";
import type { RequiredField } from "../utils/creationValidation";

type Props = {
  sheet: CharacterSheet;
  mode: CharacterSheetMode;
  readOnly?: boolean;
  missingRequiredFields?: RequiredField[];
  set: SheetActions["set"];
  selectClass: SheetActions["selectClass"];
  selectBackground: SheetActions["selectBackground"];
  selectRace: SheetActions["selectRace"];
  selectClassEquipment: SheetActions["selectClassEquipment"];
  pickClassSkill: SheetActions["pickClassSkill"];
  pickClassToolProficiency: SheetActions["pickClassToolProficiency"];
  selectLanguageChoice: SheetActions["selectLanguageChoice"];
};

export const CharacterInfo = ({
  sheet,
  mode,
  readOnly = false,
  missingRequiredFields = [],
  set,
  selectClass,
  selectBackground,
  selectRace,
  selectClassEquipment,
  pickClassSkill,
  pickClassToolProficiency,
  selectLanguageChoice,
}: Props) => {
  const { t } = useLocale();
  const isCreation = mode === "creation";
  const raceData = getRace(sheet.race);
  const classData = getClass(sheet.class);
  const backgroundData = getBackground(sheet.background);

  const missing = new Set(missingRequiredFields);
  const hasAttempted = missingRequiredFields.length > 0;

  const errorInput = (field: RequiredField) =>
    hasAttempted && missing.has(field)
      ? "ring-1 ring-red-500/60 border-red-500/40"
      : "";

  const requiredMark = (field: RequiredField) =>
    isCreation && (
      <span
        className={`ml-0.5 ${missing.has(field) && hasAttempted ? "text-red-400" : "text-slate-500"}`}
      >
        *
      </span>
    );

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
            type="number" min={1} max={20} value={sheet.level} disabled={isCreation || readOnly}
            onChange={(e) => set("level", Math.max(1, Math.min(20, safeParseInt(e.target.value, 1))))}
            className={`${input} ${isCreation || readOnly ? "opacity-70" : ""}`}
          />
        </div>

        {!isCreation && !readOnly && (
          <div className="xl:col-span-2">
            <label className={fieldLabel}>{t("sheet.basicInfo.xp")}</label>
            <input
              type="number" min={0} value={sheet.experiencePoints}
              onChange={(e) => set("experiencePoints", Math.max(0, safeParseInt(e.target.value)))}
              className={input}
            />
          </div>
        )}
      </div>

      {/* Racial / class / background previews */}
      <div className="mt-5 grid gap-3 xl:grid-cols-3">
        {raceData && (
          <div className="rounded-[24px] border border-white/8 bg-slate-950/55 p-4 text-xs text-slate-400 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
            <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">{t("sheet.basicInfo.racePreview")}</p>
            <p className="mt-3 text-sm font-semibold text-slate-100">{raceData.name}</p>
            <p className="mt-1 leading-6">
              <span className="text-slate-300">{raceData.size}</span>
              <span className="mx-2 text-slate-600">•</span>
              <span>{t("sheet.basicInfo.speed")} {raceData.speed}ft</span>
              {raceData.darkvision && (
                <>
                  <span className="mx-2 text-slate-600">•</span>
                  <span>{t("sheet.basicInfo.darkvision")} {raceData.darkvision}ft</span>
                </>
              )}
            </p>
            {raceData.languages.length > 0 && (() => {
              const fixed = raceData.languages.filter((l) => l !== LANGUAGE_CHOICE_SLOT);
              const choiceCount = raceData.languages.filter((l) => l === LANGUAGE_CHOICE_SLOT).length;
              const parts = [...fixed];
              if (choiceCount > 0) parts.push(`+${choiceCount} ${t("sheet.languages.toChoose")}`);
              return <p className="mt-2 leading-6">{t("sheet.basicInfo.languages")}: {parts.join(", ")}</p>;
            })()}
            {Object.entries(raceData.abilityBonuses).length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {Object.entries(raceData.abilityBonuses).map(([k, v]) => (
                  <span key={k} className="rounded-full border border-limiar-500/20 bg-limiar-500/10 px-2.5 py-1 font-semibold text-limiar-300">
                    {k.slice(0, 3).toUpperCase()} {v! >= 0 ? `+${v}` : v}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

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
            <p className="mt-1 leading-6">{t("sheet.basicInfo.feature")}: {backgroundData.feature}</p>
            <p className="mt-2 leading-6">{t("sheet.basicInfo.equipment")}: {backgroundData.startingEquipment.join(", ")}</p>
          </div>
        )}
      </div>

      {/* Class skill selection */}
      {isCreation && <ClassSkillPicker sheet={sheet} pickClassSkill={pickClassSkill} missingRequiredFields={missingRequiredFields} />}
      {isCreation && <ClassToolProficiencyPicker sheet={sheet} pickClassToolProficiency={pickClassToolProficiency} missingRequiredFields={missingRequiredFields} />}
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
