import { useState, type ReactNode } from "react";
import type {
  BaseItemArmorCategory,
  BaseItemWeaponCategory,
  BaseItemWeaponRangeType,
} from "../../../entities/base-item";
import {
  getItemPropertyLabels,
  normalizeItemProperties,
  type ItemPropertySlug,
  type Item,
  type ItemInput,
  type ItemType,
} from "../../../entities/item";
import { useLocale } from "../../../shared/hooks/useLocale";
import { localizedItemName } from "../utils/localizedItemName";
import { CATALOG_TYPE_META } from "../utils/catalogTypeMeta";
import { getShopItemTypeLabelKey } from "../utils/shopItemTypes";
import { formatItemPrice } from "../utils/shopCurrency";
import { ItemAutomationFields } from "./ItemAutomationFields";

type CatalogItemCardProps = {
  item: Item;
  itemTypes: ItemType[];
  onUpdate?: (itemId: string, payload: ItemInput) => boolean | Promise<boolean>;
  onDelete?: (itemId: string) => void | Promise<void>;
};

const DEX_RULE_LABELS = {
  full: { en: "Full DEX", pt: "DEX completo" },
  max_2: { en: "Max +2 DEX", pt: "Máx. +2 DEX" },
  none: { en: "No DEX bonus", pt: "Sem bônus de DEX" },
} as const;

const localizeDexRule = (value: string | null | undefined, locale: string) => {
  if (!value) return null;
  const labels = DEX_RULE_LABELS[value as keyof typeof DEX_RULE_LABELS];
  if (!labels) return value;
  return locale === "pt" ? labels.pt : labels.en;
};

