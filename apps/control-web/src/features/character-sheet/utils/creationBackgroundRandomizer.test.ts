import { describe, expect, it } from "vitest";
import {
  getBackgroundRandomOptions,
  hasBackgroundRandomOptions,
  rollBackgroundRandomOption,
} from "./creationBackgroundRandomizer";

describe("creationBackgroundRandomizer", () => {
  it("returns acolyte personality trait options", () => {
    const options = getBackgroundRandomOptions("acolyte", "personalityTraits");

    expect(options).toHaveLength(8);
    expect(options[0]).toContain("idolatro um herói");
  });

  it("returns acolyte options for the other structured fields", () => {
    expect(getBackgroundRandomOptions("acolyte", "ideals")).toHaveLength(6);
    expect(getBackgroundRandomOptions("acolyte", "bonds")).toHaveLength(6);
    expect(getBackgroundRandomOptions("acolyte", "flaws")).toHaveLength(6);
    expect(getBackgroundRandomOptions("acolyte", "ideals")[0]).toContain("Tradição.");
    expect(getBackgroundRandomOptions("acolyte", "bonds")[0]).toContain("relíquia ancestral");
    expect(getBackgroundRandomOptions("acolyte", "flaws")[0]).toContain("julgo os outros severamente");
  });

  it("normalizes background aliases before looking up options", () => {
    expect(hasBackgroundRandomOptions("folk-hero", "personalityTraits")).toBe(true);
    expect(hasBackgroundRandomOptions("acolyte", "personalityTraits")).toBe(true);
  });

  it("returns null when the field has no configured table", () => {
    expect(rollBackgroundRandomOption("", "personalityTraits", () => 0)).toBeNull();
  });

  it("rolls a deterministic option when rng is injected", () => {
    const first = rollBackgroundRandomOption("acolyte", "personalityTraits", () => 0);
    const last = rollBackgroundRandomOption("acolyte", "personalityTraits", () => 0.999999);
    const ideal = rollBackgroundRandomOption("acolyte", "ideals", () => 0);
    const bond = rollBackgroundRandomOption("acolyte", "bonds", () => 0.999999);
    const flaw = rollBackgroundRandomOption("acolyte", "flaws", () => 0.999999);

    expect(first).toBe(
      "Eu idolatro um herói particular da minha fé, e constantemente me refiro a seus feitos e exemplos.",
    );
    expect(last).toBe(
      "Eu passei tanto tempo no templo que possuo pouca prática em lidar com as pessoas mundo a fora.",
    );
    expect(ideal).toBe(
      "Tradição. As tradições ancestrais de adoração e sacrifício devem ser preservadas e perpetradas. (Leal)",
    );
    expect(bond).toBe(
      "Eu busco guardar um texto sagrado que meus inimigos dizem ser herético e tentam destruí-lo.",
    );
    expect(flaw).toBe(
      "Depois de escolher um objetivo, eu fico obcecado em cumpri-lo, até mesmo em detrimento de qualquer outra coisa em minha vida.",
    );
  });

  it("returns charlatan options for all structured fields", () => {
    expect(getBackgroundRandomOptions("charlatan", "personalityTraits")).toHaveLength(8);
    expect(getBackgroundRandomOptions("charlatan", "ideals")).toHaveLength(6);
    expect(getBackgroundRandomOptions("charlatan", "bonds")).toHaveLength(6);
    expect(getBackgroundRandomOptions("charlatan", "flaws")).toHaveLength(6);
    expect(getBackgroundRandomOptions("charlatan", "personalityTraits")[0]).toContain("Apaixono-me facilmente");
    expect(getBackgroundRandomOptions("charlatan", "ideals")[0]).toBe("Independência.");
    expect(getBackgroundRandomOptions("charlatan", "bonds")[0]).toContain("pessoa errada");
    expect(getBackgroundRandomOptions("charlatan", "flaws")[0]).toContain("Não resisto a um rosto bonito");
  });

  it("returns criminal options for all structured fields", () => {
    expect(getBackgroundRandomOptions("criminal", "personalityTraits")).toHaveLength(8);
    expect(getBackgroundRandomOptions("criminal", "ideals")).toHaveLength(6);
    expect(getBackgroundRandomOptions("criminal", "bonds")).toHaveLength(6);
    expect(getBackgroundRandomOptions("criminal", "flaws")).toHaveLength(6);
    expect(getBackgroundRandomOptions("criminal", "personalityTraits")[0]).toContain("sempre tenho um plano");
    expect(getBackgroundRandomOptions("criminal", "ideals")[0]).toContain("Honra:");
    expect(getBackgroundRandomOptions("criminal", "bonds")[0]).toContain("dívida enorme");
    expect(getBackgroundRandomOptions("criminal", "flaws")[0]).toContain("roubar");
  });

  it("returns entertainer options for all structured fields", () => {
    expect(getBackgroundRandomOptions("entertainer", "personalityTraits")).toHaveLength(8);
    expect(getBackgroundRandomOptions("entertainer", "ideals")).toHaveLength(6);
    expect(getBackgroundRandomOptions("entertainer", "bonds")).toHaveLength(6);
    expect(getBackgroundRandomOptions("entertainer", "flaws")).toHaveLength(6);
    expect(getBackgroundRandomOptions("entertainer", "personalityTraits")[0]).toContain("cativar uma multidao");
    expect(getBackgroundRandomOptions("entertainer", "ideals")[0]).toContain("Beleza:");
    expect(getBackgroundRandomOptions("entertainer", "bonds")[0]).toContain("teatro");
    expect(getBackgroundRandomOptions("entertainer", "flaws")[0]).toContain("prazeres da carne");
  });

  it("returns folk hero options for all structured fields", () => {
    expect(getBackgroundRandomOptions("folk_hero", "personalityTraits")).toHaveLength(8);
    expect(getBackgroundRandomOptions("folk_hero", "ideals")).toHaveLength(6);
    expect(getBackgroundRandomOptions("folk_hero", "bonds")).toHaveLength(6);
    expect(getBackgroundRandomOptions("folk_hero", "flaws")).toHaveLength(6);
    expect(getBackgroundRandomOptions("folk_hero", "personalityTraits")[0]).toContain("julgo as pessoas");
    expect(getBackgroundRandomOptions("folk_hero", "ideals")[0]).toContain("Respeito:");
    expect(getBackgroundRandomOptions("folk_hero", "bonds")[0]).toContain("daria a minha vida");
    expect(getBackgroundRandomOptions("folk_hero", "flaws")[0]).toContain("facilmente enganado");
  });

  it("returns guild artisan options for all structured fields", () => {
    expect(getBackgroundRandomOptions("guild_artisan", "personalityTraits")).toHaveLength(8);
    expect(getBackgroundRandomOptions("guild_artisan", "ideals")).toHaveLength(6);
    expect(getBackgroundRandomOptions("guild_artisan", "bonds")).toHaveLength(6);
    expect(getBackgroundRandomOptions("guild_artisan", "flaws")).toHaveLength(6);
    expect(getBackgroundRandomOptions("guild_artisan", "personalityTraits")[0]).toContain("orgulhoso do meu trabalho");
    expect(getBackgroundRandomOptions("guild_artisan", "ideals")[0]).toContain("Comunidade:");
    expect(getBackgroundRandomOptions("guild_artisan", "bonds")[0]).toContain("A guilda onde aprendi");
    expect(getBackgroundRandomOptions("guild_artisan", "flaws")[0]).toContain("ganancioso ao extremo");
    expect(hasBackgroundRandomOptions("guild-artisan", "personalityTraits")).toBe(true);
  });

  it("returns hermit options for all structured fields", () => {
    expect(getBackgroundRandomOptions("hermit", "personalityTraits")).toHaveLength(8);
    expect(getBackgroundRandomOptions("hermit", "ideals")).toHaveLength(6);
    expect(getBackgroundRandomOptions("hermit", "bonds")).toHaveLength(6);
    expect(getBackgroundRandomOptions("hermit", "flaws")).toHaveLength(6);
    expect(getBackgroundRandomOptions("hermit", "personalityTraits")[0]).toContain("solidao");
    expect(getBackgroundRandomOptions("hermit", "ideals")[0]).toContain("Conhecimento:");
    expect(getBackgroundRandomOptions("hermit", "bonds")[0]).toContain("segredo terrivel");
    expect(getBackgroundRandomOptions("hermit", "flaws")[0]).toContain("dogmatico ao extremo");
  });

  it("returns noble options for all structured fields", () => {
    expect(getBackgroundRandomOptions("noble", "personalityTraits")).toHaveLength(8);
    expect(getBackgroundRandomOptions("noble", "ideals")).toHaveLength(6);
    expect(getBackgroundRandomOptions("noble", "bonds")).toHaveLength(6);
    expect(getBackgroundRandomOptions("noble", "flaws")).toHaveLength(6);
    expect(getBackgroundRandomOptions("noble", "personalityTraits")[0]).toContain("presente de valor inestimavel");
    expect(getBackgroundRandomOptions("noble", "ideals")[0]).toContain("Respeito:");
    expect(getBackgroundRandomOptions("noble", "bonds")[0]).toContain("recuperar as terras");
    expect(getBackgroundRandomOptions("noble", "flaws")[0]).toContain("pessoas comuns sao inferiores");
  });

  it("returns outlander options for all structured fields", () => {
    expect(getBackgroundRandomOptions("outlander", "personalityTraits")).toHaveLength(8);
    expect(getBackgroundRandomOptions("outlander", "ideals")).toHaveLength(6);
    expect(getBackgroundRandomOptions("outlander", "bonds")).toHaveLength(6);
    expect(getBackgroundRandomOptions("outlander", "flaws")).toHaveLength(6);
    expect(getBackgroundRandomOptions("outlander", "personalityTraits")[0]).toContain("guiado pelos meus instintos");
    expect(getBackgroundRandomOptions("outlander", "ideals")[0]).toContain("Mudanca:");
    expect(getBackgroundRandomOptions("outlander", "bonds")[0]).toContain("tribo ou meu cla");
    expect(getBackgroundRandomOptions("outlander", "flaws")[0]).toContain("povos civilizados");
  });

  it("returns sage options for all structured fields", () => {
    expect(getBackgroundRandomOptions("sage", "personalityTraits")).toHaveLength(8);
    expect(getBackgroundRandomOptions("sage", "ideals")).toHaveLength(6);
    expect(getBackgroundRandomOptions("sage", "bonds")).toHaveLength(6);
    expect(getBackgroundRandomOptions("sage", "flaws")).toHaveLength(6);
    expect(getBackgroundRandomOptions("sage", "personalityTraits")[0]).toContain("jargoes academicos");
    expect(getBackgroundRandomOptions("sage", "ideals")[0]).toContain("Conhecimento:");
    expect(getBackgroundRandomOptions("sage", "bonds")[0]).toContain("biblioteca antiga");
    expect(getBackgroundRandomOptions("sage", "flaws")[0]).toContain("arrogante");
  });

  it("returns sailor options for all structured fields", () => {
    expect(getBackgroundRandomOptions("sailor", "personalityTraits")).toHaveLength(8);
    expect(getBackgroundRandomOptions("sailor", "ideals")).toHaveLength(6);
    expect(getBackgroundRandomOptions("sailor", "bonds")).toHaveLength(6);
    expect(getBackgroundRandomOptions("sailor", "flaws")).toHaveLength(6);
    expect(getBackgroundRandomOptions("sailor", "personalityTraits")[0]).toContain("expressoes de marinheiro");
    expect(getBackgroundRandomOptions("sailor", "ideals")[0]).toContain("Respeito:");
    expect(getBackgroundRandomOptions("sailor", "bonds")[0]).toContain("capitao e a tripulacao");
    expect(getBackgroundRandomOptions("sailor", "flaws")[0]).toContain("prazeres da terra firme");
  });

  it("returns soldier options for all structured fields", () => {
    expect(getBackgroundRandomOptions("soldier", "personalityTraits")).toHaveLength(8);
    expect(getBackgroundRandomOptions("soldier", "ideals")).toHaveLength(6);
    expect(getBackgroundRandomOptions("soldier", "bonds")).toHaveLength(6);
    expect(getBackgroundRandomOptions("soldier", "flaws")).toHaveLength(6);
    expect(getBackgroundRandomOptions("soldier", "personalityTraits")[0]).toContain("disciplina");
    expect(getBackgroundRandomOptions("soldier", "ideals")[0]).toContain("Maior Bem:");
    expect(getBackgroundRandomOptions("soldier", "bonds")[0]).toContain("mesmo esquadrao");
    expect(getBackgroundRandomOptions("soldier", "flaws")[0]).toContain("desprezo profundo");
  });

  it("returns urchin options for all structured fields", () => {
    expect(getBackgroundRandomOptions("urchin", "personalityTraits")).toHaveLength(8);
    expect(getBackgroundRandomOptions("urchin", "ideals")).toHaveLength(6);
    expect(getBackgroundRandomOptions("urchin", "bonds")).toHaveLength(6);
    expect(getBackgroundRandomOptions("urchin", "flaws")).toHaveLength(6);
    expect(getBackgroundRandomOptions("urchin", "personalityTraits")[0]).toContain("Eu escondo comida");
    expect(getBackgroundRandomOptions("urchin", "ideals")[0]).toContain("Respeito:");
    expect(getBackgroundRandomOptions("urchin", "bonds")[0]).toContain("pequeno objeto");
    expect(getBackgroundRandomOptions("urchin", "flaws")[0]).toContain("bater a carteira");
  });
});
