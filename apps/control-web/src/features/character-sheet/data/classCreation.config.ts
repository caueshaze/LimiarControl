import { musicalInstrumentOptions, packOptions } from "./classCreation.shared";
import {
  martialMeleeWeaponOptions,
  martialWeaponPairOptions,
  martialWeaponWithShieldOptions,
  option,
  resolveStaticConfigAgainstCatalog,
  simpleMeleePairOptions,
  simpleMeleeWeaponOptions,
  simpleWeaponOptions,
  uniqueOptions,
} from "./classCreation.helpers";
import type { ClassCreationConfig } from "./classCreation.types";

export const CLASS_CREATION_CONFIG: Record<string, ClassCreationConfig> = {
  barbarian: {
    fixedEquipment: ["Explorer's Pack", "Javelin x4"],
    equipmentChoices: [
      {
        id: "barbarian-weapon-1",
        label: "Escolha sua arma principal",
        options: uniqueOptions([
          option("Machado Grande", "Greataxe"),
          ...martialMeleeWeaponOptions,
        ]),
      },
      {
        id: "barbarian-weapon-2",
        label: "Escolha sua arma secundária",
        options: uniqueOptions([
          option("Machadinha x2", "Handaxe", "Handaxe"),
          ...simpleWeaponOptions,
        ]),
      },
    ],
  },
  bard: {
    fixedEquipment: ["Leather", "Dagger"],
    equipmentChoices: [
      { id: "bard-weapon", label: "Escolha sua arma inicial", options: uniqueOptions([option("Rapieira", "Rapier"), option("Espada Longa", "Longsword"), ...simpleWeaponOptions]) },
      { id: "bard-pack", label: "Escolha sua mochila", options: packOptions(["Mochila do Diplomata", "Diplomat's Pack"], ["Mochila do Artista", "Entertainer's Pack"]) },
      { id: "bard-instrument", label: "Escolha seu instrumento musical", options: musicalInstrumentOptions },
    ],
    startingSpells: { cantrips: 2, leveledSpells: 4, leveledMode: "known", levelOneSlots: 2 },
    toolProficiencyChoices: {
      count: 3,
      options: ["Alaúde", "Flauta", "Lira", "Tambor", "Viola", "Flauta de pã", "Gaita de foles", "Oboé", "Trompete", "Harpa"],
      label: "Escolha 3 instrumentos musicais (proficiência)",
    },
  },
  cleric: {
    fixedEquipment: ["Shield", "Holy Symbol"],
    equipmentChoices: [
      { id: "cleric-weapon", label: "Escolha sua arma de clérigo", options: [option("Maça", "Mace"), option("Martelo de Guerra", "Warhammer")] },
      { id: "cleric-armor", label: "Escolha sua armadura", options: [option("Brunea", "Scale Mail"), option("Couro", "Leather"), option("Cota de Malha", "Chain Mail")] },
      { id: "cleric-ranged", label: "Escolha sua arma secundária", options: [option("Besta Leve + 20 virotes", "Light Crossbow", "Crossbow bolt x20"), ...simpleWeaponOptions] },
      { id: "cleric-pack", label: "Escolha sua mochila", options: packOptions(["Mochila do Sacerdote", "Priest's Pack"], ["Mochila do Explorador", "Explorer's Pack"]) },
    ],
    startingSpells: { cantrips: 3, leveledSpells: 1, leveledMode: "prepared", preparationAbility: "wisdom", levelOneSlots: 2 },
  },
  druid: {
    fixedEquipment: ["Leather", "Druidic Focus"],
    equipmentChoices: [
      { id: "druid-shield", label: "Escolha um escudo ou arma simples", options: uniqueOptions([option("Escudo de Madeira", "Shield"), ...simpleWeaponOptions]) },
      { id: "druid-weapon", label: "Escolha sua arma de druida", options: uniqueOptions([option("Cimitarra", "Scimitar"), ...simpleMeleeWeaponOptions]) },
      { id: "druid-pack", label: "Escolha sua mochila", options: packOptions(["Mochila do Estudioso", "Scholar's Pack"], ["Mochila do Explorador", "Explorer's Pack"]) },
    ],
    startingSpells: { cantrips: 2, leveledSpells: 1, leveledMode: "prepared", preparationAbility: "wisdom", levelOneSlots: 2 },
  },
  fighter: {
    fixedEquipment: [],
    equipmentChoices: [
      {
        id: "fighter-armor",
        label: "Escolha seu pacote de armadura",
        options: [
          { id: "fighter-chain-mail", label: "Cota de Malha", items: ["Chain Mail"] },
          { id: "fighter-hide-longbow", label: "Gibão de Peles + Arco Longo + 20 flechas", items: ["Hide", "Longbow", "Arrow x20"] },
        ],
      },
      {
        id: "fighter-main-weapon",
        label: "Escolha seu conjunto de arma principal",
        options: [...martialWeaponWithShieldOptions, ...martialWeaponPairOptions],
      },
      {
        id: "fighter-ranged",
        label: "Escolha sua arma de alcance",
        options: [
          option("Besta Leve + 20 virotes", "Light Crossbow", "Crossbow bolt x20"),
          option("Machado de Arremesso x2", "Handaxe", "Handaxe"),
        ],
      },
      { id: "fighter-pack", label: "Escolha sua mochila", options: packOptions(["Mochila do Aventureiro", "Adventurer's Pack"], ["Mochila do Explorador", "Explorer's Pack"]) },
    ],
  },
  monk: {
    fixedEquipment: ["Dart x10"],
    equipmentChoices: [
      { id: "monk-weapon", label: "Escolha sua arma de monge", options: uniqueOptions([option("Espada Curta", "Shortsword"), ...simpleWeaponOptions]) },
      { id: "monk-pack", label: "Escolha sua mochila", options: packOptions(["Mochila do Explorador", "Explorer's Pack"], ["Mochila do Aventureiro", "Adventurer's Pack"]) },
    ],
    toolProficiencyChoices: {
      count: 1,
      label: "Escolha uma ferramenta de artesão ou instrumento musical (proficiência)",
      options: [
        "Ferramentas de Alquimista",
        "Ferramentas de Cervejeiro",
        "Ferramentas de Calígrafo",
        "Ferramentas de Carpinteiro",
        "Ferramentas de Cartógrafo",
        "Ferramentas de Sapateiro",
        "Utensílios de Cozinheiro",
        "Ferramentas de Vidraceiro",
        "Ferramentas de Joalheiro",
        "Ferramentas de Curtidor",
        "Ferramentas de Pedreiro",
        "Ferramentas de Pintor",
        "Ferramentas de Oleiro",
        "Ferramentas de Ferreiro",
        "Ferramentas de Funileiro",
        "Ferramentas de Tecedor",
        "Ferramentas de Escultor em Madeira",
        "Alaúde",
        "Flauta",
        "Lira",
        "Tambor",
        "Viola",
        "Flauta de Pã",
        "Gaita de Foles",
        "Oboé",
        "Trompete",
        "Harpa",
      ],
    },
  },
  paladin: {
    fixedEquipment: ["Chain Mail", "Holy Symbol"],
    equipmentChoices: [
      {
        id: "paladin-main-weapon",
        label: "Escolha seu conjunto de arma principal",
        options: [...martialWeaponWithShieldOptions, ...martialWeaponPairOptions],
      },
      {
        id: "paladin-secondary",
        label: "Escolha sua arma secundária",
        options: uniqueOptions([option("Dardo de Arremesso x5", "Javelin", "Javelin", "Javelin", "Javelin", "Javelin"), ...simpleMeleeWeaponOptions]),
      },
      { id: "paladin-pack", label: "Escolha sua mochila", options: packOptions(["Mochila do Sacerdote", "Priest's Pack"], ["Mochila do Aventureiro", "Adventurer's Pack"]) },
    ],
  },
  ranger: {
    fixedEquipment: ["Longbow", "Quiver", "Arrow x20"],
    equipmentChoices: [
      { id: "ranger-armor", label: "Escolha sua armadura", options: [option("Brunea", "Scale Mail"), option("Couro", "Leather")] },
      { id: "ranger-weapons", label: "Escolha suas armas corpo a corpo", options: uniqueOptions([option("Espada Curta x2", "Shortsword", "Shortsword"), ...simpleMeleePairOptions]) },
      { id: "ranger-pack", label: "Escolha sua mochila", options: packOptions(["Mochila do Explorador", "Explorer's Pack"], ["Mochila do Aventureiro", "Adventurer's Pack"]) },
    ],
  },
  guardian: {
    fixedEquipment: ["Breastplate", "Longbow", "Quiver", "Arrow x20", "Shortsword x2"],
    equipmentChoices: [],
    startingSpells: {
      minimumLevel: 2,
      cantrips: 0,
      leveledSpells: 2,
      leveledMode: "known",
      levelOneSlots: 2,
      fixedLeveledSpellCanonicalKeys: ["hunters_mark"],
      byLevel: {
        2:  { leveledSpells: 2,  levelOneSlots: 2 },
        3:  { leveledSpells: 3,  levelOneSlots: 3 },
        4:  { leveledSpells: 3,  levelOneSlots: 3 },
        5:  { leveledSpells: 4,  levelOneSlots: 4 },
        6:  { leveledSpells: 4,  levelOneSlots: 4 },
        7:  { leveledSpells: 5,  levelOneSlots: 4 },
        8:  { leveledSpells: 5,  levelOneSlots: 4 },
        9:  { leveledSpells: 6,  levelOneSlots: 4 },
        10: { leveledSpells: 6,  levelOneSlots: 4 },
      },
    },
  },
  rogue: {
    fixedEquipment: ["Leather", "Dagger x2", "Thieves' Tools"],
    equipmentChoices: [
      { id: "rogue-weapon", label: "Escolha sua arma principal", options: [option("Rapieira", "Rapier"), option("Espada Longa", "Longsword")] },
      {
        id: "rogue-secondary",
        label: "Escolha sua arma secundária",
        options: [
          option("Arco Curto + Aljava + 20 flechas", "Shortbow", "Quiver", "Arrow x20"),
          option("Espada Curta", "Shortsword"),
        ],
      },
      { id: "rogue-pack", label: "Escolha sua mochila", options: packOptions(["Mochila do Ladrão", "Burglar's Pack"], ["Mochila do Aventureiro", "Adventurer's Pack"], ["Mochila do Explorador", "Explorer's Pack"]) },
    ],
  },
  sorcerer: {
    fixedEquipment: ["Dagger x2"],
    equipmentChoices: [
      {
        id: "sorcerer-weapon",
        label: "Escolha sua arma inicial",
        options: [
          option("Besta Leve + 20 virotes", "Light Crossbow", "Crossbow bolt x20"),
          ...simpleWeaponOptions,
        ],
      },
      { id: "sorcerer-focus", label: "Escolha seu foco", options: packOptions(["Bolsa de Componentes", "Component Pouch"], ["Foco Arcano", "Arcane Focus"]) },
      { id: "sorcerer-pack", label: "Escolha sua mochila", options: packOptions(["Mochila do Explorador", "Explorer's Pack"], ["Mochila do Aventureiro", "Adventurer's Pack"]) },
    ],
    startingSpells: { cantrips: 4, leveledSpells: 2, leveledMode: "known", levelOneSlots: 2 },
  },
  warlock: {
    fixedEquipment: ["Leather", "Dagger x2"],
    equipmentChoices: [
      {
        id: "warlock-ranged",
        label: "Escolha sua opção de alcance",
        options: [
          option("Besta Leve + 20 virotes", "Light Crossbow", "Crossbow bolt x20"),
          ...simpleWeaponOptions,
        ],
      },
      { id: "warlock-focus", label: "Escolha seu foco", options: packOptions(["Bolsa de Componentes", "Component Pouch"], ["Foco Arcano", "Arcane Focus"]) },
      { id: "warlock-pack", label: "Escolha sua mochila", options: packOptions(["Mochila do Estudioso", "Scholar's Pack"], ["Mochila do Explorador", "Explorer's Pack"]) },
      { id: "warlock-bonus-weapon", label: "Escolha sua arma simples adicional", options: simpleWeaponOptions },
    ],
    startingSpells: { cantrips: 2, leveledSpells: 2, leveledMode: "known", levelOneSlots: 1 },
  },
  wizard: {
    fixedEquipment: ["Spellbook"],
    equipmentChoices: [
      { id: "wizard-weapon", label: "Escolha sua arma inicial", options: [option("Bordão", "Quarterstaff"), option("Adaga", "Dagger")] },
      { id: "wizard-focus", label: "Escolha seu foco", options: packOptions(["Bolsa de Componentes", "Component Pouch"], ["Foco Arcano", "Arcane Focus"]) },
      { id: "wizard-pack", label: "Escolha sua mochila", options: packOptions(["Mochila do Estudioso", "Scholar's Pack"], ["Mochila do Explorador", "Explorer's Pack"]) },
    ],
    startingSpells: { cantrips: 3, leveledSpells: 6, leveledMode: "spellbook", preparationAbility: "intelligence", levelOneSlots: 2 },
  },
};

export const getResolvedStaticClassCreationConfig = (
  className: string,
): ClassCreationConfig | undefined => {
  const config = CLASS_CREATION_CONFIG[className];
  return config ? resolveStaticConfigAgainstCatalog(config) : undefined;
};
