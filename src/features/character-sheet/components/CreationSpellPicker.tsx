import { getAvailableStartingSpells } from "../utils/creationSpells";
import type { CharacterSheet } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";

type Props = {
  className: string;
  availableCantrips: number;
  availableLeveled: number;
  selectedSpells: NonNullable<CharacterSheet["spellcasting"]>["spells"];
  onToggle: SheetActions["toggleCreationSpellSelection"];
};

export const CreationSpellPicker = ({
  className,
  availableCantrips,
  availableLeveled,
  selectedSpells,
  onToggle,
}: Props) => {
  const options = getAvailableStartingSpells(className);
  const selectedNames = new Set(selectedSpells.map((spell) => spell.name.toLowerCase()));

  return (
    <div className="mt-5 space-y-4">
      <SpellChoiceGroup
        title={`Cantrips (${selectedSpells.filter((spell) => spell.level === 0).length}/${availableCantrips})`}
        limitReached={selectedSpells.filter((spell) => spell.level === 0).length >= availableCantrips}
        selectedNames={selectedNames}
        names={options.cantrips.map((spell) => spell.name)}
        onToggle={onToggle}
      />
      <SpellChoiceGroup
        title={`Level 1 Spells (${selectedSpells.filter((spell) => spell.level === 1).length}/${availableLeveled})`}
        limitReached={selectedSpells.filter((spell) => spell.level === 1).length >= availableLeveled}
        selectedNames={selectedNames}
        names={options.leveled.map((spell) => spell.name)}
        onToggle={onToggle}
      />
    </div>
  );
};

type SpellChoiceGroupProps = {
  title: string;
  limitReached: boolean;
  selectedNames: Set<string>;
  names: string[];
  onToggle: SheetActions["toggleCreationSpellSelection"];
};

const SpellChoiceGroup = ({ title, limitReached, selectedNames, names, onToggle }: SpellChoiceGroupProps) => (
  <div>
    <div className="mb-2 flex items-center justify-between">
      <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">{title}</p>
      {limitReached && <span className="text-[10px] font-semibold text-amber-300">Limit reached</span>}
    </div>
    <div className="flex max-h-48 flex-wrap gap-2 overflow-y-auto pr-1">
      {names.map((name) => {
        const selected = selectedNames.has(name.toLowerCase());
        return (
          <button
            key={name}
            type="button"
            onClick={() => onToggle(name)}
            className={`rounded-full border px-3 py-1.5 text-[11px] font-semibold transition-all ${
              selected
                ? "border-violet-500/40 bg-violet-500/15 text-violet-200"
                : "border-white/8 bg-white/[0.02] text-slate-300 hover:border-white/14 hover:text-slate-100"
            }`}
          >
            {name}
          </button>
        );
      })}
    </div>
  </div>
);
