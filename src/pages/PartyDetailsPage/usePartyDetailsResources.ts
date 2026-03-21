import { useEffect, useMemo, useState } from "react";
import type { PartyActiveSession, PartyDetail, PartyMemberSummary } from "../../shared/api/partiesRepo";
import { membersRepo } from "../../shared/api/membersRepo";
import { inventoryRepo } from "../../shared/api/inventoryRepo";
import { itemsRepo } from "../../shared/api/itemsRepo";
import { characterSheetsRepo } from "../../shared/api/characterSheetsRepo";
import type { InventoryItem } from "../../entities/inventory";
import type { CharacterSheet } from "../../features/character-sheet/model/characterSheet.types";
import { parseCharacterSheet } from "../../features/character-sheet/model/characterSheet.schema";
import {
  buildInventorySummary,
  resolveInventoryEntries,
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
  inventory: InventoryItem[];
  totalItems: number;
  distinctItems: number;
  equippedCount: number;
  previewItems: Array<{
    id: string;
    name: string;
    quantity: number;
    isEquipped: boolean;
  }>;
};

type Props = {
  activeSession: PartyActiveSession | null;
  party: PartyDetail | null;
};

export const usePartyDetailsResources = ({ activeSession, party }: Props) => {
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [playerResources, setPlayerResources] = useState<PartyDetailsPlayerResource[]>([]);

  const joinedPlayers = useMemo(
    () => party?.members.filter(isJoinedPlayer) ?? [],
    [party?.members],
  );

  useEffect(() => {
    if (!party?.id || !party.campaignId) {
      setPlayerResources([]);
      setLoadError(null);
      setLoading(false);
      return;
    }

    let cancelled = false;

    const loadResources = async () => {
      setLoading(true);
      setLoadError(null);

      try {
        const [campaignMembers, catalogItems] = await Promise.all([
          membersRepo.list(party.campaignId),
          itemsRepo.list(party.campaignId),
        ]);

        if (cancelled) {
          return;
        }

        const memberIdByUserId = Object.fromEntries(
          campaignMembers.map((member) => [member.userId, member.id]),
        );
        const itemsById = Object.fromEntries(catalogItems.map((item) => [item.id, item]));

        const resources = await Promise.all(
          joinedPlayers.map(async (player) => {
            const memberId = memberIdByUserId[player.userId];
            const [inventory, sheet] = await Promise.all([
              memberId
                ? inventoryRepo.list(party.campaignId, memberId, party.id).catch(() => [])
                : Promise.resolve([]),
              characterSheetsRepo
                .getForPlayer(party.id, player.userId)
                .then((record) => {
                  try {
                    return parseCharacterSheet(record.data);
                  } catch {
                    return null;
                  }
                })
                .catch((error: { status?: number }) => {
                  if (error?.status === 404) {
                    return null;
                  }
                  throw error;
                }),
            ]);

            const summary = buildInventorySummary(inventory, itemsById);
            const previewItems = resolveInventoryEntries(inventory, itemsById)
              .slice(0, 3)
              .map(({ entry, name }) => ({
                id: entry.id,
                isEquipped: entry.isEquipped,
                name,
                quantity: entry.quantity,
              }));

            return {
              userId: player.userId,
              displayName: getPlayerDisplayName(player),
              username: player.username ?? null,
              hasSheet: sheet !== null,
              sheet,
              inventory,
              totalItems: summary.totalItems,
              distinctItems: summary.distinctItems,
              equippedCount: summary.equippedCount,
              previewItems,
            } satisfies PartyDetailsPlayerResource;
          }),
        );

        if (!cancelled) {
          setPlayerResources(resources);
        }
      } catch (error) {
        if (!cancelled) {
          setPlayerResources([]);
          setLoadError((error as { message?: string })?.message ?? "Could not load party resources.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void loadResources();

    return () => {
      cancelled = true;
    };
  }, [joinedPlayers, party?.campaignId, party?.id]);

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
    playerResources,
    summary,
  };
};
