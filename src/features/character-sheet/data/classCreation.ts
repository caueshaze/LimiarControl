import type { AbilityName } from "../model/characterSheet.types";
import { getBaseWeapons } from "../../../entities/dnd-base";

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

export type StartingSpellMode = "known" | "prepared" | "spellbook";

export type StartingSpellConfig = {
  cantrips: number;
  leveledSpells: number;
  leveledMode: StartingSpellMode;
  preparationAbility?: AbilityName;
  levelOneSlots?: number;
};

export type ClassCreationConfig = {
  fixedEquipment: string[];
  equipmentChoices: ClassEquipmentChoiceGroup[];
  startingSpells?: StartingSpellConfig;
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
  filter: Parameters<typeof getBaseWeapons>[0],
): ClassEquipmentOption[] =>
  getBaseWeapons(filter).map((weapon) => ({
    id: slugify(weapon.name),
    label: weapon.name,
    items: [weapon.name],
  }));

const simpleWeaponOptions = weaponOptions({ category: "simple" });
const simpleMeleeWeaponOptions = weaponOptions({ category: "simple", kind: "melee" });
const martialWeaponOptions = weaponOptions({ category: "martial" });
const martialMeleeWeaponOptions = weaponOptions({ category: "martial", kind: "melee" });
const musicalInstrumentOptions = buildOptions(["Lute", "Flute", "Lyre", "Drum", "Viol", "Pan flute"]);
const simpleMeleePairOptions = simpleMeleeWeaponOptions.map((entry) =>
  option(`${entry.label} x2`, entry.label, entry.label),
);
const martialWeaponWithShieldOptions = martialWeaponOptions.map((entry) =>
  option(`${entry.label} + Escudo`, entry.label, "Escudo"),
);
const martialWeaponPairOptions = martialWeaponOptions.map((entry) =>
  option(`${entry.label} x2`, entry.label, entry.label),
);

const packOptions = (...labels: string[]) => buildOptions(labels);

