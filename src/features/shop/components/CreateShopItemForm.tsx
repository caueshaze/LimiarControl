import { useState, type FormEvent, type ReactNode } from "react";
import type {
  BaseItemArmorCategory,
  BaseItemDamageType,
  BaseItemDexBonusRule,
  BaseItemWeaponCategory,
  BaseItemWeaponRangeType,
} from "../../../entities/base-item";
import {
  type ItemPropertySlug,
  type ItemInput,
  type ItemType,
} from "../../../entities/item";
import { useLocale } from "../../../shared/hooks/useLocale";
import { CATALOG_TYPE_META } from "../utils/catalogTypeMeta";
import { getShopItemTypeLabelKey } from "../utils/shopItemTypes";
import { ItemAutomationFields } from "./ItemAutomationFields";

type CreateShopItemFormProps = {
  onCreate: (payload: ItemInput) => boolean | Promise<boolean>;
  itemTypes: ItemType[];
};

export const CreateShopItemForm = ({ onCreate, itemTypes }: CreateShopItemFormProps) => {
  const { t } = useLocale();
  const [name, setName] = useState("");
  const [type, setType] = useState<ItemType>(itemTypes[0]);
  const [description, setDescription] = useState("");
  const [price, setPrice] = useState("");
  const [weight, setWeight] = useState("");
  const [damageDice, setDamageDice] = useState("");
  const [damageType, setDamageType] = useState<BaseItemDamageType | "">("");
  const [rangeMeters, setRangeMeters] = useState("");
  const [rangeLongMeters, setRangeLongMeters] = useState("");
  const [versatileDamage, setVersatileDamage] = useState("");
  const [weaponCategory, setWeaponCategory] = useState<BaseItemWeaponCategory | "">("");
  const [weaponRangeType, setWeaponRangeType] = useState<BaseItemWeaponRangeType | "">("");
  const [armorCategory, setArmorCategory] = useState<BaseItemArmorCategory | "">("");
  const [armorClassBase, setArmorClassBase] = useState("");
  const [dexBonusRule, setDexBonusRule] = useState<BaseItemDexBonusRule | "">("");
  const [strengthRequirement, setStrengthRequirement] = useState("");
  const [stealthDisadvantage, setStealthDisadvantage] = useState(false);
  const [selectedProperties, setSelectedProperties] = useState<ItemPropertySlug[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const canSubmit = Boolean(name.trim() && description.trim() && price.trim());
  const meta = CATALOG_TYPE_META[type];

  const resetForm = () => {
    setName("");
    setType(itemTypes[0]);
    setDescription("");
    setPrice("");
    setWeight("");
    setDamageDice("");
    setDamageType("");
    setRangeMeters("");
    setRangeLongMeters("");
    setVersatileDamage("");
    setWeaponCategory("");
    setWeaponRangeType("");
    setArmorCategory("");
    setArmorClassBase("");
    setDexBonusRule("");
    setStrengthRequirement("");
    setStealthDisadvantage(false);
    setSelectedProperties([]);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canSubmit || isSubmitting) {
      return;
    }

    setIsSubmitting(true);
    try {
      const created = await onCreate({
        name: name.trim(),
        type,
        description: description.trim(),
        price: Number(price),
        weight: weight.trim() ? Number(weight) : undefined,
        damageDice:
          (type === "WEAPON" || type === "MAGIC") && damageDice.trim()
            ? damageDice.trim()
            : undefined,
        damageType:
          (type === "WEAPON" || type === "MAGIC") && damageType ? damageType : undefined,
        rangeMeters:
          (type === "WEAPON" || type === "MAGIC") && rangeMeters.trim()
            ? Number(rangeMeters)
            : undefined,
        rangeLongMeters:
          (type === "WEAPON" || type === "MAGIC") && rangeLongMeters.trim()
            ? Number(rangeLongMeters)
            : undefined,
        versatileDamage:
          type === "WEAPON" && versatileDamage.trim()
            ? versatileDamage.trim()
            : undefined,
        weaponCategory: type === "WEAPON" && weaponCategory ? weaponCategory : undefined,
        weaponRangeType:
          type === "WEAPON" && weaponRangeType ? weaponRangeType : undefined,
        armorCategory: type === "ARMOR" && armorCategory ? armorCategory : undefined,
        armorClassBase:
          type === "ARMOR" && armorClassBase.trim()
            ? Number(armorClassBase)
            : undefined,
        dexBonusRule:
          type === "ARMOR" && dexBonusRule ? dexBonusRule : undefined,
        strengthRequirement:
          type === "ARMOR" && strengthRequirement.trim()
            ? Number(strengthRequirement)
            : undefined,
        stealthDisadvantage: type === "ARMOR" ? stealthDisadvantage : undefined,
        isShield: type === "ARMOR" && armorCategory === "shield",
        properties:
          type !== "ARMOR" && selectedProperties.length > 0
            ? selectedProperties
            : undefined,
      });
      if (created) {
        resetForm();
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="relative overflow-hidden rounded-[30px] border border-white/8 bg-[linear-gradient(180deg,rgba(9,12,28,0.94),rgba(2,6,23,0.96))] p-5 shadow-[0_24px_80px_rgba(2,6,23,0.28)] transition-all duration-300"
    >
      <div className={`pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.06),transparent_28%),linear-gradient(135deg,var(--tw-gradient-stops))] ${meta.panelClass}`} />
      <div className="pointer-events-none absolute -right-20 top-10 h-40 w-40 rounded-full bg-white/5 blur-3xl transition-all duration-500" />

      <div className="relative">
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(180px,220px)]">
          <div className="min-w-0">
            <p className="text-[10px] font-semibold uppercase tracking-[0.26em] text-slate-500">
              {t("catalog.formTitle")}
            </p>
            <h2 className="mt-2 text-2xl font-semibold leading-tight text-white">
              {t("catalog.formHeadline")}
            </h2>
            <p className="mt-2 max-w-xl text-sm leading-6 text-slate-400">
              {t("catalog.formDescription")}
            </p>
            <p className="mt-3 max-w-xl text-xs leading-6 text-slate-500">
              {t("catalog.formModeCustom")}
            </p>
          </div>

          <div className="rounded-[24px] border border-white/8 bg-slate-950/45 p-4 backdrop-blur-xl">
            <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
              {t("shop.form.type")}
            </p>
            <div className="mt-3 flex items-center gap-3">
              <span className={`inline-flex h-10 w-10 items-center justify-center rounded-2xl border ${meta.chipClass}`}>
                <svg className="h-4.5 w-4.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.7}>
                  <path strokeLinecap="round" strokeLinejoin="round" d={meta.iconPath} />
                </svg>
              </span>
              <div className="min-w-0">
                <p className="break-words text-sm font-semibold text-white">
                  {t(getShopItemTypeLabelKey(type))}
                </p>
                <p className="mt-1 text-[11px] uppercase tracking-[0.18em] text-slate-500">
                  {t("catalog.formRequiredFields")}
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-5 rounded-[26px] border border-white/8 bg-slate-950/35 p-3 sm:p-4">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-2">
          {itemTypes.map((itemType) => {
            const itemMeta = CATALOG_TYPE_META[itemType];
            const active = itemType === type;
            return (
              <button
                key={itemType}
                type="button"
                onClick={() => setType(itemType)}
                className={`min-w-0 rounded-2xl border px-4 py-3 text-left transition-all duration-300 ${
                  active
                    ? `${itemMeta.chipClass} shadow-[0_14px_32px_rgba(15,23,42,0.22)]`
                    : "border-white/8 bg-white/3 text-slate-300 hover:border-white/16 hover:bg-white/6"
                }`}
              >
                <div className="flex min-w-0 items-center gap-3">
                  <span className={`inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border ${active ? "border-current/20 bg-black/10" : "border-white/8 bg-slate-950/45"}`}>
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.7}>
                      <path strokeLinecap="round" strokeLinejoin="round" d={itemMeta.iconPath} />
                    </svg>
                  </span>
                  <span className="min-w-0">
                    <span className="block break-words text-sm font-semibold leading-5">
                      {t(getShopItemTypeLabelKey(itemType))}
                    </span>
                  </span>
                </div>
              </button>
            );
          })}
          </div>
        </div>

        <div className="mt-5 grid gap-4">
          <Field label={t("shop.form.name")}>
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-limiar-400/60 focus:outline-none"
              placeholder={t("shop.form.namePlaceholder")}
            />
          </Field>

          <Field label={t("shop.form.description")}>
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-limiar-400/60 focus:outline-none"
              rows={4}
              placeholder={t("shop.form.descriptionPlaceholder")}
            />
          </Field>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t("shop.form.price")}>
              <input
                value={price}
                onChange={(event) => setPrice(event.target.value)}
                className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-limiar-400/60 focus:outline-none"
                inputMode="decimal"
                placeholder={t("shop.form.pricePlaceholder")}
              />
            </Field>
            <Field label={t("shop.form.weight")}>
              <input
                value={weight}
                onChange={(event) => setWeight(event.target.value)}
                className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-limiar-400/60 focus:outline-none"
                inputMode="decimal"
                placeholder={t("shop.form.weightPlaceholder")}
              />
            </Field>
          </div>

          <ItemAutomationFields
            type={type}
            damageDice={damageDice}
            damageType={damageType}
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
            onDamageDiceChange={setDamageDice}
            onDamageTypeChange={setDamageType}
            onRangeMetersChange={setRangeMeters}
            onRangeLongMetersChange={setRangeLongMeters}
            onVersatileDamageChange={setVersatileDamage}
            onWeaponCategoryChange={setWeaponCategory}
            onWeaponRangeTypeChange={setWeaponRangeType}
            onArmorCategoryChange={setArmorCategory}
            onArmorClassBaseChange={setArmorClassBase}
            onDexBonusRuleChange={setDexBonusRule}
            onStrengthRequirementChange={setStrengthRequirement}
            onStealthDisadvantageChange={setStealthDisadvantage}
            onPropertiesChange={setSelectedProperties}
          />

          <button
            type="submit"
            disabled={!canSubmit || isSubmitting}
            className="inline-flex w-full items-center justify-center rounded-2xl bg-[linear-gradient(120deg,#c4b5fd_0%,#67e8f9_48%,#fde68a_100%)] px-5 py-3 text-sm font-bold text-slate-950 shadow-[0_20px_40px_rgba(103,232,249,0.16)] transition hover:-translate-y-px disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? t("catalog.creatingAction") : t("catalog.createAction")}
          </button>
        </div>
      </div>
    </form>
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
