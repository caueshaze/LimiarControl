import { useCallback, useEffect, useState } from "react";
import { CampaignSystemType } from "../../../entities/campaign";
import type { InventoryItem } from "../../../entities/inventory";
import type { Item, ItemInput, ItemType } from "../../../entities/item";
import { ITEM_TYPES } from "../../../entities/item";
import { normalizeItemProperties } from "../../../entities/item";
import { itemsRepo } from "../../../shared/api/itemsRepo";
import {
  inventoryRepo,
  type InventorySellResult,
} from "../../../shared/api/inventoryRepo";
import { parseNullableInt, parseNullableNumber } from "../../../shared/lib/parse";
import { useCampaigns } from "../../campaign-select";

const mapFieldError = (
  field:
    | "price"
    | "weight"
    | "rangeMeters"
    | "rangeLongMeters"
    | "armorClassBase"
    | "strengthRequirement",
) => {
  if (field === "price") return "catalog.validation.price";
  if (field === "weight") return "catalog.validation.weight";
  if (field === "armorClassBase") return "catalog.validation.armorClass";
  if (field === "strengthRequirement") return "catalog.validation.strengthRequirement";
  return "catalog.validation.range";
};

const isItemType = (value: string): value is ItemType =>
  Object.values(ITEM_TYPES).includes(value as ItemType);

const isItem = (value: Item): boolean =>
  Boolean(value?.id && value?.name && isItemType(value.type) && value.description);

