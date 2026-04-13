import { describe, expect, it } from "vitest";
import { encounterSnapshotResponseSchema } from "@limiarmap/shared-contracts";
import { InMemoryEncounterRepository } from "../../src/modules/encounters/encounter-repository";
import { ObstaclePaintService } from "../../src/modules/encounters/obstacle-paint-service";
import { toEncounterSnapshot } from "../../src/modules/encounters/encounter-snapshot";

describe("obstacle paint integration", () => {
  it("allows the GM to paint a movement-blocking circle", () => {
    const repository = new InMemoryEncounterRepository();
    const service = new ObstaclePaintService(repository);

    const result = service.paintObstacle(
      "demo-session",
      "gm",
      { x: 12, y: 9 },
      1,
      "paint",
      {
        blocksMovement: true,
        blocksEffect: false,
        blocksVision: false,
        cover: "none",
        clipsDiagonalMovement: true,
        movementCostMultiplier: 1
      },
      "obs-action-1"
    );

    expect(result.accepted).toBe(true);
    expect(result.encounter.obstacles.some((obstacle) => obstacle.label === "Passagem bloqueada")).toBe(true);
    expect(result.encounter.combatState.version).toBe(2);
  });

  it("rejects obstacle painting from non-GM actors", () => {
    const repository = new InMemoryEncounterRepository();
    const service = new ObstaclePaintService(repository);

    const result = service.paintObstacle(
      "demo-session",
      "player",
      { x: 12, y: 9 },
      1,
      "paint",
      {
        blocksMovement: true,
        blocksEffect: false,
        blocksVision: false,
        cover: "none",
        clipsDiagonalMovement: true,
        movementCostMultiplier: 1
      },
      "obs-action-2"
    );

    expect(result.accepted).toBe(false);
    expect(result.rejectionReason).toBe("not_gm");
  });

  it("can erase painted cells and returns the authoritative snapshot", () => {
    const repository = new InMemoryEncounterRepository();
    const service = new ObstaclePaintService(repository);

    service.paintObstacle(
      "demo-session",
      "gm",
      { x: 12, y: 9 },
      1,
      "paint",
      {
        blocksMovement: true,
        blocksEffect: false,
        blocksVision: false,
        cover: "none",
        clipsDiagonalMovement: true,
        movementCostMultiplier: 1
      },
      "obs-action-3"
    );

    const eraseResult = service.paintObstacle(
      "demo-session",
      "gm",
      { x: 12, y: 9 },
      0,
      "erase",
      undefined,
      "obs-action-4"
    );

    expect(eraseResult.accepted).toBe(true);
    expect(
      eraseResult.encounter.obstacles.some((obstacle) =>
        obstacle.cells.some((cell) => cell.x === 12 && cell.y === 9)
      )
    ).toBe(false);

    const snapshot = toEncounterSnapshot(repository.requireEncounter("demo-session"));
    expect(() => encounterSnapshotResponseSchema.parse(snapshot)).not.toThrow();
  });

  // --- Phase 6 preset label tests ---

  it("solid_wall preset produces label 'Parede solida'", () => {
    const repository = new InMemoryEncounterRepository();
    const service = new ObstaclePaintService(repository);

    const result = service.paintObstacle(
      "demo-session",
      "gm",
      { x: 5, y: 5 },
      0,
      "paint",
      {
        blocksMovement: true,
        blocksEffect: true,
        blocksVision: true,
        cover: "full",
        clipsDiagonalMovement: true,
      },
      "obs-solid-wall"
    );

    expect(result.accepted).toBe(true);
    expect(result.encounter.obstacles.some((o) => o.label === "Parede solida")).toBe(true);
  });

  it("dense_obstacle preset (blocksMovement + threeQuarters cover) produces label 'Obstaculo denso'", () => {
    const repository = new InMemoryEncounterRepository();
    const service = new ObstaclePaintService(repository);

    const result = service.paintObstacle(
      "demo-session",
      "gm",
      { x: 6, y: 5 },
      0,
      "paint",
      {
        blocksMovement: true,
        blocksEffect: false,
        blocksVision: false,
        cover: "threeQuarters",
        clipsDiagonalMovement: true,
      },
      "obs-dense"
    );

    expect(result.accepted).toBe(true);
    expect(result.encounter.obstacles.some((o) => o.label === "Obstaculo denso")).toBe(true);
  });

  it("barricade preset (half cover, no block flags) produces label 'Barricada'", () => {
    const repository = new InMemoryEncounterRepository();
    const service = new ObstaclePaintService(repository);

    const result = service.paintObstacle(
      "demo-session",
      "gm",
      { x: 7, y: 5 },
      0,
      "paint",
      {
        blocksMovement: false,
        blocksEffect: false,
        blocksVision: false,
        cover: "half",
        clipsDiagonalMovement: false,
      },
      "obs-barricade"
    );

    expect(result.accepted).toBe(true);
    expect(result.encounter.obstacles.some((o) => o.label === "Barricada")).toBe(true);
  });

  it("transparent_barrier preset (blocksMovement + blocksEffect, no vision) produces label 'Barreira transparente'", () => {
    const repository = new InMemoryEncounterRepository();
    const service = new ObstaclePaintService(repository);

    const result = service.paintObstacle(
      "demo-session",
      "gm",
      { x: 8, y: 5 },
      0,
      "paint",
      {
        blocksMovement: true,
        blocksEffect: true,
        blocksVision: false,
        cover: "none",
        clipsDiagonalMovement: false,
      },
      "obs-transparent"
    );

    expect(result.accepted).toBe(true);
    expect(result.encounter.obstacles.some((o) => o.label === "Barreira transparente")).toBe(true);
  });

  it("spell_blocker preset (blocksEffect only) produces label 'Barreira de efeito'", () => {
    const repository = new InMemoryEncounterRepository();
    const service = new ObstaclePaintService(repository);

    const result = service.paintObstacle(
      "demo-session",
      "gm",
      { x: 9, y: 5 },
      0,
      "paint",
      {
        blocksMovement: false,
        blocksEffect: true,
        blocksVision: false,
        cover: "none",
        clipsDiagonalMovement: false,
      },
      "obs-spell-blocker"
    );

    expect(result.accepted).toBe(true);
    expect(result.encounter.obstacles.some((o) => o.label === "Barreira de efeito")).toBe(true);
  });

  it("threeQuarters-cover-only obstacle (no movement block) produces label 'Cobertura 3/4'", () => {
    const repository = new InMemoryEncounterRepository();
    const service = new ObstaclePaintService(repository);

    const result = service.paintObstacle(
      "demo-session",
      "gm",
      { x: 10, y: 5 },
      0,
      "paint",
      {
        blocksMovement: false,
        blocksEffect: false,
        blocksVision: false,
        cover: "threeQuarters",
        clipsDiagonalMovement: false,
      },
      "obs-3q-cover-only"
    );

    expect(result.accepted).toBe(true);
    expect(result.encounter.obstacles.some((o) => o.label === "Cobertura 3/4")).toBe(true);
  });

  it("painted solid_wall carries full semantic fields through snapshot validation", () => {
    const repository = new InMemoryEncounterRepository();
    const service = new ObstaclePaintService(repository);

    service.paintObstacle(
      "demo-session",
      "gm",
      { x: 3, y: 3 },
      0,
      "paint",
      {
        blocksMovement: true,
        blocksEffect: true,
        blocksVision: true,
        cover: "full",
        clipsDiagonalMovement: true,
      },
      "obs-solid-snapshot"
    );

    const snapshot = toEncounterSnapshot(repository.requireEncounter("demo-session"));
    expect(() => encounterSnapshotResponseSchema.parse(snapshot)).not.toThrow();

    const obstacle = snapshot.obstacles.find((o) => o.label === "Parede solida");
    expect(obstacle).toBeDefined();
    expect(obstacle!.blocksMovement).toBe(true);
    expect(obstacle!.blocksEffect).toBe(true);
    expect(obstacle!.blocksVision).toBe(true);
    expect(obstacle!.cover).toBe("full");
  });

  it("painted dense_obstacle carries correct semantic fields through snapshot", () => {
    const repository = new InMemoryEncounterRepository();
    const service = new ObstaclePaintService(repository);

    service.paintObstacle(
      "demo-session",
      "gm",
      { x: 4, y: 3 },
      0,
      "paint",
      {
        blocksMovement: true,
        blocksEffect: false,
        blocksVision: false,
        cover: "threeQuarters",
        clipsDiagonalMovement: true,
      },
      "obs-dense-snapshot"
    );

    const snapshot = toEncounterSnapshot(repository.requireEncounter("demo-session"));
    const obstacle = snapshot.obstacles.find((o) => o.label === "Obstaculo denso");
    expect(obstacle).toBeDefined();
    expect(obstacle!.blocksMovement).toBe(true);
    expect(obstacle!.blocksEffect).toBe(false);
    expect(obstacle!.blocksVision).toBe(false);
    expect(obstacle!.cover).toBe("threeQuarters");
  });

  it("barricade carries cover=half and no block flags through snapshot", () => {
    const repository = new InMemoryEncounterRepository();
    const service = new ObstaclePaintService(repository);

    service.paintObstacle(
      "demo-session",
      "gm",
      { x: 5, y: 3 },
      0,
      "paint",
      {
        blocksMovement: false,
        blocksEffect: false,
        blocksVision: false,
        cover: "half",
        clipsDiagonalMovement: false,
      },
      "obs-barricade-snapshot"
    );

    const snapshot = toEncounterSnapshot(repository.requireEncounter("demo-session"));
    const obstacle = snapshot.obstacles.find((o) => o.label === "Barricada");
    expect(obstacle).toBeDefined();
    expect(obstacle!.blocksMovement).toBe(false);
    expect(obstacle!.blocksEffect).toBe(false);
    expect(obstacle!.cover).toBe("half");
  });
});