export const CatalogItemCard = ({
  item,
  itemTypes,
  onUpdate,
  onDelete,
}: CatalogItemCardProps) => {
  const { t, locale } = useLocale();
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [name, setName] = useState(item.name);
  const [type, setType] = useState<ItemType>(item.type);
  const [description, setDescription] = useState(item.description);
  const [price, setPrice] = useState(item.price?.toString() ?? "");
  const [weight, setWeight] = useState(item.weight?.toString() ?? "");
  const [damageDice, setDamageDice] = useState(item.damageDice ?? "");
  const [damageType, setDamageType] = useState(item.damageType ?? "");
  const [rangeMeters, setRangeMeters] = useState(item.rangeMeters?.toString() ?? "");
  const [rangeLongMeters, setRangeLongMeters] = useState(item.rangeLongMeters?.toString() ?? "");
  const [versatileDamage, setVersatileDamage] = useState(item.versatileDamage ?? "");
  const [weaponCategory, setWeaponCategory] = useState<BaseItemWeaponCategory | "">(
    item.weaponCategory ?? "",
  );
  const [weaponRangeType, setWeaponRangeType] = useState<BaseItemWeaponRangeType | "">(
    item.weaponRangeType ?? "",
  );
  const [armorCategory, setArmorCategory] = useState<BaseItemArmorCategory | "">(
    item.armorCategory ?? "",
  );
  const [armorClassBase, setArmorClassBase] = useState(
    item.armorClassBase?.toString() ?? "",
  );
  const [dexBonusRule, setDexBonusRule] = useState(item.dexBonusRule ?? "");
  const [strengthRequirement, setStrengthRequirement] = useState(
    item.strengthRequirement?.toString() ?? "",
  );
  const [stealthDisadvantage, setStealthDisadvantage] = useState(
    item.stealthDisadvantage ?? false,
  );
  const initialProperties = normalizeItemProperties(item.properties);
  const [selectedProperties, setSelectedProperties] = useState<ItemPropertySlug[]>(
    initialProperties.value,
  );

  const localizedName = localizedItemName(item, locale);
  const propertyItems = getItemPropertyLabels(item.properties?.filter(Boolean) ?? [], locale);
  const secondaryName =
    locale === "pt"
      ? item.nameEnSnapshot && item.nameEnSnapshot !== localizedName
        ? item.nameEnSnapshot
        : null
      : item.namePtSnapshot && item.namePtSnapshot !== localizedName
        ? item.namePtSnapshot
        : null;
  const meta = CATALOG_TYPE_META[item.type];
  const editingMeta = CATALOG_TYPE_META[type];
  const canSave = Boolean(name.trim() && description.trim());

  const statItems = [
    item.damageDice
      ? {
          label: t("catalog.card.damage"),
          value: item.damageType ? `${item.damageDice} ${item.damageType}` : item.damageDice,
        }
      : null,
    typeof item.rangeMeters === "number"
      ? {
          label: t("catalog.card.range"),
          value:
            typeof item.rangeLongMeters === "number"
              ? `${item.rangeMeters}/${item.rangeLongMeters} m`
              : `${item.rangeMeters} m`,
        }
      : null,
    item.versatileDamage
      ? { label: t("catalog.card.versatileDamage"), value: item.versatileDamage }
      : null,
    typeof item.armorClassBase === "number"
      ? { label: t("catalog.card.armorClassBase"), value: `${item.armorClassBase}` }
      : null,
    item.dexBonusRule
      ? {
          label: t("catalog.card.dexBonusRule"),
          value: localizeDexRule(item.dexBonusRule, locale) ?? item.dexBonusRule,
        }
      : null,
    typeof item.strengthRequirement === "number"
      ? { label: t("catalog.card.strengthRequirement"), value: `${item.strengthRequirement}` }
      : null,
    typeof item.weight === "number"
      ? { label: t("catalog.card.weight"), value: `${item.weight}` }
      : null,
  ].filter((entry): entry is { label: string; value: string } => Boolean(entry));

  const sourceLabel =
    item.baseItemId && !item.isCustom
      ? t("catalog.card.baseLinked")
      : t("catalog.card.custom");
  const sourceClass =
    item.baseItemId && !item.isCustom
      ? "border-emerald-300/20 bg-emerald-400/12 text-emerald-100"
      : "border-amber-300/20 bg-amber-300/12 text-amber-50";

  const handleSave = async () => {
    if (!onUpdate || !canSave || isSaving) {
      return;
    }

    setIsSaving(true);
    try {
      const updated = await onUpdate(item.id, {
        name: name.trim(),
        type,
        description: description.trim(),
        price,
        weight,
        damageDice:
          (type === "WEAPON" || type === "MAGIC") && damageDice.trim()
            ? damageDice.trim()
            : undefined,
        damageType:
          (type === "WEAPON" || type === "MAGIC") && damageType.trim()
            ? damageType.trim()
            : undefined,
        rangeMeters:
          (type === "WEAPON" || type === "MAGIC") && rangeMeters.trim()
            ? rangeMeters
            : undefined,
        rangeLongMeters:
          (type === "WEAPON" || type === "MAGIC") && rangeLongMeters.trim()
            ? rangeLongMeters
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
          type === "ARMOR" && armorClassBase.trim() ? armorClassBase : undefined,
        dexBonusRule:
          type === "ARMOR" && dexBonusRule.trim() ? dexBonusRule.trim() : undefined,
        strengthRequirement:
          type === "ARMOR" && strengthRequirement.trim()
            ? strengthRequirement
            : undefined,
        stealthDisadvantage: type === "ARMOR" ? stealthDisadvantage : undefined,
        isShield: type === "ARMOR" && armorCategory === "shield",
        properties:
          type !== "ARMOR" && selectedProperties.length > 0
            ? selectedProperties
            : undefined,
      });
      if (updated) {
        setIsEditing(false);
      }
    } finally {
      setIsSaving(false);
    }
  };

  if (!isEditing) {
    return (
      <article className="group relative overflow-hidden rounded-[28px] border border-white/8 bg-[linear-gradient(180deg,rgba(8,12,28,0.92),rgba(3,7,20,0.97))] p-5 shadow-[0_24px_60px_rgba(2,6,23,0.24)] transition duration-300 hover:border-white/12 hover:translate-y-[-2px]">
        <div
          className={`pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.06),transparent_28%),linear-gradient(135deg,var(--tw-gradient-stops))] ${meta.panelClass}`}
        />

        <div className="relative">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="flex flex-wrap gap-2">
                <span
                  className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] ${meta.chipClass}`}
                >
                  <svg
                    className="h-3.5 w-3.5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={1.7}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d={meta.iconPath}
                    />
                  </svg>
                  {t(getShopItemTypeLabelKey(item.type))}
                </span>
                <span
                  className={`rounded-full border px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] ${sourceClass}`}
                >
                  {sourceLabel}
                </span>
              </div>

              <h3 className="mt-4 break-words font-display text-2xl font-bold text-white">
                {localizedName}
              </h3>
              {secondaryName && (
                <p className="mt-1 text-xs uppercase tracking-[0.18em] text-slate-500">
                  {secondaryName}
                </p>
              )}
            </div>

            <div className="min-w-[120px] rounded-[24px] border border-white/8 bg-white/[0.05] px-4 py-3 text-right">
              <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
                {t("catalog.card.price")}
              </p>
              <p className="mt-3 font-display text-2xl font-bold text-white">
                {formatItemPrice(item.price, item.priceLabel)}
              </p>
            </div>
          </div>

          <p className="mt-4 text-sm leading-7 text-slate-300">{item.description}</p>

          {(statItems.length > 0 || propertyItems.length > 0) && (
            <div className="mt-5 grid gap-3 xl:grid-cols-[minmax(0,0.88fr)_minmax(0,1.12fr)]">
              {statItems.length > 0 && (
                <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
                  {statItems.map((stat) => (
                    <div
                      key={stat.label}
                      className="rounded-2xl border border-white/8 bg-slate-950/55 px-4 py-3"
                    >
                      <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
                        {stat.label}
                      </p>
                      <p className="mt-2 text-sm font-semibold text-white">
                        {stat.value}
                      </p>
                    </div>
                  ))}
                </div>
              )}

              {propertyItems.length > 0 && (
                <div className="rounded-2xl border border-white/8 bg-slate-950/55 px-4 py-3">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
                    {t("catalog.card.properties")}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {propertyItems.map((property) => (
                      <span
                        key={property}
                        className="rounded-full border border-white/8 bg-white/[0.05] px-3 py-1.5 text-xs text-slate-200"
                      >
                        {property}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {(onUpdate || onDelete) && (
            <div className="mt-5 flex flex-wrap gap-2">
              {onUpdate && (
                <button
                  type="button"
                  onClick={() => setIsEditing(true)}
                  className="inline-flex items-center rounded-full border border-white/10 bg-white/[0.05] px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-100 transition hover:border-white/20 hover:bg-white/[0.09]"
                >
                  {t("catalog.edit")}
                </button>
              )}
              {onDelete && (
                <button
                  type="button"
                  onClick={() => void onDelete(item.id)}
                  className="inline-flex items-center rounded-full border border-rose-300/18 bg-rose-400/10 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-rose-100 transition hover:border-rose-300/28 hover:bg-rose-400/16"
                >
                  {t("catalog.delete")}
                </button>
              )}
            </div>
          )}
        </div>
      </article>
    );
  }

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
                onChange={(event) => setName(event.target.value)}
                className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-limiar-400/60 focus:outline-none"
              />
            </Field>
            <Field label={t("shop.form.type")}>
              <select
                value={type}
                onChange={(event) => setType(event.target.value as ItemType)}
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
                placeholder={t("shop.form.pricePlaceholder")}
              />
            </Field>
            <Field label={t("shop.form.weight")}>
              <input
                value={weight}
                onChange={(event) => setWeight(event.target.value)}
                className="w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-limiar-400/60 focus:outline-none"
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
            legacyUnknownProperties={initialProperties.invalid}
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

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => void handleSave()}
              disabled={!canSave || isSaving}
              className="inline-flex items-center rounded-full bg-[linear-gradient(120deg,#c4b5fd_0%,#67e8f9_48%,#fde68a_100%)] px-4 py-2 text-[11px] font-bold uppercase tracking-[0.18em] text-slate-950 transition hover:translate-y-[-1px] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSaving ? t("catalog.saving") : t("catalog.save")}
            </button>
            <button
              type="button"
              onClick={() => setIsEditing(false)}
              className="inline-flex items-center rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-200 transition hover:border-white/20 hover:bg-white/[0.08]"
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
