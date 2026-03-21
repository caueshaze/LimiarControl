import type { AbilityName, SkillName } from "../model/characterSheet.types";
import { describeDefaultClassStartingEquipment } from "./classCreation";

export type DndSubclass = {
  id: string;
  name: string;
};

export type DndClass = {
  id: string;
  name: string;
  hitDice: string;
  primaryAbility: AbilityName[];
  savingThrows: AbilityName[];
  armorProficiencies: string[];
  weaponProficiencies: string[];
  skillChoices: SkillName[];
  skillCount: number;
  spellcastingAbility: AbilityName | null;
  /** Level at which the subclass choice unlocks (1, 2, or 3). */
  subclassLevel: number;
  /** Label shown in the UI for subclass picker (e.g. "Domínio Divino"). */
  subclassLabel: string;
  /** Available subclass options (PHB). */
  subclasses: DndSubclass[];
  /**
   * Level at which the class gains a Fighting Style choice, or null if it never does.
   * Fighter = 1, Paladin = 2, Ranger = 2, others = null.
   */
  fightingStyleLevel: number | null;
  /**
   * IDs of fighting styles available to this class (subset of FIGHTING_STYLES).
   * Empty array for classes without a fighting style.
   * Fighter: all 6 | Paladin: defense, dueling, great_weapon_fighting, protection
   * Ranger: archery, defense, dueling, two_weapon_fighting
   */
  fightingStyleOptions: string[];
  /**
   * Level at which the class first gains Expertise, or null if it never does.
   * Rogue = 1, Bard = 3, others = null.
   */
  expertiseLevel: number | null;
  /** Number of expertise slots unlocked at `expertiseLevel`. */
  expertiseCount: number;
  // Derived preview only. Character creation uses classCreation.ts as source of truth.
  startingEquipment: string[];
};

// ── Fighting Styles ──────────────────────────────────────────────────────────

export type FightingStyle = {
  id: string;
  name: string;
};

export const FIGHTING_STYLES: FightingStyle[] = [
  { id: "archery", name: "Arquearia" },
  { id: "great_weapon_fighting", name: "Combate com Armas Grandes" },
  { id: "two_weapon_fighting", name: "Combate com Duas Armas" },
  { id: "defense", name: "Defesa" },
  { id: "dueling", name: "Duelismo" },
  { id: "protection", name: "Proteção" },
];

// ── Class Definitions ────────────────────────────────────────────────────────

type ClassDefinition = Omit<DndClass, "startingEquipment" | "fightingStyleOptions"> & {
  fightingStyleOptions?: string[];
};

const ALL_FIGHTING_STYLE_IDS = FIGHTING_STYLES.map((style) => style.id);
const PALADIN_FIGHTING_STYLE_IDS = ["defense", "dueling", "great_weapon_fighting", "protection"];
const RANGER_FIGHTING_STYLE_IDS = ["archery", "defense", "dueling", "two_weapon_fighting"];

const getDefaultFightingStyleOptions = (classId: string): string[] => {
  if (classId === "fighter") return ALL_FIGHTING_STYLE_IDS;
  if (classId === "paladin") return PALADIN_FIGHTING_STYLE_IDS;
  if (classId === "ranger") return RANGER_FIGHTING_STYLE_IDS;
  return [];
};

