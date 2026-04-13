import { useCallback, useEffect, useState } from "react";
import type { InventoryItem } from "../../../entities/inventory";
import { inventoryRepo } from "../../../shared/api/inventoryRepo";
import { useCampaigns } from "../../campaign-select";

type UseInventoryOptions = {
  memberId?: string | null;
  partyId?: string | null;
};

export const useInventory = (options?: UseInventoryOptions) => {
  const { selectedCampaignId } = useCampaigns();
  const memberId = options?.memberId ?? null;
  const partyId = options?.partyId ?? null;
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [inventoryLoading, setInventoryLoading] = useState(false);
  const [inventoryError, setInventoryError] = useState<string | null>(null);

  const refreshInventory = useCallback(
    async ({ silent = false }: { silent?: boolean } = {}) => {
      if (!selectedCampaignId) {
        setInventory([]);
        setInventoryError(null);
        return;
      }
      if (options?.memberId === null) {
        setInventory([]);
        setInventoryError(null);
        return;
      }
      if (!silent) {
        setInventoryLoading(true);
      }
      try {
        const data = await inventoryRepo.list(selectedCampaignId, memberId, partyId);
        setInventory(Array.isArray(data) ? data : []);
        setInventoryError(null);
      } catch (error: unknown) {
        const typedError = error as { message?: string };
        setInventory([]);
        setInventoryError(typedError?.message ?? "Failed to load inventory");
      } finally {
        if (!silent) {
          setInventoryLoading(false);
        }
      }
    },
    [selectedCampaignId, memberId, partyId, options?.memberId]
  );

  useEffect(() => {
    if (!selectedCampaignId) {
      setInventory([]);
      setInventoryError(null);
      return;
    }
    if (options?.memberId === null) {
      setInventory([]);
      setInventoryError(null);
      return;
    }
    void refreshInventory();
  }, [selectedCampaignId, options?.memberId, refreshInventory]);

  const toggleEquipped = (id: string) => {
    if (!selectedCampaignId) {
      return Promise.resolve();
    }
    const target = inventory.find((item) => item.id === id);
    if (!target) {
      return Promise.resolve();
    }
    const nextValue = !target.isEquipped;
    return inventoryRepo
      .update(selectedCampaignId, id, { isEquipped: nextValue })
      .then((updated) => {
        setInventory((current) =>
          current.map((item) => (item.id === id ? updated : item))
        );
      });
  };

  return {
    inventory,
    inventoryLoading,
    inventoryError,
    refreshInventory,
    toggleEquipped,
    selectedCampaignId,
  };
};
