import type {
  AbilityName,
  CharacterClassFeature,
  CharacterSheet,
} from "../model/characterSheet.types";
import { getDraconicLineageState } from "./draconicAncestry";

type FeatureDefinition = Omit<CharacterClassFeature, "levelGranted"> & {
  metadata?: Record<string, unknown> | null;
};

const normalizeClassId = (value: string | null | undefined) =>
  String(value ?? "").trim().toLowerCase();

const emptyAbilityBonuses = (): Record<AbilityName, number> => ({
  strength: 0,
  dexterity: 0,
  constitution: 0,
  intelligence: 0,
  wisdom: 0,
  charisma: 0,
});

const FEATURE_REGISTRY: Record<string, FeatureDefinition> = {
  favored_enemy_beasts: {
    id: "favored_enemy_beasts",
    source: "class",
    label: "Inimigo Favorito: Feras",
    description: "Inimigo favorito fixo do Guardião: feras.",
    kind: "passive",
    metadata: { favoredEnemy: "beasts" },
  },
  natural_explorer_forest: {
    id: "natural_explorer_forest",
    source: "class",
    label: "Explorador Natural: Floresta",
    description: "Terreno favorecido fixo do Guardião: floresta.",
    kind: "passive",
    metadata: { terrain: "forest" },
  },
  fighting_style_archery: {
    id: "fighting_style_archery",
    source: "class",
    label: "Estilo de Luta: Arqueria",
    description: "Recebe +2 em jogadas de ataque com armas à distância.",
    kind: "fighting_style",
    metadata: {
      fightingStyle: "archery",
      attackBonus: 2,
      appliesTo: "ranged_weapon_attacks",
    },
  },
  spellcasting_guardian: {
    id: "spellcasting_guardian",
    source: "class",
    label: "Conjuração",
    description: "Conjuração de Guardião baseada em Sabedoria.",
    kind: "spellcasting",
    metadata: {
      spellcastingAbility: "wisdom",
      mechanicsFamily: "ranger",
    },
  },
  primeval_awareness: {
    id: "primeval_awareness",
    source: "class",
    label: "Consciência Primitiva",
    description: "Consciência Primitiva conforme o material do Guardião.",
    kind: "passive",
    metadata: null,
  },
  subclass_hunter: {
    id: "subclass_hunter",
    source: "subclass",
    label: "Caçador",
    description: "Subclasse fixa do Guardião no nível 3.",
    kind: "subclass",
    metadata: { subclass: "hunter" },
  },
  hunter_colossus_slayer: {
    id: "hunter_colossus_slayer",
    source: "subclass",
    label: "Assassino de Colossos",
    description: "Uma vez por turno, ao atingir com arma um alvo já ferido, causa +1d8.",
    kind: "passive",
    metadata: {
      damageDice: "1d8",
      oncePerTurn: true,
      trigger: "weapon_hit_target_below_max_hp",
    },
  },
  asi_guardian_dexterity_2: {
    id: "asi_guardian_dexterity_2",
    source: "class",
    label: "Aumento de Atributo",
    description: "Aumenta Destreza em +2 no nível 4.",
    kind: "asi",
    metadata: { ability: "dexterity", bonus: 2 },
  },
  draconic_ancestry: {
    id: "draconic_ancestry",
    source: "subclass",
    label: "Ancestral Dracônico",
    description: "A linhagem dracônica define o tipo de dano e a resistência futura da subclasse.",
    kind: "subclass",
    metadata: null,
  },
  elemental_affinity: {
    id: "elemental_affinity",
    source: "subclass",
    label: "Afinidade Elemental",
    description: "Magias do tipo da linhagem ficam elegíveis ao bônus de Carisma e concedem resistência associada.",
    kind: "passive",
    metadata: null,
  },
};

export const resolveClassMechanicsFamily = (classId: string): string =>
  normalizeClassId(classId) === "guardian" ? "ranger" : normalizeClassId(classId);

