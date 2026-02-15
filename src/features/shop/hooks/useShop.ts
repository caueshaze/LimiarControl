import { useCallback, useEffect, useState } from "react";
import { nanoid } from "nanoid";
import type { Item, ItemInput, ItemType } from "../../../entities/item";
import { ITEM_TYPES } from "../../../entities/item";
import { itemsRepo } from "../../../shared/api/itemsRepo";
import { inventoryRepo } from "../../../shared/api/inventoryRepo";
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

const normalizeItems = (data: unknown): Item[] => {
  if (!Array.isArray(data)) {
    return [];
  }
  return data.filter(isItem);
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
    return { ok: false, message: price.error as const };
  }
  const weight = parseNullableNumber(payload.weight, mapFieldError("weight"));
  if (!weight.ok) {
    return { ok: false, message: weight.error as const };
  }
  const rangeMeters = parseNullableNumber(
    payload.rangeMeters,
    mapFieldError("rangeMeters")
  );
  if (!rangeMeters.ok) {
    return { ok: false, message: rangeMeters.error as const };
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

  const loadItems = useCallback(
    (target?: { campaignId?: string | null; sessionId?: string | null }) => {
      const targetSessionId = target?.sessionId ?? sessionId;
      const targetCampaignId = target?.campaignId ?? campaignId;
      if (!targetSessionId && !targetCampaignId) {
        setItems([]);
        setItemsError(null);
        return Promise.resolve([]);
      }
      setItemsLoading(true);
      const request = targetSessionId
        ? itemsRepo.listBySession(targetSessionId)
        : itemsRepo.list(targetCampaignId as string);
      return request
        .then((data) => {
          const next = normalizeItems(data);
          setItems(next);
          setItemsError(null);
          return next;
        })
        .catch((error: { message?: string }) => {
          setItems([]);
          setItemsError(error?.message ?? "Failed to load items");
          return [];
        })
        .finally(() => {
          setItemsLoading(false);
        });
    },
    [campaignId, sessionId]
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
      .create(campaignId, normalized.value)
      .then((item) => {
        setItems((current) => [item, ...current]);
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
      .update(campaignId, itemId, normalized.value)
      .then((item) => {
        setItems((current) =>
          current.map((entry) => (entry.id === itemId ? item : entry))
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

  const buyItem = (itemId: string) => {
    if (!sessionId) {
      return;
    }
    return inventoryRepo.buy(sessionId, {
      itemId,
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
    itemTypes: Object.values(ITEM_TYPES),
    selectedCampaignId: campaignId,
  };
};
