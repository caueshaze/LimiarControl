import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import type { Item } from "../../entities/item";
import type { InventoryItem } from "../../entities/inventory";
import { parseCharacterSheet } from "../../features/character-sheet/model/characterSheet.schema";
import type { CharacterSheet } from "../../features/character-sheet/model/characterSheet.types";
import {
  buildArmorFromItem,
  buildArmorOptions,
  buildWeaponOptions,
  hasInventoryEntry,
} from "../../features/inventory/components/sessionInventoryPanel.utils";
import { sessionStatesRepo } from "../../shared/api/sessionStatesRepo";
import type { LocaleKey } from "../../shared/i18n";
import type { ToastState } from "../../shared/ui/Toast";

type Props = {
  activeSessionId: string | null;
  inventory: InventoryItem[] | null;
  itemsById: Record<string, Item>;
  locale: "en" | "pt" | string;
  playerSheet: CharacterSheet | null;
  setPlayerSheet: Dispatch<SetStateAction<CharacterSheet | null>>;
  showToast: (toast: ToastState) => void;
  t: (key: LocaleKey) => string;
};

const LOADOUT_STATUS_DURATION_MS = 2200;

export const usePlayerBoardLoadout = ({
  activeSessionId,
  inventory,
  itemsById,
  locale,
  playerSheet,
  setPlayerSheet,
  showToast,
  t,
}: Props) => {
  const [loadoutStatus, setLoadoutStatus] = useState<string | null>(null);
  const [isSavingLoadout, setIsSavingLoadout] = useState(false);
  const clearStatusTimeoutRef = useRef<number | null>(null);

  const weaponOptions = useMemo(
    () => buildWeaponOptions(inventory, itemsById, locale),
    [inventory, itemsById, locale],
  );
  const armorOptions = useMemo(
    () => buildArmorOptions(inventory, itemsById, locale),
    [inventory, itemsById, locale],
  );

  const selectedWeaponId = useMemo(() => {
    if (!playerSheet?.currentWeaponId) return null;
    return hasInventoryEntry(inventory, playerSheet.currentWeaponId)
      ? playerSheet.currentWeaponId
      : null;
  }, [inventory, playerSheet?.currentWeaponId]);

  const selectedArmorId = useMemo(() => {
    if (!playerSheet?.equippedArmorItemId) return null;
    return hasInventoryEntry(inventory, playerSheet.equippedArmorItemId)
      ? playerSheet.equippedArmorItemId
      : null;
  }, [inventory, playerSheet?.equippedArmorItemId]);

  const scheduleStatusClear = useCallback(() => {
    if (clearStatusTimeoutRef.current) {
      window.clearTimeout(clearStatusTimeoutRef.current);
    }
    clearStatusTimeoutRef.current = window.setTimeout(() => {
      setLoadoutStatus(null);
      clearStatusTimeoutRef.current = null;
    }, LOADOUT_STATUS_DURATION_MS);
  }, []);

  const persistLoadout = useCallback(
    async (payload: { currentWeaponId: string | null; equippedArmorItemId: string | null }) => {
      if (!activeSessionId || !playerSheet) {
        return;
      }

      const previousSheet = playerSheet;
      setPlayerSheet((current) =>
        current
          ? {
              ...current,
              currentWeaponId: payload.currentWeaponId,
              equippedArmorItemId: payload.equippedArmorItemId,
              equippedArmor: buildArmorFromItem(
                payload.equippedArmorItemId
                  ? itemsById[
                      inventory?.find((entry) => entry.id === payload.equippedArmorItemId)?.itemId ?? ""
                    ]
                  : null,
              ),
            }
          : current,
      );
      setIsSavingLoadout(true);
      setLoadoutStatus(t("playerBoard.loadoutSaving"));

      try {
        const record = await sessionStatesRepo.updateMineLoadout(activeSessionId, payload);
        const nextSheet = parseCharacterSheet(record.state);
        setPlayerSheet(nextSheet);
        setLoadoutStatus(t("playerBoard.loadoutSaved"));
        scheduleStatusClear();
      } catch (error) {
        setPlayerSheet(previousSheet);
        setLoadoutStatus(t("playerBoard.loadoutSaveError"));
        scheduleStatusClear();
        showToast({
          variant: "error",
          title: t("playerBoard.loadoutSaveErrorTitle"),
          description:
            (error as { message?: string })?.message ??
            t("playerBoard.loadoutSaveError"),
        });
      } finally {
        setIsSavingLoadout(false);
      }
    },
    [activeSessionId, inventory, itemsById, playerSheet, scheduleStatusClear, setPlayerSheet, showToast, t],
  );

  const handleWeaponChange = useCallback(
    (inventoryItemId: string | null) => {
      if (inventoryItemId === selectedWeaponId) {
        return;
      }
      void persistLoadout({
        currentWeaponId: inventoryItemId,
        equippedArmorItemId: selectedArmorId,
      });
    },
    [persistLoadout, selectedArmorId],
  );

  const handleArmorChange = useCallback(
    (inventoryItemId: string | null) => {
      if (inventoryItemId === selectedArmorId) {
        return;
      }
      void persistLoadout({
        currentWeaponId: selectedWeaponId,
        equippedArmorItemId: inventoryItemId,
      });
    },
    [persistLoadout, selectedArmorId, selectedWeaponId],
  );

  useEffect(() => () => {
    if (clearStatusTimeoutRef.current) {
      window.clearTimeout(clearStatusTimeoutRef.current);
    }
  }, []);

  return {
    armorOptions,
    handleArmorChange,
    handleWeaponChange,
    isSavingLoadout,
    loadoutStatus,
    selectedArmorId,
    selectedWeaponId,
    weaponOptions,
  };
};
