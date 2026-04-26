import { describe, expect, it } from "vitest";
import { buildSpellMapPreviewHighlights } from "./spellMapPreviewHighlights";
import type { SpellMapPreviewModel } from "./spellMapPreviewModel";

const baseSingleTarget: SpellMapPreviewModel = {
  status: "valid",
  reason: null,
  rangeMeters: 36,
  areaShape: null,
  areaSizeMeters: null,
  effectInstanceCount: 1,
};

const baseMultiInstance: SpellMapPreviewModel = {
  status: "valid",
  rangeMeters: 36,
  areaShape: null,
  areaSizeMeters: null,
  effectInstanceCount: 3,
  instanceStatuses: [
    { instanceIndex: 1, targetRefId: "goblin-a", status: "valid" },
    { instanceIndex: 2, targetRefId: "goblin-a", status: "valid" },
    { instanceIndex: 3, targetRefId: "orc-b", status: "valid" },
  ],
};

describe("buildSpellMapPreviewHighlights – single-target", () => {
  it("emite highlight target valid quando alvo está no alcance", () => {
    const highlights = buildSpellMapPreviewHighlights(baseSingleTarget, "enemy-1");

    expect(highlights).toHaveLength(1);
    expect(highlights[0]).toMatchObject({
      kind: "target",
      status: "valid",
      targetRefId: "enemy-1",
    });
  });

  it("emite highlight target invalid com reason quando fora de alcance", () => {
    const model: SpellMapPreviewModel = {
      ...baseSingleTarget,
      status: "invalid",
      reason: "out_of_range",
    };

    const highlights = buildSpellMapPreviewHighlights(model, "enemy-1");

    expect(highlights).toHaveLength(1);
    expect(highlights[0]).toMatchObject({
      kind: "target",
      status: "invalid",
      targetRefId: "enemy-1",
      reason: "out_of_range",
    });
  });

  it("retorna lista vazia quando não há targetRefId", () => {
    const highlights = buildSpellMapPreviewHighlights(baseSingleTarget, null);
    expect(highlights).toHaveLength(0);
  });

  it("retorna lista vazia quando status é unknown sem targetRefId", () => {
    const model: SpellMapPreviewModel = { ...baseSingleTarget, status: "unknown" };
    const highlights = buildSpellMapPreviewHighlights(model, undefined);
    expect(highlights).toHaveLength(0);
  });

  it("emite highlight unknown quando status é unknown com targetRefId", () => {
    const model: SpellMapPreviewModel = { ...baseSingleTarget, status: "unknown" };
    const highlights = buildSpellMapPreviewHighlights(model, "enemy-1");

    expect(highlights).toHaveLength(1);
    expect(highlights[0]).toMatchObject({ kind: "target", status: "unknown", targetRefId: "enemy-1" });
  });
});

