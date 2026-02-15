import { useEffect, useState } from "react";
import type { InventoryItem } from "../../../entities/inventory";
import { inventoryRepo } from "../../../shared/api/inventoryRepo";
import { useCampaigns } from "../../campaign-select";

type UseInventoryOptions = {
  memberId?: string | null;
};

export const useInventory = (options?: UseInventoryOptions) => {
  const { selectedCampaignId } = useCampaigns();
  const memberId = options?.memberId ?? null;
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [inventoryLoading, setInventoryLoading] = useState(false);
  const [inventoryError, setInventoryError] = useState<string | null>(null);

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
    let active = true;
    setInventoryLoading(true);
    inventoryRepo
      .list(selectedCampaignId, memberId)
      .then((data) => {
        if (!active) return;
        setInventory(Array.isArray(data) ? data : []);
        setInventoryError(null);
      })
      .catch((error: { message?: string }) => {
        if (!active) return;
        setInventory([]);
        setInventoryError(error?.message ?? "Failed to load inventory");
      })
      .finally(() => {
        if (!active) return;
        setInventoryLoading(false);
      });

    return () => {
      active = false;
    };
  }, [selectedCampaignId, memberId, options?.memberId]);

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
    toggleEquipped,
    selectedCampaignId,
  };
};
