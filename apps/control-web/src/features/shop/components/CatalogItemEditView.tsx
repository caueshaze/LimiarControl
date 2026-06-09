import type { ReactNode } from "react";
import type { BaseSpell } from "../../../entities/base-spell";
import type {
  BaseItemEquipmentCategory,
  BaseItemArmorCategory,
  BaseItemDamageType,
  BaseItemDexBonusRule,
  BaseItemWeaponCategory,
  BaseItemWeaponRangeType,
} from "../../../entities/base-item";
import type { ItemPropertySlug, ItemType } from "../../../entities/item";
import { useLocale } from "../../../shared/hooks/useLocale";
import { getShopItemTypeLabelKey } from "../utils/shopItemTypes";
import { ItemAutomationFields } from "./ItemAutomationFields";
import { MagicBraceletFields } from "./MagicBraceletFields";

type Props = {
  itemTypes: ItemType[];
  localizedName: string;
  editingMeta: {
    chipClass: string;
    panelClass: string;
  };
  type: ItemType;
  spells: BaseSpell[];
  name: string;
  description: string;
  price: string;
  equipmentCategory: BaseItemEquipmentCategory | "";
  weight: string;
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
  isPurchasable: boolean;
  chargesMax: string;
  rechargeType: "" | "none" | "short_rest" | "long_rest" | "dawn" | "custom";
  spellCanonicalKey: string;
  castLevel: string;
  ignoreComponents: boolean;
  noFreeHandRequired: boolean;
  selectedProperties: ItemPropertySlug[];
  legacyUnknownProperties: string[];
  canSave: boolean;
  isSaving: boolean;
  onNameChange: (value: string) => void;
  onTypeChange: (value: ItemType) => void;
  onDescriptionChange: (value: string) => void;
  onPriceChange: (value: string) => void;
  onEquipmentCategoryChange: (value: BaseItemEquipmentCategory | "") => void;
  onWeightChange: (value: string) => void;
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
  onIsPurchasableChange: (value: boolean) => void;
  onChargesMaxChange: (value: string) => void;
  onRechargeTypeChange: (value: "" | "none" | "short_rest" | "long_rest" | "dawn" | "custom") => void;
  onSpellCanonicalKeyChange: (value: string) => void;
  onCastLevelChange: (value: string) => void;
  onIgnoreComponentsChange: (value: boolean) => void;
  onNoFreeHandRequiredChange: (value: boolean) => void;
  onPropertiesChange: (value: ItemPropertySlug[]) => void;
  onCancel: () => void;
  onSave: () => void;
};

