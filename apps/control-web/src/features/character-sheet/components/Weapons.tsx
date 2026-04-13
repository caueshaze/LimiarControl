import type { AbilityName, CharacterSheet, Weapon } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import { Section } from "./Section";
import { RemoveBtn } from "./Section";
import { input, fieldLabel, chk, btnPrimary } from "./styles";
import { ABILITIES, DAMAGE_TYPES } from "../constants";
import { computeWeaponAttack, computeWeaponDamage, formatMod, safeParseInt } from "../utils/calculations";
import { useLocale } from "../../../shared/hooks/useLocale";
import type { LocaleKey } from "../../../shared/i18n";
import { WEAPON_PROPERTY_SLUGS, getItemPropertyLabel, resolveItemPropertySlug } from "../../../entities/item";
import { AUTOMATION_DICE_OPTIONS, buildAutomationSelectOptions } from "../../../shared/lib/itemAutomationOptions";

type Props = {
  weapons: CharacterSheet["weapons"];
  abilities: CharacterSheet["abilities"];
  fightingStyle: CharacterSheet["fightingStyle"];
  level: number;
  readOnly?: boolean;
  onAdd: SheetActions["addWeapon"];
  onRemove: SheetActions["removeWeapon"];
  onUpdate: SheetActions["updateWeapon"];
};

export const Weapons = ({ weapons, abilities, fightingStyle, level, readOnly = false, onAdd, onRemove, onUpdate }: Props) => {
  const { t, locale } = useLocale();

  return (
    <Section title={t("sheet.weapons.title")} color="bg-orange-500">
      <div className="space-y-3">
        {weapons.length === 0 && !readOnly && (
          <div className="flex flex-col items-center gap-2 py-4 text-slate-600">
            <svg className="h-7 w-7 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.59 14.37a6 6 0 01-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 006.16-12.12A14.98 14.98 0 009.631 8.41m5.96 5.96a14.926 14.926 0 01-5.841 2.58m-.119-8.54a6 6 0 00-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 00-2.58 5.84m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 01-2.448-2.448 14.9 14.9 0 01.06-.312m-2.24 2.39a4.493 4.493 0 00-1.757 4.306 4.493 4.493 0 004.306-1.758M16.5 9a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z" />
            </svg>
            <p className="text-xs">{t("sheet.weapons.addWeapon")}</p>
          </div>
        )}
        {weapons.map((weapon) => (
          <WeaponRow
            key={weapon.id}
            weapon={weapon}
            abilities={abilities}
            fightingStyle={fightingStyle}
            level={level}
            readOnly={readOnly}
            onRemove={onRemove}
            onUpdate={onUpdate}
            locale={locale}
            t={t}
          />
        ))}
      </div>
      {!readOnly && (
        <button type="button" onClick={onAdd} className={`mt-4 ${btnPrimary}`}>
          {t("sheet.weapons.addWeapon")}
        </button>
      )}
    </Section>
  );
};

type RowProps = {
  weapon: Weapon;
  abilities: CharacterSheet["abilities"];
  fightingStyle: CharacterSheet["fightingStyle"];
  level: number;
  readOnly: boolean;
  onRemove: SheetActions["removeWeapon"];
  onUpdate: SheetActions["updateWeapon"];
  locale: string;
  t: (key: LocaleKey) => string;
};

const normalizeWeaponProperties = (value: string) => {
  const seen = new Set<string>();
  const normalized: string[] = [];

  value
    .split(",")
    .map((entry) => entry.trim())
    .filter(Boolean)
    .forEach((entry) => {
      const normalizedEntry = resolveItemPropertySlug(entry) ?? entry;
      if (seen.has(normalizedEntry)) {
        return;
      }
      seen.add(normalizedEntry);
      normalized.push(normalizedEntry);
    });

  return normalized;
};

const buildWeaponPropertyOptions = (value: string) => {
  const selected = normalizeWeaponProperties(value);
  const seen = new Set<string>();
  const options: string[] = [];

  [...selected, ...WEAPON_PROPERTY_SLUGS].forEach((entry) => {
    if (seen.has(entry)) {
      return;
    }
    seen.add(entry);
    options.push(entry);
  });

  return options;
};

const WeaponRow = ({ weapon, abilities, fightingStyle, level, readOnly, onRemove, onUpdate, locale, t }: RowProps) => {
  const atkBonus = computeWeaponAttack(weapon, abilities, level, fightingStyle);
  const dmg = computeWeaponDamage(weapon, abilities);
  const selectedProperties = normalizeWeaponProperties(weapon.properties);
  const propertyOptions = buildWeaponPropertyOptions(weapon.properties);

  return (
    <div className="rounded-xl border border-slate-800/60 bg-void-950/40 p-4">
      <div className="flex flex-wrap items-start gap-3">
        <div className="flex-1 space-y-2">
          <input
            type="text" placeholder={t("sheet.weapons.namePlaceholder")} value={weapon.name}
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
          <label className={fieldLabel}>{t("sheet.weapons.ability")}</label>
          <select value={weapon.ability} disabled={readOnly} onChange={(e) => onUpdate(weapon.id, "ability", e.target.value as AbilityName)} className={input}>
            {ABILITIES.map((a) => <option key={a.key} value={a.key}>{a.short}</option>)}
          </select>
        </div>
        <div>
          <label className={fieldLabel}>{t("sheet.weapons.damageDice")}</label>
          <select
            value={weapon.damageDice}
            disabled={readOnly}
            onChange={(e) => onUpdate(weapon.id, "damageDice", e.target.value)}
            className={input}
          >
            {buildAutomationSelectOptions(weapon.damageDice, AUTOMATION_DICE_OPTIONS).map((option) => (
              <option key={option || "none"} value={option}>
                {option || "-"}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className={fieldLabel}>{t("sheet.weapons.damageType")}</label>
          <select value={weapon.damageType} disabled={readOnly} onChange={(e) => onUpdate(weapon.id, "damageType", e.target.value)} className={input}>
            {DAMAGE_TYPES.map((dt) => <option key={dt} value={dt}>{dt}</option>)}
          </select>
        </div>
        <div>
          <label className={fieldLabel}>{t("sheet.weapons.magicBonus")}</label>
          <input type="number" min={0} max={3} value={weapon.magicBonus} disabled={readOnly} onChange={(e) => onUpdate(weapon.id, "magicBonus", Math.max(0, safeParseInt(e.target.value)))} className={input} />
        </div>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-3">
        <div>
          <label className={fieldLabel}>{t("sheet.weapons.properties")}</label>
          <select
            multiple
            value={selectedProperties}
            disabled={readOnly}
            onChange={(e) => {
              const values = Array.from(e.target.selectedOptions, (option) => option.value);
              onUpdate(weapon.id, "properties", values.join(", "));
            }}
            className={`${input} min-h-[7rem]`}
          >
            {propertyOptions.map((property) => (
              <option key={property} value={property}>
                {getItemPropertyLabel(property, locale)}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className={fieldLabel}>{t("sheet.weapons.range")}</label>
          <input type="text" placeholder={t("sheet.weapons.rangePlaceholder")} value={weapon.range} disabled={readOnly} onChange={(e) => onUpdate(weapon.id, "range", e.target.value)} className={input} />
        </div>
      </div>

      <label className="mt-3 flex items-center gap-2">
        <input type="checkbox" checked={weapon.proficient} disabled={readOnly} onChange={() => onUpdate(weapon.id, "proficient", !weapon.proficient)} className={chk} />
        <span className="text-xs text-slate-400">{t("sheet.weapons.proficient")}</span>
      </label>
    </div>
  );
};
