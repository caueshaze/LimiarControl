import { useCallback, useEffect, useState } from "react";
import { CampaignSystemType } from "../../../entities/campaign";
import type { InventoryItem } from "../../../entities/inventory";
import type { Item, ItemInput } from "../../../entities/item";
import { ITEM_TYPES } from "../../../entities/item";
import { itemsRepo } from "../../../shared/api/itemsRepo";
import {
  inventoryRepo,
  type InventorySellResult,
} from "../../../shared/api/inventoryRepo";
import { useCampaigns } from "../../campaign-select";
import { isItem, validateCatalogItemPayload } from "./shopValidation";

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

    const validation = validateCatalogItemPayload(payload);
    if (!validation.ok) {
      return { ok: false, message: validation.message };
    }

    try {
      const item = await itemsRepo.create(campaignId, {
        name: validation.value.name.trim(),
        type: validation.value.type,
        description: validation.value.description.trim(),
        price: validation.value.price,
        weight: validation.value.weight,
        damageDice: validation.value.damageDice,
        damageType: validation.value.damageType,
        rangeMeters: validation.value.rangeMeters,
        rangeLongMeters: validation.value.rangeLongMeters,
        versatileDamage: validation.value.versatileDamage,
        weaponCategory: validation.value.weaponCategory || undefined,
        weaponRangeType: validation.value.weaponRangeType || undefined,
        armorCategory: validation.value.armorCategory || undefined,
        armorClassBase: validation.value.armorClassBase,
        dexBonusRule: validation.value.dexBonusRule || undefined,
        strengthRequirement: validation.value.strengthRequirement,
        stealthDisadvantage: validation.value.stealthDisadvantage,
        isShield: validation.value.isShield,
        properties: validation.value.properties,
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

    const validation = validateCatalogItemPayload(payload);
    if (!validation.ok) {
      return { ok: false, message: validation.message };
    }

    try {
      const item = await itemsRepo.update(campaignId, itemId, {
        name: validation.value.name.trim(),
        type: validation.value.type,
        description: validation.value.description.trim(),
        price: validation.value.price,
        weight: validation.value.weight,
        damageDice: validation.value.damageDice,
        damageType: validation.value.damageType,
        rangeMeters: validation.value.rangeMeters,
        rangeLongMeters: validation.value.rangeLongMeters,
        versatileDamage: validation.value.versatileDamage,
        weaponCategory: validation.value.weaponCategory || undefined,
        weaponRangeType: validation.value.weaponRangeType || undefined,
        armorCategory: validation.value.armorCategory || undefined,
        armorClassBase: validation.value.armorClassBase,
        dexBonusRule: validation.value.dexBonusRule || undefined,
        strengthRequirement: validation.value.strengthRequirement,
        stealthDisadvantage: validation.value.stealthDisadvantage,
        isShield: validation.value.isShield,
        properties: validation.value.properties,
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
