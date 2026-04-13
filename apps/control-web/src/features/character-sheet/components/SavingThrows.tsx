import type { AbilityName, CharacterSheet } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import { Section } from "./Section";
import { chk } from "./styles";
import { ABILITIES } from "../constants";
import { computeSaveMod, formatMod } from "../utils/calculations";
import { useLocale } from "../../../shared/hooks/useLocale";

type Props = {
  className?: string;
  abilities: CharacterSheet["abilities"];
  savingThrowProficiencies: CharacterSheet["savingThrowProficiencies"];
  level: number;
  onToggle: SheetActions["toggleSaveProf"];
  readOnly?: boolean;
};

export const SavingThrows = ({ className, abilities, savingThrowProficiencies, level, onToggle, readOnly = false }: Props) => {
  const { t } = useLocale();

  return (
    <Section title={t("sheet.saves.title")} color="bg-amber-500" className={className}>
      <div className="space-y-1.5">
        {ABILITIES.map(({ key, short }) => {
          const total = computeSaveMod(key, abilities[key], savingThrowProficiencies[key], level);
          return (
            <SaveRow
              key={key}
              abilityKey={key}
              short={short}
              total={total}
              proficient={savingThrowProficiencies[key]}
              onToggle={onToggle}
              readOnly={readOnly}
              labelProf={t("sheet.saves.prof")}
              labelBase={t("sheet.saves.base")}
            />
          );
        })}
      </div>
    </Section>
  );
};

type RowProps = {
  abilityKey: AbilityName;
  short: string;
  total: number;
  proficient: boolean;
  onToggle: (a: AbilityName) => void;
  readOnly: boolean;
  labelProf: string;
  labelBase: string;
};

const SaveRow = ({ abilityKey, short, total, proficient, onToggle, readOnly, labelProf, labelBase }: RowProps) => (
  <label className={`flex items-center gap-2.5 rounded-xl border border-white/6 bg-white/3 px-3 py-2 transition-all ${readOnly ? "" : "cursor-pointer hover:border-white/10 hover:bg-white/5"}`}>
    <input type="checkbox" checked={proficient} disabled={readOnly} onChange={() => onToggle(abilityKey)} className={chk} />
    <span className="inline-flex min-w-10 justify-center rounded-full bg-slate-950/80 px-2.5 py-1 text-sm font-bold text-slate-100">{formatMod(total)}</span>
    <span className="text-sm font-medium text-slate-300">{short}</span>
    <span className={`ml-auto rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.24em] ${proficient ? "bg-amber-500/10 text-amber-300" : "bg-white/4 text-slate-500"}`}>
      {proficient ? labelProf : labelBase}
    </span>
  </label>
);
