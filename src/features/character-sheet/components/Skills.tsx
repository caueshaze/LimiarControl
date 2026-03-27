import type { CharacterSheet, ProficiencyLevel, SkillName } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import { Section } from "./Section";
import { chk } from "./styles";
import { ABILITY_SHORT, SKILL_ABILITY_MAP, SKILL_LABELS, SKILL_NAMES } from "../constants";
import { computePassivePerception, computeSkillMod, formatMod } from "../utils/calculations";
import { useLocale } from "../../../shared/hooks/useLocale";

type Props = {
  className?: string;
  abilities: CharacterSheet["abilities"];
  skillProficiencies: CharacterSheet["skillProficiencies"];
  level: number;
  onCycleProf: SheetActions["cycleSkillProf"];
  readOnly?: boolean;
};

export const Skills = ({ className, abilities, skillProficiencies, level, onCycleProf, readOnly = false }: Props) => {
  const { t } = useLocale();
  const passivePerception = computePassivePerception({ abilities, skillProficiencies, level } as CharacterSheet);

  return (
    <Section title={t("sheet.skills.title")} color="bg-cyan-500" className={className}>
      <div className="space-y-1.5">
        {SKILL_NAMES.map((skill) => {
          const total = computeSkillMod(skill, abilities, skillProficiencies, level);
          const profLevel = skillProficiencies[skill];
          return (
            <SkillRow
              key={skill}
              skill={skill}
              total={total}
              profLevel={profLevel}
              abilityShort={ABILITY_SHORT[SKILL_ABILITY_MAP[skill]]}
              onCycleProf={onCycleProf}
              readOnly={readOnly}
              cycleProfTitle={t("sheet.skills.cycleProficiency")}
            />
          );
        })}
      </div>
      <div className="mt-3 flex items-center gap-2 border-t border-white/6 pt-3 text-xs text-slate-400">
        <span className="font-bold">{t("sheet.skills.passivePerception")}:</span>
        <span className="text-sm font-bold text-slate-200">{passivePerception}</span>
      </div>
    </Section>
  );
};

type RowProps = {
  skill: SkillName;
  total: number;
  profLevel: ProficiencyLevel;
  abilityShort: string;
  onCycleProf: (s: SkillName) => void;
  readOnly: boolean;
  cycleProfTitle: string;
};

const PROF_STYLE: Record<number, string> = {
  2: "border-amber-500 bg-amber-500/30 text-amber-300",
  1: "border-limiar-500 bg-limiar-500/30 text-limiar-300",
  0.5: "border-slate-500 bg-slate-500/20 text-slate-400",
  0: "border-slate-700 bg-transparent text-slate-700",
};

const PROF_LABEL: Record<number, string> = { 2: "E", 1: "P", 0.5: "H", 0: "" };

const SkillRow = ({ skill, total, profLevel, abilityShort, onCycleProf, readOnly, cycleProfTitle }: RowProps) => (
  <div className="flex items-center gap-2.5 rounded-xl border border-white/6 bg-white/3 px-3 py-1.5 transition-all hover:border-white/10 hover:bg-white/5">
    <button
      type="button"
      onClick={() => onCycleProf(skill)}
      disabled={readOnly}
      title={cycleProfTitle}
      className={`h-6 w-6 shrink-0 rounded-full border text-[10px] font-bold transition-colors ${PROF_STYLE[profLevel]} ${readOnly ? "cursor-not-allowed opacity-70" : ""}`}
    >
      {PROF_LABEL[profLevel]}
    </button>
    <span className="inline-flex min-w-10 justify-center rounded-full bg-slate-950/80 px-2.5 py-1 text-sm font-bold text-slate-100">{formatMod(total)}</span>
    <span className="min-w-0 flex-1 text-sm font-medium leading-snug text-slate-300">{SKILL_LABELS[skill]}</span>
    <span className="shrink-0 rounded-full bg-white/4 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
      {abilityShort}
    </span>
  </div>
);

export { chk };
