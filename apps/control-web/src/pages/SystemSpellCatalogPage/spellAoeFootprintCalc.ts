export type FootprintCell = { x: number; y: number };

export function getRequiredDimensionField(
  shape: string,
): "radiusMeters" | "lengthMeters" | "sideMeters" {
  if (shape === "sphere" || shape === "cylinder") return "radiusMeters";
  if (shape === "cone" || shape === "line") return "lengthMeters";
  return "sideMeters";
}

export function computeAoeFootprint(
  shape: string,
  sizeCells: number,
): FootprintCell[] {
  if (shape === "sphere" || shape === "cylinder") {
    const cells: FootprintCell[] = [];
    for (let x = -sizeCells; x <= sizeCells; x++) {
      for (let y = -sizeCells; y <= sizeCells; y++) {
        if (x * x + y * y <= sizeCells * sizeCells) {
          cells.push({ x, y });
        }
      }
    }
    return cells;
  }

  if (shape === "cone") {
    const cells: FootprintCell[] = [{ x: 0, y: 0 }];
    for (let x = 1; x <= sizeCells; x++) {
      for (let y = -x; y <= x; y++) {
        cells.push({ x, y });
      }
    }
    return cells;
  }

  if (shape === "line") {
    const cells: FootprintCell[] = [];
    for (let x = 1; x <= sizeCells; x++) {
      cells.push({ x, y: 0 });
    }
    return cells;
  }

  if (shape === "cube") {
    const cells: FootprintCell[] = [];
    for (let x = 0; x < sizeCells; x++) {
      for (let y = 0; y < sizeCells; y++) {
        cells.push({ x, y });
      }
    }
    return cells;
  }

  return [];
}
