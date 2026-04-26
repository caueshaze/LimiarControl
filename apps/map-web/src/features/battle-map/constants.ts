import type { Obstacle } from "@limiarmap/shared-contracts";

export const DEFAULT_MAP_IMAGE_URL = "/maps/map.jpg";

// ─── Types ────────────────────────────────────────────────────────────────────

export const C = {
  bg: 0x111923,
  gridLine: 0x96d7ff,
  gridLineAlpha: 0.22,
  gridLineEdit: 0x96dcff,
  gridLineEditAlpha: 0.42,
  gridBorder: 0x96d7ff,
  gridBorderAlpha: 0.34,
  gridBorderEdit: 0x6ebeff,
  gridBorderEditAlpha: 0.98,
  gridEditBg: 0x5ca9ff,
  gridEditBgAlpha: 0.08,
  obsMoveSpell: 0xd24646,
  obsMoveSpellAlpha: 0.38,
  obsMove: 0xffa436,
  obsMoveAlpha: 0.34,
  obsSpell: 0xbc56ff,
  obsSpellAlpha: 0.32,
  obsCover: 0xffdc78,
  obsCoverAlpha: 0.22,
  obsCoverThreeQ: 0xffaa44,
  obsCoverThreeQAlpha: 0.28,
  obsVision: 0x5ed2ff,
  obsVisionAlpha: 0.22,
  // Phase 7: difficult terrain — earthy brown tint, distinct from all blocker colors
  obsDifficultTerrain: 0x9c7040,
  obsDifficultTerrainAlpha: 0.32,
  movPreview: 0x00dc5a,
  movPreviewAlpha: 0.28,
  tgtPreview: 0xb450ff,
  tgtPreviewAlpha: 0.3,
  tokenPlayer: 0x2a7abf,
  tokenGm: 0xbf3030,
  tokenNeutral: 0x2d7a3a,
  tokenBorderNormal: 0xffffff,
  tokenBorderNormalAlpha: 0.6,
  tokenBorderSelected: 0x00e676,
  tokenBorderActive: 0xffd700,
  handleEdge: 0x5ca9ff,
  edgeWall: 0xd24646,
  edgeWallAlpha: 0.85,
  edgeBarrier: 0xffa436,
  edgeBarrierAlpha: 0.75,
  edgeCoverHalf: 0xffdc78,
  edgeCoverHalfAlpha: 0.7,
  edgeCoverThreeQ: 0xffaa44,
  edgeCoverThreeQAlpha: 0.7,
  edgeVisionBlocker: 0x5ed2ff,
  edgeVisionBlockerAlpha: 0.6,
  edgeEffectBlocker: 0xbc56ff,
  edgeEffectBlockerAlpha: 0.6,

  // ─── Tactical preview (Phase U1) ───────────────────────────────────────────
  // Reach overlay — soft blue tint on cells within movement/attack reach
  previewReach: 0x5ca9ff,
  previewReachAlpha: 0.14,
  previewReachBorder: 0x5ca9ff,
  previewReachBorderAlpha: 0.28,
  // AoE footprint — warm amber (distinct from all obstacle/preview colors)
  previewAoe: 0xff9040,
  previewAoeAlpha: 0.22,
  previewAoeBorder: 0xffb060,
  previewAoeBorderAlpha: 0.5,
  // Target validity — green ring (valid) / red ring (invalid)
  previewTargetValid: 0x22dd88,
  previewTargetValidAlpha: 0.9,
  previewTargetInvalid: 0xff4444,
  previewTargetInvalidAlpha: 0.85,

  // Spell preview highlights — partial (orange); unknown skips rendering (no ring drawn)
  spellHighlightPartial: 0xf97316,
  spellHighlightPartialAlpha: 0.75,
};

export const COVER_RANK: Record<Obstacle["cover"], number> = {
  none: 0,
  half: 1,
  threeQuarters: 2,
  full: 3
};

// ─── Utilities ────────────────────────────────────────────────────────────────
