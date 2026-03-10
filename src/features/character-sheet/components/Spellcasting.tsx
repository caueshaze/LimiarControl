import type { AbilityName, CharacterSheet, Spell } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import { Section, RemoveBtn } from "./Section";
import { input, fieldLabel, btnPrimary, btnDanger, chk } from "./styles";
import { ABILITIES, SPELL_SCHOOLS } from "../constants";
import { computeSpellAttack, computeSpellSaveDC, formatMod, safeParseInt } from "../utils/calculations";
import { getClassCreationConfig } from "../data/classCreation";
import { getStartingSpellLimits } from "../utils/creationSpells";
import { CreationSpellPicker } from "./CreationSpellPicker";

type Props = {
  className?: string;
  spellcasting: CharacterSheet["spellcasting"];
  abilities: CharacterSheet["abilities"];
  level: number;
  readOnly?: boolean;
  onEnable: SheetActions["enableSpellcasting"];
  onDisable: SheetActions["disableSpellcasting"];
  onSetAbility: SheetActions["setSpellAbility"];
  onSetSlot: SheetActions["setSpellSlot"];
  onAddSpell: SheetActions["addSpell"];
  onRemoveSpell: SheetActions["removeSpell"];
  onUpdateSpell: SheetActions["updateSpell"];
  onToggleCreationSpell?: SheetActions["toggleCreationSpellSelection"];
};

export const Spellcasting = ({
  className = "",
  spellcasting, abilities, level,
  readOnly = false,
  onEnable, onDisable, onSetAbility,
  onSetSlot, onAddSpell, onRemoveSpell, onUpdateSpell,
  onToggleCreationSpell,
}: Props) => {
  const creationConfig = className ? getClassCreationConfig(className)?.startingSpells : null;

  if (!spellcasting) {
    return (
      <Section title="Spellcasting" color="bg-violet-500" defaultOpen={false}>
        <div className="flex flex-col items-center gap-3 py-4">
          <p className="text-xs text-slate-500">
            {readOnly ? "No spellcasting for this class at creation." : "This character has no spellcasting."}
          </p>
          {!readOnly && (
            <button type="button" onClick={onEnable} className={btnPrimary}>
              Enable Spellcasting
            </button>
          )}
        </div>
      </Section>
    );
  }

  const abilityScore = abilities[spellcasting.ability];
  const saveDC = computeSpellSaveDC(level, abilityScore);
  const atkBonus = computeSpellAttack(level, abilityScore);
  const startingSpellLimits = className ? getStartingSpellLimits(className, abilities, level) : null;

  return (
    <Section title="Spellcasting" color="bg-violet-500">
      <div className="flex flex-wrap items-end gap-4">
        <div>
          <label className={fieldLabel}>Spellcasting Ability</label>
          {readOnly ? (
            <input
              type="text"
              value={spellcasting.ability.toUpperCase()}
              disabled
              className={`${input} opacity-70`}
              style={{ width: "auto" }}
            />
          ) : (
            <select
              value={spellcasting.ability}
              onChange={(e) => onSetAbility(e.target.value as AbilityName)}
              className={input}
              style={{ width: "auto" }}
            >
              {ABILITIES.map((a) => (
                <option key={a.key} value={a.key}>{a.label}</option>
              ))}
            </select>
          )}
        </div>
        <div className="flex gap-4 text-sm">
          <div className="text-center">
            <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">Save DC</div>
            <div className="font-bold text-violet-300">{saveDC}</div>
          </div>
          <div className="text-center">
            <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">Atk Bonus</div>
            <div className="font-bold text-violet-300">{formatMod(atkBonus)}</div>
          </div>
        </div>
        {!readOnly && (
          <button type="button" onClick={onDisable} className={`ml-auto ${btnDanger}`}>
            Remove Spellcasting
          </button>
        )}
      </div>

      {readOnly && startingSpellLimits && creationConfig && onToggleCreationSpell && (
        <>
          <div className="mt-4 rounded-2xl border border-white/6 bg-white/[0.03] px-4 py-3 text-xs text-slate-400">
            <p className="font-semibold text-slate-200">
              Level 1 Slots: <span className="text-violet-300">{startingSpellLimits.levelOneSlots}</span>
            </p>
            <p className="mt-1">
              {creationConfig.leveledMode === "spellbook"
                ? "Pick the spells that go into your spellbook."
                : creationConfig.leveledMode === "prepared"
                  ? "Pick the spells you want prepared at creation."
                  : "Pick the spells your class knows at level 1."}
            </p>
          </div>
          <CreationSpellPicker
            className={className}
            availableCantrips={startingSpellLimits.cantrips}
            availableLeveled={startingSpellLimits.leveledSpells}
            selectedSpells={spellcasting.spells}
            onToggle={onToggleCreationSpell}
          />
        </>
      )}

      {!readOnly && <div className="mt-4">
        <div className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-500">Spell Slots</div>
        <div className="flex flex-wrap gap-2">
          {Array.from({ length: 9 }, (_, i) => i + 1).map((lvl) => {
            const slot = spellcasting.slots[lvl] ?? { max: 0, used: 0 };
            if (slot.max === 0 && slot.used === 0) return null;
            return (
              <SlotPip key={lvl} level={lvl} slot={slot} onSetSlot={onSetSlot} />
            );
          })}
        </div>
        <div className="mt-2 grid grid-cols-3 gap-2 sm:grid-cols-5 md:grid-cols-9">
          {Array.from({ length: 9 }, (_, i) => i + 1).map((lvl) => {
            const slot = spellcasting.slots[lvl] ?? { max: 0, used: 0 };
            return (
              <div key={lvl} className="flex flex-col items-center gap-1">
                <span className="text-[9px] font-semibold uppercase text-slate-600">Lv{lvl}</span>
                <input
                  type="number" min={0} max={9} value={slot.max}
                  onChange={(e) => onSetSlot(lvl, "max", safeParseInt(e.target.value))}
                  className="w-full rounded-lg border border-white/10 bg-void-900/50 py-1 text-center text-xs font-bold text-slate-100 focus:border-violet-500 focus:outline-none"
                  title={`Level ${lvl} max slots`}
                />
                <input
                  type="number" min={0} max={slot.max} value={slot.used}
                  onChange={(e) => onSetSlot(lvl, "used", safeParseInt(e.target.value))}
                  className="w-full rounded-lg border border-white/10 bg-void-900/50 py-1 text-center text-xs text-slate-400 focus:border-violet-500 focus:outline-none"
                  title={`Level ${lvl} used slots`}
                />
              </div>
            );
          })}
        </div>
        <div className="mt-1 flex justify-center gap-6 text-[10px] text-slate-600">
          <span>Top = Max slots</span>
          <span>Bottom = Used slots</span>
        </div>
      </div>}

      {!readOnly && <div className="mt-4">
        <div className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-500">Known / Prepared Spells</div>
        <div className="space-y-2">
          {spellcasting.spells.map((spell) => (
            <SpellRow key={spell.id} spell={spell} onRemove={onRemoveSpell} onUpdate={onUpdateSpell} />
          ))}
          {spellcasting.spells.length === 0 && (
            <p className="py-2 text-center text-xs text-slate-600">No spells added yet.</p>
          )}
        </div>
        <button type="button" onClick={onAddSpell} className={`mt-3 ${btnPrimary}`}>
          Add Spell
        </button>
      </div>}
    </Section>
  );
};

