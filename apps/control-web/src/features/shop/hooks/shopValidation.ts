import type { Item, ItemInput, ItemType } from "../../../entities/item";
import { ITEM_TYPES, normalizeItemProperties } from "../../../entities/item";
import { parseNullableInt, parseNullableNumber } from "../../../shared/lib/parse";

const mapFieldError = (
  field:
    | "price"
    | "weight"
    | "rangeMeters"
    | "rangeLongMeters"
    | "armorClassBase"
    | "strengthRequirement"
    | "healBonus",
) => {
  if (field === "price") return "catalog.validation.price";
  if (field === "weight") return "catalog.validation.weight";
  if (field === "armorClassBase") return "catalog.validation.armorClass";
  if (field === "strengthRequirement") return "catalog.validation.strengthRequirement";
  if (field === "healBonus") return "catalog.validation.healBonus";
  return "catalog.validation.range";
};

export const isItemType = (value: string): value is ItemType =>
  Object.values(ITEM_TYPES).includes(value as ItemType);

export const isItem = (value: Item): boolean =>
  Boolean(value?.id && value?.name && isItemType(value.type) && value.description);

const validateStructuredPayload = (payload: ItemInput) => {
  if (
    payload.rangeLongMeters !== null &&
    payload.rangeLongMeters !== undefined &&
    `${payload.rangeLongMeters}`.trim() !== "" &&
    (payload.rangeMeters === null ||
      payload.rangeMeters === undefined ||
      `${payload.rangeMeters}`.trim() === "")
  ) {
    return "catalog.validation.range" as const;
  }

  if (payload.type === "WEAPON") {
    if (
      !payload.damageDice?.trim() ||
      !payload.damageType?.trim() ||
      !payload.weaponCategory ||
      !payload.weaponRangeType
    ) {
      return "catalog.validation.weaponFields" as const;
    }
    if (
      payload.weaponRangeType === "ranged" &&
      (payload.rangeMeters === null ||
        payload.rangeMeters === undefined ||
        `${payload.rangeMeters}`.trim() === "")
    ) {
      return "catalog.validation.weaponFields" as const;
    }
    if (payload.versatileDamage && !payload.properties?.includes("versatile")) {
      return "catalog.validation.versatile" as const;
    }
  }

  if (payload.type === "MAGIC" && payload.damageDice?.trim() && !payload.damageType?.trim()) {
    return "catalog.validation.magicDamageType" as const;
  }

  if (payload.type === "ARMOR") {
    if (
      !payload.armorCategory ||
      payload.armorClassBase === null ||
      payload.armorClassBase === undefined ||
      `${payload.armorClassBase}`.trim() === ""
    ) {
      return "catalog.validation.armorFields" as const;
    }
    if (payload.armorCategory !== "shield" && !payload.dexBonusRule?.trim()) {
      return "catalog.validation.armorFields" as const;
    }
  }

  return null;
};

export const validateCatalogItemPayload = (payload: ItemInput) => {
  if (!payload.name.trim() || !payload.description.trim()) {
    return { ok: false as const, message: "catalog.validation.generic" as const };
  }
  if (!isItemType(payload.type)) {
    return { ok: false as const, message: "catalog.validation.generic" as const };
  }

  const price = parseNullableNumber(payload.price, mapFieldError("price"));
  if (!price.ok) {
    return { ok: false as const, message: price.error };
  }

  const weight = parseNullableNumber(payload.weight, mapFieldError("weight"));
  if (!weight.ok) {
    return { ok: false as const, message: weight.error };
  }

  const rangeMeters = parseNullableNumber(payload.rangeMeters, mapFieldError("rangeMeters"));
  if (!rangeMeters.ok) {
    return { ok: false as const, message: rangeMeters.error };
  }

  const rangeLongMeters = parseNullableNumber(
    payload.rangeLongMeters,
    mapFieldError("rangeLongMeters"),
  );
  if (!rangeLongMeters.ok) {
    return { ok: false as const, message: rangeLongMeters.error };
  }

  const armorClassBase = parseNullableInt(
    payload.armorClassBase,
    mapFieldError("armorClassBase"),
  );
  if (!armorClassBase.ok) {
    return { ok: false as const, message: armorClassBase.error };
  }

  const strengthRequirement = parseNullableInt(
    payload.strengthRequirement,
    mapFieldError("strengthRequirement"),
  );
  if (!strengthRequirement.ok) {
    return { ok: false as const, message: strengthRequirement.error };
  }

  const healBonus = parseNullableInt(payload.healBonus, mapFieldError("healBonus"));
  if (!healBonus.ok) {
    return { ok: false as const, message: healBonus.error };
  }

  const properties = normalizeItemProperties(payload.properties);
  if (!properties.ok) {
    return { ok: false as const, message: "catalog.validation.properties" as const };
  }

  const structuredValidationError = validateStructuredPayload({
    ...payload,
    rangeMeters: rangeMeters.value,
    rangeLongMeters: rangeLongMeters.value,
    armorClassBase: armorClassBase.value,
    strengthRequirement: strengthRequirement.value,
    healBonus: healBonus.value,
    properties: properties.value,
  });
  if (structuredValidationError) {
    return { ok: false as const, message: structuredValidationError };
  }

  return {
    ok: true as const,
    value: {
      ...payload,
      price: price.value,
      weight: weight.value,
      rangeMeters: rangeMeters.value,
      rangeLongMeters: rangeLongMeters.value,
      armorClassBase: armorClassBase.value,
      strengthRequirement: strengthRequirement.value,
      healBonus: healBonus.value,
      properties: properties.value,
    },
  };
};
