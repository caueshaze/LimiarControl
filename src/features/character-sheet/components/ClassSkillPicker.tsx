import type { CharacterSheet, SkillName } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import { getClass } from "../data/classes";
import { getBackground } from "../data/backgrounds";
import { SKILL_LABELS } from "../constants";

type Props = {
  sheet: CharacterSheet;
  pickClassSkill: SheetActions["pickClassSkill"];
};

export const ClassSkillPicker = ({ sheet, pickClassSkill }: Props) => {
  const cls = getClass(sheet.class);
  if (!cls) return null;

  const bgSkills = new Set(getBackground(sheet.background)?.skillProficiencies ?? []);
  const chosen = new Set(sheet.classSkillChoices);
  const slotsUsed = sheet.classSkillChoices.length;
  const slotsTotal = cls.skillCount;
  const remaining = slotsTotal - slotsUsed;

  return (
    <div className="mt-5 rounded-[24px] border border-white/8 bg-slate-950/55 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
          {cls.name} — Class Skills
        </span>
        <span className={`rounded-full px-2.5 py-1 text-[11px] font-bold ${remaining > 0 ? "bg-amber-500/10 text-amber-300" : "bg-emerald-500/10 text-emerald-300"}`}>
          {slotsUsed}/{slotsTotal} chosen
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
                title="Already granted by background"
                className="rounded-full border border-white/8 bg-white/[0.03] px-3 py-1.5 text-[11px] text-slate-500 line-through"
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
                    ? "border-white/8 bg-white/[0.02] text-slate-300 hover:border-slate-400/40 hover:text-slate-100"
                    : "cursor-not-allowed border-white/5 bg-transparent text-slate-700"
              }`}
            >
              {SKILL_LABELS[skill]}
            </button>
          );
        })}
      </div>

      {remaining > 0 && (
        <p className="mt-2 text-[10px] text-amber-500/80">
          Choose {remaining} more skill{remaining > 1 ? "s" : ""}
        </p>
      )}
    </div>
  );
};
