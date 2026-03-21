import type { CharacterSheet, SkillName } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import type { RequiredField } from "../utils/creationValidation";
import { getClass, hasExpertiseAtCreation } from "../data/classes";
import { getBackground } from "../data/backgrounds";
import { SKILL_LABELS } from "../constants";
import { useLocale } from "../../../shared/hooks/useLocale";

type Props = {
  sheet: CharacterSheet;
  pickExpertise: SheetActions["pickExpertise"];
  missingRequiredFields?: RequiredField[];
};

export const ClassExpertisePicker = ({ sheet, pickExpertise, missingRequiredFields = [] }: Props) => {
  const { t } = useLocale();
  const cls = getClass(sheet.class);
  if (!cls || !hasExpertiseAtCreation(cls, sheet.level)) return null;

  // All proficient skills: background + class choices
  const bgSkills = new Set<SkillName>(getBackground(sheet.background)?.skillProficiencies ?? []);
  const proficientSkills = new Set<SkillName>([...bgSkills, ...sheet.classSkillChoices]);
  const allSkills = Object.keys(SKILL_LABELS) as SkillName[];

  const chosen = new Set(sheet.expertiseChoices);
  const slotsUsed = sheet.expertiseChoices.length;
  const slotsTotal = cls.expertiseCount;
  const remaining = slotsTotal - slotsUsed;
  const hasError = missingRequiredFields.includes("expertise");

  return (
    <div className={`mt-5 rounded-[24px] border bg-slate-950/55 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] ${hasError ? "border-red-500/40" : "border-white/8"}`}>
      <div className="mb-3 flex items-center justify-between">
        <span className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
          {cls.name} — {t("sheet.expertisePicker.title")}
        </span>
        <span className={`rounded-full px-2.5 py-1 text-[11px] font-bold ${remaining > 0 ? "bg-amber-500/10 text-amber-300" : "bg-emerald-500/10 text-emerald-300"}`}>
          {t("sheet.expertisePicker.chosen").replace("{used}", String(slotsUsed)).replace("{total}", String(slotsTotal))}
        </span>
      </div>

      <div className="flex flex-wrap gap-2">
        {allSkills.map((skill) => {
          const isProficient = proficientSkills.has(skill);
          const isChosen = chosen.has(skill);
          const canPick = isProficient && (isChosen || remaining > 0);

          if (!isProficient) {
            return (
              <span
                key={skill}
                title={t("sheet.expertisePicker.notProficient")}
                className="rounded-full border border-white/5 bg-transparent px-3 py-1.5 text-[11px] text-slate-700"
              >
                {SKILL_LABELS[skill]}
              </span>
            );
          }

          return (
            <button
              key={skill}
              type="button"
              onClick={() => pickExpertise(skill)}
              disabled={!canPick}
              className={`rounded-full border px-3 py-1.5 text-[11px] font-semibold transition-all ${
                isChosen
                  ? "border-violet-500/40 bg-violet-500/15 text-violet-200"
                  : canPick
                    ? "border-white/8 bg-white/[0.02] text-slate-300 hover:border-slate-400/40 hover:text-slate-100"
                    : "cursor-not-allowed border-white/5 bg-transparent text-slate-600"
              }`}
            >
              {SKILL_LABELS[skill]}
            </button>
          );
        })}
      </div>

      {remaining > 0 && (
        <p className={`mt-2 text-[10px] ${hasError ? "text-red-400" : "text-amber-500/80"}`}>
          {remaining > 1
            ? t("sheet.expertisePicker.chooseMorePlural").replace("{n}", String(remaining))
            : t("sheet.expertisePicker.chooseMore").replace("{n}", String(remaining))}
        </p>
      )}
    </div>
  );
};
