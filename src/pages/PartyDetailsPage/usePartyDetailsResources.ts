import { useCallback, useEffect, useMemo, useState } from "react";
import type { PartyActiveSession, PartyDetail, PartyMemberSummary } from "../../shared/api/partiesRepo";
import { membersRepo } from "../../shared/api/membersRepo";
import { inventoryRepo } from "../../shared/api/inventoryRepo";
import { itemsRepo } from "../../shared/api/itemsRepo";
import { characterSheetDraftsRepo } from "../../shared/api/characterSheetDraftsRepo";
import { characterSheetsRepo } from "../../shared/api/characterSheetsRepo";
import type {
  CharacterSheetRecord,
  PartyCharacterSheetDraftRecord,
} from "../../entities/character";
import type { InventoryItem } from "../../entities/inventory";
import type { CharacterSheet } from "../../features/character-sheet/model/characterSheet.types";
import { parseCharacterSheet } from "../../features/character-sheet/model/characterSheet.schema";
import {
  buildInventorySummary,
  resolveInventoryEntries,
  type SessionInventoryResolvedEntry,
} from "../../features/inventory/components/sessionInventoryPanel.utils";

const isJoinedPlayer = (member: PartyMemberSummary) =>
  member.role === "PLAYER" && member.status === "joined";

const getPlayerDisplayName = (player: PartyMemberSummary) =>
  player.displayName || player.username || "Player";

export type PartyDetailsPlayerResource = {
  userId: string;
  displayName: string;
  username?: string | null;
  hasSheet: boolean;
  sheet: CharacterSheet | null;
  sheetRecord: CharacterSheetRecord | null;
  sheetStatus: "missing" | "pending_acceptance" | "accepted";
  inventory: InventoryItem[];
  totalItems: number;
  distinctItems: number;
  equippedCount: number;
  resolvedInventory: SessionInventoryResolvedEntry[];
};

type Props = {
  activeSession: PartyActiveSession | null;
  locale: "en" | "pt" | string;
  party: PartyDetail | null;
};

export const usePartyDetailsResources = ({ activeSession, locale, party }: Props) => {
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<PartyCharacterSheetDraftRecord[]>([]);
  const [playerResources, setPlayerResources] = useState<PartyDetailsPlayerResource[]>([]);

  const joinedPlayers = useMemo(
    () => party?.members.filter(isJoinedPlayer) ?? [],
    [party?.members],
  );

  const joinedPlayersSignature = useMemo(
    () =>
      joinedPlayers
        .map((player) => [player.userId, player.displayName ?? "", player.username ?? ""].join(":"))
        .join("|"),
    [joinedPlayers],
  );

  const stableJoinedPlayers = useMemo(
    () => joinedPlayers,
    [joinedPlayersSignature],
  );

  const loadResources = useCallback(async () => {
    if (!party?.id || !party.campaignId) {
      setPlayerResources([]);
      setDrafts([]);
      setLoadError(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    setLoadError(null);

    try {
      const [campaignMembers, catalogItems, draftRecords] = await Promise.all([
        membersRepo.list(party.campaignId),
        itemsRepo.list(party.campaignId),
        characterSheetDraftsRepo.list(party.id).catch(() => []),
      ]);

      const memberIdByUserId = Object.fromEntries(
        campaignMembers.map((member) => [member.userId, member.id]),
      );
      const itemsById = Object.fromEntries(catalogItems.map((item) => [item.id, item]));

      const resources = await Promise.all(
        stableJoinedPlayers.map(async (player) => {
          const memberId = memberIdByUserId[player.userId];
          const [inventory, sheetRecord] = await Promise.all([
            memberId
              ? inventoryRepo.list(party.campaignId, memberId, party.id).catch(() => [])
              : Promise.resolve([]),
            characterSheetsRepo
              .getForPlayer(party.id, player.userId)
              .then((record) => record)
              .catch((error: { status?: number }) => {
                if (error?.status === 404) {
                  return null;
                }
                throw error;
              }),
          ]);

          let sheet: CharacterSheet | null = null;
          if (sheetRecord) {
            try {
              sheet = parseCharacterSheet(sheetRecord.data);
            } catch {
              sheet = null;
            }
          }

          const summary = buildInventorySummary(inventory, itemsById, locale);
          const resolvedInventory = resolveInventoryEntries(inventory, itemsById, locale);
          const hasSheet = sheetRecord !== null;
          const sheetStatus =
            !sheetRecord
              ? "missing"
              : sheetRecord.acceptedAt
                ? "accepted"
                : "pending_acceptance";

          return {
            userId: player.userId,
            displayName: getPlayerDisplayName(player),
            username: player.username ?? null,
            hasSheet,
            sheet,
            sheetRecord,
            sheetStatus,
            inventory,
            totalItems: summary.totalItems,
            distinctItems: summary.distinctItems,
            equippedCount: summary.equippedCount,
            resolvedInventory,
          } satisfies PartyDetailsPlayerResource;
        }),
      );

      setDrafts(draftRecords);
      setPlayerResources(resources);
    } catch (error) {
      setDrafts([]);
      setPlayerResources([]);
      setLoadError((error as { message?: string })?.message ?? "Could not load party resources.");
    } finally {
      setLoading(false);
    }
  }, [locale, party?.campaignId, party?.id, stableJoinedPlayers]);

  useEffect(() => {
    void loadResources();
  }, [loadResources]);

  const summary = useMemo(() => {
    const invitedPlayers = party?.members.filter(
      (member) => member.role === "PLAYER" && member.status === "invited",
    ).length ?? 0;

    return {
      activeSessionStatus: activeSession?.status ?? null,
      invitedPlayers,
      joinedPlayers: joinedPlayers.length,
      readySheets: playerResources.filter((player) => player.hasSheet).length,
      totalInventoryItems: playerResources.reduce((sum, player) => sum + player.totalItems, 0),
      totalPlayers: joinedPlayers.length,
    };
  }, [activeSession?.status, joinedPlayers.length, party?.members, playerResources]);

  return {
    loadError,
    loading,
    drafts,
    playerResources,
    reloadResources: loadResources,
    summary,
  };
};
