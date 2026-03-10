import type { AbilityName, CharacterSheet, Weapon } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import { Section } from "./Section";
import { RemoveBtn } from "./Section";
import { input, fieldLabel, chk, btnPrimary } from "./styles";
import { ABILITIES, DAMAGE_TYPES } from "../constants";
import { computeWeaponAttack, computeWeaponDamage, formatMod, safeParseInt } from "../utils/calculations";

type Props = {
  weapons: CharacterSheet["weapons"];
  abilities: CharacterSheet["abilities"];
  level: number;
  readOnly?: boolean;
  onAdd: SheetActions["addWeapon"];
  onRemove: SheetActions["removeWeapon"];
  onUpdate: SheetActions["updateWeapon"];
};

export const Weapons = ({ weapons, abilities, level, readOnly = false, onAdd, onRemove, onUpdate }: Props) => (
  <Section title="Attacks & Weapons" color="bg-orange-500">
    <div className="space-y-3">
      {weapons.map((weapon) => (
        <WeaponRow
          key={weapon.id}
          weapon={weapon}
          abilities={abilities}
          level={level}
          readOnly={readOnly}
          onRemove={onRemove}
          onUpdate={onUpdate}
        />
      ))}
    </div>
    {!readOnly && (
      <button type="button" onClick={onAdd} className={`mt-4 ${btnPrimary}`}>
        Add Weapon
      </button>
    )}
  </Section>
);

type RowProps = {
  weapon: Weapon;
  abilities: CharacterSheet["abilities"];
  level: number;
  readOnly: boolean;
  onRemove: SheetActions["removeWeapon"];
  onUpdate: SheetActions["updateWeapon"];
};

const WeaponRow = ({ weapon, abilities, level, readOnly, onRemove, onUpdate }: RowProps) => {
  const atkBonus = computeWeaponAttack(weapon, abilities, level);
  const dmg = computeWeaponDamage(weapon, abilities);

  return (
    <div className="rounded-xl border border-slate-800/60 bg-void-950/40 p-4">
      <div className="flex flex-wrap items-start gap-3">
        <div className="flex-1 space-y-2">
          <input
            type="text" placeholder="Weapon name" value={weapon.name}
            disabled={readOnly}
            onChange={(e) => onUpdate(weapon.id, "name", e.target.value)}
            className={`font-bold ${input}`}
          />
          <div className="flex gap-4 text-xs">
            <span className="text-slate-400">Atk: <span className="font-bold text-limiar-400">{formatMod(atkBonus)}</span></span>
            <span className="text-slate-400">Dmg: <span className="font-bold text-slate-200">{dmg} {weapon.damageType}</span></span>
          </div>
        </div>
        {!readOnly && <RemoveBtn onClick={() => onRemove(weapon.id)} title="Remove weapon" />}
      </div>

      <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div>
          <label className={fieldLabel}>Ability</label>
          <select value={weapon.ability} disabled={readOnly} onChange={(e) => onUpdate(weapon.id, "ability", e.target.value as AbilityName)} className={input}>
            {ABILITIES.map((a) => <option key={a.key} value={a.key}>{a.short}</option>)}
          </select>
        </div>
        <div>
          <label className={fieldLabel}>Damage Dice</label>
          <input type="text" placeholder="1d8" value={weapon.damageDice} disabled={readOnly} onChange={(e) => onUpdate(weapon.id, "damageDice", e.target.value)} className={input} />
        </div>
        <div>
          <label className={fieldLabel}>Damage Type</label>
          <select value={weapon.damageType} disabled={readOnly} onChange={(e) => onUpdate(weapon.id, "damageType", e.target.value)} className={input}>
            {DAMAGE_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
        <div>
          <label className={fieldLabel}>Magic Bonus</label>
          <input type="number" min={0} max={3} value={weapon.magicBonus} disabled={readOnly} onChange={(e) => onUpdate(weapon.id, "magicBonus", Math.max(0, safeParseInt(e.target.value)))} className={input} />
        </div>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-3">
        <div>
          <label className={fieldLabel}>Properties</label>
          <input type="text" placeholder="Finesse, Light..." value={weapon.properties} disabled={readOnly} onChange={(e) => onUpdate(weapon.id, "properties", e.target.value)} className={input} />
        </div>
        <div>
          <label className={fieldLabel}>Range</label>
          <input type="text" placeholder="150/600" value={weapon.range} disabled={readOnly} onChange={(e) => onUpdate(weapon.id, "range", e.target.value)} className={input} />
        </div>
      </div>

      <label className="mt-3 flex items-center gap-2">
        <input type="checkbox" checked={weapon.proficient} disabled={readOnly} onChange={() => onUpdate(weapon.id, "proficient", !weapon.proficient)} className={chk} />
        <span className="text-xs text-slate-400">Proficient</span>
      </label>
    </div>
  );
};
