// ── Ability & Skill Types ───────────────────────────────────────────────────

export type AbilityName =
  | "strength"
  | "dexterity"
  | "constitution"
  | "intelligence"
  | "wisdom"
  | "charisma";

export type SkillName =
  | "acrobatics"
  | "animalHandling"
  | "arcana"
  | "athletics"
  | "deception"
  | "history"
  | "insight"
  | "intimidation"
  | "investigation"
  | "medicine"
  | "nature"
  | "perception"
  | "performance"
  | "persuasion"
  | "religion"
  | "sleightOfHand"
  | "stealth"
  | "survival";

export type ProficiencyLevel = 0 | 0.5 | 1 | 2;

// ── Armor & Shield ──────────────────────────────────────────────────────────

export type ArmorType = "none" | "light" | "medium" | "heavy";

export type Armor = {
  name: string;
  baseAC: number;
  dexCap: number | null; // null = unlimited
  armorType: ArmorType;
  allowsDex?: boolean;
  stealthDisadvantage?: boolean;
  minStrength?: number | null;
};

export type Shield = {
  name: string;
  bonus: number;
};

// ── Weapon ──────────────────────────────────────────────────────────────────

export type Weapon = {
  id: string;
  name: string;
  ability: AbilityName;
  damageDice: string;
  damageType: string;
  proficient: boolean;
  magicBonus: number;
  properties: string;
  range: string;
};

// ── Inventory ───────────────────────────────────────────────────────────────

export type InventoryItem = {
  id: string;
  name: string;
  quantity: number;
  weight: number;
  notes: string;
  canonicalKey?: string | null;
  campaignItemId?: string | null;
  baseItemId?: string | null;
};

export type Currency = {
  copperValue: number;
};

// ── Spellcasting ────────────────────────────────────────────────────────────

export type SpellcastingMode = "known" | "prepared" | "spellbook";

export type Spell = {
  id: string;
  name: string;
  canonicalKey?: string | null;
  level: number; // 0 = cantrip
  school: string;
  prepared: boolean;
  notes: string;
};

export type SpellSlots = {
  max: number;
  used: number;
};

export type SpellcastingData = {
  ability: AbilityName;
  mode: SpellcastingMode;
  slots: Record<number, SpellSlots>; // keys 1-9
  spells: Spell[];
};

// ── Conditions ──────────────────────────────────────────────────────────────

export type ConditionName =
  | "blinded"
  | "charmed"
  | "deafened"
  | "frightened"
  | "grappled"
  | "incapacitated"
  | "invisible"
  | "paralyzed"
  | "petrified"
  | "poisoned"
  | "prone"
  | "restrained"
  | "stunned"
  | "unconscious";

// ── Death Saves ─────────────────────────────────────────────────────────────

export type DeathSaves = {
  successes: number; // 0-3
  failures: number; // 0-3
};

export type CharacterSheetMode = "creation" | "play";
export type RestState = "exploration" | "short_rest" | "long_rest";

// ── Character Sheet ─────────────────────────────────────────────────────────

export type CharacterSheet = {
  schemaVersion: number; // incrementar em migrações futuras

  // Basic info
  name: string;
  class: string;
  subclass: string | null;
  currentWeaponId: string | null;
  equippedArmorItemId: string | null;
  level: number;
  background: string;
  playerName: string;
  race: string;
  alignment: string;
  experiencePoints: number;
  restState: RestState;
  pendingLevelUp: boolean;
  inspiration: boolean;

  // Abilities
  abilities: Record<AbilityName, number>;
  savingThrowProficiencies: Record<AbilityName, boolean>;
  skillProficiencies: Record<SkillName, ProficiencyLevel>;

  // Combat
  equippedArmor: Armor;
  equippedShield: Shield | null;
  miscACBonus: number;
  speed: number;

  // HP
  maxHP: number;
  currentHP: number;
  tempHP: number;

  // Hit Dice
  hitDiceType: string;
  hitDiceTotal: number;
  hitDiceRemaining: number;

  // Death Saves
  deathSaves: DeathSaves;

  // Weapons
  weapons: Weapon[];

  // Inventory
  inventory: InventoryItem[];
  currency: Currency;

  // Spellcasting
  spellcasting: SpellcastingData | null;

  // Proficiencies & Languages
  languages: string[];
  toolProficiencies: string[];
  weaponProficiencies: string[];
  armorProficiencies: string[];

  // Conditions
  conditions: Record<ConditionName, boolean>;

  // Skill choices tracking
  classSkillChoices: SkillName[];
  classToolProficiencyChoices: string[];
  raceToolProficiencyChoices: string[];
  classEquipmentSelections: Record<string, string>;
  languageChoices: string[];
  /** Race-specific configuration choices (e.g. dragonborn ancestry). */
  raceConfig: {
    dragonbornAncestry?: string | null;
    gnomeSubrace?: string | null;
    halfElfAbilityChoices?: AbilityName[];
    halfElfSkillChoices?: SkillName[];
  } | null;
  /** Subclass-specific configuration choices (e.g. dragon ancestor for Draconic Bloodline). */
  subclassConfig: Record<string, string> | null;
  /** Fighting Style chosen at creation (Fighter lv1, Paladin/Ranger lv2). */
  fightingStyle: string | null;
  /** Skills chosen for Expertise (proficiency × 2) at creation (Rogue lv1, Bard lv3). */
  expertiseChoices: SkillName[];

  // Text fields
  featuresAndTraits: string;
  notes: string;
};
