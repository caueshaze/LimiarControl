import type { CharacterSheet } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import { getRace } from "../data/races";
import { getBackground } from "../data/backgrounds";
import { LANGUAGE_CHOICE_SLOT, LANGUAGES, getAvailableLanguages } from "../data/languages";
import { input, fieldLabel } from "./styles";
import { useLocale } from "../../../shared/hooks/useLocale";
import type { RequiredField } from "../utils/creationValidation";

type Props = {
  sheet: CharacterSheet;
  onSelectLanguage: SheetActions["selectLanguageChoice"];
  missingRequiredFields?: RequiredField[];
};

export const LanguageChoicePicker = ({
  sheet,
  onSelectLanguage,
  missingRequiredFields = [],
}: Props) => {
  const { t } = useLocale();
  const race = getRace(sheet.race, sheet.raceConfig);
  const background = getBackground(sheet.background);

  // Collect all language entries from race + background
  const allEntries = [
    ...(race?.languages ?? []),
    ...(background?.languages ?? []),
  ];

  // Fixed languages (non-choice entries, deduplicated)
  const fixedLanguages = [...new Set(
    allEntries.filter((e) => e !== LANGUAGE_CHOICE_SLOT),
  )];

  // Count choice slots
  const choiceSlots = allEntries.filter((e) => e === LANGUAGE_CHOICE_SLOT).length;
  if (choiceSlots === 0) return null;

  const hasAttempted = missingRequiredFields.length > 0;
  const hasMissing = missingRequiredFields.includes("languageChoices");
  const errorRing = hasAttempted && hasMissing
    ? "ring-1 ring-red-500/60 border-red-500/40"
    : "";

  // For each slot, compute which languages are available
  // (exclude fixed + already chosen in other slots)
  const slots = Array.from({ length: choiceSlots }, (_, i) => {
    const currentChoice = sheet.languageChoices[i] ?? "";
    const otherChoices = sheet.languageChoices.filter((_, j) => j !== i && j < choiceSlots);
    const allKnown = [...fixedLanguages, ...otherChoices].filter(Boolean);
    const available = getAvailableLanguages(allKnown);
    return { index: i, currentChoice, available };
  });

  // Determine source label for each slot
  const raceSlots = (race?.languages ?? []).filter((e) => e === LANGUAGE_CHOICE_SLOT).length;

  return (
    <div className="mt-4 rounded-[24px] border border-white/8 bg-slate-950/55 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
      <div className="mb-3">
        <span className={fieldLabel}>{t("sheet.languages.choiceTitle")}</span>
        {hasAttempted && hasMissing && (
          <p className="mt-0.5 text-[10px] text-red-400">{t("sheet.validation.required")}</p>
        )}
      </div>

      {fixedLanguages.length > 0 && (
        <p className="mb-3 text-xs text-slate-400">
          {t("sheet.languages.fixed")}: {fixedLanguages.join(", ")}
        </p>
      )}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {slots.map((slot) => {
          const source = slot.index < raceSlots
            ? t("sheet.languages.fromRace")
            : t("sheet.languages.fromBackground");

          return (
            <div key={slot.index}>
              <label className="mb-1 block text-[10px] font-medium text-slate-500">
                {t("sheet.languages.slotLabel")} {slot.index + 1}
                <span className="ml-1 text-slate-600">({source})</span>
              </label>
              <select
                value={slot.currentChoice}
                onChange={(e) => onSelectLanguage(slot.index, e.target.value)}
                className={`${input} ${!slot.currentChoice ? errorRing : ""}`}
              >
                <option value="">{t("sheet.languages.selectLanguage")}</option>
                {slot.available.map((lang) => (
                  <option key={lang.id} value={lang.name}>
                    {lang.name} {lang.tier === "exotic" ? `(${t("sheet.languages.exotic")})` : ""}
                  </option>
                ))}
                {/* Keep current choice visible even if it's not in "available" */}
                {slot.currentChoice && !slot.available.some((l) => l.name === slot.currentChoice) && (
                  <option value={slot.currentChoice}>{slot.currentChoice}</option>
                )}
              </select>
            </div>
          );
        })}
      </div>
    </div>
  );
};
