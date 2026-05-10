import type { ActiveAreaEffect, Coordinate, SpellAnchor, Token } from "@limiarmap/shared-contracts";
import { reconnectAs } from "./centrifugo-client";
import {
  battleMapStore,
  type EmbeddedCombatPhase,
  type EmbeddedSelectionMode,
  type SpellMapHighlight
} from "../features/battle-map/battle-map-store";

type MapActorType = "player" | "gm";

type EmbeddedMapContextMessage = {
  type: "limiar-control:map-context";
  payload: {
    sessionId: string;
    actor?: {
      actorId: string;
      actorType: MapActorType;
    } | null;
    selectionMode?: EmbeddedSelectionMode;
    previewCells?: Coordinate[];
    activeAreaEffects?: ActiveAreaEffect[];
    spellAnchors?: SpellAnchor[];
    selectedCell?: Coordinate | null;
    selectedTargetRefId?: string | null;
    combatPhase?: EmbeddedCombatPhase | null;
    spellHighlights?: SpellMapHighlight[];
  };
};

type EmbeddedMapReadyMessage = {
  type: "limiar-map:ready";
  payload: {
    sessionId: string;
  };
};

type EmbeddedMapTokenSelectedMessage = {
  type: "limiar-map:token-selected";
  payload: {
    sessionId: string;
    tokenId: string;
    combatantId: string | null;
    label: string;
    position: Coordinate;
  };
};

type EmbeddedMapCellSelectedMessage = {
  type: "limiar-map:cell-selected";
  payload: {
    sessionId: string;
    cell: Coordinate;
    tokenId: string | null;
    combatantId: string | null;
  };
};

type EmbeddedMapCellHoveredMessage = {
  type: "limiar-map:cell-hovered";
  payload: {
    sessionId: string;
    cell: Coordinate | null;
    tokenId: string | null;
    combatantId: string | null;
  };
};

const isCoordinate = (value: unknown): value is Coordinate => {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as { x?: unknown; y?: unknown };
  return Number.isInteger(candidate.x) && Number.isInteger(candidate.y);
};

export const isEmbeddedMapContextMessage = (
  value: unknown,
): value is EmbeddedMapContextMessage => {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as { type?: unknown; payload?: unknown };
  if (candidate.type !== "limiar-control:map-context" || !candidate.payload || typeof candidate.payload !== "object") {
    return false;
  }

  const payload = candidate.payload as {
    sessionId?: unknown;
    actor?: { actorId?: unknown; actorType?: unknown } | null;
    selectionMode?: unknown;
    previewCells?: unknown;
    activeAreaEffects?: unknown;
    spellAnchors?: unknown;
    selectedCell?: unknown;
    selectedTargetRefId?: unknown;
    combatPhase?: unknown;
    spellHighlights?: unknown;
  };

  const actorValid =
    payload.actor == null ||
    (typeof payload.actor.actorId === "string" &&
      (payload.actor.actorType === "player" || payload.actor.actorType === "gm"));
  const selectionModeValid =
    payload.selectionMode == null ||
    payload.selectionMode === "none" ||
    payload.selectionMode === "select-token" ||
    payload.selectionMode === "select-cell";
  const previewCellsValid =
    payload.previewCells == null ||
    (Array.isArray(payload.previewCells) && payload.previewCells.every(isCoordinate));
  const activeAreaEffectsValid =
    payload.activeAreaEffects == null ||
    (Array.isArray(payload.activeAreaEffects) &&
      payload.activeAreaEffects.every((effect) => {
        if (!effect || typeof effect !== "object") return false;
        const candidate = effect as {
          id?: unknown;
          sourceSpellName?: unknown;
          anchorCell?: unknown;
          areaShape?: unknown;
          affectedCells?: unknown;
        };
        return (
          typeof candidate.id === "string" &&
          typeof candidate.sourceSpellName === "string" &&
          isCoordinate(candidate.anchorCell) &&
          typeof candidate.areaShape === "string" &&
          Array.isArray(candidate.affectedCells) &&
          candidate.affectedCells.every(isCoordinate)
        );
      }));
  const spellAnchorsValid =
    payload.spellAnchors == null ||
    (Array.isArray(payload.spellAnchors) &&
      payload.spellAnchors.every((anchor) => {
        if (!anchor || typeof anchor !== "object") return false;
        const candidate = anchor as {
          id?: unknown;
          sourceSpellKey?: unknown;
          position?: unknown;
          renderKind?: unknown;
        };
        return (
          typeof candidate.id === "string" &&
          typeof candidate.sourceSpellKey === "string" &&
          isCoordinate(candidate.position) &&
          typeof candidate.renderKind === "string"
        );
      }));
  const selectedCellValid =
    payload.selectedCell == null || isCoordinate(payload.selectedCell);
  const selectedTargetValid =
    payload.selectedTargetRefId == null || typeof payload.selectedTargetRefId === "string";
  const combatPhaseValid =
    payload.combatPhase == null ||
    payload.combatPhase === "initiative" ||
    payload.combatPhase === "placement" ||
    payload.combatPhase === "active" ||
    payload.combatPhase === "ended";
  const spellHighlightsValid =
    payload.spellHighlights == null || Array.isArray(payload.spellHighlights);

  return (
    typeof payload.sessionId === "string" &&
    actorValid &&
    selectionModeValid &&
    previewCellsValid &&
    activeAreaEffectsValid &&
    spellAnchorsValid &&
    selectedCellValid &&
    selectedTargetValid &&
    combatPhaseValid &&
    spellHighlightsValid
  );
};

