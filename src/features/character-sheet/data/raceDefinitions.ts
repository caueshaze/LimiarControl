import type { AbilityName, SkillName } from "../model/characterSheet.types";
import { LANGUAGE_CHOICE_SLOT } from "./languages";
import { DRAGONBORN_ANCESTRIES } from "./dragonbornAncestries";

export type RaceToolProficiencyChoice = {
  count: number;
  options: string[];
  label: string;
};

export type RaceConfigField = {
  key: "dragonbornAncestry" | "gnomeSubrace" | "halfElfAbilityChoices" | "halfElfSkillChoices";
  label: string;
  required: boolean;
} & (
  | {
    kind?: "select";
    options: Array<{ id: string; name: string }>;
  }
  | {
    kind: "ability_multi";
    count: number;
    exclude?: AbilityName[];
  }
  | {
    kind: "skill_multi";
    count: number;
  }
);

export type RaceStructuredFeature =
  | { id: string; label: string; kind: "passive"; description?: string }
  | {
    id: string;
    label: string;
    kind: "rule";
    ruleId: string;
    trigger?: string;
    effect?: string;
    damageType?: string;
    uses?: number;
    recharge?: "short_rest" | "long_rest";
    description?: string;
  }
  | {
    id: string;
    label: string;
    kind: "spell";
    spellCanonicalKey: string;
    ability: AbilityName;
    // `known` means the spell is granted by the race as a permanent racial spell.
    // It does not imply automatic insertion into `sheet.spellcasting`, which remains class-scoped today.
    minLevel?: number;
    known?: boolean;
    uses?: number;
    recharge?: "short_rest" | "long_rest";
    castAtLevel?: number;
    description?: string;
  }
  | { id: string; label: string; kind: "tool_proficiency"; toolCanonicalKey: string; description?: string };

export type RaceDefinitionVariant = {
  id: string;
  name: string;
  abilityBonuses?: Partial<Record<AbilityName, number>>;
  traits?: string[];
  weaponProficiencies?: string[];
  armorProficiencies?: string[];
  skillProficiencies?: SkillName[];
  toolProficiencyChoices?: RaceToolProficiencyChoice;
  structuredFeatures?: RaceStructuredFeature[];
};

export type RaceDefinition = {
  id: string;
  name: string;
  selectable?: boolean;
  aliases?: string[];
  size: "Pequeno" | "Médio";
  darkvision: number | null;
  languages: string[];
  abilityBonuses: Partial<Record<AbilityName, number>>;
  speed: number;
  traits: string[];
  weaponProficiencies?: string[];
  armorProficiencies?: string[];
  skillProficiencies?: SkillName[];
  toolProficiencyChoices?: RaceToolProficiencyChoice;
  structuredFeatures?: RaceStructuredFeature[];
  configFields?: RaceConfigField[];
  variants?: Record<string, RaceDefinitionVariant>;
};

const DRAGONBORN_ANCESTRY_OPTIONS = DRAGONBORN_ANCESTRIES.map((ancestry) => ({
  id: ancestry.id,
  name: ancestry.label,
}));

