import { describe, expect, it } from "vitest";

import {
  appendCombatLogEntries,
  buildCombatParticipantViews,
  localizeCombatLogMessage,
} from "./combatUi.helpers";

describe("combatUi.helpers", () => {
  it("builds participant views with current turn and vitals", () => {
    const views = buildCombatParticipantViews({
      currentTurnIndex: 1,
      entityVitalsByRefId: {
        entity_1: { currentHp: 12, maxHp: 20 },
      },
      participants: [
        {
          actor_user_id: "user-1",
          display_name: "Aela",
          id: "p1",
          initiative: 15,
          kind: "player",
          ref_id: "user-1",
          status: "active",
          team: "players",
          visible: true,
        },
        {
          actor_user_id: null,
          display_name: "Goblin",
          id: "e1",
          initiative: 11,
          kind: "session_entity",
          ref_id: "entity_1",
          status: "active",
          team: "enemies",
          visible: true,
        },
      ],
      playerVitalsByUserId: {
        "user-1": { currentHp: 22, maxHp: 30 },
      },
      userId: "user-1",
    });

    expect(views[0]?.isSelf).toBe(true);
    expect(views[0]?.currentHp).toBe(22);
    expect(views[1]?.isCurrentTurn).toBe(true);
    expect(views[1]?.maxHp).toBe(20);
  });

  it("deduplicates combat log entries and keeps the latest window", () => {
    const next = appendCombatLogEntries(
      [
        { id: "1", message: "A", source: null },
        { id: "2", message: "B", source: null },
      ],
      [
        { id: "2", message: "B updated", source: "player_turn" },
        { id: "3", message: "C", source: null },
      ],
      2,
    );

    expect(next).toEqual([
      { id: "2", message: "B updated", source: "player_turn" },
      { id: "3", message: "C", source: null },
    ]);
  });

  it("localizes common english combat log messages to portuguese", () => {
    expect(localizeCombatLogMessage("Combat started! Roll for initiative.", "pt")).toBe(
      "Combate iniciado! Role a iniciativa.",
    );
    expect(
      localizeCombatLogMessage("Goblin used Claw on Aela: HIT (roll 18) for 7 slashing damage", "pt"),
    ).toBe("Goblin usou Claw em Aela: acerto (rolagem 18) 7 de dano Cortante");
  });

  it("localizes common portuguese combat log messages to english", () => {
    expect(
      localizeCombatLogMessage("Mago conjurou Raio de Gelo em Goblin. 8 de dano de Frio", "en"),
    ).toBe("Mago cast Raio de Gelo on Goblin. 8 Cold damage");
  });
});
