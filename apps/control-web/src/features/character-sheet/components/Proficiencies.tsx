import { useRef } from "react";
import type { CharacterSheet } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import { Section } from "./Section";
import { tagBadge } from "./styles";
import { useLocale } from "../../../shared/hooks/useLocale";
import type { LocaleKey } from "../../../shared/i18n";

type TagField = "languages" | "toolProficiencies" | "weaponProficiencies" | "armorProficiencies";

type Props = {
  languages: CharacterSheet["languages"];
  toolProficiencies: CharacterSheet["toolProficiencies"];
  weaponProficiencies: CharacterSheet["weaponProficiencies"];
  armorProficiencies: CharacterSheet["armorProficiencies"];
  onAddTag: SheetActions["addTag"];
  onRemoveTag: SheetActions["removeTag"];
  readOnly?: boolean;
  catalogOptions?: Partial<Record<TagField, string[]>>;
};

export const Proficiencies = ({
  languages, toolProficiencies, weaponProficiencies, armorProficiencies,
  onAddTag, onRemoveTag, readOnly = false,
  catalogOptions,
}: Props) => {
  const { t } = useLocale();

  return (
    <Section title={t("sheet.proficiencies.title")} color="bg-teal-500">
      <div className="space-y-4">
        <TagGroup label={t("sheet.proficiencies.languages")} items={languages} field="languages" placeholder={t("sheet.proficiencies.addLang")} onAdd={onAddTag} onRemove={onRemoveTag} readOnly={readOnly} t={t} options={catalogOptions?.languages} />
        <TagGroup label={t("sheet.proficiencies.tools")} items={toolProficiencies} field="toolProficiencies" placeholder={t("sheet.proficiencies.addTool")} onAdd={onAddTag} onRemove={onRemoveTag} readOnly={readOnly} t={t} options={catalogOptions?.toolProficiencies} />
        <TagGroup label={t("sheet.proficiencies.weapons")} items={weaponProficiencies} field="weaponProficiencies" placeholder={t("sheet.proficiencies.addWeapon")} onAdd={onAddTag} onRemove={onRemoveTag} readOnly={readOnly} t={t} options={catalogOptions?.weaponProficiencies} />
        <TagGroup label={t("sheet.proficiencies.armors")} items={armorProficiencies} field="armorProficiencies" placeholder={t("sheet.proficiencies.addArmor")} onAdd={onAddTag} onRemove={onRemoveTag} readOnly={readOnly} t={t} options={catalogOptions?.armorProficiencies} />
      </div>
    </Section>
  );
};

type TagGroupProps = {
  label: string;
  items: string[];
  field: TagField;
  placeholder: string;
  onAdd: SheetActions["addTag"];
  onRemove: SheetActions["removeTag"];
  readOnly: boolean;
  t: (key: LocaleKey) => string;
  options?: string[];
};

const normalizeOption = (value: string) =>
  value
    .trim()
    .toLocaleLowerCase("pt-BR");

const TagGroup = ({ label, items, field, placeholder, onAdd, onRemove, readOnly, t, options }: TagGroupProps) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const selectRef = useRef<HTMLSelectElement>(null);
  const availableOptions = (options ?? []).filter((option) =>
    !items.some((item) => normalizeOption(item) === normalizeOption(option)),
  );

  const handleAdd = () => {
    const val = inputRef.current?.value.trim();
    if (!val) return;
    onAdd(field, val);
    if (inputRef.current) inputRef.current.value = "";
  };

  const handleSelectAdd = () => {
    const value = selectRef.current?.value.trim();
    if (!value) return;
    onAdd(field, value);
    if (selectRef.current) selectRef.current.value = "";
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
              title={t("sheet.proficiencies.remove").replace("{item}", item)}
            >
              ×
            </button>
          </span>
        ))}
        {!readOnly && (
          <div className="flex">
            {options ? (
              <select
                ref={selectRef}
                defaultValue=""
                className="h-[26px] w-40 rounded-l-full border border-white/10 bg-void-900/50 px-2.5 text-[11px] text-slate-300 focus:border-limiar-500 focus:outline-none"
              >
                <option value="">{placeholder}</option>
                {availableOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            ) : (
              <input
                ref={inputRef}
                type="text"
                placeholder={placeholder}
                onKeyDown={handleKeyDown}
                className="h-[26px] w-28 rounded-l-full border border-white/10 bg-void-900/50 px-2.5 text-[11px] text-slate-300 placeholder-slate-600 focus:border-limiar-500 focus:outline-none"
              />
            )}
            <button
              type="button"
              onClick={options ? handleSelectAdd : handleAdd}
              disabled={!!options && availableOptions.length === 0}
              className="rounded-r-full border border-l-0 border-white/10 bg-void-900/50 px-2 text-[11px] text-limiar-400 transition-colors hover:bg-limiar-600/20 disabled:cursor-not-allowed disabled:opacity-50"
            >
              +
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
