import { useEffect, useState } from "react";
import { loadSpellCatalog, isSpellCatalogLoaded } from "../../../entities/dnd-base";
import { getAvailableStartingSpells } from "../utils/creationSpells";
import type { CharacterSheet } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";

type Props = {
  campaignId?: string | null;
  className: string;
  availableCantrips: number;
  availableLeveled: number;
  selectedSpells: NonNullable<CharacterSheet["spellcasting"]>["spells"];
  onToggle: SheetActions["toggleCreationSpellSelection"];
};

export const CreationSpellPicker = ({
  campaignId = null,
  className,
  availableCantrips,
  availableLeveled,
  selectedSpells,
  onToggle,
}: Props) => {
  const [ready, setReady] = useState(isSpellCatalogLoaded(campaignId));

  useEffect(() => {
    setReady(isSpellCatalogLoaded(campaignId));
  }, [campaignId]);

  useEffect(() => {
    if (ready) return;
    loadSpellCatalog(campaignId).then(() => setReady(true));
  }, [campaignId, ready]);

  if (!ready) {
    return (
      <div className="mt-5 flex items-center gap-2 text-xs text-slate-500">
        <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <circle cx="12" cy="12" r="10" strokeOpacity={0.25} />
          <path d="M12 2a10 10 0 019.5 6.5" strokeLinecap="round" />
        </svg>
        Loading spells...
      </div>
    );
  }

  const options = getAvailableStartingSpells(className, campaignId);
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
