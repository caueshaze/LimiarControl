import type { ReactNode } from "react";
import type {
  BaseItemArmorCategory,
  BaseItemDamageType,
  BaseItemDexBonusRule,
  BaseItemWeaponCategory,
  BaseItemWeaponRangeType,
} from "../../../entities/base-item";
import type { ItemPropertySlug, ItemType } from "../../../entities/item";
import { useLocale } from "../../../shared/hooks/useLocale";
import {
  AUTOMATION_ARMOR_CLASS_OPTIONS,
  AUTOMATION_DICE_OPTIONS,
  AUTOMATION_HEAL_BONUS_OPTIONS,
  AUTOMATION_RANGE_OPTIONS,
  AUTOMATION_STRENGTH_REQUIREMENT_OPTIONS,
  buildAutomationSelectOptions,
} from "../../../shared/lib/itemAutomationOptions";
import { ItemPropertiesSelector } from "./ItemPropertiesSelector";

type ItemAutomationFieldsProps = {
  type: ItemType;
  damageDice: string;
  damageType: BaseItemDamageType | "";
  healDice: string;
  healBonus: string;
  rangeMeters: string;
  rangeLongMeters: string;
  versatileDamage: string;
  weaponCategory: BaseItemWeaponCategory | "";
  weaponRangeType: BaseItemWeaponRangeType | "";
  armorCategory: BaseItemArmorCategory | "";
  armorClassBase: string;
  dexBonusRule: BaseItemDexBonusRule | "";
  strengthRequirement: string;
  stealthDisadvantage: boolean;
  properties: ItemPropertySlug[];
  legacyUnknownProperties?: string[];
  onDamageDiceChange: (value: string) => void;
  onDamageTypeChange: (value: BaseItemDamageType | "") => void;
  onHealDiceChange: (value: string) => void;
  onHealBonusChange: (value: string) => void;
  onRangeMetersChange: (value: string) => void;
  onRangeLongMetersChange: (value: string) => void;
  onVersatileDamageChange: (value: string) => void;
  onWeaponCategoryChange: (value: BaseItemWeaponCategory | "") => void;
  onWeaponRangeTypeChange: (value: BaseItemWeaponRangeType | "") => void;
  onArmorCategoryChange: (value: BaseItemArmorCategory | "") => void;
  onArmorClassBaseChange: (value: string) => void;
  onDexBonusRuleChange: (value: BaseItemDexBonusRule | "") => void;
  onStrengthRequirementChange: (value: string) => void;
  onStealthDisadvantageChange: (value: boolean) => void;
  onPropertiesChange: (value: ItemPropertySlug[]) => void;
};

const DAMAGE_TYPE_OPTIONS = [
  { value: "acid", labels: { en: "Acid", pt: "Ácido" } },
  { value: "bludgeoning", labels: { en: "Bludgeoning", pt: "Contundente" } },
  { value: "cold", labels: { en: "Cold", pt: "Frio" } },
  { value: "fire", labels: { en: "Fire", pt: "Fogo" } },
  { value: "force", labels: { en: "Force", pt: "Força" } },
  { value: "lightning", labels: { en: "Lightning", pt: "Elétrico" } },
  { value: "necrotic", labels: { en: "Necrotic", pt: "Necrótico" } },
  { value: "piercing", labels: { en: "Piercing", pt: "Perfurante" } },
  { value: "poison", labels: { en: "Poison", pt: "Veneno" } },
  { value: "psychic", labels: { en: "Psychic", pt: "Psíquico" } },
  { value: "radiant", labels: { en: "Radiant", pt: "Radiante" } },
  { value: "slashing", labels: { en: "Slashing", pt: "Cortante" } },
  { value: "thunder", labels: { en: "Thunder", pt: "Trovão" } },
] as const;

const WEAPON_CATEGORY_OPTIONS = [
  { value: "simple", labels: { en: "Simple", pt: "Simples" } },
  { value: "martial", labels: { en: "Martial", pt: "Marcial" } },
] as const;

const WEAPON_RANGE_TYPE_OPTIONS = [
  { value: "melee", labels: { en: "Melee", pt: "Corpo a corpo" } },
  { value: "ranged", labels: { en: "Ranged", pt: "À distância" } },
] as const;

const ARMOR_CATEGORY_OPTIONS = [
  { value: "light", labels: { en: "Light", pt: "Leve" } },
  { value: "medium", labels: { en: "Medium", pt: "Média" } },
  { value: "heavy", labels: { en: "Heavy", pt: "Pesada" } },
  { value: "shield", labels: { en: "Shield", pt: "Escudo" } },
] as const;

