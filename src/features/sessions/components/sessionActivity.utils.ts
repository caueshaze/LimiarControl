import type { ActivityEvent } from "../../../shared/api/sessionsRepo";

export const formatSessionActivityOffset = (seconds: number): string => {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) {
    return `${h}h${String(m).padStart(2, "0")}m`;
  }
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
};

export type SessionActivityDisplayItem =
  | {
      event: ActivityEvent;
      key: string;
      type: "event";
    }
  | {
      events: ActivityEvent[];
      isLatest: boolean;
      key: string;
      type: "combat-module";
    };

export const buildSessionActivityDisplayItems = (
  events: ActivityEvent[],
): SessionActivityDisplayItem[] => {
  const items: SessionActivityDisplayItem[] = [];
  let combatWindow: ActivityEvent[] | null = null;

  for (const [index, event] of events.entries()) {
    const eventKey = `${event.type}-${event.timestamp}-${index}`;

    if (event.type === "combat" && event.action === "started") {
      if (combatWindow?.length) {
        items.push({
          events: combatWindow,
          isLatest: false,
          key: `combat-${combatWindow[0]?.timestamp ?? event.timestamp}-${index}`,
          type: "combat-module",
        });
      }
      combatWindow = [event];
      continue;
    }

    if (combatWindow) {
      combatWindow.push(event);
      if (event.type === "combat" && event.action === "ended") {
        items.push({
          events: combatWindow,
          isLatest: false,
          key: `combat-${combatWindow[0]?.timestamp ?? event.timestamp}-${index}`,
          type: "combat-module",
        });
        combatWindow = null;
      }
      continue;
    }

    items.push({
      event,
      key: eventKey,
      type: "event",
    });
  }

  if (combatWindow && combatWindow.length > 0) {
    items.push({
      events: combatWindow,
      isLatest: false,
      key: `combat-${combatWindow[0]?.timestamp ?? "active"}-open`,
      type: "combat-module",
    });
  }

  const latestCombatIndex = [...items].map((item) => item.type).lastIndexOf("combat-module");

  return items
    .map((item, index) =>
      item.type === "combat-module"
        ? {
            ...item,
            isLatest: index === latestCombatIndex,
          }
        : item,
    )
    .reverse();
};
