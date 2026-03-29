import { describe, expect, it } from "vitest";

import { seedSpellCatalogCache } from "../../../entities/dnd-base";
import { ITEM_TYPES } from "../../../entities/item";
import type { InventoryItem } from "../../../entities/inventory";
import type { Item } from "../../../entities/item";
import { buildSpellOptions } from "./usePlayerCombatModeHelpers";

describe("buildSpellOptions", () => {
  it("includes cast_spell magic items from inventory without requiring spellcasting", () => {
    seedSpellCatalogCache([
      {
        canonicalKey: "magic_missile",
        name: "Magic Missile",
        level: 1,
        school: "evocation",
        castingTimeType: "action",
        castingTime: "1 action",
        range: "36 m",
        components: "V, S",
        duration: "Instantaneous",
        concentration: false,
        ritual: false,
        description: "Test spell.",
        resolutionType: "damage",
        damageType: "Force",
        savingThrow: null,
        saveSuccessOutcome: null,
        healDice: null,
        upcast: null,
        classes: ["Wizard"],
      },
    ], "camp-bracelet");

    const inventory: InventoryItem[] = [
      {
        id: "inv-1",
        itemId: "item-1",
        memberId: "member-1",
        quantity: 1,
        chargesCurrent: 1,
        isEquipped: false,
      },
    ];
    const itemsById: Record<string, Item> = {
      "item-1": {
        id: "item-1",
        name: "Bracelete de Phantyr: Mísseis Mágicos",
        type: ITEM_TYPES.MAGIC,
        description: "Bracelete de uso único.",
        chargesMax: 1,
        rechargeType: "none",
        magicEffect: {
          type: "cast_spell",
          spellCanonicalKey: "magic_missile",
          castLevel: 1,
          ignoreComponents: true,
          noFreeHandRequired: true,
        },
      },
    };

    const options = buildSpellOptions(null, "camp-bracelet", inventory, itemsById);

    expect(options).toEqual([
      expect.objectContaining({
        id: "magic-item:inv-1",
        canonicalKey: "magic_missile",
        sourceType: "magic_item",
        sourceItemName: "Bracelete de Phantyr: Mísseis Mágicos",
        inventoryItemId: "inv-1",
        chargesCurrent: 1,
        chargesMax: 1,
        fixedCastLevel: 1,
        ignoreComponents: true,
        noFreeHandRequired: true,
      }),
    ]);
  });

  it("hides exhausted magic items from combat spell options", () => {
    seedSpellCatalogCache([
      {
        canonicalKey: "detect_magic",
        name: "Detect Magic",
        level: 1,
        school: "divination",
        castingTimeType: "action",
        castingTime: "1 action",
        range: "Self",
        components: "V, S",
        duration: "10 minutes",
        concentration: true,
        ritual: true,
        description: "Test spell.",
        resolutionType: "utility",
        damageType: null,
        savingThrow: null,
        saveSuccessOutcome: null,
        healDice: null,
        upcast: null,
        classes: ["Wizard"],
      },
    ], "camp-bracelet-exhausted");

    const options = buildSpellOptions(
      null,
      "camp-bracelet-exhausted",
      [
        {
          id: "inv-1",
          itemId: "item-1",
          memberId: "member-1",
          quantity: 1,
          chargesCurrent: 0,
          isEquipped: false,
        },
      ],
      {
        "item-1": {
          id: "item-1",
          name: "Bracelete de Phantyr: Detectar Magia",
          type: ITEM_TYPES.MAGIC,
          description: "Bracelete descarregado.",
          chargesMax: 1,
          rechargeType: "none",
          magicEffect: {
            type: "cast_spell",
            spellCanonicalKey: "detect_magic",
            castLevel: 1,
            ignoreComponents: true,
            noFreeHandRequired: true,
          },
        },
      },
    );

    expect(options).toEqual([]);
  });
});
