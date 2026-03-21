import { CLASS_EQUIPMENT_RULES } from "./classEquipmentRules";
import { getCreationItemCatalog } from "../utils/creationItemCatalog";
import { resolveClassEquipmentRules } from "../utils/resolveClassEquipmentRules";
import { getResolvedStaticClassCreationConfig, CLASS_CREATION_CONFIG } from "./classCreation.config";
import type { ClassCreationConfig } from "./classCreation.types";
export type {
  ClassCreationConfig,
  ClassEquipmentChoiceGroup,
  ClassEquipmentOption,
  StartingSpellConfig,
  StartingSpellMode,
  ToolProficiencyChoiceConfig,
} from "./classCreation.types";

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
  const staticConfig = CLASS_CREATION_CONFIG[className];
  if (!staticConfig) {
    return undefined;
  }
  return getResolvedStaticClassCreationConfig(className);
};

export const describeDefaultClassStartingEquipment = (className: string): string[] => {
  const config = CLASS_CREATION_CONFIG[className];
  if (!config) {
    return [];
  }
  return [
    ...config.fixedEquipment,
    ...config.equipmentChoices.flatMap((group) => group.options[0]?.items ?? []),
  ];
};
