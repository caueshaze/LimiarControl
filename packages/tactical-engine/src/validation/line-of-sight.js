import {
  blocksEffect,
  blocksVision,
  getHighestCover,
  COVER_RANK
} from "./obstacle-rules";
import { traceLine } from "../targeting/line-trace";
import { findEdgeBetween } from "../grid/grid-state";
export function isCellHeavilyObscured(cell, activeAreaEffects = []) {
  if (!activeAreaEffects.length) return false;
  for (const effect of activeAreaEffects) {
    if (effect.effectKind !== "obscurement") continue;
    if (effect.obscurement !== "heavily_obscured") continue;
    for (const affected of effect.affectedCells) {
      if (affected.x === cell.x && affected.y === cell.y) return true;
    }
  }
  return false;
}
export function hasLineOfSight(
  obstacles,
  from,
  to,
  edgeObstacles = [],
  activeAreaEffects = []
) {
  return evaluateLineOfSight(
    obstacles,
    from,
    to,
    edgeObstacles,
    activeAreaEffects
  ).ok;
}
export function evaluateLineOfSight(
  obstacles,
  from,
  to,
  edgeObstacles = [],
  activeAreaEffects = []
) {
  if (isCellHeavilyObscured(from, activeAreaEffects)) {
    return { ok: false, reason: "origin_heavily_obscured" };
  }
  if (isCellHeavilyObscured(to, activeAreaEffects)) {
    return { ok: false, reason: "target_heavily_obscured" };
  }
  const intermediate = traceLine(from, to);
  const fullPath = [from, ...intermediate, to];
  for (const cell of intermediate) {
    if (isCellHeavilyObscured(cell, activeAreaEffects)) {
      return { ok: false, reason: "line_of_sight_obscured" };
    }
    if (blocksVision(obstacles, cell)) {
      return { ok: false, reason: "no_line_of_sight" };
    }
  }
  for (let i = 0; i < fullPath.length - 1; i++) {
    const edge = findEdgeBetween(edgeObstacles, fullPath[i], fullPath[i + 1]);
    if (edge?.blocksVision) {
      return { ok: false, reason: "no_line_of_sight" };
    }
  }
  return { ok: true };
}
export function hasLineOfEffect(obstacles, from, to, edgeObstacles = []) {
  const intermediate = traceLine(from, to);
  const fullPath = [from, ...intermediate, to];
  for (const cell of intermediate) {
    if (blocksEffect(obstacles, cell)) {
      return false;
    }
  }
  for (let i = 0; i < fullPath.length - 1; i++) {
    const edge = findEdgeBetween(edgeObstacles, fullPath[i], fullPath[i + 1]);
    if (edge?.blocksEffect) {
      return false;
    }
  }
  return true;
}
export function evaluateCover(obstacles, from, to, edgeObstacles = []) {
  const intermediate = traceLine(from, to);
  const cellsToCheck = [...intermediate, to];
  const fullPath = [from, ...intermediate, to];
  let highest = "none";
  for (const cell of cellsToCheck) {
    const cellCover = getHighestCover(obstacles, cell);
    if (COVER_RANK[cellCover] > COVER_RANK[highest]) {
      highest = cellCover;
    }
    if (highest === "full") {
      return "full";
    }
  }
  for (let i = 0; i < fullPath.length - 1; i++) {
    const edge = findEdgeBetween(edgeObstacles, fullPath[i], fullPath[i + 1]);
    if (
      edge &&
      edge.cover !== "none" &&
      COVER_RANK[edge.cover] > COVER_RANK[highest]
    ) {
      highest = edge.cover;
    }
    if (highest === "full") {
      return "full";
    }
  }
  return highest;
}
