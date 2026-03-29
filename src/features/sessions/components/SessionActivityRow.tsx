import type { ActivityEvent } from "../../../shared/api/sessionsRepo";
import { useLocale } from "../../../shared/hooks/useLocale";
import {
  SessionActivityCombatRow,
  SessionActivityRestRow,
  SessionActivityRewardRow,
  SessionActivityRollRequestRow,
  SessionActivityRollRow,
  SessionActivityShopRow,
} from "./SessionActivityRowEventsA";
import {
  SessionActivityConsumableRow,
  SessionActivityEntityRow,
  SessionActivityHitDiceRow,
  SessionActivityLevelUpRow,
  SessionActivityPlayerHpRow,
  SessionActivityPurchaseRow,
  SessionActivityRollResolvedRow,
} from "./SessionActivityRowEventsB";

export const SessionActivityRow = ({ event, isGm = false }: { event: ActivityEvent; isGm?: boolean }) => {
  const { t } = useLocale();
  const actor = event.displayName ?? event.username ?? t("sessionActivity.unknownActor");

  if (event.type === "roll") {
    return <SessionActivityRollRow event={event} actor={actor} />;
  }

  if (event.type === "shop") {
    return <SessionActivityShopRow event={event} actor={actor} />;
  }

  if (event.type === "roll_request") {
    return <SessionActivityRollRequestRow event={event} actor={actor} />;
  }

  if (event.type === "combat") {
    return <SessionActivityCombatRow event={event} actor={actor} />;
  }

  if (event.type === "rest") {
    return <SessionActivityRestRow event={event} actor={actor} />;
  }

  if (event.type === "reward") {
    return <SessionActivityRewardRow event={event} actor={actor} />;
  }

  if (event.type === "level_up") {
    return <SessionActivityLevelUpRow event={event} actor={actor} />;
  }

  if (event.type === "hit_dice") {
    return <SessionActivityHitDiceRow event={event} actor={actor} />;
  }

  if (event.type === "consumable") {
    return <SessionActivityConsumableRow event={event} actor={actor} />;
  }

  if (event.type === "player_hp") {
    return <SessionActivityPlayerHpRow event={event} actor={actor} />;
  }

  if (event.type === "entity") {
    return <SessionActivityEntityRow event={event} actor={actor} isGm={isGm} />;
  }

  if (event.type === "roll_resolved") {
    return <SessionActivityRollResolvedRow event={event} actor={actor} />;
  }

  return <SessionActivityPurchaseRow event={event} actor={actor} />;
};