const DEX_BONUS_RULE_OPTIONS = [
  { value: "full", labels: { en: "Full Dexterity", pt: "Destreza completa" } },
  { value: "max_2", labels: { en: "Max +2 Dexterity", pt: "Máx. +2 de Destreza" } },
  { value: "none", labels: { en: "No Dexterity bonus", pt: "Sem bônus de Destreza" } },
] as const;

const getLocalizedLabel = (
  locale: string,
  labels: { en: string; pt: string },
) => (locale === "pt" ? labels.pt : labels.en);

const Field = ({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) => (
  <label className="block">
    <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
      {label}
    </span>
    <div className="mt-2">{children}</div>
  </label>
);

export const ItemAutomationFields = ({
  type,
  damageDice,
  damageType,
  healDice,
  healBonus,
  rangeMeters,
  rangeLongMeters,
  versatileDamage,
  weaponCategory,
  weaponRangeType,
  armorCategory,
  armorClassBase,
  dexBonusRule,
  strengthRequirement,
  stealthDisadvantage,
  properties,
  legacyUnknownProperties = [],
  onDamageDiceChange,
  onDamageTypeChange,
  onHealDiceChange,
  onHealBonusChange,
  onRangeMetersChange,
  onRangeLongMetersChange,
  onVersatileDamageChange,
  onWeaponCategoryChange,
  onWeaponRangeTypeChange,
  onArmorCategoryChange,
  onArmorClassBaseChange,
  onDexBonusRuleChange,
  onStrengthRequirementChange,
  onStealthDisadvantageChange,
  onPropertiesChange,
}: ItemAutomationFieldsProps) => {
  const { t, locale } = useLocale();
  const supportsCombatFields = type === "WEAPON" || type === "MAGIC";
  const supportsWeaponFields = type === "WEAPON";
  const supportsArmorFields = type === "ARMOR";
  const supportsConsumableFields = type === "CONSUMABLE";

  if (!supportsCombatFields && !supportsArmorFields && !supportsConsumableFields && type !== "MISC") {
    return null;
  }

  return (
    <div className="grid gap-4">
      {supportsCombatFields && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Field label={t("shop.form.damage")}>
              <select
                value={damageDice}
                onChange={(event) => onDamageDiceChange(event.target.value)}
                className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-limiar-400/60 focus:outline-none"
              >
                {buildAutomationSelectOptions(damageDice, AUTOMATION_DICE_OPTIONS).map((option) => (
                  <option key={option || "none"} value={option}>
                    {option || t("shop.form.damageNone")}
                  </option>
                ))}
              </select>
            </Field>

            <Field label={t("shop.form.damageType")}>
              <select
                value={damageType}
                onChange={(event) => onDamageTypeChange(event.target.value as BaseItemDamageType | "")}
                className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-limiar-400/60 focus:outline-none"
              >
                <option value="">{t("shop.form.optionNone")}</option>
                {DAMAGE_TYPE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {getLocalizedLabel(locale, option.labels)}
                  </option>
                ))}
              </select>
            </Field>

            <Field label={t("shop.form.range")}>
              <select
                value={rangeMeters}
                onChange={(event) => onRangeMetersChange(event.target.value)}
                className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-limiar-400/60 focus:outline-none"
              >
                {buildAutomationSelectOptions(rangeMeters, AUTOMATION_RANGE_OPTIONS).map((option) => (
                  <option key={option || "none"} value={option}>
                    {option || t("shop.form.optionNone")}
                  </option>
                ))}
              </select>
            </Field>

            <Field label={t("shop.form.longRange")}>
              <select
                value={rangeLongMeters}
                onChange={(event) => onRangeLongMetersChange(event.target.value)}
                className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-limiar-400/60 focus:outline-none"
              >
                {buildAutomationSelectOptions(rangeLongMeters, AUTOMATION_RANGE_OPTIONS).map((option) => (
                  <option key={option || "none"} value={option}>
                    {option || t("shop.form.optionNone")}
                  </option>
                ))}
              </select>
            </Field>
          </div>

          {supportsWeaponFields && (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <Field label={t("shop.form.weaponCategory")}>
                <select
                  value={weaponCategory}
                  onChange={(event) => onWeaponCategoryChange(event.target.value as BaseItemWeaponCategory | "")}
                  className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-limiar-400/60 focus:outline-none"
                >
                  <option value="">{t("shop.form.optionNone")}</option>
                  {WEAPON_CATEGORY_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {getLocalizedLabel(locale, option.labels)}
                    </option>
                  ))}
                </select>
              </Field>

              <Field label={t("shop.form.weaponRangeType")}>
                <select
                  value={weaponRangeType}
                  onChange={(event) => onWeaponRangeTypeChange(event.target.value as BaseItemWeaponRangeType | "")}
                  className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-limiar-400/60 focus:outline-none"
                >
                  <option value="">{t("shop.form.optionNone")}</option>
                  {WEAPON_RANGE_TYPE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {getLocalizedLabel(locale, option.labels)}
                    </option>
                  ))}
                </select>
              </Field>

              <Field label={t("shop.form.versatileDamage")}>
                <select
                  value={versatileDamage}
                  onChange={(event) => onVersatileDamageChange(event.target.value)}
                  className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-limiar-400/60 focus:outline-none"
                >
                  {buildAutomationSelectOptions(versatileDamage, AUTOMATION_DICE_OPTIONS).map((option) => (
                    <option key={option || "none"} value={option}>
                      {option || t("shop.form.optionNone")}
                    </option>
                  ))}
                </select>
              </Field>
            </div>
          )}
        </>
      )}

      {supportsArmorFields && (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Field label={t("shop.form.armorCategory")}>
            <select
              value={armorCategory}
              onChange={(event) => onArmorCategoryChange(event.target.value as BaseItemArmorCategory | "")}
              className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-limiar-400/60 focus:outline-none"
            >
              <option value="">{t("shop.form.optionNone")}</option>
              {ARMOR_CATEGORY_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {getLocalizedLabel(locale, option.labels)}
                </option>
              ))}
            </select>
          </Field>

          <Field label={t("shop.form.armorClassBase")}>
            <select
              value={armorClassBase}
              onChange={(event) => onArmorClassBaseChange(event.target.value)}
              className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-limiar-400/60 focus:outline-none"
            >
              {buildAutomationSelectOptions(armorClassBase, AUTOMATION_ARMOR_CLASS_OPTIONS).map((option) => (
                <option key={option || "none"} value={option}>
                  {option || t("shop.form.optionNone")}
                </option>
              ))}
            </select>
          </Field>

          <Field label={t("shop.form.dexBonusRule")}>
            <select
              value={dexBonusRule}
              onChange={(event) => onDexBonusRuleChange(event.target.value as BaseItemDexBonusRule | "")}
              disabled={armorCategory === "shield"}
              className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-limiar-400/60 focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
            >
              <option value="">{t("shop.form.optionNone")}</option>
              {DEX_BONUS_RULE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {getLocalizedLabel(locale, option.labels)}
                </option>
              ))}
            </select>
          </Field>

          <Field label={t("shop.form.strengthRequirement")}>
            <select
              value={strengthRequirement}
              onChange={(event) => onStrengthRequirementChange(event.target.value)}
              disabled={armorCategory === "shield"}
              className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-limiar-400/60 focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
            >
              {buildAutomationSelectOptions(strengthRequirement, AUTOMATION_STRENGTH_REQUIREMENT_OPTIONS).map((option) => (
                <option key={option || "none"} value={option}>
                  {option || t("shop.form.optionNone")}
                </option>
              ))}
            </select>
          </Field>

          <label className="flex items-center gap-3 rounded-2xl border border-white/8 bg-slate-950/45 px-4 py-3 text-sm text-slate-200 sm:col-span-2 xl:col-span-4">
            <input
              type="checkbox"
              checked={stealthDisadvantage}
              onChange={(event) => onStealthDisadvantageChange(event.target.checked)}
              className="h-4 w-4 rounded border-white/20 bg-slate-950/70 text-limiar-300 focus:ring-limiar-300/40"
            />
            <span>{t("shop.form.stealthDisadvantage")}</span>
          </label>
        </div>
      )}

      {supportsConsumableFields && (
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t("shop.form.healDice")}>
            <select
              value={healDice}
              onChange={(event) => onHealDiceChange(event.target.value)}
              className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-limiar-400/60 focus:outline-none"
            >
              {buildAutomationSelectOptions(healDice, AUTOMATION_DICE_OPTIONS).map((option) => (
                <option key={option || "none"} value={option}>
                  {option || t("shop.form.optionNone")}
                </option>
              ))}
            </select>
          </Field>

          <Field label={t("shop.form.healBonus")}>
            <select
              value={healBonus}
              onChange={(event) => onHealBonusChange(event.target.value)}
              className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-limiar-400/60 focus:outline-none"
            >
              {buildAutomationSelectOptions(healBonus, AUTOMATION_HEAL_BONUS_OPTIONS).map((option) => (
                <option key={option || "none"} value={option}>
                  {option || t("shop.form.optionNone")}
                </option>
              ))}
            </select>
          </Field>
        </div>
      )}

      {!supportsArmorFields && (
        <Field label={t("shop.form.properties")}>
          <ItemPropertiesSelector
            value={properties}
            legacyUnknown={legacyUnknownProperties}
            onChange={onPropertiesChange}
          />
        </Field>
      )}
    </div>
  );
};
