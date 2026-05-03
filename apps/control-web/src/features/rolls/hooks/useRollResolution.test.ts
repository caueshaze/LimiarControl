import { describe, expect, it } from "vitest";
import { buildRollResolutionBody } from "./useRollResolution";

describe("buildRollResolutionBody", () => {
  it("serializa ability com alvo contextual quando presente", () => {
    expect(
      buildRollResolutionBody("player", "user-1", {
        rollType: "ability",
        ability: "wisdom",
        advantageMode: "normal",
        targetParticipantId: "target-1",
        rollSource: "system",
      }),
    ).toMatchObject({
      actor_kind: "player",
      actor_ref_id: "user-1",
      ability: "wisdom",
      target_participant_id: "target-1",
      roll_source: "system",
    });
  });

  it("serializa skill sem target contextual quando nao houver alvo", () => {
    expect(
      buildRollResolutionBody("player", "user-1", {
        rollType: "skill",
        skill: "perception",
        advantageMode: "normal",
        rollSource: "system",
      }),
    ).toMatchObject({
      actor_kind: "player",
      actor_ref_id: "user-1",
      skill: "perception",
      roll_source: "system",
    });
  });
});
