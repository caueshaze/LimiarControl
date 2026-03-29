import { useState } from "react";
import type {
  BaseItemArmorCategory,
  BaseItemDamageType,
  BaseItemDexBonusRule,
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
import { buildCatalogStatItems, CatalogItemReadonlyView } from "./CatalogItemReadonlyView";
import { CatalogItemEditView } from "./CatalogItemEditView";

type CatalogItemCardProps = {
  item: Item;
  itemTypes: ItemType[];
  onUpdate?: (itemId: string, payload: ItemInput) => boolean | Promise<boolean>;
  onDelete?: (itemId: string) => void | Promise<void>;
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
  const [damageType, setDamageType] = useState<BaseItemDamageType | "">(item.damageType ?? "");
  const [healDice, setHealDice] = useState(item.healDice ?? "");
  const [healBonus, setHealBonus] = useState(item.healBonus?.toString() ?? "");
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
  const [dexBonusRule, setDexBonusRule] = useState<BaseItemDexBonusRule | "">(item.dexBonusRule ?? "");
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

  const statItems = buildCatalogStatItems(item, locale, {
    damage: t("catalog.card.damage"),
    healing: t("catalog.admin.table.healDice"),
    range: t("catalog.card.range"),
    versatileDamage: t("catalog.card.versatileDamage"),
    armorClassBase: t("catalog.card.armorClassBase"),
    dexBonusRule: t("catalog.card.dexBonusRule"),
    strengthRequirement: t("catalog.card.strengthRequirement"),
    weight: t("catalog.card.weight"),
  });

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
          (type === "WEAPON" || type === "MAGIC") && damageType ? damageType : undefined,
        healDice:
          type === "CONSUMABLE" && healDice.trim()
            ? healDice.trim()
            : undefined,
        healBonus:
          type === "CONSUMABLE" && healBonus.trim()
            ? healBonus
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
          type === "ARMOR" && dexBonusRule ? dexBonusRule : undefined,
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
      <CatalogItemReadonlyView
        item={item}
        locale={locale}
        localizedName={localizedName}
        secondaryName={secondaryName}
        meta={meta}
        propertyItems={propertyItems}
        sourceClass={sourceClass}
        sourceLabel={sourceLabel}
        statItems={statItems}
        onDelete={onDelete}
        onEdit={onUpdate ? () => setIsEditing(true) : undefined}
      />
    );
  }

  return (
    <CatalogItemEditView
      itemTypes={itemTypes}
      localizedName={localizedName}
      editingMeta={editingMeta}
      type={type}
      name={name}
      description={description}
      price={price}
      weight={weight}
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
      selectedProperties={selectedProperties}
      legacyUnknownProperties={initialProperties.invalid}
      canSave={canSave}
      isSaving={isSaving}
      onNameChange={setName}
      onTypeChange={setType}
      onDescriptionChange={setDescription}
      onPriceChange={setPrice}
      onWeightChange={setWeight}
      onDamageDiceChange={setDamageDice}
      onDamageTypeChange={setDamageType}
      onHealDiceChange={setHealDice}
      onHealBonusChange={setHealBonus}
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
      onCancel={() => setIsEditing(false)}
      onSave={() => void handleSave()}
    />
  );
};
