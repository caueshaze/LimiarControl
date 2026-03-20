import type { AbilityName, SpellcastingMode } from "../model/characterSheet.types";
import { getCreationWeapons } from "./creationWeapons";
import { CLASS_EQUIPMENT_RULES } from "./classEquipmentRules";
import { getCreationItemCatalog } from "../utils/creationItemCatalog";
import { resolveClassEquipmentRules } from "../utils/resolveClassEquipmentRules";

// Source of truth for class-based starting equipment during character creation.
// The creation flow derives its loadout from this file, not from classes.ts.
export type ClassEquipmentOption = {
  id: string;
  label: string;
  items: string[];
};

export type ClassEquipmentChoiceGroup = {
  id: string;
  label: string;
  options: ClassEquipmentOption[];
};

/** @deprecated Use `SpellcastingMode` from characterSheet.types.ts */
export type StartingSpellMode = SpellcastingMode;

export type StartingSpellConfig = {
  cantrips: number;
  leveledSpells: number;
  leveledMode: SpellcastingMode;
  preparationAbility?: AbilityName;
  levelOneSlots?: number;
};

export type ToolProficiencyChoiceConfig = {
  count: number;
  options: string[];
  label: string;
};

export type ClassCreationConfig = {
  fixedEquipment: string[];
  equipmentChoices: ClassEquipmentChoiceGroup[];
  startingSpells?: StartingSpellConfig;
  toolProficiencyChoices?: ToolProficiencyChoiceConfig;
};

const slugify = (value: string) =>
  value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");

const buildOptions = (labels: string[]) =>
  labels.map((label) => ({ id: slugify(label), label, items: [label] }));

const option = (label: string, ...items: string[]): ClassEquipmentOption => ({
  id: slugify(label),
  label,
  items,
});

