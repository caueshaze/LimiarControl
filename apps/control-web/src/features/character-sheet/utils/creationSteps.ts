import type { CreationValidationResult, RequiredField } from "./creationValidation";

export type CreationFlowContext = "player-creation" | "gm-draft";

export type CreationStepId =
  | "identity"
  | "class"
  | "origin"
  | "abilities"
  | "loadout"
  | "review";

export type CreationStepStatus =
  | "locked"
  | "available"
  | "current"
  | "done"
  | "error";

export type CreationStepDefinition = {
  id: CreationStepId;
  fields: RequiredField[];
};

export const CREATION_STEP_ORDER: CreationStepId[] = [
  "identity",
  "class",
  "origin",
  "abilities",
  "loadout",
  "review",
];

export const CREATION_STEP_DEFINITIONS: CreationStepDefinition[] = [
  { id: "identity", fields: ["name", "playerName", "background", "alignment"] },
  { id: "class", fields: ["class", "subclass", "subclassConfig", "fightingStyle"] },
  { id: "origin", fields: ["race", "raceConfig", "languageChoices", "raceToolProficiency"] },
  { id: "abilities", fields: ["classSkills", "expertise", "classToolProficiencies"] },
  { id: "loadout", fields: ["equipmentChoices", "cantrips", "leveledSpells"] },
  { id: "review", fields: [] },
];

const STEP_DEFINITION_BY_ID = Object.fromEntries(
  CREATION_STEP_DEFINITIONS.map((step) => [step.id, step]),
) as Record<CreationStepId, CreationStepDefinition>;

const STEP_INDEX_BY_ID = Object.fromEntries(
  CREATION_STEP_ORDER.map((stepId, index) => [stepId, index]),
) as Record<CreationStepId, number>;

export const parseCreationStepId = (
  value: string | null | undefined,
): CreationStepId | null => {
  if (!value) {
    return null;
  }
  return CREATION_STEP_ORDER.includes(value as CreationStepId)
    ? (value as CreationStepId)
    : null;
};

export const getStepFields = (stepId: CreationStepId): RequiredField[] =>
  STEP_DEFINITION_BY_ID[stepId].fields;

export const getStepMissingFields = (
  validation: CreationValidationResult,
  stepId: CreationStepId,
): RequiredField[] => {
  const stepFields = new Set(getStepFields(stepId));
  return validation.missingRequiredFields.filter((field) => stepFields.has(field));
};

export const isStepComplete = (
  validation: CreationValidationResult,
  stepId: CreationStepId,
): boolean => getStepMissingFields(validation, stepId).length === 0;

export const getFirstInvalidStepId = (
  validation: CreationValidationResult,
): CreationStepId | null => {
  for (const stepId of CREATION_STEP_ORDER) {
    if (stepId === "review") {
      continue;
    }
    if (!isStepComplete(validation, stepId)) {
      return stepId;
    }
  }
  return null;
};

export const getLastReachableStepId = (
  validation: CreationValidationResult,
): CreationStepId => {
  const firstInvalidStep = getFirstInvalidStepId(validation);
  if (!firstInvalidStep) {
    return "review";
  }
  return firstInvalidStep;
};

export const resolveReachableCreationStep = (
  requestedStep: CreationStepId | null,
  validation: CreationValidationResult,
): CreationStepId => {
  const fallbackStep = getLastReachableStepId(validation);
  if (!requestedStep) {
    return fallbackStep;
  }

  const firstInvalidStep = getFirstInvalidStepId(validation);
  if (!firstInvalidStep) {
    return requestedStep;
  }

  return STEP_INDEX_BY_ID[requestedStep] <= STEP_INDEX_BY_ID[firstInvalidStep]
    ? requestedStep
    : firstInvalidStep;
};

export const getStepStatus = ({
  stepId,
  currentStepId,
  validation,
}: {
  stepId: CreationStepId;
  currentStepId: CreationStepId;
  validation: CreationValidationResult;
  context: CreationFlowContext;
}): CreationStepStatus => {
  if (stepId === currentStepId) {
    return "current";
  }

  const firstInvalidStep = getFirstInvalidStepId(validation);
  const currentIndex = STEP_INDEX_BY_ID[currentStepId];
  const stepIndex = STEP_INDEX_BY_ID[stepId];

  if (!firstInvalidStep) {
    return stepId === "review" || stepIndex < currentIndex ? "done" : "available";
  }

  const firstInvalidIndex = STEP_INDEX_BY_ID[firstInvalidStep];

  if (stepIndex < firstInvalidIndex) {
    return getStepMissingFields(validation, stepId).length > 0 ? "error" : "done";
  }

  if (stepIndex === firstInvalidIndex) {
    return getStepMissingFields(validation, stepId).length > 0 ? "error" : "available";
  }

  return "locked";
};

export const canNavigateToStep = ({
  targetStepId,
  currentStepId,
  validation,
}: {
  targetStepId: CreationStepId;
  currentStepId: CreationStepId;
  validation: CreationValidationResult;
  context: CreationFlowContext;
}): boolean => {
  const targetIndex = STEP_INDEX_BY_ID[targetStepId];
  const currentIndex = STEP_INDEX_BY_ID[currentStepId];

  if (targetIndex <= currentIndex) {
    return true;
  }

  return getStepStatus({
    stepId: targetStepId,
    currentStepId,
    validation,
    context: "player-creation",
  }) !== "locked";
};

export const getNextCreationStepId = (
  currentStepId: CreationStepId,
): CreationStepId | null => {
  const nextIndex = STEP_INDEX_BY_ID[currentStepId] + 1;
  return CREATION_STEP_ORDER[nextIndex] ?? null;
};

export const getPreviousCreationStepId = (
  currentStepId: CreationStepId,
): CreationStepId | null => {
  const previousIndex = STEP_INDEX_BY_ID[currentStepId] - 1;
  return CREATION_STEP_ORDER[previousIndex] ?? null;
};
