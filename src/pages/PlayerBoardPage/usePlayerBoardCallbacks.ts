import { useCallback, type Dispatch, type SetStateAction } from "react";
import { routes } from "../../app/routes/routes";
import { localizedItemName } from "../../features/shop/utils/localizedItemName";
import type { InventoryItem } from "../../entities/inventory";
import type { Item } from "../../entities/item";
import type { useLocale } from "../../shared/hooks/useLocale";

type Props = {
  locale: "pt" | "en";
  navigate: (to: string) => void;
  partyId?: string;
  setInventoryFlash: (value: boolean) => void;
  setMyInventory: Dispatch<SetStateAction<InventoryItem[] | null>>;
  setPlayerWallet: (value: any) => void;
  showToast: (toast: {
    variant: "success" | "error";
    title: string;
    description: string;
  }) => void;
  t: ReturnType<typeof useLocale>["t"];
};

export const usePlayerBoardCallbacks = ({
  locale,
  navigate,
  partyId,
  setInventoryFlash,
  setMyInventory,
  setPlayerWallet,
  showToast,
  t,
}: Props) => {
  const translateShopErrorMessage = useCallback(
    (message?: string | null) => {
      if (!message) {
        return t("shop.buyErrorDescription");
      }
      if (message === "Not enough currency") {
        return t("shop.error.notEnoughCurrency");
      }
      return message;
    },
    [t],
  );

  const handleOpenSheet = useCallback(() => {
    if (!partyId) {
      return;
    }
    navigate(
      `${routes.characterSheetParty.replace(":partyId", partyId)}?${new URLSearchParams({
        mode: "play",
        returnTo: "board",
      }).toString()}`,
    );
  }, [navigate, partyId]);

  const upsertInventoryEntry = useCallback(
    (nextEntry: InventoryItem) => {
      setMyInventory((current) => {
        const source = current ?? [];
        const existing = source.find((entry) => entry.id === nextEntry.id);
        if (existing) {
          return source.map((entry) => (entry.id === nextEntry.id ? nextEntry : entry));
        }
        const sameItem = source.find((entry) => entry.itemId === nextEntry.itemId);
        if (sameItem) {
          return source.map((entry) =>
            entry.itemId === nextEntry.itemId
              ? {
                  ...entry,
                  quantity: nextEntry.quantity,
                  isEquipped: nextEntry.isEquipped,
                  notes: nextEntry.notes,
                }
              : entry,
          );
        }
        return [nextEntry, ...source];
      });
    },
    [setMyInventory],
  );

  const applySoldInventoryEntry = useCallback(
    (soldInventoryItemId: string, nextEntry: InventoryItem | null) => {
      setMyInventory((current) => {
        const source = current ?? [];
        if (nextEntry) {
          return source.map((entry) => (entry.id === soldInventoryItemId ? nextEntry : entry));
        }
        return source.filter((entry) => entry.id !== soldInventoryItemId);
      });
    },
    [setMyInventory],
  );

  const createBuySuccessToast = useCallback(
    (item: Item) => ({
      variant: "success" as const,
      title: t("shop.buyTitle"),
      description: `${localizedItemName(item, locale)} ${t("shop.buyDescription")}`,
    }),
    [locale, t],
  );

  const createSellSuccessToast = useCallback(
    (item: Item, refundLabel: string) => ({
      variant: "success" as const,
      title: t("shop.sellSuccessTitle"),
      description: `${localizedItemName(item, locale)} ${t("shop.sellSuccessDescription")} ${refundLabel}.`,
    }),
    [locale, t],
  );

  const flashInventory = useCallback(() => {
    setInventoryFlash(true);
    window.setTimeout(() => setInventoryFlash(false), 1800);
  }, [setInventoryFlash]);

  return {
    applySoldInventoryEntry,
    createBuySuccessToast,
    createSellSuccessToast,
    flashInventory,
    handleOpenSheet,
    setPlayerWallet,
    showToast,
    translateShopErrorMessage,
    upsertInventoryEntry,
  };
};