export const getFixedSubclassForClassLevel = (
  classId: string,
  level: number,
): string | null => {
  if (normalizeClassId(classId) === "guardian" && level >= 3) {
    return "hunter";
  }
  return null;
};

export const getFixedFightingStyleForClassLevel = (
  classId: string,
  level: number,
): string | null => {
  if (normalizeClassId(classId) === "guardian" && level >= 2) {
    return "archery";
  }
  return null;
};

export const hasFixedSubclassAtLevel = (classId: string, level: number): boolean =>
  getFixedSubclassForClassLevel(classId, level) !== null;

export const hasFixedFightingStyleAtLevel = (classId: string, level: number): boolean =>
  getFixedFightingStyleForClassLevel(classId, level) !== null;

export const getClassLevelAbilityBonuses = (
  classId: string,
  level: number,
): Record<AbilityName, number> => {
  const bonuses = emptyAbilityBonuses();
  if (normalizeClassId(classId) === "guardian" && level >= 4) {
    bonuses.dexterity = 2;
  }
  return bonuses;
};

export const applyClassLevelAbilityBonuses = (
  abilities: CharacterSheet["abilities"],
  classId: string,
  level: number,
): CharacterSheet["abilities"] => {
  const bonuses = getClassLevelAbilityBonuses(classId, level);
  return {
    strength: abilities.strength + bonuses.strength,
    dexterity: abilities.dexterity + bonuses.dexterity,
    constitution: abilities.constitution + bonuses.constitution,
    intelligence: abilities.intelligence + bonuses.intelligence,
    wisdom: abilities.wisdom + bonuses.wisdom,
    charisma: abilities.charisma + bonuses.charisma,
  };
};

export const stripClassLevelAbilityBonuses = (
  abilities: CharacterSheet["abilities"],
  classId: string,
  level: number,
): CharacterSheet["abilities"] => {
  const bonuses = getClassLevelAbilityBonuses(classId, level);
  return {
    strength: abilities.strength - bonuses.strength,
    dexterity: abilities.dexterity - bonuses.dexterity,
    constitution: abilities.constitution - bonuses.constitution,
    intelligence: abilities.intelligence - bonuses.intelligence,
    wisdom: abilities.wisdom - bonuses.wisdom,
    charisma: abilities.charisma - bonuses.charisma,
  };
};

export const swapClassLevelAbilityBonuses = (
  abilities: CharacterSheet["abilities"],
  previousClassId: string,
  previousLevel: number,
  nextClassId: string,
  nextLevel: number,
): CharacterSheet["abilities"] =>
  applyClassLevelAbilityBonuses(
    stripClassLevelAbilityBonuses(abilities, previousClassId, previousLevel),
    nextClassId,
    nextLevel,
  );

const featureAtLevel = (id: keyof typeof FEATURE_REGISTRY, levelGranted: number): CharacterClassFeature => ({
  ...FEATURE_REGISTRY[id],
  levelGranted,
});

const buildDraconicAncestryFeature = (
  classId: string,
  level: number,
  subclass: string | null | undefined,
  subclassConfig: Record<string, string> | null | undefined,
): CharacterClassFeature | null => {
  const lineage = getDraconicLineageState({
    classId,
    subclass,
    level,
    subclassConfig,
  });
  if (!lineage.damageType || !lineage.ancestry) {
    return null;
  }

  return {
    ...featureAtLevel("draconic_ancestry", 1),
    label: `Ancestral Dracônico: ${lineage.ancestryLabel ?? lineage.ancestry}`,
    metadata: {
      ancestry: lineage.ancestry,
      damageType: lineage.damageType,
      resistanceType: lineage.resistanceType,
    },
  };
};

