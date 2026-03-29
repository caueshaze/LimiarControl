import { BACKGROUNDS } from "../data/backgrounds";
import { CLASS_CREATION_CONFIG } from "../data/classCreation.config";
import { CLASSES } from "../data/classes";
import { RACE_DEFINITIONS } from "../data/raceDefinitions";
import {
  getCreationCatalogItemsSorted,
  getWeaponsFromCatalog,
} from "./creationItemCatalog";

const normalizeLabel = (value: string) => value.trim();

const uniqueSorted = (values: string[]) =>
  [...new Set(values.map(normalizeLabel).filter(Boolean))].sort((a, b) =>
    a.localeCompare(b, "pt-BR"),
  );

const stripToolFeaturePrefix = (label: string) =>
  label.replace(/^Profici[eê]ncia:\s*/i, "").trim();

const getRaceToolFeatureLabels = () => {
  const toolLabels: string[] = [];

  for (const race of RACE_DEFINITIONS) {
    for (const feature of race.structuredFeatures ?? []) {
      if (feature.kind === "tool_proficiency") {
        toolLabels.push(stripToolFeaturePrefix(feature.label));
      }
    }

    for (const variant of Object.values(race.variants ?? {})) {
      for (const feature of variant.structuredFeatures ?? []) {
        if (feature.kind === "tool_proficiency") {
          toolLabels.push(stripToolFeaturePrefix(feature.label));
        }
      }
    }
  }

  return toolLabels;
};

export const getDraftToolProficiencyOptions = () =>
  uniqueSorted([
    ...BACKGROUNDS.flatMap((background) => background.toolProficiencies),
    ...Object.values(CLASS_CREATION_CONFIG).flatMap(
      (config) => config.toolProficiencyChoices?.options ?? [],
    ),
    ...RACE_DEFINITIONS.flatMap((race) => race.toolProficiencyChoices?.options ?? []),
    ...getRaceToolFeatureLabels(),
  ]);

export const getDraftWeaponProficiencyOptions = () =>
  uniqueSorted([
    ...CLASSES.flatMap((cls) => cls.weaponProficiencies),
    ...RACE_DEFINITIONS.flatMap((race) => race.weaponProficiencies ?? []),
    ...RACE_DEFINITIONS.flatMap((race) =>
      Object.values(race.variants ?? {}).flatMap((variant) => variant.weaponProficiencies ?? []),
    ),
    ...getWeaponsFromCatalog().map((item) => item.namePt || item.name),
  ]);

export const getDraftArmorProficiencyOptions = () =>
  uniqueSorted([
    ...CLASSES.flatMap((cls) => cls.armorProficiencies),
    ...RACE_DEFINITIONS.flatMap((race) => race.armorProficiencies ?? []),
    ...RACE_DEFINITIONS.flatMap((race) =>
      Object.values(race.variants ?? {}).flatMap((variant) => variant.armorProficiencies ?? []),
    ),
    ...getCreationCatalogItemsSorted()
      .filter((item) => item.itemKind === "armor")
      .map((item) => item.namePt || item.name),
  ]);
