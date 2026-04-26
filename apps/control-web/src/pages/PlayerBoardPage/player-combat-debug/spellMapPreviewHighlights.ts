import type { SpellMapPreviewModel } from "./spellMapPreviewModel";

export type SpellMapHighlightKind = "target" | "instance-target" | "area-cell";

export type SpellMapHighlightStatus = "valid" | "invalid" | "partial" | "unknown";

export type SpellMapHighlight = {
  kind: SpellMapHighlightKind;
  status: SpellMapHighlightStatus;
  targetRefId?: string | null;
  instanceIndex?: number | null;
  reason?: string | null;
};

export function buildSpellMapPreviewHighlights(
  model: SpellMapPreviewModel,
  selectedTargetRefId?: string | null,
): SpellMapHighlight[] {
  // Area spells: emit a single area-cell status signal (no coordinates — cells live in previewCells)
  if (model.areaShape) {
    if (model.status === "unknown") return [];
    return [{ kind: "area-cell", status: model.status }];
  }

  // Multi-instance spells (Magic Missile, Eldritch Blast, etc.)
  if (model.instanceStatuses && model.instanceStatuses.length > 0) {
    const highlights: SpellMapHighlight[] = [];
    for (const inst of model.instanceStatuses) {
      if (!inst.targetRefId) continue;
      highlights.push({
        kind: "instance-target",
        status: inst.status,
        targetRefId: inst.targetRefId,
        instanceIndex: inst.instanceIndex,
        reason: inst.reason ?? null,
      });
    }
    return highlights;
  }

  // Single-target
  if (!selectedTargetRefId) return [];
  return [
    {
      kind: "target",
      status: model.status,
      targetRefId: selectedTargetRefId,
      reason: model.reason ?? null,
    },
  ];
}
