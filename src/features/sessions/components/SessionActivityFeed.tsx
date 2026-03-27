import { useMemo } from "react";
import type { ActivityEvent } from "../../../shared/api/sessionsRepo";
import { SessionActivityCombatModule } from "./SessionActivityCombatModule";
import { SessionActivityRow } from "./SessionActivityRow";
import { buildSessionActivityDisplayItems } from "./sessionActivity.utils";

type Props = {
  events: ActivityEvent[];
  sessionId: string;
};

export const SessionActivityFeed = ({
  events,
  sessionId,
}: Props) => {
  const displayItems = useMemo(() => buildSessionActivityDisplayItems(events), [events]);

  return (
    <div className="space-y-2">
      {displayItems.map((item) =>
        item.type === "combat-module" ? (
          <SessionActivityCombatModule
            events={item.events}
            isLatest={item.isLatest}
            key={item.key}
            sessionId={sessionId}
          />
        ) : (
          <SessionActivityRow event={item.event} key={item.key} />
        ),
      )}
    </div>
  );
};