const uniqueOptions = (options: ClassEquipmentOption[]) => {
  const seen = new Set<string>();
  return options.filter((option) => {
    const key = option.label.toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
};

const weaponOptions = (
  filter: Parameters<typeof getCreationWeapons>[0],
): ClassEquipmentOption[] =>
  getCreationWeapons(filter).map((weapon) => ({
    id: slugify(weapon.label),
    label: weapon.label,
    items: [weapon.name],
  }));

const simpleWeaponOptions = weaponOptions({ category: "simple" });
const simpleMeleeWeaponOptions = weaponOptions({ category: "simple", kind: "melee" });
const martialWeaponOptions = weaponOptions({ category: "martial" });
const martialMeleeWeaponOptions = weaponOptions({ category: "martial", kind: "melee" });
const musicalInstrumentOptions = buildOptions(["Alaúde", "Flauta", "Lira", "Tambor", "Viola", "Flauta de pã"]);
const simpleMeleePairOptions = simpleMeleeWeaponOptions.map((entry) =>
  option(`${entry.label} x2`, entry.label, entry.label),
);
const martialWeaponWithShieldOptions = martialWeaponOptions.map((entry) =>
  option(`${entry.label} + Escudo`, entry.label, "Shield"),
);
const martialWeaponPairOptions = martialWeaponOptions.map((entry) =>
  option(`${entry.label} x2`, entry.label, entry.label),
);

// pack: label shown to user, englishKey: functional item name passed to canonicalization
const pack = (label: string, englishKey: string): ClassEquipmentOption => ({
  id: slugify(englishKey),
  label,
  items: [englishKey],
});
const packOptions = (...pairs: [string, string][]) => pairs.map(([label, key]) => pack(label, key));

export const CLASS_CREATION_CONFIG: Record<string, ClassCreationConfig> = {
  // PHB p.48: (a) machado grande ou (b) qualquer marcial corpo-a-corpo
  //           (a) dois machados de mão ou (b) qualquer simples
  //           pacote de aventureiro + 4 azagaias (fixo)
  barbarian: {
    fixedEquipment: ["Explorer's Pack", "Javelin x4"],
    equipmentChoices: [
      {
        id: "barbarian-weapon-1",
        label: "Escolha 1: Arma principal",
        options: martialMeleeWeaponOptions,
      },
      {
        id: "barbarian-weapon-2",
        label: "Escolha 2: Arma secundária",
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
    fixedEquipment: ["Leather", "Explorer's Pack", "Druidic Focus"],
    equipmentChoices: [
      { id: "druid-shield", label: "Escolha sua defesa", options: uniqueOptions([option("Escudo de Madeira", "Shield"), ...simpleWeaponOptions]) },
      { id: "druid-weapon", label: "Escolha sua arma de druida", options: uniqueOptions([option("Cimitarra", "Scimitar"), ...simpleMeleeWeaponOptions]) },
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
          { id: "fighter-leather-longbow", label: "Couro + Arco Longo + 20 flechas", items: ["Leather", "Longbow", "Arrow x20"] },
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
          option("Machadinha x2", "Handaxe", "Handaxe"),
        ],
      },
      { id: "fighter-pack", label: "Escolha sua mochila", options: packOptions(["Mochila do Masmorrador", "Dungeoneer's Pack"], ["Mochila do Explorador", "Explorer's Pack"]) },
    ],
  },
  monk: {
    fixedEquipment: ["Dart x10"],
    equipmentChoices: [
      { id: "monk-weapon", label: "Escolha sua arma de monge", options: uniqueOptions([option("Espada Curta", "Shortsword"), ...simpleWeaponOptions]) },
      { id: "monk-pack", label: "Escolha sua mochila", options: packOptions(["Mochila do Masmorrador", "Dungeoneer's Pack"], ["Mochila do Explorador", "Explorer's Pack"]) },
    ],
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
      { id: "paladin-pack", label: "Escolha sua mochila", options: packOptions(["Mochila do Sacerdote", "Priest's Pack"], ["Mochila do Explorador", "Explorer's Pack"]) },
    ],
  },
  ranger: {
    fixedEquipment: ["Longbow", "Quiver", "Arrow x20"],
    equipmentChoices: [
      { id: "ranger-armor", label: "Escolha sua armadura", options: [option("Brunea", "Scale Mail"), option("Couro", "Leather")] },
      { id: "ranger-weapons", label: "Escolha suas armas corpo a corpo", options: uniqueOptions([option("Espada Curta x2", "Shortsword", "Shortsword"), ...simpleMeleePairOptions]) },
      { id: "ranger-pack", label: "Escolha sua mochila", options: packOptions(["Mochila do Masmorrador", "Dungeoneer's Pack"], ["Mochila do Explorador", "Explorer's Pack"]) },
    ],
  },
  rogue: {
    fixedEquipment: ["Leather", "Dagger x2", "Thieves' Tools"],
    equipmentChoices: [
      { id: "rogue-weapon", label: "Escolha sua arma principal", options: [option("Rapieira", "Rapier"), option("Espada Curta", "Shortsword")] },
      {
        id: "rogue-secondary",
        label: "Escolha sua arma secundária",
        options: [
          option("Arco Curto + Aljava + 20 flechas", "Shortbow", "Quiver", "Arrow x20"),
          option("Espada Curta", "Shortsword"),
        ],
      },
      { id: "rogue-pack", label: "Escolha sua mochila", options: packOptions(["Mochila do Ladrão", "Burglar's Pack"], ["Mochila do Masmorrador", "Dungeoneer's Pack"], ["Mochila do Explorador", "Explorer's Pack"]) },
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
      { id: "sorcerer-pack", label: "Escolha sua mochila", options: packOptions(["Mochila do Masmorrador", "Dungeoneer's Pack"], ["Mochila do Explorador", "Explorer's Pack"]) },
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
      { id: "warlock-pack", label: "Escolha sua mochila", options: packOptions(["Mochila do Estudioso", "Scholar's Pack"], ["Mochila do Masmorrador", "Dungeoneer's Pack"]) },
      { id: "warlock-bonus-weapon", label: "Escolha sua arma simples adicional", options: simpleWeaponOptions },
    ],
    startingSpells: { cantrips: 2, leveledSpells: 2, leveledMode: "known", levelOneSlots: 1 },
  },
  wizard: {
    fixedEquipment: ["Spellbook"],
    equipmentChoices: [
      { id: "wizard-weapon", label: "Escolha sua arma inicial", options: [option("Cajado", "Quarterstaff"), option("Adaga", "Dagger")] },
      { id: "wizard-focus", label: "Escolha seu foco", options: packOptions(["Bolsa de Componentes", "Component Pouch"], ["Foco Arcano", "Arcane Focus"]) },
      { id: "wizard-pack", label: "Escolha sua mochila", options: packOptions(["Mochila do Estudioso", "Scholar's Pack"], ["Mochila do Explorador", "Explorer's Pack"]) },
    ],
    startingSpells: { cantrips: 3, leveledSpells: 6, leveledMode: "spellbook", preparationAbility: "intelligence", levelOneSlots: 2 },
  },
};

export const getClassCreationConfig = (className: string): ClassCreationConfig | undefined => {
  // Try DB-driven rules first (currently Barbarian only)
  const rules = CLASS_EQUIPMENT_RULES[className];
  if (rules) {
    const catalog = getCreationItemCatalog();
    const resolved = resolveClassEquipmentRules(rules, catalog);
    if (resolved) {
      // Merge with static config to preserve startingSpells if defined
      const staticConfig = CLASS_CREATION_CONFIG[className];
      return staticConfig?.startingSpells
        ? { ...resolved, startingSpells: staticConfig.startingSpells }
        : resolved;
    }
  }

  // Fallback to static config
  return CLASS_CREATION_CONFIG[className];
};

export const describeDefaultClassStartingEquipment = (className: string): string[] => {
  const config = getClassCreationConfig(className);
  if (!config) {
    return [];
  }
  return [
    ...config.fixedEquipment,
    ...config.equipmentChoices.flatMap((group) => group.options[0]?.items ?? []),
  ];
};