const buildElementalAffinityFeature = (
  classId: string,
  level: number,
  subclass: string | null | undefined,
  subclassConfig: Record<string, string> | null | undefined,
): CharacterClassFeature | null => {
  const lineage = getDraconicLineageState({
    classId,
    subclass,
    level,
    subclassConfig,
  });
  if (!lineage.hasElementalAffinity || !lineage.damageType || !lineage.resistanceType) {
    return null;
  }

  return {
    ...featureAtLevel("elemental_affinity", 6),
    metadata: {
      ancestry: lineage.ancestry,
      damageType: lineage.damageType,
      resistanceType: lineage.resistanceType,
      damageBonusAbility: "charisma",
      grantsResistanceAtLevel: 6,
    },
  };
};

export const buildClassFeatures = (
  classId: string,
  level: number,
  subclass: string | null | undefined,
  subclassConfig?: Record<string, string> | null | undefined,
): CharacterClassFeature[] => {
  const normalizedClassId = normalizeClassId(classId);
  const features: CharacterClassFeature[] = [];

  if (normalizedClassId === "guardian") {
    if (level >= 1) {
      features.push(featureAtLevel("favored_enemy_beasts", 1));
      features.push(featureAtLevel("natural_explorer_forest", 1));
    }
    if (level >= 2) {
      features.push(featureAtLevel("fighting_style_archery", 2));
      features.push(featureAtLevel("spellcasting_guardian", 2));
    }
    if (level >= 3) {
      features.push(featureAtLevel("primeval_awareness", 3));
      if ((subclass ?? getFixedSubclassForClassLevel(classId, level)) === "hunter") {
        features.push(featureAtLevel("subclass_hunter", 3));
        features.push(featureAtLevel("hunter_colossus_slayer", 3));
      }
    }
    if (level >= 4) {
      features.push(featureAtLevel("asi_guardian_dexterity_2", 4));
    }
    return features;
  }

  if (normalizedClassId === "sorcerer" && subclass === "draconic_bloodline") {
    const ancestryFeature = buildDraconicAncestryFeature(classId, level, subclass, subclassConfig);
    if (ancestryFeature) {
      features.push(ancestryFeature);
    }
    if (level >= 6) {
      const elementalAffinityFeature = buildElementalAffinityFeature(
        classId,
        level,
        subclass,
        subclassConfig,
      );
      if (elementalAffinityFeature) {
        features.push(elementalAffinityFeature);
      }
    }
  }

  return features;
};

export const hasClassFeature = (
  features: CharacterClassFeature[] | null | undefined,
  featureId: string,
): boolean => (features ?? []).some((feature) => feature.id === featureId);

export const applyCanonicalClassState = (
  sheet: CharacterSheet,
): CharacterSheet => {
  const fixedSubclass = getFixedSubclassForClassLevel(sheet.class, sheet.level);
  const fixedFightingStyle = getFixedFightingStyleForClassLevel(sheet.class, sheet.level);
  const subclass = fixedSubclass ?? sheet.subclass;
  const fightingStyle = fixedFightingStyle ?? sheet.fightingStyle;

  return {
    ...sheet,
    subclass,
    fightingStyle,
    classFeatures: buildClassFeatures(sheet.class, sheet.level, subclass, sheet.subclassConfig),
  };
};

export const isRangedWeaponAttack = ({
  rangeType,
  properties,
}: {
  rangeType?: string | null;
  properties?: string | null;
}): boolean => {
  if (rangeType === "ranged") {
    return true;
  }
  const normalizedProperties = String(properties ?? "").toLowerCase();
  return normalizedProperties.includes("ammunition") || normalizedProperties.includes("municao");
};

export const getFightingStyleAttackBonus = ({
  fightingStyle,
  rangeType,
  properties,
}: {
  fightingStyle?: string | null;
  rangeType?: string | null;
  properties?: string | null;
}): number => {
  if (fightingStyle !== "archery") {
    return 0;
  }
  return isRangedWeaponAttack({ rangeType, properties }) ? 2 : 0;
};
