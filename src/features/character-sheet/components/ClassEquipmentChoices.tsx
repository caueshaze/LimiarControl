import type { CharacterSheet } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import { getClassCreationConfig } from "../data/classCreation";
import { fieldLabel, input } from "./styles";

type Props = {
  className: string;
  selections: CharacterSheet["classEquipmentSelections"];
  onSelect: SheetActions["selectClassEquipment"];
};

export const ClassEquipmentChoices = ({ className, selections, onSelect }: Props) => {
  const config = getClassCreationConfig(className);
  if (!config || config.equipmentChoices.length === 0) return null;

  return (
    <div className="mt-5 rounded-[24px] border border-white/8 bg-slate-950/55 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
          Starting Equipment Choices
        </span>
        <span className="rounded-full bg-white/[0.04] px-2.5 py-1 text-[11px] font-semibold text-slate-300">
          {config.equipmentChoices.length} groups
        </span>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {config.equipmentChoices.map((group) => {
          const selectedId = selections[group.id] ?? group.options[0]?.id ?? "";
          return (
            <div key={group.id}>
              <label className={fieldLabel}>{group.label}</label>
              <select
                value={selectedId}
                onChange={(event) => onSelect(group.id, event.target.value)}
                className={input}
              >
                {group.options.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          );
        })}
      </div>
    </div>
  );
};
