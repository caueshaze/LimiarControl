import type { SkillName } from "../model/characterSheet.types";
import { LANGUAGE_CHOICE_SLOT } from "./languages";

export type BackgroundFeature = {
  id: string;
  label: string;
  description: string;
};

type BackgroundDefinition = {
  id: string;
  aliases?: string[];
  name: string;
  skillProficiencies: SkillName[];
  toolProficiencyCanonicalKeys: string[];
  languages: string[];
  feature: BackgroundFeature;
  startingEquipment: string[];
};

export type Background = {
  id: string;
  name: string;
  skillProficiencies: SkillName[];
  toolProficiencyCanonicalKeys: string[];
  toolProficiencies: string[];
  languages: string[];
  feature: BackgroundFeature;
  startingEquipment: string[];
};

const TOOL_LABELS_BY_CANONICAL_KEY: Record<string, string> = {
  artisans_tools: "Ferramentas de Artesão",
  disguise_kit: "Kit de Disfarce",
  forgery_kit: "Kit de Falsificação",
  gaming_set: "Jogo de Mesa",
  herbalism_kit: "Kit de Herbalismo",
  musical_instrument: "Instrumento Musical",
  navigators_tools: "Ferramentas de Navegação",
  thieves_tools: "Ferramentas de Ladrão",
  vehicles_land: "Veículos (terrestres)",
  vehicles_water: "Veículos (aquáticos)",
};

