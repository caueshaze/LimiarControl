import { useRef } from "react";
import type { CharacterSheet } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import { Section } from "./Section";
import { tagBadge } from "./styles";

type TagField = "languages" | "toolProficiencies" | "weaponProficiencies" | "armorProficiencies";

type Props = {
  languages: CharacterSheet["languages"];
  toolProficiencies: CharacterSheet["toolProficiencies"];
  weaponProficiencies: CharacterSheet["weaponProficiencies"];
  armorProficiencies: CharacterSheet["armorProficiencies"];
  onAddTag: SheetActions["addTag"];
  onRemoveTag: SheetActions["removeTag"];
  readOnly?: boolean;
};

export const Proficiencies = ({
  languages, toolProficiencies, weaponProficiencies, armorProficiencies,
  onAddTag, onRemoveTag, readOnly = false,
}: Props) => (
  <Section title="Languages & Proficiencies" color="bg-teal-500">
    <div className="space-y-4">
      <TagGroup label="Languages" items={languages} field="languages" placeholder="Add language..." onAdd={onAddTag} onRemove={onRemoveTag} readOnly={readOnly} />
      <TagGroup label="Tool Proficiencies" items={toolProficiencies} field="toolProficiencies" placeholder="Add tool..." onAdd={onAddTag} onRemove={onRemoveTag} readOnly={readOnly} />
      <TagGroup label="Weapon Proficiencies" items={weaponProficiencies} field="weaponProficiencies" placeholder="Add weapon..." onAdd={onAddTag} onRemove={onRemoveTag} readOnly={readOnly} />
      <TagGroup label="Armor Proficiencies" items={armorProficiencies} field="armorProficiencies" placeholder="Add armor..." onAdd={onAddTag} onRemove={onRemoveTag} readOnly={readOnly} />
    </div>
  </Section>
);

type TagGroupProps = {
  label: string;
  items: string[];
  field: TagField;
  placeholder: string;
  onAdd: SheetActions["addTag"];
  onRemove: SheetActions["removeTag"];
  readOnly: boolean;
};

const TagGroup = ({ label, items, field, placeholder, onAdd, onRemove, readOnly }: TagGroupProps) => {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleAdd = () => {
    const val = inputRef.current?.value.trim();
    if (!val) return;
    onAdd(field, val);
    if (inputRef.current) inputRef.current.value = "";
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") { e.preventDefault(); handleAdd(); }
  };

  return (
    <div>
      <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
        {label}
      </div>
      <div className="flex flex-wrap gap-1.5">
        {items.map((item, idx) => (
          <span key={idx} className={tagBadge}>
            {item}
            <button
              type="button"
              onClick={() => onRemove(field, idx)}
              disabled={readOnly}
              className="ml-0.5 text-slate-500 transition-colors hover:text-rose-400"
              title={`Remove ${item}`}
            >
              ×
            </button>
          </span>
        ))}
        {!readOnly && (
          <div className="flex">
            <input
              ref={inputRef}
              type="text"
              placeholder={placeholder}
              onKeyDown={handleKeyDown}
              className="h-[26px] w-28 rounded-l-full border border-white/10 bg-void-900/50 px-2.5 text-[11px] text-slate-300 placeholder-slate-600 focus:border-limiar-500 focus:outline-none"
            />
            <button
              type="button"
              onClick={handleAdd}
              className="rounded-r-full border border-l-0 border-white/10 bg-void-900/50 px-2 text-[11px] text-limiar-400 transition-colors hover:bg-limiar-600/20"
            >
              +
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
