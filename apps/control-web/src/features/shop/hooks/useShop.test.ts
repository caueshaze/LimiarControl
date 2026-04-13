import { describe, expect, it } from "vitest";

import type { ItemInput } from "../../../entities/item";
import { toItemRepoPayload } from "./useShop";

describe("toItemRepoPayload", () => {
  it("preserves campaignSpellId for campaign-backed magic item spell effects", () => {
    const payload: ItemInput = {
      name: "  Wand of Thorns  ",
      type: "MAGIC",
      description: "  Casts Spike Growth.  ",
      price: 250,
      magicEffect: {
        type: "cast_spell",
        campaignSpellId: "camp-spell-1",
        spellCanonicalKey: "spike_growth",
        castLevel: 2,
        ignoreComponents: true,
        noFreeHandRequired: false,
      },
    };

    expect(toItemRepoPayload(payload)).toEqual(
      expect.objectContaining({
        name: "Wand of Thorns",
        description: "Casts Spike Growth.",
        magicEffect: {
          type: "cast_spell",
          campaignSpellId: "camp-spell-1",
          spellCanonicalKey: "spike_growth",
          castLevel: 2,
          ignoreComponents: true,
          noFreeHandRequired: false,
        },
      }),
    );
  });

  it("keeps legacy canonical-only magic item spell effects valid", () => {
    const payload: ItemInput = {
      name: "Wand of Missiles",
      type: "MAGIC",
      description: "Casts Magic Missile.",
      price: 100,
      magicEffect: {
        type: "cast_spell",
        spellCanonicalKey: "magic_missile",
        castLevel: 1,
        ignoreComponents: true,
        noFreeHandRequired: true,
      },
    };

    expect(toItemRepoPayload(payload)).toEqual(
      expect.objectContaining({
        magicEffect: {
          type: "cast_spell",
          spellCanonicalKey: "magic_missile",
          castLevel: 1,
          ignoreComponents: true,
          noFreeHandRequired: true,
        },
      }),
    );
  });
});
