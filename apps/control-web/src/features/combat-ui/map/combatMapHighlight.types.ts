export type SpellMapHighlightKind =
  | "target"
  | "instance-target"
  | "area-cell"
  | "affected-token";

export type SpellMapHighlightStatus =
  | "valid"
  | "invalid"
  | "partial"
  | "unknown";

export type SpellMapHighlight = {
  kind: SpellMapHighlightKind;
  status: SpellMapHighlightStatus;
  targetRefId?: string | null;
  instanceIndex?: number | null;
  cell?: { x: number; y: number } | null;
  label?: string | null;
  reason?: string | null;
};
