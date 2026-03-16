import { useCallback, useEffect, useRef, useState } from "react";
import type { InventoryItem } from "../../../entities/inventory";
import type { Item, ItemInput, ItemType } from "../../../entities/item";
import { ITEM_TYPES } from "../../../entities/item";
import { itemsRepo } from "../../../shared/api/itemsRepo";
import {
  inventoryRepo,
  type InventorySellResult,
} from "../../../shared/api/inventoryRepo";
import { parseNullableNumber } from "../../../shared/lib/parse";
import { useCampaigns } from "../../campaign-select";
import { BASE_CATALOG_ITEMS, getBaseCatalogItemByName } from "../data/baseCatalogItems";


const mapFieldError = (field: "price" | "weight" | "rangeMeters") => {
  if (field === "price") return "catalog.validation.price";
  if (field === "weight") return "catalog.validation.weight";
  return "catalog.validation.range";
};

const isItemType = (value: string): value is ItemType =>
  Object.values(ITEM_TYPES).includes(value as ItemType);

const isItem = (value: Item): boolean =>
  Boolean(value?.id && value?.name && isItemType(value.type) && value.description);

const withBaseMetadata = (item: Item): Item => {
  const baseItem = getBaseCatalogItemByName(item.name);
  const priceMatchesBase =
    baseItem &&
    typeof item.price === "number" &&
    typeof baseItem.price === "number" &&
    Math.abs(item.price - baseItem.price) < 0.0001;

  return {
    ...item,
    priceLabel: item.priceLabel ?? (priceMatchesBase ? baseItem?.priceLabel : undefined),
  };
};

const normalizeItems = (data: unknown): Item[] => {
  if (!Array.isArray(data)) {
    return [];
  }
  return data.filter(isItem).map(withBaseMetadata);
};

const normalizeItemInput = (payload: ItemInput) => {
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
  const rangeMeters = parseNullableNumber(
    payload.rangeMeters,
    mapFieldError("rangeMeters")
  );
  if (!rangeMeters.ok) {
    return { ok: false, message: rangeMeters.error };
  }

  return {
    ok: true,
    value: {
      ...payload,
      name: payload.name.trim(),
      description: payload.description.trim(),
      price: price.value,
      weight: weight.value,
      rangeMeters: rangeMeters.value,
    },
  };
};

type UseShopOptions = {
  campaignId?: string | null;
  sessionId?: string | null;
  auto?: boolean;
};

export const useShop = (options?: UseShopOptions) => {
  const { selectedCampaignId } = useCampaigns();
  const campaignId = options?.campaignId ?? selectedCampaignId ?? null;
  const sessionId = options?.sessionId ?? null;
  const auto = options?.auto ?? true;
  const [items, setItems] = useState<Item[]>([]);
  const [itemsError, setItemsError] = useState<string | null>(null);
  const [itemsLoading, setItemsLoading] = useState(false);
  const seededCampaignsRef = useRef<Set<string>>(new Set());

  const ensureBaseCatalog = useCallback(
    async (targetCampaignId: string, existingItems?: Item[]) => {
      const alreadySeeded = seededCampaignsRef.current.has(targetCampaignId);
      const normalizedExisting = existingItems ?? normalizeItems(await itemsRepo.list(targetCampaignId));
      if (alreadySeeded) {
        return normalizedExisting;
      }

      const existingNames = new Set(normalizedExisting.map((item) => item.name.toLowerCase()));
      const missingItems = BASE_CATALOG_ITEMS.filter(
        (item) => !existingNames.has(item.name.toLowerCase())
      );

      if (missingItems.length > 0) {
        await Promise.all(
          missingItems.map((item) =>
            itemsRepo.create(targetCampaignId, {
              name: item.name,
              type: item.type,
              description: item.description,
              price: item.price ?? null,
              weight: item.weight ?? null,
              damageDice: item.damageDice,
              rangeMeters: item.rangeMeters ?? null,
              properties: item.properties,
            })
          )
        );
      }

      seededCampaignsRef.current.add(targetCampaignId);
      if (missingItems.length === 0) {
        return normalizedExisting;
      }
      return normalizeItems(await itemsRepo.list(targetCampaignId));
    },
    []
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
        const next = normalizeItems(data);
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
    [campaignId, ensureBaseCatalog, sessionId]
  );

  useEffect(() => {
    if (!auto) {
      return;
    }
    void loadItems();
  }, [campaignId, sessionId, auto, loadItems]);

  const createItem = (payload: ItemInput) => {
    if (!campaignId) {
      return Promise.resolve({ ok: false, message: "No campaign selected." });
    }

    const normalized = normalizeItemInput(payload);
    if (!normalized.ok) {
      if (import.meta.env.DEV) {
        console.error("Item validation failed", normalized.message);
      }
      return Promise.resolve({ ok: false, message: normalized.message });
    }

    return itemsRepo
      .create(campaignId, normalized.value!)
      .then((item) => {
        setItems((current) => [normalizeItems([item])[0], ...current]);
        return { ok: true };
      })
      .catch((error: { message?: string }) => ({
        ok: false,
        message: error?.message ?? "Failed to create item",
      }));
  };

  const updateItem = (itemId: string, payload: ItemInput) => {
    if (!campaignId) {
      return Promise.resolve({ ok: false, message: "No campaign selected." });
    }

    const normalized = normalizeItemInput(payload);
    if (!normalized.ok) {
      if (import.meta.env.DEV) {
        console.error("Item validation failed", normalized.message);
      }
      return Promise.resolve({ ok: false, message: normalized.message });
    }

    return itemsRepo
      .update(campaignId, itemId, normalized.value!)
      .then((item) => {
        setItems((current) =>
          current.map((entry) => (entry.id === itemId ? normalizeItems([item])[0] : entry))
        );
        return { ok: true };
      })
      .catch((error: { message?: string }) => ({
        ok: false,
        message: error?.message ?? "Failed to update item",
      }));
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
  };
};