export const RACE_DEFINITIONS: RaceDefinition[] = [
  { id: "hill-dwarf", name: "Anão da Colina", size: "Médio", darkvision: 60, languages: ["Comum", "Anão"], abilityBonuses: { constitution: 2, wisdom: 1 }, speed: 25, traits: ["Resiliência Anã", "Sentido de Pedra", "Robustez Anã", "Sem Penalidade de Armadura Pesada"], weaponProficiencies: ["Machado de batalha", "Machadinha", "Martelo leve", "Martelo de guerra"], toolProficiencyChoices: { count: 1, options: ["Ferramentas de Ferreiro", "Ferramentas de Cervejeiro", "Ferramentas de Pedreiro"], label: "Escolha uma ferramenta de artesão (proficiência racial)" } },
  { id: "mountain-dwarf", name: "Anão da Montanha", size: "Médio", darkvision: 60, languages: ["Comum", "Anão"], abilityBonuses: { constitution: 2, strength: 2 }, speed: 25, traits: ["Resiliência Anã", "Sentido de Pedra", "Proficiência em Armadura", "Sem Penalidade de Armadura Pesada"], weaponProficiencies: ["Machado de batalha", "Machadinha", "Martelo leve", "Martelo de guerra"], armorProficiencies: ["Leve", "Média"], toolProficiencyChoices: { count: 1, options: ["Ferramentas de Ferreiro", "Ferramentas de Cervejeiro", "Ferramentas de Pedreiro"], label: "Escolha uma ferramenta de artesão (proficiência racial)" } },
  { id: "high-elf", name: "Elfo Alto", size: "Médio", darkvision: 60, languages: ["Comum", "Élfico", LANGUAGE_CHOICE_SLOT], abilityBonuses: { dexterity: 2, intelligence: 1 }, speed: 30, traits: ["Ancestralidade Feérica", "Transe", "Truque"], skillProficiencies: ["perception"], weaponProficiencies: ["Espada longa", "Espada curta", "Arco longo", "Arco curto"] },
  { id: "wood-elf", name: "Elfo da Floresta", size: "Médio", darkvision: 60, languages: ["Comum", "Élfico"], abilityBonuses: { dexterity: 2, wisdom: 1 }, speed: 35, traits: ["Ancestralidade Feérica", "Transe", "Pés Velozes", "Máscara da Natureza"], skillProficiencies: ["perception"], weaponProficiencies: ["Espada longa", "Espada curta", "Arco longo", "Arco curto"] },
  { id: "dark-elf", name: "Elfo Negro (Drow)", size: "Médio", darkvision: 120, languages: ["Comum", "Élfico"], abilityBonuses: { dexterity: 2, charisma: 1 }, speed: 30, traits: ["Ancestralidade Feérica", "Transe", "Sensibilidade à Luz Solar", "Magia Drow"], skillProficiencies: ["perception"], weaponProficiencies: ["Rapieira", "Espada curta", "Besta de mão"] },
  { id: "lightfoot-halfling", name: "Halfling Pés-Leves", size: "Pequeno", darkvision: null, languages: ["Comum", "Halfling"], abilityBonuses: { dexterity: 2, charisma: 1 }, speed: 25, traits: ["Sortudo", "Corajoso", "Agilidade Halfling", "Naturalmente Furtivo"] },
  { id: "stout-halfling", name: "Halfling Robusto", size: "Pequeno", darkvision: null, languages: ["Comum", "Halfling"], abilityBonuses: { dexterity: 2, constitution: 1 }, speed: 25, traits: ["Sortudo", "Corajoso", "Agilidade Halfling", "Resiliência Robusta"] },
  { id: "human", name: "Humano", size: "Médio", darkvision: null, languages: ["Comum", LANGUAGE_CHOICE_SLOT], abilityBonuses: { strength: 1, dexterity: 1, constitution: 1, intelligence: 1, wisdom: 1, charisma: 1 }, speed: 30, traits: [] },
  { id: "dragonborn", name: "Draconato", size: "Médio", darkvision: null, languages: ["Comum", "Dracônico"], abilityBonuses: { strength: 2, charisma: 1 }, speed: 30, traits: ["Ancestralidade Dracônica", "Sopro de Dragão", "Resistência a Danos"], configFields: [{ key: "dragonbornAncestry", label: "Ancestral dracônico", required: true, options: DRAGONBORN_ANCESTRY_OPTIONS }] },
  {
    id: "gnome",
    name: "Gnomo",
    selectable: true,
    aliases: ["forest-gnome", "rock-gnome"],
    size: "Pequeno",
    darkvision: 60,
    languages: ["Comum", "Gnomo"],
    abilityBonuses: { intelligence: 2 },
    speed: 25,
    traits: ["Astúcia Gnômica"],
    structuredFeatures: [
      {
        id: "gnome-cunning",
        label: "Astúcia Gnômica",
        kind: "rule",
        ruleId: "gnome_cunning",
        description: "Vantagem em testes de resistência de INT, WIS e CHA contra magia.",
      },
    ],
    configFields: [{
      key: "gnomeSubrace",
      label: "Sub-raça do Gnomo",
      required: true,
      options: [
        { id: "forest", name: "Gnomo da Floresta" },
        { id: "rock", name: "Gnomo da Rocha" },
      ],
    }],
    variants: {
      forest: {
        id: "forest",
        name: "Gnomo da Floresta",
        abilityBonuses: { dexterity: 1 },
        traits: ["Ilusionista Natural", "Falar com Animais"],
        structuredFeatures: [
          {
            id: "minor-illusion",
            label: "Ilusionista Natural",
            kind: "spell",
            spellCanonicalKey: "minor_illusion",
            ability: "intelligence",
            description: "Você conhece o truque Minor Illusion; Inteligência é sua habilidade de conjuração para ele.",
          },
          {
            id: "speak-with-small-beasts",
            label: "Falar com Bestas Pequenas",
            kind: "passive",
            description: "Por meio de sons e gestos, você pode comunicar ideias simples a bestas Pequenas ou menores.",
          },
        ],
      },
      rock: {
        id: "rock",
        name: "Gnomo da Rocha",
        abilityBonuses: { constitution: 1 },
        traits: ["Lore de Artesão", "Engenhoca"],
        structuredFeatures: [
          {
            id: "tinkers-tools",
            label: "Proficiência: Ferramentas de Engenhoqueiro",
            kind: "tool_proficiency",
            toolCanonicalKey: "tinkers_tools",
          },
          {
            id: "artificers-lore",
            label: "Lore de Artesão",
            kind: "passive",
            description: "Sua proficiência em testes de History relacionados a itens mágicos, objetos alquímicos e dispositivos tecnológicos é dobrada.",
          },
          {
            id: "tinker",
            label: "Engenhoca",
            kind: "passive",
            description: "Você pode usar Ferramentas de Engenhoqueiro para construir pequenos dispositivos mecânicos.",
          },
        ],
      },
    },
  },
  {
    id: "half-elf",
    name: "Meio-Elfo",
    size: "Médio",
    darkvision: 60,
    languages: ["Comum", "Élfico", LANGUAGE_CHOICE_SLOT],
    abilityBonuses: { charisma: 2 },
    speed: 30,
    traits: ["Ancestralidade Feérica", "Versatilidade de Perícias"],
    structuredFeatures: [
      {
        id: "fey-ancestry",
        label: "Ancestralidade Feérica",
        kind: "rule",
        ruleId: "fey_ancestry",
        description: "Vantagem em testes de resistência contra encantamento, e magia não pode colocar você para dormir.",
      },
      {
        id: "skill-versatility",
        label: "Versatilidade em Perícias",
        kind: "passive",
        description: "Escolha duas perícias para ganhar proficiência racial.",
      },
    ],
    configFields: [
      {
        key: "halfElfAbilityChoices",
        label: "Bônus raciais (+1 em dois atributos)",
        required: true,
        kind: "ability_multi",
        count: 2,
        exclude: ["charisma"],
      },
      {
        key: "halfElfSkillChoices",
        label: "Versatilidade em Perícias",
        required: true,
        kind: "skill_multi",
        count: 2,
      },
    ],
  },
  {
    id: "half-orc",
    name: "Meio-Orc",
    size: "Médio",
    darkvision: 60,
    languages: ["Comum", "Orc"],
    abilityBonuses: { strength: 2, constitution: 1 },
    speed: 30,
    traits: ["Ameaçador", "Resistência Implacável", "Ataques Selvagens"],
    skillProficiencies: ["intimidation"],
    structuredFeatures: [
      {
        id: "menacing",
        label: "Ameaçador",
        kind: "passive",
        description: "Você tem proficiência na perícia Intimidação.",
      },
      {
        id: "relentless_endurance",
        label: "Resistência Implacável",
        kind: "rule",
        ruleId: "relentless_endurance",
        trigger: "on_drop_to_zero_hp",
        effect: "set_hp_to_1",
        uses: 1,
        recharge: "long_rest",
        description: "Quando você é reduzido a 0 HP, mas não morre instantaneamente, volta para 1 HP. Uma vez por descanso longo.",
      },
      {
        id: "savage_attacks",
        label: "Ataques Selvagens",
        kind: "rule",
        ruleId: "savage_attacks",
        trigger: "on_melee_critical_hit",
        effect: "extra_weapon_damage_die",
        description: "Quando acerta um crítico com arma corpo-a-corpo, role um dado de dano adicional da arma.",
      },
    ],
  },
  {
    id: "tiefling",
    name: "Tiefling",
    size: "Médio",
    darkvision: 60,
    languages: ["Comum", "Infernal"],
    abilityBonuses: { intelligence: 1, charisma: 2 },
    speed: 30,
    traits: ["Resistência Infernal", "Thaumaturgy", "Hellish Rebuke", "Darkness"],
    structuredFeatures: [
      {
        id: "infernal_resistance",
        label: "Resistência Infernal",
        kind: "rule",
        ruleId: "infernal_resistance",
        effect: "damage_resistance",
        damageType: "fire",
        description: "Você tem resistência a dano de fogo.",
      },
      {
        id: "thaumaturgy",
        label: "Thaumaturgy",
        kind: "spell",
        spellCanonicalKey: "thaumaturgy",
        ability: "charisma",
        minLevel: 1,
        known: true,
        description: "Você conhece o truque Thaumaturgy; Carisma é sua habilidade de conjuração para ele.",
      },
      {
        id: "hellish_rebuke",
        label: "Hellish Rebuke",
        kind: "spell",
        spellCanonicalKey: "hellish_rebuke",
        ability: "charisma",
        minLevel: 3,
        uses: 1,
        recharge: "long_rest",
        castAtLevel: 2,
        description: "A partir do 3º nível, você pode conjurar Hellish Rebuke como magia de 2º nível uma vez por descanso longo.",
      },
      {
        id: "darkness",
        label: "Darkness",
        kind: "spell",
        spellCanonicalKey: "darkness",
        ability: "charisma",
        minLevel: 5,
        uses: 1,
        recharge: "long_rest",
        description: "A partir do 5º nível, você pode conjurar Darkness uma vez por descanso longo.",
      },
    ],
  },
];