const CLASS_DEFINITIONS: ClassDefinition[] = [
  { id: "barbarian", name: "Bárbaro", hitDice: "d12", primaryAbility: ["strength"], savingThrows: ["strength", "constitution"], armorProficiencies: ["Leve", "Média", "Escudos"], weaponProficiencies: ["Simples", "Marciais"], skillChoices: ["animalHandling", "athletics", "intimidation", "nature", "perception", "survival"], skillCount: 2, spellcastingAbility: null, subclassLevel: 3, subclassLabel: "Caminho Primitivo", subclasses: [{ id: "berserker", name: "Caminho do Furioso" }, { id: "totem_warrior", name: "Caminho do Guerreiro Totêmico" }], fightingStyleLevel: null, expertiseLevel: null, expertiseCount: 0 },
  { id: "bard", name: "Bardo", hitDice: "d8", primaryAbility: ["charisma"], savingThrows: ["dexterity", "charisma"], armorProficiencies: ["Leve"], weaponProficiencies: ["Simples", "Bestas de mão", "Espadas longas", "Rapieiras", "Espadas curtas"], skillChoices: ["acrobatics", "animalHandling", "arcana", "athletics", "deception", "history", "insight", "intimidation", "investigation", "medicine", "nature", "perception", "performance", "persuasion", "religion", "sleightOfHand", "stealth", "survival"], skillCount: 3, spellcastingAbility: "charisma", subclassLevel: 3, subclassLabel: "Colégio de Bardo", subclasses: [{ id: "lore", name: "Colégio do Conhecimento" }, { id: "valor", name: "Colégio da Bravura" }], fightingStyleLevel: null, expertiseLevel: 3, expertiseCount: 2 },
  { id: "cleric", name: "Clérigo", hitDice: "d8", primaryAbility: ["wisdom"], savingThrows: ["wisdom", "charisma"], armorProficiencies: ["Leve", "Média", "Escudos"], weaponProficiencies: ["Simples"], skillChoices: ["history", "insight", "medicine", "persuasion", "religion"], skillCount: 2, spellcastingAbility: "wisdom", subclassLevel: 1, subclassLabel: "Domínio Divino", subclasses: [{ id: "life", name: "Domínio da Vida" }, { id: "light", name: "Domínio da Luz" }, { id: "knowledge", name: "Domínio do Conhecimento" }, { id: "nature", name: "Domínio da Natureza" }, { id: "tempest", name: "Domínio da Tempestade" }, { id: "trickery", name: "Domínio da Enganação" }, { id: "war", name: "Domínio da Guerra" }], fightingStyleLevel: null, expertiseLevel: null, expertiseCount: 0 },
  { id: "druid", name: "Druida", hitDice: "d8", primaryAbility: ["wisdom"], savingThrows: ["intelligence", "wisdom"], armorProficiencies: ["Leve", "Média", "Escudos (não-metálicos)"], weaponProficiencies: ["Clavas", "Adagas", "Dardos", "Azagaias", "Maças", "Bordões", "Cimitarras", "Foices", "Fundas", "Lanças"], skillChoices: ["arcana", "animalHandling", "insight", "medicine", "nature", "perception", "religion", "survival"], skillCount: 2, spellcastingAbility: "wisdom", subclassLevel: 2, subclassLabel: "Círculo Druídico", subclasses: [{ id: "land", name: "Círculo da Terra" }, { id: "moon", name: "Círculo da Lua" }], fightingStyleLevel: null, expertiseLevel: null, expertiseCount: 0 },
  { id: "fighter", name: "Guerreiro", hitDice: "d10", primaryAbility: ["strength", "dexterity"], savingThrows: ["strength", "constitution"], armorProficiencies: ["Leve", "Média", "Pesada", "Escudos"], weaponProficiencies: ["Simples", "Marciais"], skillChoices: ["acrobatics", "animalHandling", "athletics", "history", "insight", "intimidation", "perception", "survival"], skillCount: 2, spellcastingAbility: null, subclassLevel: 3, subclassLabel: "Arquétipo Marcial", subclasses: [{ id: "champion", name: "Campeão" }, { id: "battle_master", name: "Mestre de Batalha" }, { id: "eldritch_knight", name: "Cavaleiro Arcano" }], fightingStyleLevel: 1, expertiseLevel: null, expertiseCount: 0 },
  { id: "monk", name: "Monge", hitDice: "d8", primaryAbility: ["dexterity", "wisdom"], savingThrows: ["strength", "dexterity"], armorProficiencies: [], weaponProficiencies: ["Simples", "Espadas curtas"], skillChoices: ["acrobatics", "athletics", "history", "insight", "religion", "stealth"], skillCount: 2, spellcastingAbility: null, subclassLevel: 3, subclassLabel: "Tradição Monástica", subclasses: [{ id: "open_hand", name: "Caminho da Mão Aberta" }, { id: "shadow", name: "Caminho da Sombra" }, { id: "four_elements", name: "Caminho dos Quatro Elementos" }], fightingStyleLevel: null, expertiseLevel: null, expertiseCount: 0 },
  { id: "paladin", name: "Paladino", hitDice: "d10", primaryAbility: ["strength", "charisma"], savingThrows: ["wisdom", "charisma"], armorProficiencies: ["Leve", "Média", "Pesada", "Escudos"], weaponProficiencies: ["Simples", "Marciais"], skillChoices: ["athletics", "insight", "intimidation", "medicine", "persuasion", "religion"], skillCount: 2, spellcastingAbility: "charisma", subclassLevel: 3, subclassLabel: "Juramento Sagrado", subclasses: [{ id: "devotion", name: "Juramento de Devoção" }, { id: "ancients", name: "Juramento dos Anciões" }, { id: "vengeance", name: "Juramento de Vingança" }], fightingStyleLevel: 2, expertiseLevel: null, expertiseCount: 0 },
  { id: "ranger", name: "Patrulheiro", hitDice: "d10", primaryAbility: ["dexterity", "wisdom"], savingThrows: ["strength", "dexterity"], armorProficiencies: ["Leve", "Média", "Escudos"], weaponProficiencies: ["Simples", "Marciais"], skillChoices: ["animalHandling", "athletics", "insight", "investigation", "nature", "perception", "stealth", "survival"], skillCount: 3, spellcastingAbility: "wisdom", subclassLevel: 3, subclassLabel: "Arquétipo de Patrulheiro", subclasses: [{ id: "hunter", name: "Caçador" }, { id: "beast_master", name: "Mestre das Feras" }], fightingStyleLevel: 2, expertiseLevel: null, expertiseCount: 0 },
  { id: "rogue", name: "Ladino", hitDice: "d8", primaryAbility: ["dexterity"], savingThrows: ["dexterity", "intelligence"], armorProficiencies: ["Leve"], weaponProficiencies: ["Simples", "Bestas de mão", "Espadas longas", "Rapieiras", "Espadas curtas"], skillChoices: ["acrobatics", "athletics", "deception", "insight", "intimidation", "investigation", "perception", "performance", "persuasion", "sleightOfHand", "stealth"], skillCount: 4, spellcastingAbility: null, subclassLevel: 3, subclassLabel: "Arquétipo de Ladino", subclasses: [{ id: "thief", name: "Ladrão" }, { id: "assassin", name: "Assassino" }, { id: "arcane_trickster", name: "Trapaceiro Arcano" }], fightingStyleLevel: null, expertiseLevel: 1, expertiseCount: 2 },
  { id: "sorcerer", name: "Feiticeiro", hitDice: "d6", primaryAbility: ["charisma"], savingThrows: ["constitution", "charisma"], armorProficiencies: [], weaponProficiencies: ["Adagas", "Dardos", "Fundas", "Bordões", "Bestas leves"], skillChoices: ["arcana", "deception", "insight", "intimidation", "persuasion", "religion"], skillCount: 2, spellcastingAbility: "charisma", subclassLevel: 1, subclassLabel: "Origem de Feitiçaria", subclasses: [{ id: "draconic_bloodline", name: "Linhagem Dracônica" }, { id: "wild_magic", name: "Magia Selvagem" }], fightingStyleLevel: null, expertiseLevel: null, expertiseCount: 0 },
  { id: "warlock", name: "Bruxo", hitDice: "d8", primaryAbility: ["charisma"], savingThrows: ["wisdom", "charisma"], armorProficiencies: ["Leve"], weaponProficiencies: ["Simples"], skillChoices: ["arcana", "deception", "history", "intimidation", "investigation", "nature", "religion"], skillCount: 2, spellcastingAbility: "charisma", subclassLevel: 1, subclassLabel: "Patrono Transcendental", subclasses: [{ id: "archfey", name: "A Arquifada" }, { id: "fiend", name: "O Corruptor" }, { id: "great_old_one", name: "O Grande Antigo" }], fightingStyleLevel: null, expertiseLevel: null, expertiseCount: 0 },
  { id: "wizard", name: "Mago", hitDice: "d6", primaryAbility: ["intelligence"], savingThrows: ["intelligence", "wisdom"], armorProficiencies: [], weaponProficiencies: ["Adagas", "Dardos", "Fundas", "Bordões", "Bestas leves"], skillChoices: ["arcana", "history", "insight", "investigation", "medicine", "religion"], skillCount: 2, spellcastingAbility: "intelligence", subclassLevel: 2, subclassLabel: "Tradição Arcana", subclasses: [{ id: "abjuration", name: "Escola de Abjuração" }, { id: "conjuration", name: "Escola de Conjuração" }, { id: "divination", name: "Escola de Adivinhação" }, { id: "enchantment", name: "Escola de Encantamento" }, { id: "evocation", name: "Escola de Evocação" }, { id: "illusion", name: "Escola de Ilusão" }, { id: "necromancy", name: "Escola de Necromancia" }, { id: "transmutation", name: "Escola de Transmutação" }], fightingStyleLevel: null, expertiseLevel: null, expertiseCount: 0 },
];

