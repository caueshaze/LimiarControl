import { blocksEffect, blocksVision, getHighestCover, COVER_RANK } from "./obstacle-rules";
import { traceLine } from "../targeting/line-trace";
import { findEdgeBetween } from "../grid/grid-state";
export function hasLineOfSight(obstacles, from, to, edgeObstacles = []) {
    const intermediate = traceLine(from, to);
    for (const cell of intermediate) {
        if (blocksVision(obstacles, cell)) {
            return false;
        }
    }
    for (let i = 0; i < intermediate.length - 1; i++) {
        const edge = findEdgeBetween(edgeObstacles, intermediate[i], intermediate[i + 1]);
        if (edge?.blocksVision) {
            return false;
        }
    }
    return true;
}
export function hasLineOfEffect(obstacles, from, to, edgeObstacles = []) {
    const intermediate = traceLine(from, to);
    for (const cell of intermediate) {
        if (blocksEffect(obstacles, cell)) {
            return false;
        }
    }
    for (let i = 0; i < intermediate.length - 1; i++) {
        const edge = findEdgeBetween(edgeObstacles, intermediate[i], intermediate[i + 1]);
        if (edge?.blocksEffect) {
            return false;
        }
    }
    return true;
}
export function evaluateCover(obstacles, from, to, edgeObstacles = []) {
    const intermediate = traceLine(from, to);
    const cellsToCheck = [...intermediate, to];
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
    for (let i = 0; i < cellsToCheck.length - 1; i++) {
        const edge = findEdgeBetween(edgeObstacles, cellsToCheck[i], cellsToCheck[i + 1]);
        if (edge && edge.cover !== "none" && COVER_RANK[edge.cover] > COVER_RANK[highest]) {
            highest = edge.cover;
        }
        if (highest === "full") {
            return "full";
        }
    }
    return highest;
}
