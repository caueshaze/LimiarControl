import { useLocale } from "../../shared/hooks/useLocale";
import type { Item } from "../../entities/item";
import { useMemo } from "react";
import type { InventoryItem } from "../../entities/inventory";
import { useCharacterSheetDerived } from "../../features/character-sheet/hooks/useCharacterSheetDerived";
import { INITIAL_SHEET } from "../../features/character-sheet/model/initialSheet";
import { getCharacterProgressState } from "../../features/character-sheet/utils/progression";
import type { CharacterSheet } from "../../features/character-sheet/model/characterSheet.types";
import type { LocaleKey } from "../../shared/i18n";
import type { PlayerBoardStatusSummary } from "./playerBoard.types";
import { buildPlayerBoardWeaponSummary } from "./playerBoardWeaponSummary";

type ActiveSessionLike = {
  status: "ACTIVE" | "LOBBY" | "CLOSED";
};

type Props = {
  activeSession: ActiveSessionLike | null;
  effectiveCampaignId: string | null;
  inventory: InventoryItem[] | null;
  itemsById: Record<string, Item>;
  playerSheet: CharacterSheet | null;
  selectedCampaignName?: string | null;
  t: (key: LocaleKey) => string;
};

export const usePlayerBoardSummary = ({
  activeSession,
  effectiveCampaignId,
  inventory,
  itemsById,
  playerSheet,
  selectedCampaignName,
  t,
}: Props) => {
  const { locale } = useLocale();
  const { ac, hpPercent, initiative, passivePerception, spellAttack, spellSaveDC } =
    useCharacterSheetDerived(playerSheet ?? INITIAL_SHEET);
  const xpState = getCharacterProgressState(
    playerSheet?.level ?? INITIAL_SHEET.level,
    playerSheet?.experiencePoints ?? INITIAL_SHEET.experiencePoints,
  );
  const campaignTitle = useMemo(
    () => selectedCampaignName ?? t("playerBoard.noCampaign"),
    [selectedCampaignName, t],
  );

  const inventoryTotal = useMemo(
    () => inventory?.reduce((sum, entry) => sum + entry.quantity, 0) ?? 0,
    [inventory],
  );

  const sessionStatusLabel = useMemo(() => {
    if (activeSession?.status === "ACTIVE") return t("playerBoard.sessionActive");
    if (activeSession?.status === "LOBBY") return t("home.player.statusLobby");
    return t("playerBoard.sessionInactive");
  }, [activeSession?.status, t]);

  const sessionStatusTone = useMemo(() => {
    if (activeSession?.status === "ACTIVE") return "active" as const;
    if (activeSession?.status === "LOBBY") return "lobby" as const;
    return "idle" as const;
  }, [activeSession?.status]);

  const boardDescription = useMemo(() => {
    if (!effectiveCampaignId) return t("playerBoard.noCampaignHint");
    if (!activeSession) return t("playerBoard.waitingSession");
    return t("playerBoard.readyHint");
  }, [activeSession, effectiveCampaignId, t]);

  const currentWeapon = useMemo(
    () =>
      buildPlayerBoardWeaponSummary({
        inventory,
        itemsById,
        locale,
        playerSheet,
      }),
    [inventory, itemsById, locale, playerSheet],
  );

  const playerStatus = useMemo<PlayerBoardStatusSummary | null>(() => {
    if (!playerSheet) return null;
    return {
      ac,
      currentHp: playerSheet.currentHP,
      currentWeapon,
      experiencePoints: playerSheet.experiencePoints,
      hitDiceRemaining: playerSheet.hitDiceRemaining,
      hitDiceTotal: playerSheet.hitDiceTotal,
      hitDieType: playerSheet.hitDiceType,
      hpPercent,
      initiative,
      level: playerSheet.level,
      maxHp: playerSheet.maxHP,
      nextLevelThreshold: xpState.nextLevelThreshold,
      passivePerception,
      spellAttack,
      spellSaveDC,
      tempHp: playerSheet.tempHP,
      xpPercent: xpState.progressPercent,
    };
  }, [ac, currentWeapon, hpPercent, initiative, passivePerception, playerSheet, spellAttack, spellSaveDC, xpState.nextLevelThreshold, xpState.progressPercent]);

  return {
    boardDescription,
    campaignTitle,
    inventoryTotal,
    playerStatus,
    sessionStatusLabel,
    sessionStatusTone,
  };
};
