import type { BaseItem, BaseItemWritePayload } from "../../entities/base-item";
import {
  BaseItemArmorCategory as BaseItemArmorCategoryValues,
  BaseItemKind as BaseItemKindValues,
  BaseItemSource as BaseItemSourceValues,
  BaseItemWeaponRangeType as BaseItemWeaponRangeTypeValues,
} from "../../entities/base-item";
import type { FormState } from "./systemCatalog.types";

export const normalizeOptionalText = (value: string) => {
  const normalized = value.trim();
  return normalized ? normalized : undefined;
};

export const normalizeCanonicalKey = (value: string) =>
  value
    .trim()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_+|_+$/g, "");

const parseOptionalNumber = (
  value: string,
  label: string,
): { value?: number; error?: string } => {
  const normalized = value.trim();
  if (!normalized) {
    return {};
  }
  const parsed = Number(normalized);
  if (!Number.isFinite(parsed)) {
    return { error: `${label} precisa ser numérico.` };
  }
  return { value: parsed };
};

const parseOptionalInteger = (
  value: string,
  label: string,
): { value?: number; error?: string } => {
  const result = parseOptionalNumber(value, label);
  if (result.error || result.value === undefined) {
    return result;
  }
  if (!Number.isInteger(result.value)) {
    return { error: `${label} precisa ser inteiro.` };
  }
  return { value: result.value };
};

export const createEmptyForm = (): FormState => ({
  system: "DND5E",
  canonicalKey: "",
  nameEn: "",
  namePt: "",
  descriptionEn: "",
  descriptionPt: "",
  itemKind: BaseItemKindValues.GEAR,
  equipmentCategory: "",
  costQuantity: "",
  costUnit: "",
  weight: "",
  weaponCategory: "",
  weaponRangeType: "",
  damageDice: "",
  damageType: "",
  healDice: "",
  healBonus: "",
  rangeNormalMeters: "",
  rangeLongMeters: "",
  versatileDamage: "",
  weaponPropertiesJson: [],
  armorCategory: "",
  armorClassBase: "",
  dexBonusRule: "",
  strengthRequirement: "",
  stealthDisadvantage: false,
  source: BaseItemSourceValues.ADMIN_PANEL,
  sourceRef: "",
  isSrd: false,
  isActive: true,
});

export const formFromItem = (item: BaseItem): FormState => ({
  system: item.system,
  canonicalKey: item.canonicalKey,
  nameEn: item.nameEn ?? "",
  namePt: item.namePt ?? "",
  descriptionEn: item.descriptionEn ?? "",
  descriptionPt: item.descriptionPt ?? "",
  itemKind: item.itemKind,
  equipmentCategory: item.equipmentCategory ?? "",
  costQuantity: item.costQuantity != null ? String(item.costQuantity) : "",
  costUnit: item.costUnit ?? "",
  weight: item.weight != null ? String(item.weight) : "",
  weaponCategory: item.weaponCategory ?? "",
  weaponRangeType: item.weaponRangeType ?? "",
  damageDice: item.damageDice ?? "",
  damageType: item.damageType ?? "",
  healDice: item.healDice ?? "",
  healBonus: item.healBonus != null ? String(item.healBonus) : "",
  rangeNormalMeters: item.rangeNormalMeters != null ? String(item.rangeNormalMeters) : "",
  rangeLongMeters: item.rangeLongMeters != null ? String(item.rangeLongMeters) : "",
  versatileDamage: item.versatileDamage ?? "",
  weaponPropertiesJson: item.weaponPropertiesJson ?? [],
  armorCategory: item.armorCategory ?? "",
  armorClassBase: item.armorClassBase != null ? String(item.armorClassBase) : "",
  dexBonusRule: item.dexBonusRule ?? "",
  strengthRequirement:
    item.strengthRequirement != null ? String(item.strengthRequirement) : "",
  stealthDisadvantage: Boolean(item.stealthDisadvantage),
  source: item.source ?? BaseItemSourceValues.ADMIN_PANEL,
  sourceRef: item.sourceRef ?? "",
  isSrd: item.isSrd,
  isActive: item.isActive,
});

