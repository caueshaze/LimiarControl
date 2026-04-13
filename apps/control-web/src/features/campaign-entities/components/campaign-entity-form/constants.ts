import { nanoid } from "nanoid";
import {
  EMPTY_ENTITY_ABILITIES,
  ENTITY_ABILITIES,
  ENTITY_CREATURE_TYPES,
  ENTITY_DAMAGE_TYPES,
  ENTITY_SIZES,
  ENTITY_SKILLS,
  type AbilityName,
  type CampaignEntity,
  type CampaignEntityPayload,
  type CombatAction,
  type CombatActionKind,
  type CreatureType,
  type DamageType,
  type EntityCategory,
  type EntitySize,
  type SkillName,
} from "../../../../entities/campaign-entity";

export const CATEGORIES: EntityCategory[] = ["npc", "enemy", "creature", "ally"];
export const ACTION_KINDS: CombatActionKind[] = [
  "weapon_attack",
  "spell_attack",
  "saving_throw",
  "heal",
  "utility",
];

export const sectionClass =
  "rounded-3xl border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.78),rgba(2,6,23,0.94))] p-4 sm:p-5 lg:p-6 shadow-[0_20px_60px_rgba(2,6,23,0.16)]";
export const fieldClass =
  "w-full rounded-2xl border border-white/10 bg-slate-950/80 px-4 py-3 text-sm text-slate-100 shadow-[0_10px_25px_rgba(2,6,23,0.18)] transition focus:border-emerald-300/40 focus:outline-none placeholder:text-slate-500";
export const rowDisplayClass =
  "rounded-2xl border border-white/8 bg-white/3 px-4 py-3 text-sm text-slate-200";

export const isAbilityName = (value: string | null | undefined): value is AbilityName =>
  ENTITY_ABILITIES.some((ability) => ability.key === value);

export const isSkillName = (value: string | null | undefined): value is SkillName =>
  ENTITY_SKILLS.some((skill) => skill.key === value);

export const isDamageType = (value: string | null | undefined): value is DamageType =>
  ENTITY_DAMAGE_TYPES.some((entry) => entry.key === value);

export const isEntitySize = (value: string | null | undefined): value is EntitySize =>
  ENTITY_SIZES.some((size) => size.key === value);

export const isCreatureType = (value: string | null | undefined): value is CreatureType =>
  ENTITY_CREATURE_TYPES.some((type) => type.key === value);

export const createCombatAction = (): CombatAction => ({
  id: nanoid(),
  name: "",
  kind: "weapon_attack",
  campaignItemId: null,
  weaponCanonicalKey: null,
  spellCanonicalKey: null,
  toHitBonus: null,
  spellAttackBonus: null,
  damageDice: "",
  damageBonus: null,
  damageType: null,
  rangeMeters: null,
  isMelee: null,
  saveAbility: null,
  saveDc: null,
  castAtLevel: null,
  healDice: "",
  healBonus: null,
  description: "",
});

export const emptyPayload = (): CampaignEntityPayload => ({
  name: "",
  category: "npc",
  size: null,
  creatureType: null,
  creatureSubtype: "",
  description: "",
  imageUrl: "",
  armorClass: null,
  maxHp: null,
  speedMeters: null,
  initiativeBonus: null,
  abilities: { ...EMPTY_ENTITY_ABILITIES },
  savingThrows: {},
  skills: {},
  senses: null,
  spellcasting: null,
  damageResistances: [],
  damageImmunities: [],
  damageVulnerabilities: [],
  conditionImmunities: [],
  combatActions: [],
  actions: "",
  notesPrivate: "",
  notesPublic: "",
});

export const createInitialPayload = (initial?: CampaignEntity | null): CampaignEntityPayload =>
  initial
    ? {
        name: initial.name,
        category: initial.category,
        size: initial.size ?? null,
        creatureType: initial.creatureType ?? null,
        creatureSubtype: initial.creatureSubtype ?? "",
        description: initial.description ?? "",
        imageUrl: initial.imageUrl ?? "",
        armorClass: initial.armorClass ?? null,
        maxHp: initial.maxHp ?? null,
        speedMeters: initial.speedMeters ?? null,
        initiativeBonus: initial.initiativeBonus ?? null,
        abilities: initial.abilities ?? { ...EMPTY_ENTITY_ABILITIES },
        savingThrows: initial.savingThrows ?? {},
        skills: initial.skills ?? {},
        senses: initial.senses ?? null,
        spellcasting: initial.spellcasting ?? null,
        damageResistances: initial.damageResistances ?? [],
        damageImmunities: initial.damageImmunities ?? [],
        damageVulnerabilities: initial.damageVulnerabilities ?? [],
        conditionImmunities: initial.conditionImmunities ?? [],
        combatActions: initial.combatActions ?? [],
        actions: initial.actions ?? "",
        notesPrivate: initial.notesPrivate ?? "",
        notesPublic: initial.notesPublic ?? "",
      }
    : emptyPayload();

export const hasAdvancedData = (initial?: CampaignEntity | null) =>
  Boolean(
    initial?.size ||
      initial?.creatureType ||
      initial?.creatureSubtype ||
      Object.keys(initial?.savingThrows ?? {}).length > 0 ||
      Object.keys(initial?.skills ?? {}).length > 0 ||
      initial?.senses ||
      initial?.spellcasting ||
      (initial?.damageResistances?.length ?? 0) > 0 ||
      (initial?.damageImmunities?.length ?? 0) > 0 ||
      (initial?.damageVulnerabilities?.length ?? 0) > 0 ||
      (initial?.conditionImmunities?.length ?? 0) > 0,
  );
