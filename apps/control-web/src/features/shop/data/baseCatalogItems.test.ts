import { describe, expect, it } from "vitest";

import { getDndItemAliases } from "../../../entities/dnd-base";
import {
  BASE_CATALOG_ITEMS,
  getBaseCatalogItemByName,
  getMissingBaseCatalogItems,
} from "./baseCatalogItems";

describe("baseCatalogItems", () => {
  it("canonicalizes seeded weapon and armor names", () => {
    expect(BASE_CATALOG_ITEMS.some((item) => item.name === "Shield")).toBe(true);
    expect(BASE_CATALOG_ITEMS.some((item) => item.name === "Light Crossbow")).toBe(true);
    expect(BASE_CATALOG_ITEMS.some((item) => item.name === "Shortsword")).toBe(true);
    expect(BASE_CATALOG_ITEMS.some((item) => item.name === "Mace")).toBe(true);

    expect(BASE_CATALOG_ITEMS.some((item) => item.name === "Escudo")).toBe(false);
    expect(BASE_CATALOG_ITEMS.some((item) => item.name === "Besta Leve")).toBe(false);
    expect(BASE_CATALOG_ITEMS.some((item) => item.name === "Espada Curta")).toBe(false);
    expect(BASE_CATALOG_ITEMS.some((item) => item.name === "Maça")).toBe(false);
  });

  it("resolves canonical base catalog items through aliases", () => {
    expect(getBaseCatalogItemByName("Shield")?.name).toBe("Shield");
    expect(getBaseCatalogItemByName("Escudo")?.name).toBe("Shield");
    expect(getBaseCatalogItemByName("Wooden Shield")?.name).toBe("Shield");

    expect(getBaseCatalogItemByName("Light Crossbow")?.name).toBe("Light Crossbow");
    expect(getBaseCatalogItemByName("Besta Leve")?.name).toBe("Light Crossbow");
    expect(getBaseCatalogItemByName("Crossbow, light")?.name).toBe("Light Crossbow");
  });

  it("compares seed presence by canonical key instead of literal name", () => {
    const missingWithAliasesPresent = getMissingBaseCatalogItems([
      { name: "Escudo" },
      { name: "Besta Leve" },
      { name: "Espada Curta" },
      { name: "Maça" },
    ]);

    expect(missingWithAliasesPresent.some((item) => item.name === "Shield")).toBe(false);
    expect(missingWithAliasesPresent.some((item) => item.name === "Light Crossbow")).toBe(false);
    expect(missingWithAliasesPresent.some((item) => item.name === "Shortsword")).toBe(false);
    expect(missingWithAliasesPresent.some((item) => item.name === "Mace")).toBe(false);
  });

  it("exposes aliases for robust search", () => {
    expect(getDndItemAliases("Shield")).toEqual(
      expect.arrayContaining(["Shield", "Escudo", "Wooden Shield"]),
    );
    expect(getDndItemAliases("Light Crossbow")).toEqual(
      expect.arrayContaining(["Light Crossbow", "Besta Leve", "Crossbow, light"]),
    );
  });
});