describe("buildSpellMapPreviewHighlights – multi-instância", () => {
  it("Magic Missile 5 instâncias todas válidas gera 5 highlights instance-target", () => {
    const model: SpellMapPreviewModel = {
      ...baseSingleTarget,
      status: "valid",
      effectInstanceCount: 5,
      instanceStatuses: [
        { instanceIndex: 1, targetRefId: "goblin-a", status: "valid" },
        { instanceIndex: 2, targetRefId: "goblin-a", status: "valid" },
        { instanceIndex: 3, targetRefId: "orc-b", status: "valid" },
        { instanceIndex: 4, targetRefId: "orc-b", status: "valid" },
        { instanceIndex: 5, targetRefId: "goblin-a", status: "valid" },
      ],
    };

    const highlights = buildSpellMapPreviewHighlights(model);

    expect(highlights).toHaveLength(5);
    expect(highlights.every((h) => h.kind === "instance-target")).toBe(true);
    expect(highlights.every((h) => h.status === "valid")).toBe(true);
  });

  it("Eldritch Blast feixe 1 válido, feixe 2 inválido gera highlights com status diferentes", () => {
    const model: SpellMapPreviewModel = {
      ...baseSingleTarget,
      status: "partial",
      effectInstanceCount: 2,
      instanceStatuses: [
        { instanceIndex: 1, targetRefId: "goblin-a", status: "valid" },
        { instanceIndex: 2, targetRefId: "orc-b", status: "invalid", reason: "out_of_range" },
      ],
    };

    const highlights = buildSpellMapPreviewHighlights(model);

    expect(highlights).toHaveLength(2);
    expect(highlights[0]).toMatchObject({ kind: "instance-target", status: "valid", targetRefId: "goblin-a", instanceIndex: 1 });
    expect(highlights[1]).toMatchObject({ kind: "instance-target", status: "invalid", targetRefId: "orc-b", instanceIndex: 2, reason: "out_of_range" });
  });

  it("instâncias sem targetRefId são omitidas da lista", () => {
    const model: SpellMapPreviewModel = {
      ...baseSingleTarget,
      status: "unknown",
      effectInstanceCount: 3,
      instanceStatuses: [
        { instanceIndex: 1, targetRefId: null, status: "unknown" },
        { instanceIndex: 2, targetRefId: null, status: "unknown" },
        { instanceIndex: 3, targetRefId: null, status: "unknown" },
      ],
    };

    const highlights = buildSpellMapPreviewHighlights(model);
    expect(highlights).toHaveLength(0);
  });

  it("mistura de instâncias atribuídas e não-atribuídas emite apenas as com targetRefId", () => {
    const model: SpellMapPreviewModel = {
      ...baseSingleTarget,
      status: "partial",
      effectInstanceCount: 3,
      instanceStatuses: [
        { instanceIndex: 1, targetRefId: "goblin-a", status: "valid" },
        { instanceIndex: 2, targetRefId: null, status: "unknown" },
        { instanceIndex: 3, targetRefId: "orc-b", status: "invalid", reason: "out_of_range" },
      ],
    };

    const highlights = buildSpellMapPreviewHighlights(model);

    expect(highlights).toHaveLength(2);
    expect(highlights.map((h) => h.targetRefId)).toEqual(["goblin-a", "orc-b"]);
  });

  it("preserva instanceIndex em cada highlight", () => {
    const highlights = buildSpellMapPreviewHighlights(baseMultiInstance);

    expect(highlights[0].instanceIndex).toBe(1);
    expect(highlights[1].instanceIndex).toBe(2);
    expect(highlights[2].instanceIndex).toBe(3);
  });
});

describe("buildSpellMapPreviewHighlights – área", () => {
  it("Fireball com preview válido emite area-cell valid", () => {
    const model: SpellMapPreviewModel = {
      status: "valid",
      rangeMeters: 36,
      areaShape: "sphere",
      areaSizeMeters: 6,
      effectInstanceCount: 1,
      affectedTargetCount: 3,
    };

    const highlights = buildSpellMapPreviewHighlights(model);

    expect(highlights).toHaveLength(1);
    expect(highlights[0]).toMatchObject({ kind: "area-cell", status: "valid" });
  });

  it("área inválida emite area-cell invalid", () => {
    const model: SpellMapPreviewModel = {
      status: "invalid",
      reason: "out_of_range",
      rangeMeters: 36,
      areaShape: "sphere",
      areaSizeMeters: 6,
      effectInstanceCount: 1,
    };

    const highlights = buildSpellMapPreviewHighlights(model);

    expect(highlights).toHaveLength(1);
    expect(highlights[0]).toMatchObject({ kind: "area-cell", status: "invalid" });
  });

  it("área unknown (sem preview result) retorna lista vazia", () => {
    const model: SpellMapPreviewModel = {
      status: "unknown",
      rangeMeters: 36,
      areaShape: "sphere",
      areaSizeMeters: 6,
      effectInstanceCount: 1,
    };

    const highlights = buildSpellMapPreviewHighlights(model);
    expect(highlights).toHaveLength(0);
  });

  it("área ignora selectedTargetRefId passado (área não usa target)", () => {
    const model: SpellMapPreviewModel = {
      status: "valid",
      rangeMeters: 36,
      areaShape: "cone",
      areaSizeMeters: 9,
      effectInstanceCount: 1,
    };

    const highlights = buildSpellMapPreviewHighlights(model, "enemy-1");

    expect(highlights).toHaveLength(1);
    expect(highlights[0].kind).toBe("area-cell");
    expect(highlights[0].targetRefId).toBeUndefined();
  });
});