type SlotPipProps = {
  level: number;
  slot: { max: number; used: number };
  onSetSlot: SheetActions["setSpellSlot"];
};

const SlotPip = ({ level, slot, onSetSlot }: SlotPipProps) => (
  <div className="flex items-center gap-1.5 rounded-full border border-slate-700 bg-void-950/60 px-2.5 py-1">
    <span className="text-[10px] font-bold text-violet-400">L{level}</span>
    {Array.from({ length: slot.max }, (_, i) => (
      <button
        key={i}
        type="button"
        onClick={() => onSetSlot(level, "used", i < slot.used ? i : i + 1)}
        title={i < slot.used ? "Mark unused" : "Mark used"}
        className={`h-3 w-3 rounded-full border transition-colors ${
          i < slot.used
            ? "border-slate-600 bg-slate-700"
            : "border-violet-500 bg-violet-500/40"
        }`}
      />
    ))}
  </div>
);

type SpellRowProps = {
  spell: Spell;
  onRemove: SheetActions["removeSpell"];
  onUpdate: SheetActions["updateSpell"];
};

const SpellRow = ({ spell, onRemove, onUpdate }: SpellRowProps) => (
  <div className="flex items-start gap-2 rounded-xl border border-slate-800/60 bg-void-950/40 p-3">
    <div className="flex-1 grid grid-cols-2 gap-2 sm:grid-cols-4">
      <div className="sm:col-span-2">
        <label className={fieldLabel}>Spell Name</label>
        <input
          type="text" placeholder="Spell name" value={spell.name}
          onChange={(e) => onUpdate(spell.id, "name", e.target.value)}
          className={input}
        />
      </div>
      <div>
        <label className={fieldLabel}>Level</label>
        <select value={spell.level} onChange={(e) => onUpdate(spell.id, "level", safeParseInt(e.target.value))} className={input}>
          <option value={0}>Cantrip</option>
          {Array.from({ length: 9 }, (_, i) => i + 1).map((l) => (
            <option key={l} value={l}>{l}</option>
          ))}
        </select>
      </div>
      <div>
        <label className={fieldLabel}>School</label>
        <select value={spell.school} onChange={(e) => onUpdate(spell.id, "school", e.target.value)} className={input}>
          {SPELL_SCHOOLS.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>
      <div className="sm:col-span-3">
        <label className={fieldLabel}>Notes</label>
        <input
          type="text" placeholder="Concentration, 1 hour..." value={spell.notes}
          onChange={(e) => onUpdate(spell.id, "notes", e.target.value)}
          className={input}
        />
      </div>
      <div className="flex items-end pb-1">
        <label className="flex items-center gap-2 text-xs text-slate-400">
          <input
            type="checkbox" checked={spell.prepared}
            onChange={() => onUpdate(spell.id, "prepared", !spell.prepared)}
            className={chk}
          />
          Prepared
        </label>
      </div>
    </div>
    <RemoveBtn onClick={() => onRemove(spell.id)} title="Remove spell" />
  </div>
);
