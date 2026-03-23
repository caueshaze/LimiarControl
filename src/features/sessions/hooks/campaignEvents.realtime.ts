import type { RealtimeHistoryPublication } from "../../../shared/realtime/centrifugoClient";

const CAMPAIGN_EVENT_TYPES = new Set([
  "session_started",
  "session_closed",
  "session_resumed",
  "session_lobby",
  "player_joined_lobby",
  "shop_opened",
  "shop_closed",
  "combat_started",
  "combat_ended",
  "roll_requested",
  "dice_rolled",
  "shop_purchase_created",
  "shop_sale_created",
  "party_member_updated",
  "session_state_updated",
  "gm_granted_currency",
  "gm_granted_item",
  "gm_granted_xp",
  "rest_started",
  "rest_ended",
  "hit_dice_used",
  "level_up_requested",
  "level_up_approved",
  "level_up_denied",
  "entity_revealed",
  "entity_hidden",
  "entity_hp_updated",
  "session_entity_added",
  "session_entity_removed",
  "roll_resolved",
]);

export const isSupportedCampaignEventType = (type?: string): boolean =>
  CAMPAIGN_EVENT_TYPES.has(type ?? "");

export const getCampaignEventVersionKey = (
  campaignId: string | null | undefined,
  event: { payload?: Record<string, unknown>; type?: string },
) => {
  switch (event.type) {
    case "party_member_updated":
      return `${event.type}:${event.payload?.partyId ?? ""}:${event.payload?.userId ?? ""}`;
    case "session_state_updated":
      return `${event.type}:${event.payload?.sessionId ?? ""}:${event.payload?.playerUserId ?? ""}`;
    case "gm_granted_currency":
    case "gm_granted_item":
    case "gm_granted_xp":
    case "hit_dice_used":
      return `${event.type}:${event.payload?.sessionId ?? ""}:${event.payload?.playerUserId ?? ""}`;
    case "level_up_requested":
    case "level_up_approved":
    case "level_up_denied":
      return `${event.type}:${event.payload?.partyId ?? ""}:${event.payload?.playerUserId ?? ""}`;
    case "player_joined_lobby":
      return `${event.type}:${event.payload?.sessionId ?? ""}:${event.payload?.userId ?? ""}`;
    case "session_started":
    case "session_closed":
    case "session_resumed":
    case "session_lobby":
    case "shop_opened":
    case "shop_closed":
    case "combat_started":
    case "combat_ended":
    case "rest_started":
    case "rest_ended":
    case "roll_requested":
    case "dice_rolled":
    case "shop_purchase_created":
    case "shop_sale_created":
      return `${event.type}:${event.payload?.sessionId ?? campaignId ?? ""}`;
    case "entity_revealed":
    case "entity_hidden":
    case "entity_hp_updated":
    case "session_entity_added":
    case "session_entity_removed":
      return `${event.type}:${event.payload?.sessionId ?? ""}:${event.payload?.sessionEntityId ?? ""}`;
    case "roll_resolved":
      return `roll_resolved:${event.payload?.sessionId ?? ""}:${event.payload?.event_id ?? ""}`;
    default:
      return event.type ?? "unknown";
  }
};

export const sortRealtimeHistoryByVersion = (
  publications: RealtimeHistoryPublication[],
): RealtimeHistoryPublication[] =>
  [...publications].sort((left, right) => {
    const leftVersion =
      typeof (left.data as { version?: unknown } | null | undefined)?.version === "number"
        ? (left.data as { version: number }).version
        : 0;
    const rightVersion =
      typeof (right.data as { version?: unknown } | null | undefined)?.version === "number"
        ? (right.data as { version: number }).version
        : 0;
    if (leftVersion !== rightVersion) {
      return leftVersion - rightVersion;
    }
    const leftOffset = left.offset ? Number(left.offset) : 0;
    const rightOffset = right.offset ? Number(right.offset) : 0;
    return leftOffset - rightOffset;
  });
