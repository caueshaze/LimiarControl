import { useEffect, useMemo, useState } from "react";
import type { InventoryItem } from "../../../entities/inventory";
import type { Item } from "../../../entities/item";
import { ITEM_TYPES } from "../../../entities/item";
import type { CombatParticipant } from "../../../shared/api/combatRepo";
import type { Locale } from "../../../shared/i18n";
import { localizedItemName } from "../../../features/shop/utils/localizedItemName";
import { getDamageRollCount, getDamageRollSides } from "../../../shared/utils/diceExpression";
import { buildHealingLabel } from "./usePlayerCombatModeHelpers";
import type { CombatConsumableOption } from "./usePlayerCombatMode.types";

type UseConsumablesProps = {
  actorParticipantId: string | null;
  inventory: InventoryItem[] | null;
  itemsById: Record<string, Item>;
  locale: Locale;
  participants: CombatParticipant[];
  actorParticipant: CombatParticipant | null;
};

export const useConsumables = ({
  actorParticipantId,
  inventory,
  itemsById,
  locale,
  participants,
  actorParticipant,
}: UseConsumablesProps) => {
  const [consumableItemId, setConsumableItemId] = useState("");
  const [useObjectTargetParticipantId, setUseObjectTargetParticipantId] = useState("");
  const [useObjectRollMode, setUseObjectRollMode] = useState<"system" | "manual">("system");
  const [useObjectManualRolls, setUseObjectManualRolls] = useState<number[]>([]);
  const [useObjectNote, setUseObjectNote] = useState("");

  const consumableOptions: CombatConsumableOption[] = useMemo(() => {
    return (inventory ?? [])
      .map((entry) => ({
        entry,
        item: itemsById[entry.itemId] ?? null,
      }))
      .filter(
        (candidate) => candidate.item?.type === ITEM_TYPES.CONSUMABLE && candidate.entry.quantity > 0,
      )
      .map((candidate) => ({
        id: candidate.entry.id,
        isHealingConsumable:
          candidate.item?.type === ITEM_TYPES.CONSUMABLE &&
          Boolean(candidate.item.healDice || typeof candidate.item.healBonus === "number"),
        healingLabel: candidate.item ? buildHealingLabel(candidate.item) : null,
        item: candidate.item,
        label: candidate.item
          ? `${localizedItemName(candidate.item, locale)} x${candidate.entry.quantity}`
          : `Item x${candidate.entry.quantity}`,
        manualRollCount: getDamageRollCount(candidate.item?.healDice),
        manualRollSides: getDamageRollSides(candidate.item?.healDice),
      }));
  }, [inventory, itemsById, locale]);

  useEffect(() => {
    if (!consumableOptions.length) {
      setConsumableItemId("");
      return;
    }
    setConsumableItemId((current) =>
      current === "" || consumableOptions.some((option) => option.id === current)
        ? current
        : consumableOptions[0]!.id,
    );
  }, [consumableOptions]);

  const selectedConsumable = useMemo(
    () => consumableOptions.find((option) => option.id === consumableItemId) ?? null,
    [consumableItemId, consumableOptions],
  );

  const useObjectTargetOptions = useMemo(() => {
    if (!actorParticipant) {
      return [];
    }
    const friendlyTeams =
      actorParticipant.team === "players" || actorParticipant.team === "allies"
        ? new Set(["players", "allies"])
        : actorParticipant.team === "enemies"
          ? new Set(["enemies"])
          : new Set([actorParticipant.team]);

    return participants.filter((participant) => {
      if (participant.status === "dead" || participant.status === "defeated") {
        return false;
      }
      if (participant.id === actorParticipant.id) {
        return true;
      }
      return friendlyTeams.has(participant.team);
    });
  }, [actorParticipant, participants]);

  useEffect(() => {
    if (!selectedConsumable?.isHealingConsumable) {
      setUseObjectTargetParticipantId("");
      setUseObjectRollMode("system");
      setUseObjectManualRolls([]);
      return;
    }
    const selfTarget = actorParticipantId
      ? useObjectTargetOptions.find((participant) => participant.id === actorParticipantId)
      : null;
    const fallbackTarget = selfTarget ?? useObjectTargetOptions[0] ?? null;
    setUseObjectTargetParticipantId((current) =>
      current && useObjectTargetOptions.some((participant) => participant.id === current)
        ? current
        : fallbackTarget?.id ?? "",
    );
  }, [
    actorParticipantId,
    selectedConsumable?.id,
    selectedConsumable?.isHealingConsumable,
    useObjectTargetOptions,
  ]);

  useEffect(() => {
    if (
      useObjectRollMode === "manual" &&
      selectedConsumable?.isHealingConsumable &&
      (selectedConsumable.manualRollCount < 1 || selectedConsumable.manualRollSides < 1)
    ) {
      setUseObjectRollMode("system");
      setUseObjectManualRolls([]);
    }
  }, [
    selectedConsumable?.isHealingConsumable,
    selectedConsumable?.manualRollCount,
    selectedConsumable?.manualRollSides,
    useObjectRollMode,
  ]);

  return {
    consumableItemId,
    consumableOptions,
    selectedConsumable,
    setConsumableItemId,
    setUseObjectManualRolls,
    setUseObjectNote,
    setUseObjectRollMode,
    setUseObjectTargetParticipantId,
    useObjectManualRolls,
    useObjectNote,
    useObjectRollMode,
    useObjectTargetOptions,
    useObjectTargetParticipantId,
  };
};