const LEGACY_SUBCLASS_IDS: Record<string, Record<string, string>> = {
  barbarian: {
    furioso: "berserker",
    "guerreiro-totemico": "totem_warrior",
  },
  bard: {
    conhecimento: "lore",
    bravura: "valor",
  },
  cleric: {
    vida: "life",
    luz: "light",
    conhecimento: "knowledge",
    natureza: "nature",
    tempestade: "tempest",
    enganacao: "trickery",
    guerra: "war",
  },
  druid: {
    terra: "land",
    lua: "moon",
  },
  fighter: {
    campeao: "champion",
    "mestre-de-batalha": "battle_master",
    "cavaleiro-arcano": "eldritch_knight",
  },
  monk: {
    "mao-aberta": "open_hand",
    sombra: "shadow",
    "quatro-elementos": "four_elements",
  },
  paladin: {
    devocao: "devotion",
    ancioes: "ancients",
    vinganca: "vengeance",
  },
  ranger: {
    cacador: "hunter",
    "mestre-das-feras": "beast_master",
  },
  rogue: {
    ladrao: "thief",
    assassino: "assassin",
    "trapaceiro-arcano": "arcane_trickster",
  },
  sorcerer: {
    "linhagem-draconica": "draconic_bloodline",
    "magia-selvagem": "wild_magic",
  },
  warlock: {
    arquifada: "archfey",
    corruptor: "fiend",
    "grande-antigo": "great_old_one",
  },
  wizard: {
    abjuracao: "abjuration",
    conjuracao: "conjuration",
    adivinhacao: "divination",
    encantamento: "enchantment",
    evocacao: "evocation",
    ilusao: "illusion",
    necromancia: "necromancy",
    transmutacao: "transmutation",
  },
};