const validateStructuredPayload = (payload: ItemInput) => {
  if (payload.rangeLongMeters !== null && payload.rangeLongMeters !== undefined && `${payload.rangeLongMeters}`.trim() !== "" && (payload.rangeMeters === null || payload.rangeMeters === undefined || `${payload.rangeMeters}`.trim() === "")) {
    return "catalog.validation.range" as const;
  }

  if (payload.type === "WEAPON") {
    if (
      !payload.damageDice?.trim()
      || !payload.damageType?.trim()
      || !payload.weaponCategory
      || !payload.weaponRangeType
    ) {
      return "catalog.validation.weaponFields" as const;
    }
    if (payload.weaponRangeType === "ranged" && (payload.rangeMeters === null || payload.rangeMeters === undefined || `${payload.rangeMeters}`.trim() === "")) {
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
    if (!payload.armorCategory || payload.armorClassBase === null || payload.armorClassBase === undefined || `${payload.armorClassBase}`.trim() === "") {
      return "catalog.validation.armorFields" as const;
    }
    if (payload.armorCategory !== "shield" && !payload.dexBonusRule?.trim()) {
      return "catalog.validation.armorFields" as const;
    }
  }

  return null;
};

type UseShopOptions = {
  campaignId?: string | null;
  sessionId?: string | null;
  auto?: boolean;
};

export const useShop = (options?: UseShopOptions) => {
  const { campaigns, selectedCampaignId } = useCampaigns();
  const campaignId = options?.campaignId ?? selectedCampaignId ?? null;
  const campaignSystemType =
    campaigns.find((campaign) => campaign.id === campaignId)?.systemType ?? null;
  const sessionId = options?.sessionId ?? null;
  const auto = options?.auto ?? true;
  const [items, setItems] = useState<Item[]>([]);
  const [itemsError, setItemsError] = useState<string | null>(null);
  const [itemsLoading, setItemsLoading] = useState(false);

  const loadItems = useCallback(
    async (target?: { campaignId?: string | null; sessionId?: string | null }) => {
      const targetSessionId = target?.sessionId ?? sessionId;
      const targetCampaignId = target?.campaignId ?? campaignId;
      if (!targetSessionId && !targetCampaignId) {
        setItems([]);
        setItemsError(null);
        return [];
      }
      setItemsLoading(true);
      try {
        const data = targetSessionId
          ? await itemsRepo.listBySession(targetSessionId)
          : await itemsRepo.list(targetCampaignId as string);
        const next = Array.isArray(data) ? data.filter(isItem) : [];
        setItems(next);
        setItemsError(null);
        return next;
      } catch (error: unknown) {
        setItems([]);
        setItemsError((error as { message?: string })?.message ?? "Failed to load items");
        return [];
      } finally {
        setItemsLoading(false);
      }
    },
    [campaignId, sessionId],
  );

  useEffect(() => {
    if (!auto) {
      return;
    }
    void loadItems();
  }, [campaignId, sessionId, auto, loadItems]);

  const createItem = async (payload: ItemInput) => {
    if (!campaignId) {
      return { ok: false, message: "No campaign selected." };
    }

    if (!payload.name.trim() || !payload.description.trim()) {
      return { ok: false, message: "catalog.validation.generic" as const };
    }
    if (!isItemType(payload.type)) {
      return { ok: false, message: "catalog.validation.generic" as const };
    }

    const price = parseNullableNumber(payload.price, mapFieldError("price"));
    if (!price.ok) {
      return { ok: false, message: price.error };
    }
    const weight = parseNullableNumber(payload.weight, mapFieldError("weight"));
    if (!weight.ok) {
      return { ok: false, message: weight.error };
    }
    const rangeMeters = parseNullableNumber(payload.rangeMeters, mapFieldError("rangeMeters"));
    if (!rangeMeters.ok) {
      return { ok: false, message: rangeMeters.error };
    }
    const rangeLongMeters = parseNullableNumber(
      payload.rangeLongMeters,
      mapFieldError("rangeLongMeters"),
    );
    if (!rangeLongMeters.ok) {
      return { ok: false, message: rangeLongMeters.error };
    }
    const armorClassBase = parseNullableInt(
      payload.armorClassBase,
      mapFieldError("armorClassBase"),
    );
    if (!armorClassBase.ok) {
      return { ok: false, message: armorClassBase.error };
    }
    const strengthRequirement = parseNullableInt(
      payload.strengthRequirement,
      mapFieldError("strengthRequirement"),
    );
    if (!strengthRequirement.ok) {
      return { ok: false, message: strengthRequirement.error };
    }
    const properties = normalizeItemProperties(payload.properties);
    if (!properties.ok) {
      return { ok: false, message: "catalog.validation.properties" as const };
    }
    const structuredValidationError = validateStructuredPayload({
      ...payload,
      rangeMeters: rangeMeters.value,
      rangeLongMeters: rangeLongMeters.value,
      armorClassBase: armorClassBase.value,
      strengthRequirement: strengthRequirement.value,
      properties: properties.value,
    });
    if (structuredValidationError) {
      return { ok: false, message: structuredValidationError };
    }

    try {
      const item = await itemsRepo.create(campaignId, {
        name: payload.name.trim(),
        type: payload.type,
        description: payload.description.trim(),
        price: price.value,
        weight: weight.value,
        damageDice: payload.damageDice,
        damageType: payload.damageType,
        rangeMeters: rangeMeters.value,
        rangeLongMeters: rangeLongMeters.value,
        versatileDamage: payload.versatileDamage,
        weaponCategory: payload.weaponCategory || undefined,
        weaponRangeType: payload.weaponRangeType || undefined,
        armorCategory: payload.armorCategory || undefined,
        armorClassBase: armorClassBase.value,
        dexBonusRule: payload.dexBonusRule?.trim() ? payload.dexBonusRule.trim() : undefined,
        strengthRequirement: strengthRequirement.value,
        stealthDisadvantage: payload.stealthDisadvantage,
        isShield: payload.isShield,
        properties: properties.value,
      });
      if (item) {
        setItems((current) => [item, ...current]);
      }
      return { ok: true };
    } catch (error: unknown) {
      return {
        ok: false,
        message: (error as { message?: string })?.message ?? "Failed to create item",
      };
    }
  };

  const updateItem = async (itemId: string, payload: ItemInput) => {
    if (!campaignId) {
      return { ok: false, message: "No campaign selected." };
    }

    if (!payload.name.trim() || !payload.description.trim()) {
      return { ok: false, message: "catalog.validation.generic" as const };
    }
    if (!isItemType(payload.type)) {
      return { ok: false, message: "catalog.validation.generic" as const };
    }

    const price = parseNullableNumber(payload.price, mapFieldError("price"));
    if (!price.ok) {
      return { ok: false, message: price.error };
    }
    const weight = parseNullableNumber(payload.weight, mapFieldError("weight"));
    if (!weight.ok) {
      return { ok: false, message: weight.error };
    }
    const rangeMeters = parseNullableNumber(payload.rangeMeters, mapFieldError("rangeMeters"));
    if (!rangeMeters.ok) {
      return { ok: false, message: rangeMeters.error };
    }
    const rangeLongMeters = parseNullableNumber(
      payload.rangeLongMeters,
      mapFieldError("rangeLongMeters"),
    );
    if (!rangeLongMeters.ok) {
      return { ok: false, message: rangeLongMeters.error };
    }
    const armorClassBase = parseNullableInt(
      payload.armorClassBase,
      mapFieldError("armorClassBase"),
    );
    if (!armorClassBase.ok) {
      return { ok: false, message: armorClassBase.error };
    }
    const strengthRequirement = parseNullableInt(
      payload.strengthRequirement,
      mapFieldError("strengthRequirement"),
    );
    if (!strengthRequirement.ok) {
      return { ok: false, message: strengthRequirement.error };
    }
    const properties = normalizeItemProperties(payload.properties);
    if (!properties.ok) {
      return { ok: false, message: "catalog.validation.properties" as const };
    }
    const structuredValidationError = validateStructuredPayload({
      ...payload,
      rangeMeters: rangeMeters.value,
      rangeLongMeters: rangeLongMeters.value,
      armorClassBase: armorClassBase.value,
      strengthRequirement: strengthRequirement.value,
      properties: properties.value,
    });
    if (structuredValidationError) {
      return { ok: false, message: structuredValidationError };
    }

    try {
      const item = await itemsRepo.update(campaignId, itemId, {
        name: payload.name.trim(),
        type: payload.type,
        description: payload.description.trim(),
        price: price.value,
        weight: weight.value,
        damageDice: payload.damageDice,
        damageType: payload.damageType,
        rangeMeters: rangeMeters.value,
        rangeLongMeters: rangeLongMeters.value,
        versatileDamage: payload.versatileDamage,
        weaponCategory: payload.weaponCategory || undefined,
        weaponRangeType: payload.weaponRangeType || undefined,
        armorCategory: payload.armorCategory || undefined,
        armorClassBase: armorClassBase.value,
        dexBonusRule: payload.dexBonusRule?.trim() ? payload.dexBonusRule.trim() : undefined,
        strengthRequirement: strengthRequirement.value,
        stealthDisadvantage: payload.stealthDisadvantage,
        isShield: payload.isShield,
        properties: properties.value,
      });
      if (item) {
        setItems((current) =>
          current.map((entry) => (entry.id === itemId ? item : entry)),
        );
      }
      return { ok: true };
    } catch (error: unknown) {
      return {
        ok: false,
        message: (error as { message?: string })?.message ?? "Failed to update item",
      };
    }
  };

  const deleteItem = (itemId: string) => {
    if (!campaignId) {
      return Promise.resolve();
    }

    return itemsRepo.remove(campaignId, itemId).then(() => {
      setItems((current) => current.filter((item) => item.id !== itemId));
    });
  };

  const buyItem = (itemId: string): Promise<InventoryItem> => {
    if (!sessionId) {
      return Promise.reject(new Error("No active session"));
    }
    return inventoryRepo.buy(sessionId, {
      itemId,
      quantity: 1,
    });
  };

  const sellItem = (inventoryItemId: string): Promise<InventorySellResult> => {
    if (!sessionId) {
      return Promise.reject(new Error("No active session"));
    }
    return inventoryRepo.sell(sessionId, {
      inventoryItemId,
      quantity: 1,
    });
  };

  return {
    items,
    itemsLoading,
    itemsError,
    loadItems,
    createItem,
    updateItem,
    deleteItem,
    buyItem,
    sellItem,
    itemTypes: Object.values(ITEM_TYPES),
    selectedCampaignId: campaignId,
    campaignSystemType,
  };
};
