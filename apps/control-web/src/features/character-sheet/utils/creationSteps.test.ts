import { describe, expect, it } from "vitest";
import type { CreationValidationResult } from "./creationValidation";
import {
  canNavigateToStep,
  getFirstInvalidStepId,
  getStepMissingFields,
  getStepStatus,
  resolveReachableCreationStep,
} from "./creationSteps";

const validation = (
  missingRequiredFields: CreationValidationResult["missingRequiredFields"],
): CreationValidationResult => ({
  isValid: missingRequiredFields.length === 0,
  missingRequiredFields,
});

describe("creationSteps", () => {
  it("routes invalid review requests to the first invalid step", () => {
    expect(
      resolveReachableCreationStep(
        "review",
        validation(["class", "race"]),
      ),
    ).toBe("class");
  });

  it("keeps reachable requested steps", () => {
    expect(
      resolveReachableCreationStep(
        "class",
        validation(["race"]),
      ),
    ).toBe("class");
  });

  it("accepts review when validation is complete", () => {
    expect(resolveReachableCreationStep("review", validation([]))).toBe("review");
  });

  it("maps missing fields to their step", () => {
    expect(getStepMissingFields(validation(["class", "subclass", "race"]), "class")).toEqual([
      "class",
      "subclass",
    ]);
  });

  it("finds the first invalid step in order", () => {
    expect(getFirstInvalidStepId(validation(["classToolProficiencies"]))).toBe("abilities");
  });

  it("marks future steps as locked until previous invalid step is resolved", () => {
    expect(
      getStepStatus({
        stepId: "origin",
        currentStepId: "class",
        validation: validation(["class"]),
        context: "player-creation",
      }),
    ).toBe("locked");
  });

  it("marks previous invalid steps as error", () => {
    expect(
      getStepStatus({
        stepId: "class",
        currentStepId: "origin",
        validation: validation(["class"]),
        context: "player-creation",
      }),
    ).toBe("error");
  });

  it("allows navigation backwards even when future steps are locked", () => {
    expect(
      canNavigateToStep({
        targetStepId: "identity",
        currentStepId: "class",
        validation: validation(["class"]),
        context: "player-creation",
      }),
    ).toBe(true);
  });

  it("blocks navigation to locked future steps", () => {
    expect(
      canNavigateToStep({
        targetStepId: "loadout",
        currentStepId: "class",
        validation: validation(["background"]),
        context: "player-creation",
      }),
    ).toBe(false);
  });
});