// ── Subclass config fields ───────────────────────────────────────────────────

export type SubclassConfigField = {
  key: string;
  label: string;
  options: { id: string; name: string }[];
};

const SUBCLASS_CONFIG_FIELDS: Record<string, SubclassConfigField[]> = {
  "sorcerer.draconic_bloodline": [
    {
      key: "dragonAncestor",
      label: "Ancestral Dracônico",
      options: [
        { id: "blue", name: "Azul (Elétrico)" },
        { id: "white", name: "Branco (Frio)" },
        { id: "bronze", name: "Bronze (Elétrico)" },
        { id: "copper", name: "Cobre (Ácido)" },
        { id: "brass", name: "Latão (Fogo)" },
        { id: "black", name: "Negro (Ácido)" },
        { id: "gold", name: "Ouro (Fogo)" },
        { id: "silver", name: "Prata (Frio)" },
        { id: "green", name: "Verde (Veneno)" },
        { id: "red", name: "Vermelho (Fogo)" },
      ],
    },
  ],
};

export const getSubclassConfigFields = (
  classId: string,
  subclassId: string | null | undefined,
): SubclassConfigField[] =>
  subclassId ? (SUBCLASS_CONFIG_FIELDS[`${classId}.${subclassId}`] ?? []) : [];

// ── Subclass language grants ─────────────────────────────────────────────────

const SUBCLASS_LANGUAGE_GRANTS: Record<string, string[]> = {
  "sorcerer.draconic_bloodline": ["Dracônico"],
};

export const getSubclassLanguageGrants = (
  classId: string,
  subclassId: string | null | undefined,
): string[] =>
  subclassId ? (SUBCLASS_LANGUAGE_GRANTS[`${classId}.${subclassId}`] ?? []) : [];

export const CLASSES: DndClass[] = CLASS_DEFINITIONS.map((entry) => ({
  ...entry,
  fightingStyleOptions: entry.fightingStyleOptions ?? getDefaultFightingStyleOptions(entry.id),
  startingEquipment: describeDefaultClassStartingEquipment(entry.id),
}));

export const getClass = (id: string): DndClass | undefined =>
  CLASSES.find((c) => c.id === id);

export const isSubclassUnlocked = (dndClass: DndClass, level: number): boolean =>
  dndClass.subclasses.length > 0 && level >= dndClass.subclassLevel;

export const hasFightingStyleAtCreation = (dndClass: DndClass, level: number): boolean =>
  dndClass.fightingStyleLevel !== null && level >= dndClass.fightingStyleLevel;

export const hasExpertiseAtCreation = (dndClass: DndClass, level: number): boolean =>
  dndClass.expertiseLevel !== null && level >= dndClass.expertiseLevel;

export const normalizeSubclassId = (
  classId: string,
  subclassId: string | null | undefined,
): string | null => {
  if (!subclassId) return null;

  const dndClass = getClass(classId);
  if (dndClass?.subclasses.some((subclass) => subclass.id === subclassId)) {
    return subclassId;
  }

  return LEGACY_SUBCLASS_IDS[classId]?.[subclassId] ?? subclassId;
};
