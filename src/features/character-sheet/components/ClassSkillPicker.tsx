import type { CharacterSheet, SkillName } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import type { RequiredField } from "../utils/creationValidation";
import { getClass } from "../data/classes";
import { getBackground } from "../data/backgrounds";
import { SKILL_LABELS } from "../constants";
import { useLocale } from "../../../shared/hooks/useLocale";

type Props = {
  sheet: CharacterSheet;
  pickClassSkill: SheetActions["pickClassSkill"];
  missingRequiredFields?: RequiredField[];
};

export const ClassSkillPicker = ({ sheet, pickClassSkill, missingRequiredFields = [] }: Props) => {
  const { t } = useLocale();
  const cls = getClass(sheet.class);
  if (!cls) return null;

  const bgSkills = new Set(getBackground(sheet.background)?.skillProficiencies ?? []);
  const chosen = new Set(sheet.classSkillChoices);
  const slotsUsed = sheet.classSkillChoices.length;
  const slotsTotal = cls.skillCount;
  const remaining = slotsTotal - slotsUsed;
  const hasError = missingRequiredFields.includes("classSkills");

  return (
    <div className={`mt-5 rounded-[24px] border bg-slate-950/55 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] ${hasError ? "border-red-500/40" : "border-white/8"}`}>
      <div className="mb-3 flex items-center justify-between">
        <span className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
          {cls.name} — {t("sheet.skillPicker.classSkills")}
        </span>
        <span className={`rounded-full px-2.5 py-1 text-[11px] font-bold ${remaining > 0 ? "bg-amber-500/10 text-amber-300" : "bg-emerald-500/10 text-emerald-300"}`}>
          {t("sheet.skillPicker.chosen").replace("{used}", String(slotsUsed)).replace("{total}", String(slotsTotal))}
        </span>
      </div>

      <div className="flex flex-wrap gap-2">
        {cls.skillChoices.map((skill: SkillName) => {
          const fromBg = bgSkills.has(skill);
          const isChosen = chosen.has(skill);
          const canPick = !fromBg && (isChosen || remaining > 0);

          if (fromBg) {
            return (
              <span
                key={skill}
                title={t("sheet.skillPicker.fromBg")}
                className="rounded-full border border-white/8 bg-white/3 px-3 py-1.5 text-[11px] text-slate-500 line-through"
              >
                {SKILL_LABELS[skill]}
              </span>
            );
          }

          return (
            <button
              key={skill}
              type="button"
              onClick={() => pickClassSkill(skill)}
              disabled={!canPick && !isChosen}
              className={`rounded-full border px-3 py-1.5 text-[11px] font-semibold transition-all ${
                isChosen
                  ? "border-limiar-500/40 bg-limiar-500/15 text-limiar-200"
                  : canPick
                    ? "border-white/8 bg-white/2 text-slate-300 hover:border-slate-400/40 hover:text-slate-100"
                    : "cursor-not-allowed border-white/5 bg-transparent text-slate-700"
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
            ? t("sheet.skillPicker.chooseMorePlural").replace("{n}", String(remaining))
            : t("sheet.skillPicker.chooseMore").replace("{n}", String(remaining))}
        </p>
      )}
    </div>
  );
};
