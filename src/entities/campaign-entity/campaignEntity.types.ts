export type EntityCategory = "npc" | "enemy" | "creature" | "ally";
export type AbilityName =
  | "strength"
  | "dexterity"
  | "constitution"
  | "intelligence"
  | "wisdom"
  | "charisma";
export type CombatActionKind = "weapon_attack" | "spell_attack" | "saving_throw" | "heal" | "utility";
export type EntitySize = "tiny" | "small" | "medium" | "large" | "huge" | "gargantuan";
export type CreatureType =
  | "aberration"
  | "beast"
  | "celestial"
  | "construct"
  | "dragon"
  | "elemental"
  | "fey"
  | "fiend"
  | "giant"
  | "humanoid"
  | "monstrosity"
  | "ooze"
  | "plant"
  | "undead";
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
export type DamageType =
  | "acid"
  | "bludgeoning"
  | "cold"
  | "fire"
  | "force"
  | "lightning"
  | "necrotic"
  | "piercing"
  | "poison"
  | "psychic"
  | "radiant"
  | "slashing"
  | "thunder";
export type ConditionType =
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

export type AbilityScores = Record<AbilityName, number>;
export type SavingThrowBonuses = Partial<Record<AbilityName, number | null>>;
export type SkillBonuses = Partial<Record<SkillName, number | null>>;

export type EntitySenses = {
  darkvisionMeters?: number | null;
  blindsightMeters?: number | null;
  tremorsenseMeters?: number | null;
  truesightMeters?: number | null;
  passivePerception?: number | null;
};

export type EntitySpellcasting = {
  ability?: AbilityName | null;
  saveDc?: number | null;
  attackBonus?: number | null;
};

export type CombatAction = {
  id: string;
  name: string;
  kind: CombatActionKind;
  campaignItemId?: string | null;
  weaponCanonicalKey?: string | null;
  spellCanonicalKey?: string | null;
  toHitBonus?: number | null;
  spellAttackBonus?: number | null;
  damageDice?: string | null;
  damageBonus?: number | null;
  damageType?: DamageType | null;
  rangeMeters?: number | null;
  isMelee?: boolean | null;
  saveAbility?: AbilityName | null;
  saveDc?: number | null;
  castAtLevel?: number | null;
  healDice?: string | null;
  healBonus?: number | null;
  description?: string | null;
  actionCost?: "action" | "bonus_action" | "reaction" | "free";
};

export type CampaignEntity = {
  id: string;
  campaignId: string;
  name: string;
  category: EntityCategory;
  size?: EntitySize | null;
  creatureType?: CreatureType | null;
  creatureSubtype?: string | null;
  description?: string | null;
  imageUrl?: string | null;
  armorClass?: number | null;
  maxHp?: number | null;
  speedMeters?: number | null;
  initiativeBonus?: number | null;
  abilities: AbilityScores;
  savingThrows: SavingThrowBonuses;
  skills: SkillBonuses;
  senses?: EntitySenses | null;
  spellcasting?: EntitySpellcasting | null;
  damageResistances: DamageType[];
  damageImmunities: DamageType[];
  damageVulnerabilities: DamageType[];
  conditionImmunities: ConditionType[];
  combatActions: CombatAction[];
  actions?: string | null;
  notesPrivate?: string | null;
  notesPublic?: string | null;
  createdAt: string;
  updatedAt?: string | null;
};

export type CampaignEntityPublic = Omit<CampaignEntity, "notesPrivate">;

export type CampaignEntityPayload = Omit<CampaignEntity, "id" | "campaignId" | "createdAt" | "updatedAt">;