export const CLASS_CREATION_CONFIG: Record<string, ClassCreationConfig> = {
  Barbarian: {
    fixedEquipment: ["Explorer's Pack", "Lança Curta (Dardo/Javelin) x4"],
    equipmentChoices: [
      { id: "barbarian-main-weapon", label: "Choose your main weapon", options: uniqueOptions(buildOptions(["Machado Grande"]).concat(martialMeleeWeaponOptions)) },
      { id: "barbarian-sidearm", label: "Choose your backup weapon", options: uniqueOptions(buildOptions(["Machado de Mão x2"]).concat(simpleWeaponOptions)) },
    ],
  },
  Bard: {
    fixedEquipment: ["Couro", "Adaga"],
    equipmentChoices: [
      { id: "bard-weapon", label: "Choose your starting weapon", options: uniqueOptions(buildOptions(["Rapieira", "Espada Longa"]).concat(simpleWeaponOptions)) },
      { id: "bard-pack", label: "Choose your pack", options: packOptions("Diplomat's Pack", "Entertainer's Pack") },
      { id: "bard-instrument", label: "Choose your instrument", options: musicalInstrumentOptions },
    ],
    startingSpells: { cantrips: 2, leveledSpells: 4, leveledMode: "known", levelOneSlots: 2 },
  },
  Cleric: {
    fixedEquipment: ["Escudo", "Holy Symbol"],
    equipmentChoices: [
      { id: "cleric-weapon", label: "Choose your cleric weapon", options: buildOptions(["Maça", "Martelo de Guerra"]) },
      { id: "cleric-armor", label: "Choose your armor", options: buildOptions(["Brunea", "Couro", "Cota de Malha"]) },
      { id: "cleric-ranged", label: "Choose your secondary weapon", options: [option("Besta Leve + Bolt x20", "Besta Leve", "Bolt x20"), ...simpleWeaponOptions] },
      { id: "cleric-pack", label: "Choose your pack", options: packOptions("Priest's Pack", "Explorer's Pack") },
    ],
    startingSpells: { cantrips: 3, leveledSpells: 1, leveledMode: "prepared", preparationAbility: "wisdom", levelOneSlots: 2 },
  },
  Druid: {
    fixedEquipment: ["Couro", "Druidic Focus"],
    equipmentChoices: [
      { id: "druid-shield", label: "Choose your defense", options: uniqueOptions(buildOptions(["Escudo"]).concat(simpleWeaponOptions)) },
      { id: "druid-weapon", label: "Choose your druid weapon", options: uniqueOptions(buildOptions(["Cimitarra"]).concat(simpleMeleeWeaponOptions)) },
    ],
    startingSpells: { cantrips: 2, leveledSpells: 1, leveledMode: "prepared", preparationAbility: "wisdom", levelOneSlots: 2 },
  },
  Fighter: {
    fixedEquipment: [],
    equipmentChoices: [
      {
        id: "fighter-armor",
        label: "Choose your armor package",
        options: [
          { id: "fighter-chain-mail", label: "Cota de Malha", items: ["Cota de Malha"] },
          { id: "fighter-leather-longbow", label: "Couro + Arco Longo + Arrow x20", items: ["Couro", "Arco Longo", "Arrow x20"] },
        ],
      },
      {
        id: "fighter-main-weapon",
        label: "Choose your primary weapon set",
        options: [...martialWeaponWithShieldOptions, ...martialWeaponPairOptions],
      },
      {
        id: "fighter-ranged",
        label: "Choose your ranged sidearm",
        options: [
          option("Besta Leve + Bolt x20", "Besta Leve", "Bolt x20"),
          option("Machado de Mão x2", "Machado de Mão x2"),
        ],
      },
      { id: "fighter-pack", label: "Choose your pack", options: packOptions("Dungeoneer's Pack", "Explorer's Pack") },
    ],
  },
  Monk: {
    fixedEquipment: ["Dart x10"],
    equipmentChoices: [
      { id: "monk-weapon", label: "Choose your monk weapon", options: uniqueOptions(buildOptions(["Espada Curta"]).concat(simpleWeaponOptions)) },
      { id: "monk-pack", label: "Choose your pack", options: packOptions("Dungeoneer's Pack", "Explorer's Pack") },
    ],
  },
  Paladin: {
    fixedEquipment: ["Cota de Malha", "Holy Symbol"],
    equipmentChoices: [
      {
        id: "paladin-main-weapon",
        label: "Choose your main weapon set",
        options: [...martialWeaponWithShieldOptions, ...martialWeaponPairOptions],
      },
      {
        id: "paladin-secondary",
        label: "Choose your secondary weapon",
        options: uniqueOptions(buildOptions(["Lança Curta (Dardo/Javelin) x5"]).concat(simpleMeleeWeaponOptions)),
      },
      { id: "paladin-pack", label: "Choose your pack", options: packOptions("Priest's Pack", "Explorer's Pack") },
    ],
  },
  Ranger: {
    fixedEquipment: ["Arco Longo", "Arrow x20"],
    equipmentChoices: [
      { id: "ranger-armor", label: "Choose your armor", options: buildOptions(["Brunea", "Couro"]) },
      { id: "ranger-weapons", label: "Choose your melee weapons", options: uniqueOptions([option("Espada Curta x2", "Espada Curta", "Espada Curta"), ...simpleMeleePairOptions]) },
      { id: "ranger-pack", label: "Choose your pack", options: packOptions("Dungeoneer's Pack", "Explorer's Pack") },
    ],
  },
  Rogue: {
    fixedEquipment: ["Couro", "Adaga x2", "Thieves' Tools"],
    equipmentChoices: [
      { id: "rogue-weapon", label: "Choose your main weapon", options: buildOptions(["Rapieira", "Espada Curta"]) },
      {
        id: "rogue-secondary",
        label: "Choose your secondary weapon",
        options: [
          option("Arco Curto + Arrow x20", "Arco Curto", "Arrow x20"),
          option("Espada Curta", "Espada Curta"),
        ],
      },
      { id: "rogue-pack", label: "Choose your pack", options: packOptions("Burglar's Pack", "Dungeoneer's Pack", "Explorer's Pack") },
    ],
  },
  Sorcerer: {
    fixedEquipment: ["Adaga x2"],
    equipmentChoices: [
      {
        id: "sorcerer-weapon",
        label: "Choose your starting weapon",
        options: [
          option("Besta Leve + Bolt x20", "Besta Leve", "Bolt x20"),
          ...simpleWeaponOptions,
        ],
      },
      { id: "sorcerer-focus", label: "Choose your focus", options: packOptions("Component Pouch", "Arcane Focus") },
      { id: "sorcerer-pack", label: "Choose your pack", options: packOptions("Dungeoneer's Pack", "Explorer's Pack") },
    ],
    startingSpells: { cantrips: 4, leveledSpells: 2, leveledMode: "known", levelOneSlots: 2 },
  },
  Warlock: {
    fixedEquipment: ["Couro", "Adaga x2"],
    equipmentChoices: [
      {
        id: "warlock-ranged",
        label: "Choose your ranged option",
        options: [
          option("Besta Leve + Bolt x20", "Besta Leve", "Bolt x20"),
          ...simpleWeaponOptions,
        ],
      },
      { id: "warlock-focus", label: "Choose your focus", options: packOptions("Component Pouch", "Arcane Focus") },
      { id: "warlock-pack", label: "Choose your pack", options: packOptions("Scholar's Pack", "Dungeoneer's Pack") },
      { id: "warlock-bonus-weapon", label: "Choose your bonus simple weapon", options: simpleWeaponOptions },
    ],
    startingSpells: { cantrips: 2, leveledSpells: 2, leveledMode: "known", levelOneSlots: 1 },
  },
  Wizard: {
    fixedEquipment: ["Spellbook"],
    equipmentChoices: [
      { id: "wizard-weapon", label: "Choose your starting weapon", options: buildOptions(["Cajado", "Adaga"]) },
      { id: "wizard-focus", label: "Choose your focus", options: packOptions("Component Pouch", "Arcane Focus") },
      { id: "wizard-pack", label: "Choose your pack", options: packOptions("Scholar's Pack", "Explorer's Pack") },
    ],
    startingSpells: { cantrips: 3, leveledSpells: 6, leveledMode: "spellbook", preparationAbility: "intelligence", levelOneSlots: 2 },
  },
};

export const getClassCreationConfig = (className: string) =>
  CLASS_CREATION_CONFIG[className];
