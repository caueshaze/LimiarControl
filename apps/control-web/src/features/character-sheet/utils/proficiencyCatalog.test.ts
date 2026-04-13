import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  resetCreationItemCatalogForTests,
  seedCreationItemCatalogForTests,
} from "./creationItemCatalog";
import { TEST_CREATION_BASE_ITEMS } from "./creationItemCatalog.testData";
import {
  getDraftArmorProficiencyOptions,
  getDraftToolProficiencyOptions,
  getDraftWeaponProficiencyOptions,
} from "./proficiencyCatalog";

describe("proficiencyCatalog", () => {
  beforeEach(() => {
    seedCreationItemCatalogForTests(TEST_CREATION_BASE_ITEMS);
  });

  afterEach(() => {
    resetCreationItemCatalogForTests();
  });

  it("builds canonical tool proficiency options from creation data", () => {
    const options = getDraftToolProficiencyOptions();

    expect(options).toContain("Kit de Disfarce");
    expect(options).toContain("Alaúde");
    expect(options).toContain("Ferramentas de Engenhoqueiro");
  });

  it("includes class/race proficiencies and catalog weapons", () => {
    const options = getDraftWeaponProficiencyOptions();

    expect(options).toContain("Simples");
    expect(options).toContain("Marciais");
    expect(options).toContain("Arco Longo");
    expect(options).toContain("Espada Curta");
  });

  it("includes armor categories and catalog armor names", () => {
    const options = getDraftArmorProficiencyOptions();

    expect(options).toContain("Leve");
    expect(options).toContain("Média");
    expect(options).toContain("Pesada");
    expect(options).toContain("Escudos");
    expect(options).toContain("Peitoral");
  });
});