export const buildPayload = (
  form: FormState,
): { payload?: BaseItemWritePayload; error?: string } => {
  const canonicalKey = normalizeCanonicalKey(form.canonicalKey);
  if (!canonicalKey) {
    return { error: "Canonical key é obrigatório." };
  }

  const nameEn = normalizeOptionalText(form.nameEn);
  const namePt = normalizeOptionalText(form.namePt);
  if (!nameEn && !namePt) {
    return { error: "Preencha ao menos um nome." };
  }

  const costQuantity = parseOptionalNumber(form.costQuantity, "Custo");
  if (costQuantity.error) return { error: costQuantity.error };
  const weight = parseOptionalNumber(form.weight, "Peso");
  if (weight.error) return { error: weight.error };
  const rangeNormalMeters = parseOptionalInteger(form.rangeNormalMeters, "Alcance normal (m)");
  if (rangeNormalMeters.error) return { error: rangeNormalMeters.error };
  const rangeLongMeters = parseOptionalInteger(form.rangeLongMeters, "Alcance longo (m)");
  if (rangeLongMeters.error) return { error: rangeLongMeters.error };
  const armorClassBase = parseOptionalInteger(form.armorClassBase, "CA base");
  if (armorClassBase.error) return { error: armorClassBase.error };
  const healBonus = parseOptionalInteger(form.healBonus, "Bônus de cura");
  if (healBonus.error) return { error: healBonus.error };
  const strengthRequirement = parseOptionalInteger(form.strengthRequirement, "Força mínima");
  if (strengthRequirement.error) return { error: strengthRequirement.error };

  const isWeapon = form.itemKind === BaseItemKindValues.WEAPON;
  const isArmor = form.itemKind === BaseItemKindValues.ARMOR;
  const isConsumable = form.itemKind === BaseItemKindValues.CONSUMABLE;
  const hasThrownProperty = form.weaponPropertiesJson.includes("thrown");
  const supportsLongRangeField =
    isWeapon &&
    (form.weaponRangeType === BaseItemWeaponRangeTypeValues.RANGED || hasThrownProperty);
  const hasVersatileProperty = form.weaponPropertiesJson.includes("versatile");
  const isShieldArmor = isArmor && form.armorCategory === BaseItemArmorCategoryValues.SHIELD;

  if (isWeapon && !form.weaponCategory)
    return { error: "Armas precisam de categoria de arma." };
  if (isWeapon && !form.weaponRangeType)
    return { error: "Armas precisam de tipo de alcance." };
  if (isWeapon && !normalizeOptionalText(form.damageDice))
    return { error: "Armas precisam de dado de dano." };
  if (isWeapon && !form.damageType)
    return { error: "Armas precisam de tipo de dano." };
  if (isWeapon && rangeNormalMeters.value === undefined)
    return { error: "Armas precisam de alcance normal em metros." };
  if (isArmor && !form.armorCategory)
    return { error: "Armaduras precisam de categoria." };
  if (isArmor && armorClassBase.value === undefined)
    return { error: "Armaduras precisam de CA base." };
  if (isArmor && !isShieldArmor && !form.dexBonusRule)
    return { error: "Armaduras não-escudo precisam de regra de DEX." };

  return {
    payload: {
      system: form.system,
      canonicalKey,
      nameEn,
      namePt,
      descriptionEn: normalizeOptionalText(form.descriptionEn),
      descriptionPt: normalizeOptionalText(form.descriptionPt),
      itemKind: form.itemKind,
      equipmentCategory: form.equipmentCategory || undefined,
      costQuantity: costQuantity.value,
      costUnit: form.costUnit || undefined,
      weight: weight.value,
      weaponCategory: isWeapon ? form.weaponCategory || undefined : undefined,
      weaponRangeType: isWeapon ? form.weaponRangeType || undefined : undefined,
      damageDice: isWeapon ? normalizeOptionalText(form.damageDice) : undefined,
      damageType: isWeapon ? form.damageType || undefined : undefined,
      healDice: isConsumable ? normalizeOptionalText(form.healDice) : undefined,
      healBonus: isConsumable ? healBonus.value : undefined,
      rangeNormalMeters: isWeapon ? rangeNormalMeters.value : undefined,
      rangeLongMeters: supportsLongRangeField ? rangeLongMeters.value : undefined,
      versatileDamage:
        isWeapon && hasVersatileProperty
          ? normalizeOptionalText(form.versatileDamage)
          : undefined,
      weaponPropertiesJson: isWeapon ? form.weaponPropertiesJson : [],
      armorCategory: isArmor ? form.armorCategory || undefined : undefined,
      armorClassBase: isArmor ? armorClassBase.value : undefined,
      dexBonusRule:
        isArmor && !isShieldArmor ? form.dexBonusRule || undefined : undefined,
      strengthRequirement:
        isArmor && !isShieldArmor ? strengthRequirement.value : undefined,
      stealthDisadvantage:
        isArmor && !isShieldArmor ? form.stealthDisadvantage : false,
      isShield: isShieldArmor,
      source: form.source,
      sourceRef: normalizeOptionalText(form.sourceRef),
      isSrd: form.isSrd,
      isActive: form.isActive,
    },
  };
};

export const currencyLabel = (value?: BaseItem["costUnit"] | "") =>
  value ? value.toUpperCase() : "sem custo";
