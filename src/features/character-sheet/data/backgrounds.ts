import type { SkillName } from "../model/characterSheet.types";
import { LANGUAGE_CHOICE_SLOT } from "./languages";

export type Background = {
  id: string;
  name: string;
  skillProficiencies: SkillName[];
  toolProficiencies: string[];
  languages: string[];
  feature: string;
  startingEquipment: string[];
};

export const BACKGROUNDS: Background[] = [
  { id: "acolyte", name: "Acólito", skillProficiencies: ["insight", "religion"], toolProficiencies: [], languages: [LANGUAGE_CHOICE_SLOT, LANGUAGE_CHOICE_SLOT], feature: "Abrigo dos Fiéis", startingEquipment: ["Holy Symbol", "Prayer book", "5 sticks of incense", "Vestments", "Common clothes", "15 GP"] },
  { id: "charlatan", name: "Charlatão", skillProficiencies: ["deception", "sleightOfHand"], toolProficiencies: ["Kit de disfarce", "Kit de falsificação"], languages: [], feature: "Identidade Falsa", startingEquipment: ["Fine clothes", "Disguise Kit", "Con tools", "15 GP"] },
  { id: "criminal", name: "Criminoso", skillProficiencies: ["deception", "stealth"], toolProficiencies: ["Ferramentas de ladrão"], languages: [], feature: "Contato Criminal", startingEquipment: ["Crowbar", "Dark common clothes with hood", "15 GP"] },
  { id: "entertainer", name: "Artista", skillProficiencies: ["acrobatics", "performance"], toolProficiencies: ["Kit de disfarce", "Instrumento musical"], languages: [], feature: "Pela Demanda Popular", startingEquipment: ["Musical Instrument", "Favor of an admirer", "Costume", "15 GP"] },
  { id: "folk-hero", name: "Herói do Povo", skillProficiencies: ["animalHandling", "survival"], toolProficiencies: ["Ferramentas de artesão", "Veículos (terrestres)"], languages: [], feature: "Hospitalidade Rústica", startingEquipment: ["Artisan's Tools", "Shovel", "Iron pot", "Common clothes", "10 GP"] },
  { id: "guild-artisan", name: "Artesão de Guilda", skillProficiencies: ["insight", "persuasion"], toolProficiencies: ["Ferramentas de artesão"], languages: [LANGUAGE_CHOICE_SLOT], feature: "Membro da Guilda", startingEquipment: ["Artisan's Tools", "Letter of introduction", "Traveler's clothes", "15 GP"] },
  { id: "hermit", name: "Eremita", skillProficiencies: ["medicine", "religion"], toolProficiencies: ["Kit de herbalismo"], languages: [LANGUAGE_CHOICE_SLOT], feature: "Descoberta", startingEquipment: ["Scroll case", "Winter blanket", "Common clothes", "Herbalism Kit", "5 GP"] },
  { id: "noble", name: "Nobre", skillProficiencies: ["history", "persuasion"], toolProficiencies: ["Jogo de mesa"], languages: [LANGUAGE_CHOICE_SLOT], feature: "Posição de Privilégio", startingEquipment: ["Fine clothes", "Signet ring", "Scroll of pedigree", "25 GP"] },
  { id: "outlander", name: "Forasteiro", skillProficiencies: ["athletics", "survival"], toolProficiencies: ["Instrumento musical"], languages: [LANGUAGE_CHOICE_SLOT], feature: "Andarilho", startingEquipment: ["Staff", "Hunting trap", "Animal trophy", "Traveler's clothes", "10 GP"] },
  { id: "sage", name: "Sábio", skillProficiencies: ["arcana", "history"], toolProficiencies: [], languages: [LANGUAGE_CHOICE_SLOT, LANGUAGE_CHOICE_SLOT], feature: "Pesquisador", startingEquipment: ["Bottle of black ink", "Quill", "Small knife", "Letter with unanswered question", "Common clothes", "10 GP"] },
  { id: "sailor", name: "Marinheiro", skillProficiencies: ["athletics", "perception"], toolProficiencies: ["Ferramentas de navegação", "Veículos (aquáticos)"], languages: [], feature: "Passagem de Navio", startingEquipment: ["Belaying pin", "50 feet of silk rope", "Lucky charm", "Common clothes", "10 GP"] },
  { id: "soldier", name: "Soldado", skillProficiencies: ["athletics", "intimidation"], toolProficiencies: ["Jogo de mesa", "Veículos (terrestres)"], languages: [], feature: "Patente Militar", startingEquipment: ["Insignia of rank", "Trophy from fallen enemy", "Gaming Set", "Common clothes", "10 GP"] },
  { id: "urchin", name: "Pivete", skillProficiencies: ["sleightOfHand", "stealth"], toolProficiencies: ["Kit de disfarce", "Ferramentas de ladrão"], languages: [], feature: "Segredos da Cidade", startingEquipment: ["Small knife", "Map of home city", "Pet mouse", "Token from parent", "Common clothes", "10 GP"] },
];

export const getBackground = (id: string): Background | undefined =>
  BACKGROUNDS.find((b) => b.id === id);
