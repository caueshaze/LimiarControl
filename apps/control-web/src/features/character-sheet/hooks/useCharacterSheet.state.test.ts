import { describe, expect, it } from "vitest";

import { INITIAL_SHEET } from "../model/initialSheet";
import {
  characterSheetHookReducer,
  initialCharacterSheetHookState,
} from "./useCharacterSheet.state";

describe("characterSheetHookReducer", () => {
  it("reset keeps the hook out of loading state", () => {
    const next = characterSheetHookReducer(
      {
        ...initialCharacterSheetHookState,
        loading: false,
        isDirty: true,
        remoteId: "sheet-1",
        characterRecord: {
          id: "sheet-1",
          partyId: "party-1",
          playerId: "player-1",
          data: { ...INITIAL_SHEET, name: "Hero" },
          sourceDraftId: "draft-1",
          deliveredByUserId: "gm-1",
          deliveredAt: "2026-03-30T20:00:00.000Z",
          acceptedAt: null,
          createdAt: "2026-03-30T20:00:00.000Z",
          updatedAt: null,
        },
      },
      { type: "reset" },
    );

    expect(next.loading).toBe(false);
    expect(next.saving).toBe(false);
    expect(next.isDirty).toBe(false);
    expect(next.importError).toBe(null);
    expect(next.sheet).toEqual(INITIAL_SHEET);
    expect(next.remoteId).toBe("sheet-1");
    expect(next.characterRecord?.sourceDraftId).toBe("draft-1");
  });
});
