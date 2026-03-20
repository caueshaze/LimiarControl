import { useCallback, useEffect, useRef, useState } from "react";
import { CampaignSystemType } from "../../../entities/campaign";
import type { InventoryItem } from "../../../entities/inventory";
import type { Item, ItemInput, ItemType } from "../../../entities/item";
import { ITEM_TYPES } from "../../../entities/item";
import { normalizeItemProperties } from "../../../entities/item";
import { itemsRepo } from "../../../shared/api/itemsRepo";
import { campaignCatalogRepo } from "../../../shared/api/campaignCatalogRepo";
import {
  inventoryRepo,
  type InventorySellResult,
} from "../../../shared/api/inventoryRepo";
import { parseNullableNumber } from "../../../shared/lib/parse";
import { useCampaigns } from "../../campaign-select";

const mapFieldError = (field: "price" | "weight" | "rangeMeters") => {
  if (field === "price") return "catalog.validation.price";
  if (field === "weight") return "catalog.validation.weight";
  return "catalog.validation.range";
};

const isItemType = (value: string): value is ItemType =>
  Object.values(ITEM_TYPES).includes(value as ItemType);

const isItem = (value: Item): boolean =>
  Boolean(value?.id && value?.name && isItemType(value.type) && value.description);

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
  const seededCampaignsRef = useRef<Set<string>>(new Set());

  const ensureBaseCatalog = useCallback(
    async (targetCampaignId: string) => {
      if (seededCampaignsRef.current.has(targetCampaignId)) {
        return;
      }
      try {
        await campaignCatalogRepo.seed(targetCampaignId);
      } catch {
        // Seed may fail for non-GM users; the catalog items
        // materialized by the GM will still be visible via list.
      }
      seededCampaignsRef.current.add(targetCampaignId);
    },
    [],
  );

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
        if (targetCampaignId) {
          await ensureBaseCatalog(targetCampaignId);
        }
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
    [campaignId, ensureBaseCatalog, sessionId],
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
    const properties = normalizeItemProperties(payload.properties);
    if (!properties.ok) {
      return { ok: false, message: "catalog.validation.properties" as const };
    }

    try {
      const item = await itemsRepo.create(campaignId, {
        name: payload.name.trim(),
        type: payload.type,
        description: payload.description.trim(),
        price: price.value,
        weight: weight.value,
        damageDice: payload.damageDice,
        rangeMeters: rangeMeters.value,
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
    const properties = normalizeItemProperties(payload.properties);
    if (!properties.ok) {
      return { ok: false, message: "catalog.validation.properties" as const };
    }

    try {
      const item = await itemsRepo.update(campaignId, itemId, {
        name: payload.name.trim(),
        type: payload.type,
        description: payload.description.trim(),
        price: price.value,
        weight: weight.value,
        damageDice: payload.damageDice,
        rangeMeters: rangeMeters.value,
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
