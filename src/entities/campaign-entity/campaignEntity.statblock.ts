import type {
  AbilityName,
  AbilityScores,
  ConditionType,
  CreatureType,
  DamageType,
  EntitySize,
  SkillName,
} from "./campaignEntity.types";

export const ENTITY_ABILITIES: { key: AbilityName; label: string; short: string }[] = [
  { key: "strength", label: "Forca", short: "FOR" },
  { key: "dexterity", label: "Destreza", short: "DES" },
  { key: "constitution", label: "Constituicao", short: "CON" },
  { key: "intelligence", label: "Inteligencia", short: "INT" },
  { key: "wisdom", label: "Sabedoria", short: "SAB" },
  { key: "charisma", label: "Carisma", short: "CAR" },
];

export const ENTITY_SKILLS: { key: SkillName; label: string; ability: AbilityName }[] = [
  { key: "acrobatics", label: "Acrobacia", ability: "dexterity" },
  { key: "animalHandling", label: "Lidar com Animais", ability: "wisdom" },
  { key: "arcana", label: "Arcanismo", ability: "intelligence" },
  { key: "athletics", label: "Atletismo", ability: "strength" },
  { key: "deception", label: "Enganacao", ability: "charisma" },
  { key: "history", label: "Historia", ability: "intelligence" },
  { key: "insight", label: "Intuicao", ability: "wisdom" },
  { key: "intimidation", label: "Intimidacao", ability: "charisma" },
  { key: "investigation", label: "Investigacao", ability: "intelligence" },
  { key: "medicine", label: "Medicina", ability: "wisdom" },
  { key: "nature", label: "Natureza", ability: "intelligence" },
  { key: "perception", label: "Percepcao", ability: "wisdom" },
  { key: "performance", label: "Atuacao", ability: "charisma" },
  { key: "persuasion", label: "Persuasao", ability: "charisma" },
  { key: "religion", label: "Religiao", ability: "intelligence" },
  { key: "sleightOfHand", label: "Prestidigitacao", ability: "dexterity" },
  { key: "stealth", label: "Furtividade", ability: "dexterity" },
  { key: "survival", label: "Sobrevivencia", ability: "wisdom" },
];

export const ENTITY_DAMAGE_TYPES: { key: DamageType; label: string }[] = [
  { key: "acid", label: "Acido" },
  { key: "bludgeoning", label: "Contundente" },
  { key: "cold", label: "Frio" },
  { key: "fire", label: "Fogo" },
  { key: "force", label: "Forca" },
  { key: "lightning", label: "Eletrico" },
  { key: "necrotic", label: "Necrotico" },
  { key: "piercing", label: "Perfurante" },
  { key: "poison", label: "Veneno" },
  { key: "psychic", label: "Psiquico" },
  { key: "radiant", label: "Radiante" },
  { key: "slashing", label: "Cortante" },
  { key: "thunder", label: "Trovao" },
];

export const ENTITY_CONDITIONS: { key: ConditionType; label: string }[] = [
  { key: "blinded", label: "Cegado" },
  { key: "charmed", label: "Encantado" },
  { key: "deafened", label: "Ensurdecido" },
  { key: "frightened", label: "Amedrontado" },
  { key: "grappled", label: "Agarrado" },
  { key: "incapacitated", label: "Incapacitado" },
  { key: "invisible", label: "Invisivel" },
  { key: "paralyzed", label: "Paralisado" },
  { key: "petrified", label: "Petrificado" },
  { key: "poisoned", label: "Envenenado" },
  { key: "prone", label: "Caido" },
  { key: "restrained", label: "Contido" },
  { key: "stunned", label: "Atordoado" },
  { key: "unconscious", label: "Inconsciente" },
];

export const ENTITY_SIZES: { key: EntitySize; label: string }[] = [
  { key: "tiny", label: "Miudo" },
  { key: "small", label: "Pequeno" },
  { key: "medium", label: "Medio" },
  { key: "large", label: "Grande" },
  { key: "huge", label: "Enorme" },
  { key: "gargantuan", label: "Gargantuesco" },
];

export const ENTITY_CREATURE_TYPES: { key: CreatureType; label: string }[] = [
  { key: "aberration", label: "Aberracao" },
  { key: "beast", label: "Besta" },
  { key: "celestial", label: "Celestial" },
  { key: "construct", label: "Construto" },
  { key: "dragon", label: "Dragao" },
  { key: "elemental", label: "Elemental" },
  { key: "fey", label: "Feerico" },
  { key: "fiend", label: "Corruptor" },
  { key: "giant", label: "Gigante" },
  { key: "humanoid", label: "Humanoide" },
  { key: "monstrosity", label: "Monstruosidade" },
  { key: "ooze", label: "Gosma" },
  { key: "plant", label: "Planta" },
  { key: "undead", label: "Morto-vivo" },
];

export const EMPTY_ENTITY_ABILITIES: AbilityScores = {
  strength: 10,
  dexterity: 10,
  constitution: 10,
  intelligence: 10,
  wisdom: 10,
  charisma: 10,
};

export const withSignedBonus = (value: number | null | undefined) => {
  if (typeof value !== "number") {
    return null;
  }
  return value >= 0 ? `+${value}` : String(value);
};