export const CatalogItemEditView = ({
  itemTypes,
  localizedName,
  editingMeta,
  type,
  spells,
  name,
  description,
  price,
  equipmentCategory,
  weight,
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
  isPurchasable,
  chargesMax,
  rechargeType,
  spellCanonicalKey,
  castLevel,
  ignoreComponents,
  noFreeHandRequired,
  selectedProperties,
  legacyUnknownProperties,
  canSave,
  isSaving,
  onNameChange,
  onTypeChange,
  onDescriptionChange,
  onPriceChange,
  onEquipmentCategoryChange,
  onWeightChange,
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
  onIsPurchasableChange,
  onChargesMaxChange,
  onRechargeTypeChange,
  onSpellCanonicalKeyChange,
  onCastLevelChange,
  onIgnoreComponentsChange,
  onNoFreeHandRequiredChange,
  onPropertiesChange,
  onCancel,
  onSave,
}: Props) => {
  const { t } = useLocale();
  const isMagicBracelet =
    equipmentCategory === "magic_bracelet" || Boolean(spellCanonicalKey);

  return (
    <article className="relative overflow-hidden rounded-[28px] border border-white/8 bg-[linear-gradient(180deg,rgba(8,12,28,0.94),rgba(3,7,20,0.98))] p-5 shadow-[0_24px_60px_rgba(2,6,23,0.24)]">
      <div
        className={`pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.06),transparent_28%),linear-gradient(135deg,var(--tw-gradient-stops))] ${editingMeta.panelClass}`}
      />

      <div className="relative">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
              {t("catalog.edit")}
            </p>
            <h3 className="mt-2 font-display text-2xl font-bold text-white">
              {localizedName}
            </h3>
          </div>
          <span
            className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] ${editingMeta.chipClass}`}
          >
            {t(getShopItemTypeLabelKey(type))}
          </span>
        </div>

        <div className="mt-5 space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t("shop.form.name")}>
              <input
                value={name}
                onChange={(event) => onNameChange(event.target.value)}
                className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-limiar-400/60 focus:outline-none"
              />
            </Field>
            <Field label={t("shop.form.type")}>
              <select
                value={type}
                onChange={(event) => onTypeChange(event.target.value as ItemType)}
                className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-limiar-400/60 focus:outline-none"
              >
                {itemTypes.map((itemType) => (
                  <option key={itemType} value={itemType}>
                    {t(getShopItemTypeLabelKey(itemType))}
                  </option>
                ))}
              </select>
            </Field>
          </div>

          <Field label={t("shop.form.description")}>
            <textarea
              value={description}
              onChange={(event) => onDescriptionChange(event.target.value)}
              className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-limiar-400/60 focus:outline-none"
              rows={4}
              placeholder={t("shop.form.descriptionPlaceholder")}
            />
          </Field>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t("shop.form.price")}>
              <input
                value={price}
                onChange={(event) => onPriceChange(event.target.value)}
                className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-limiar-400/60 focus:outline-none"
                placeholder={t("shop.form.pricePlaceholder")}
              />
            </Field>
            <Field label={t("shop.form.weight")}>
              <input
                value={weight}
                onChange={(event) => onWeightChange(event.target.value)}
                className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-limiar-400/60 focus:outline-none"
                placeholder={t("shop.form.weightPlaceholder")}
              />
            </Field>
          </div>

          <Field label={t("shop.form.equipmentCategory")}>
            <select
              value={equipmentCategory}
              onChange={(event) => onEquipmentCategoryChange(event.target.value as BaseItemEquipmentCategory | "")}
              className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-limiar-400/60 focus:outline-none"
            >
              <option value="">{t("shop.form.optionNone")}</option>
              <option value="magic_bracelet">{t("shop.form.magicBraceletCategory")}</option>
            </select>
          </Field>

          <label className="flex items-center gap-3 rounded-2xl border border-white/8 bg-slate-950/40 px-4 py-3 text-sm text-slate-200">
            <input
              type="checkbox"
              checked={isPurchasable}
              onChange={(event) => onIsPurchasableChange(event.target.checked)}
            />
            <span>{t("shop.form.isPurchasable")}</span>
          </label>

          {isMagicBracelet && (
            <MagicBraceletFields
              spells={spells}
              chargesMax={chargesMax}
              rechargeType={rechargeType}
              spellCanonicalKey={spellCanonicalKey}
              castLevel={castLevel}
              ignoreComponents={ignoreComponents}
              noFreeHandRequired={noFreeHandRequired}
              onChargesMaxChange={onChargesMaxChange}
              onRechargeTypeChange={onRechargeTypeChange}
              onSpellCanonicalKeyChange={onSpellCanonicalKeyChange}
              onCastLevelChange={onCastLevelChange}
              onIgnoreComponentsChange={onIgnoreComponentsChange}
              onNoFreeHandRequiredChange={onNoFreeHandRequiredChange}
            />
          )}

          <ItemAutomationFields
            type={type}
            damageDice={damageDice}
            damageType={damageType}
            healDice={healDice}
            healBonus={healBonus}
            rangeMeters={rangeMeters}
            rangeLongMeters={rangeLongMeters}
            versatileDamage={versatileDamage}
            weaponCategory={weaponCategory}
            weaponRangeType={weaponRangeType}
            armorCategory={armorCategory}
            armorClassBase={armorClassBase}
            dexBonusRule={dexBonusRule}
            strengthRequirement={strengthRequirement}
            stealthDisadvantage={stealthDisadvantage}
            properties={selectedProperties}
            legacyUnknownProperties={legacyUnknownProperties}
            onDamageDiceChange={onDamageDiceChange}
            onDamageTypeChange={onDamageTypeChange}
            onHealDiceChange={onHealDiceChange}
            onHealBonusChange={onHealBonusChange}
            onRangeMetersChange={onRangeMetersChange}
            onRangeLongMetersChange={onRangeLongMetersChange}
            onVersatileDamageChange={onVersatileDamageChange}
            onWeaponCategoryChange={onWeaponCategoryChange}
            onWeaponRangeTypeChange={onWeaponRangeTypeChange}
            onArmorCategoryChange={onArmorCategoryChange}
            onArmorClassBaseChange={onArmorClassBaseChange}
            onDexBonusRuleChange={onDexBonusRuleChange}
            onStrengthRequirementChange={onStrengthRequirementChange}
            onStealthDisadvantageChange={onStealthDisadvantageChange}
            onPropertiesChange={onPropertiesChange}
          />

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={onSave}
              disabled={!canSave || isSaving}
              className="inline-flex items-center rounded-full bg-[linear-gradient(120deg,#c4b5fd_0%,#67e8f9_48%,#fde68a_100%)] px-4 py-2 text-[11px] font-bold uppercase tracking-[0.18em] text-slate-950 transition hover:-translate-y-px disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSaving ? t("catalog.saving") : t("catalog.save")}
            </button>
            <button
              type="button"
              onClick={onCancel}
              className="inline-flex items-center rounded-full border border-white/10 bg-white/4 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-200 transition hover:border-white/20 hover:bg-white/8"
            >
              {t("catalog.cancel")}
            </button>
          </div>
        </div>
      </div>
    </article>
  );
};

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