const BACKGROUND_DEFINITIONS: BackgroundDefinition[] = [
  {
    id: "acolyte",
    name: "Acólito",
    skillProficiencies: ["insight", "religion"],
    toolProficiencyCanonicalKeys: [],
    languages: [LANGUAGE_CHOICE_SLOT, LANGUAGE_CHOICE_SLOT],
    feature: {
      id: "shelter_of_the_faithful",
      label: "Abrigo dos Fiéis",
      description: "Você recebe apoio básico de templos e fiéis da sua religião.",
    },
    startingEquipment: [
      "catalog:holy_symbol",
      "catalog:prayer_book",
      "catalog:incense x5",
      "catalog:vestments",
      "catalog:common_clothes",
      "15 gp",
    ],
  },
  {
    id: "charlatan",
    name: "Charlatão",
    skillProficiencies: ["deception", "sleightOfHand"],
    toolProficiencyCanonicalKeys: ["disguise_kit", "forgery_kit"],
    languages: [],
    feature: {
      id: "false_identity",
      label: "Identidade Falsa",
      description: "Você mantém uma identidade secundária convincente e bem documentada.",
    },
    startingEquipment: [
      "catalog:fine_clothes",
      "catalog:disguise_kit",
      "catalog:forgery_kit",
      "15 gp",
    ],
  },
  {
    id: "criminal",
    name: "Criminoso",
    skillProficiencies: ["deception", "stealth"],
    toolProficiencyCanonicalKeys: ["thieves_tools", "gaming_set"],
    languages: [],
    feature: {
      id: "criminal_contact",
      label: "Contato Criminal",
      description: "Você tem um contato confiável no submundo criminoso local.",
    },
    startingEquipment: [
      "catalog:crowbar",
      "catalog:dark_common_clothes_with_hood",
      "15 gp",
    ],
  },
  {
    id: "entertainer",
    name: "Artista",
    skillProficiencies: ["acrobatics", "performance"],
    toolProficiencyCanonicalKeys: ["disguise_kit", "musical_instrument"],
    languages: [],
    feature: {
      id: "by_popular_demand",
      label: "Pela Demanda Popular",
      description: "Você sempre encontra abrigo e comida modestos onde possa se apresentar.",
    },
    startingEquipment: [
      "catalog:musical_instrument",
      "catalog:favor_of_an_admirer",
      "catalog:costume",
      "15 gp",
    ],
  },
  {
    id: "folk_hero",
    aliases: ["folk-hero"],
    name: "Herói do Povo",
    skillProficiencies: ["animalHandling", "survival"],
    toolProficiencyCanonicalKeys: ["artisans_tools", "vehicles_land"],
    languages: [],
    feature: {
      id: "rustic_hospitality",
      label: "Hospitalidade Rústica",
      description: "Camponeses comuns oferecem ajuda, abrigo e proteção a você e ao seu grupo.",
    },
    startingEquipment: [
      "catalog:artisans_tools",
      "catalog:shovel",
      "catalog:iron_pot",
      "catalog:common_clothes",
      "10 gp",
    ],
  },
  {
    id: "guild_artisan",
    aliases: ["guild-artisan"],
    name: "Artesão de Guilda",
    skillProficiencies: ["insight", "persuasion"],
    toolProficiencyCanonicalKeys: ["artisans_tools"],
    languages: [LANGUAGE_CHOICE_SLOT],
    feature: {
      id: "guild_membership",
      label: "Membro da Guilda",
      description: "Sua guilda oferece reconhecimento, contatos e suporte entre seus membros.",
    },
    startingEquipment: [
      "catalog:artisans_tools",
      "catalog:letter_of_introduction",
      "catalog:travelers_clothes",
      "15 gp",
    ],
  },
  {
    id: "hermit",
    name: "Eremita",
    skillProficiencies: ["medicine", "religion"],
    toolProficiencyCanonicalKeys: ["herbalism_kit"],
    languages: [LANGUAGE_CHOICE_SLOT],
    feature: {
      id: "discovery",
      label: "Descoberta",
      description: "Seu isolamento lhe rendeu uma descoberta singular sobre o mundo.",
    },
    startingEquipment: [
      "catalog:scroll_case",
      "catalog:winter_blanket",
      "catalog:common_clothes",
      "catalog:herbalism_kit",
      "5 gp",
    ],
  },
  {
    id: "noble",
    name: "Nobre",
    skillProficiencies: ["history", "persuasion"],
    toolProficiencyCanonicalKeys: ["gaming_set"],
    languages: [LANGUAGE_CHOICE_SLOT],
    feature: {
      id: "position_of_privilege",
      label: "Posição de Privilégio",
      description: "Sua posição social garante respeito, acesso e etiqueta da alta sociedade.",
    },
    startingEquipment: [
      "catalog:fine_clothes",
      "catalog:signet_ring",
      "catalog:scroll_of_pedigree",
      "25 gp",
    ],
  },
  {
    id: "outlander",
    name: "Forasteiro",
    skillProficiencies: ["athletics", "survival"],
    toolProficiencyCanonicalKeys: ["musical_instrument"],
    languages: [LANGUAGE_CHOICE_SLOT],
    feature: {
      id: "wanderer",
      label: "Andarilho",
      description: "Você encontra comida fresca e água para si e alguns companheiros em ermos.",
    },
    startingEquipment: [
      "catalog:quarterstaff",
      "catalog:hunting_trap",
      "catalog:animal_trophy",
      "catalog:travelers_clothes",
      "10 gp",
    ],
  },
  {
    id: "sage",
    name: "Sábio",
    skillProficiencies: ["arcana", "history"],
    toolProficiencyCanonicalKeys: [],
    languages: [LANGUAGE_CHOICE_SLOT, LANGUAGE_CHOICE_SLOT],
    feature: {
      id: "researcher",
      label: "Pesquisador",
      description: "Você sabe onde encontrar ou a quem recorrer por conhecimento raro.",
    },
    startingEquipment: [
      "catalog:bottle_of_black_ink",
      "catalog:quill",
      "catalog:small_knife",
      "catalog:letter_with_unanswered_question",
      "catalog:common_clothes",
      "10 gp",
    ],
  },
  {
    id: "sailor",
    name: "Marinheiro",
    skillProficiencies: ["athletics", "perception"],
    toolProficiencyCanonicalKeys: ["navigators_tools", "vehicles_water"],
    languages: [],
    feature: {
      id: "ships_passage",
      label: "Passagem de Navio",
      description: "Você consegue transporte gratuito em embarcações para si e seus companheiros.",
    },
    startingEquipment: [
      "catalog:belaying_pin",
      "catalog:silk_rope",
      "catalog:lucky_charm",
      "catalog:common_clothes",
      "10 gp",
    ],
  },
  {
    id: "soldier",
    name: "Soldado",
    skillProficiencies: ["athletics", "intimidation"],
    toolProficiencyCanonicalKeys: ["gaming_set", "vehicles_land"],
    languages: [],
    feature: {
      id: "military_rank",
      label: "Patente Militar",
      description: "Sua patente abre portas entre militares e soldados aliados.",
    },
    startingEquipment: [
      "catalog:insignia_of_rank",
      "catalog:trophy_from_fallen_enemy",
      "catalog:gaming_set",
      "catalog:common_clothes",
      "10 gp",
    ],
  },
  {
    id: "urchin",
    name: "Pivete",
    skillProficiencies: ["sleightOfHand", "stealth"],
    toolProficiencyCanonicalKeys: ["disguise_kit", "thieves_tools"],
    languages: [],
    feature: {
      id: "city_secrets",
      label: "Segredos da Cidade",
      description: "Você conhece passagens ocultas e rotas velozes pelas áreas urbanas.",
    },
    startingEquipment: [
      "catalog:small_knife",
      "catalog:map_of_home_city",
      "catalog:pet_mouse",
      "catalog:token_from_parent",
      "catalog:common_clothes",
      "10 gp",
    ],
  },
];

const BACKGROUND_ALIASES = new Map<string, string>(
  BACKGROUND_DEFINITIONS.flatMap((background) =>
    (background.aliases ?? []).map((alias) => [alias, background.id] as const),
  ),
);

const toBackground = (definition: BackgroundDefinition): Background => ({
  id: definition.id,
  name: definition.name,
  skillProficiencies: definition.skillProficiencies,
  toolProficiencyCanonicalKeys: definition.toolProficiencyCanonicalKeys,
  toolProficiencies: definition.toolProficiencyCanonicalKeys.map(
    (key) => TOOL_LABELS_BY_CANONICAL_KEY[key] ?? key,
  ),
  languages: definition.languages,
  feature: definition.feature,
  startingEquipment: definition.startingEquipment,
});

export const BACKGROUNDS: Background[] = BACKGROUND_DEFINITIONS.map(toBackground);

export const normalizeBackgroundId = (id: string) => BACKGROUND_ALIASES.get(id) ?? id;

export const getBackground = (id: string): Background | undefined =>
  BACKGROUNDS.find((background) => background.id === normalizeBackgroundId(id));
