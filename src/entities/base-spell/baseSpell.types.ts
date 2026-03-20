import type { CampaignSystemType } from "../campaign";

export const SpellSchool = {
  ABJURATION: "abjuration",
  CONJURATION: "conjuration",
  DIVINATION: "divination",
  ENCHANTMENT: "enchantment",
  EVOCATION: "evocation",
  ILLUSION: "illusion",
  NECROMANCY: "necromancy",
  TRANSMUTATION: "transmutation",
} as const;

export type SpellSchool = (typeof SpellSchool)[keyof typeof SpellSchool];

export type BaseSpellAlias = {
  id: string;
  alias: string;
  locale?: string | null;
  aliasType?: string | null;
};

export type BaseSpell = {
  id: string;
  system: CampaignSystemType;
  canonicalKey: string;
  nameEn: string;
  namePt?: string | null;
  descriptionEn: string;
  descriptionPt?: string | null;
  level: number;
  school: SpellSchool;
  classesJson?: string[] | null;
  castingTime?: string | null;
  rangeText?: string | null;
  duration?: string | null;
  componentsJson?: string[] | null;
  materialComponentText?: string | null;
  concentration: boolean;
  ritual: boolean;
  damageType?: string | null;
  savingThrow?: string | null;
  source?: string | null;
  sourceRef?: string | null;
  isSrd: boolean;
  isActive: boolean;
  aliases: BaseSpellAlias[];
};

export type BaseSpellFilters = {
  system?: CampaignSystemType;
  level?: number;
  school?: SpellSchool;
  className?: string;
  canonicalKey?: string;
};