export function applyEmbeddedMapContext(message: EmbeddedMapContextMessage["payload"]): void {
  if (message.actor) {
    reconnectAs(message.actor.actorId, message.actor.actorType);
  }

  battleMapStore.setEmbeddedInteractionContext({
    selectionMode: message.selectionMode ?? "none",
    previewCells: message.previewCells ?? [],
    activeAreaEffects: message.activeAreaEffects ?? [],
    spellAnchors: message.spellAnchors ?? [],
    selectedCell: message.selectedCell ?? null,
    selectedTargetRefId: message.selectedTargetRefId ?? null,
    combatPhase: message.combatPhase ?? null,
    spellHighlights: Array.isArray(message.spellHighlights) ? message.spellHighlights : [],
  });
}

export function postEmbeddedMapReady(sessionId: string): void {
  const message: EmbeddedMapReadyMessage = {
    type: "limiar-map:ready",
    payload: { sessionId },
  };
  window.parent.postMessage(message, "*");
}

export function postEmbeddedTokenSelected(sessionId: string, token: Token): void {
  const message: EmbeddedMapTokenSelectedMessage = {
    type: "limiar-map:token-selected",
    payload: {
      sessionId,
      tokenId: token.id,
      combatantId: token.combatantId ?? null,
      label: token.label,
      position: token.position,
    },
  };
  window.parent.postMessage(message, "*");
}

export function postEmbeddedCellSelected(
  sessionId: string,
  cell: Coordinate,
  token: Token | null,
): void {
  const message: EmbeddedMapCellSelectedMessage = {
    type: "limiar-map:cell-selected",
    payload: {
      sessionId,
      cell,
      tokenId: token?.id ?? null,
      combatantId: token?.combatantId ?? null,
    },
  };
  window.parent.postMessage(message, "*");
}

export function postEmbeddedCellHovered(
  sessionId: string,
  cell: Coordinate | null,
  token: Token | null,
): void {
  const message: EmbeddedMapCellHoveredMessage = {
    type: "limiar-map:cell-hovered",
    payload: {
      sessionId,
      cell,
      tokenId: token?.id ?? null,
      combatantId: token?.combatantId ?? null,
    },
  };
  window.parent.postMessage(message, "*");
}
