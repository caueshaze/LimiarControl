import type { AbilityName } from "../model/characterSheet.types";
import { LANGUAGE_CHOICE_SLOT } from "./languages";

export type Race = {
  id: string;
  name: string;
  size: "Pequeno" | "Médio";
  darkvision: number | null;
  languages: string[];
  abilityBonuses: Partial<Record<AbilityName, number>>;
  speed: number;
  traits: string[];
};

export const RACES: Race[] = [
  { id: "hill-dwarf", name: "Anão da Colina", size: "Médio", darkvision: 60, languages: ["Comum", "Anão"], abilityBonuses: { constitution: 2, wisdom: 1 }, speed: 25, traits: ["Resiliência Anã", "Sentido de Pedra", "Robustez Anã", "Sem Penalidade de Armadura Pesada"] },
  { id: "mountain-dwarf", name: "Anão da Montanha", size: "Médio", darkvision: 60, languages: ["Comum", "Anão"], abilityBonuses: { constitution: 2, strength: 2 }, speed: 25, traits: ["Resiliência Anã", "Sentido de Pedra", "Proficiência em Armadura", "Sem Penalidade de Armadura Pesada"] },
  { id: "high-elf", name: "Elfo Alto", size: "Médio", darkvision: 60, languages: ["Comum", "Élfico", LANGUAGE_CHOICE_SLOT], abilityBonuses: { dexterity: 2, intelligence: 1 }, speed: 30, traits: ["Ancestralidade Feérica", "Transe", "Truque"] },
  { id: "wood-elf", name: "Elfo da Floresta", size: "Médio", darkvision: 60, languages: ["Comum", "Élfico"], abilityBonuses: { dexterity: 2, wisdom: 1 }, speed: 35, traits: ["Ancestralidade Feérica", "Transe", "Pés Velozes", "Máscara da Natureza"] },
  { id: "dark-elf", name: "Elfo Negro (Drow)", size: "Médio", darkvision: 120, languages: ["Comum", "Élfico"], abilityBonuses: { dexterity: 2, charisma: 1 }, speed: 30, traits: ["Ancestralidade Feérica", "Transe", "Sensibilidade à Luz Solar", "Magia Drow"] },
  { id: "lightfoot-halfling", name: "Halfling Pés-Leves", size: "Pequeno", darkvision: null, languages: ["Comum", "Halfling"], abilityBonuses: { dexterity: 2, charisma: 1 }, speed: 25, traits: ["Sortudo", "Corajoso", "Agilidade Halfling", "Naturalmente Furtivo"] },
  { id: "stout-halfling", name: "Halfling Robusto", size: "Pequeno", darkvision: null, languages: ["Comum", "Halfling"], abilityBonuses: { dexterity: 2, constitution: 1 }, speed: 25, traits: ["Sortudo", "Corajoso", "Agilidade Halfling", "Resiliência Robusta"] },
  { id: "human", name: "Humano", size: "Médio", darkvision: null, languages: ["Comum", LANGUAGE_CHOICE_SLOT], abilityBonuses: { strength: 1, dexterity: 1, constitution: 1, intelligence: 1, wisdom: 1, charisma: 1 }, speed: 30, traits: ["Perícia Extra"] },
  { id: "dragonborn", name: "Draconato", size: "Médio", darkvision: null, languages: ["Comum", "Dracônico"], abilityBonuses: { strength: 2, charisma: 1 }, speed: 30, traits: ["Ancestralidade Dracônica", "Sopro de Dragão", "Resistência a Danos"] },
  { id: "forest-gnome", name: "Gnomo da Floresta", size: "Pequeno", darkvision: 60, languages: ["Comum", "Gnomo"], abilityBonuses: { intelligence: 2, dexterity: 1 }, speed: 25, traits: ["Astúcia Gnômica", "Ilusionista Natural", "Falar com Animais"] },
  { id: "rock-gnome", name: "Gnomo da Rocha", size: "Pequeno", darkvision: 60, languages: ["Comum", "Gnomo"], abilityBonuses: { intelligence: 2, constitution: 1 }, speed: 25, traits: ["Astúcia Gnômica", "Lore de Artesão", "Engenhoca"] },
  { id: "half-elf", name: "Meio-Elfo", size: "Médio", darkvision: 60, languages: ["Comum", "Élfico", LANGUAGE_CHOICE_SLOT], abilityBonuses: { charisma: 2, dexterity: 1, wisdom: 1 }, speed: 30, traits: ["Ancestralidade Feérica", "Versatilidade de Perícias"] },
  { id: "half-orc", name: "Meio-Orc", size: "Médio", darkvision: 60, languages: ["Comum", "Orc"], abilityBonuses: { strength: 2, constitution: 1 }, speed: 30, traits: ["Ameaçador", "Resistência Inabalável", "Ataques Brutais"] },
  { id: "tiefling", name: "Tiefling", size: "Médio", darkvision: 60, languages: ["Comum", "Infernal"], abilityBonuses: { intelligence: 1, charisma: 2 }, speed: 30, traits: ["Resistência Infernal", "Legado Infernal"] },
];

export const getRace = (id: string): Race | undefined =>
  RACES.find((r) => r.id === id);
