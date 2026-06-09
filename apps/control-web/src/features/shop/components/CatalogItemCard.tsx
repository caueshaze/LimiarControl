import { useState } from "react";
import type { BaseSpell } from "../../../entities/base-spell";
import type {
  BaseItemEquipmentCategory,
  BaseItemArmorCategory,
  BaseItemDamageType,
  BaseItemDexBonusRule,
  BaseItemWeaponCategory,
  BaseItemWeaponRangeType,
} from "../../../entities/base-item";
import { BaseItemEquipmentCategory as BaseItemEquipmentCategoryValues } from "../../../entities/base-item";
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
  spells: BaseSpell[];
  onUpdate?: (itemId: string, payload: ItemInput) => boolean | Promise<boolean>;
  onDelete?: (itemId: string) => void | Promise<void>;
};

export const CatalogItemCard = ({
  item,
  itemTypes,
  spells,
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
  const [equipmentCategory, setEquipmentCategory] = useState<BaseItemEquipmentCategory | "">(
    item.equipmentCategory ?? (item.magicEffect?.spellCanonicalKey ? BaseItemEquipmentCategoryValues.MAGIC_BRACELET : ""),
  );
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
  const [isPurchasable, setIsPurchasable] = useState(item.isPurchasable !== false);
  const [chargesMax, setChargesMax] = useState(item.chargesMax?.toString() ?? "");
  const [rechargeType, setRechargeType] = useState<"" | "none" | "short_rest" | "long_rest" | "dawn" | "custom">(
    item.rechargeType ?? "",
  );
  const [spellCanonicalKey, setSpellCanonicalKey] = useState(
    item.magicEffect?.spellCanonicalKey ?? "",
  );
  const [castLevel, setCastLevel] = useState(
    item.magicEffect?.castLevel != null ? String(item.magicEffect.castLevel) : "1",
  );
  const [ignoreComponents, setIgnoreComponents] = useState(
    Boolean(item.magicEffect?.ignoreComponents),
  );
  const [noFreeHandRequired, setNoFreeHandRequired] = useState(
    Boolean(item.magicEffect?.noFreeHandRequired),
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
        equipmentCategory: equipmentCategory || undefined,
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
        chargesMax:
          equipmentCategory === BaseItemEquipmentCategoryValues.MAGIC_BRACELET && chargesMax.trim()
            ? chargesMax
            : undefined,
        rechargeType:
          equipmentCategory === BaseItemEquipmentCategoryValues.MAGIC_BRACELET && rechargeType
            ? rechargeType
            : undefined,
        magicEffect:
          equipmentCategory === BaseItemEquipmentCategoryValues.MAGIC_BRACELET && spellCanonicalKey
            ? {
                type: "cast_spell",
                spellCanonicalKey,
                castLevel: castLevel.trim() ? Number(castLevel) : 1,
                ignoreComponents,
                noFreeHandRequired,
              }
            : undefined,
        isPurchasable,
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
      spells={spells}
      name={name}
      description={description}
      price={price}
      equipmentCategory={equipmentCategory}
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
      isPurchasable={isPurchasable}
      chargesMax={chargesMax}
      rechargeType={rechargeType}
      spellCanonicalKey={spellCanonicalKey}
      castLevel={castLevel}
      ignoreComponents={ignoreComponents}
      noFreeHandRequired={noFreeHandRequired}
      selectedProperties={selectedProperties}
      legacyUnknownProperties={initialProperties.invalid}
      canSave={canSave}
      isSaving={isSaving}
      onNameChange={setName}
      onTypeChange={setType}
      onDescriptionChange={setDescription}
      onPriceChange={setPrice}
      onEquipmentCategoryChange={(value) => {
        setEquipmentCategory(value);
        if (value === BaseItemEquipmentCategoryValues.MAGIC_BRACELET) {
          setType("MAGIC");
          setChargesMax((current) => current || "1");
          setRechargeType((current) => current || "none");
        } else {
          setChargesMax("");
          setRechargeType("");
          setSpellCanonicalKey("");
          setCastLevel("1");
          setIgnoreComponents(false);
          setNoFreeHandRequired(false);
        }
      }}
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
      onIsPurchasableChange={setIsPurchasable}
      onChargesMaxChange={setChargesMax}
      onRechargeTypeChange={setRechargeType}
      onSpellCanonicalKeyChange={setSpellCanonicalKey}
      onCastLevelChange={setCastLevel}
      onIgnoreComponentsChange={setIgnoreComponents}
      onNoFreeHandRequiredChange={setNoFreeHandRequired}
      onPropertiesChange={setSelectedProperties}
      onCancel={() => setIsEditing(false)}
      onSave={() => void handleSave()}
    />
  );
};
