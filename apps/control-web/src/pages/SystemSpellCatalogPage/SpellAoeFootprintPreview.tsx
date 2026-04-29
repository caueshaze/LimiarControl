import { metersToCells } from "../../features/combat-ui/hooks/useTargetingPreview";
import {
  computeAoeFootprint,
  getRequiredDimensionField,
} from "./spellAoeFootprintCalc";

type Props = {
  areaShape: string;
  radiusMeters: string;
  lengthMeters: string;
  sideMeters: string;
};

const DIMENSION_LABEL: Record<string, string> = {
  radiusMeters: "raio",
  lengthMeters: "comprimento",
  sideMeters: "tamanho do lado",
};

const CELL_SIZE = 18;

function buildGrid(cells: FootprintCell[]): {
  grid: boolean[][];
  gridWidth: number;
  gridHeight: number;
  offsetX: number;
  offsetY: number;
} {
  if (cells.length === 0) return { grid: [], gridWidth: 0, gridHeight: 0, offsetX: 0, offsetY: 0 };

  const minX = Math.min(...cells.map((c) => c.x));
  const maxX = Math.max(...cells.map((c) => c.x));
  const minY = Math.min(...cells.map((c) => c.y));
  const maxY = Math.max(...cells.map((c) => c.y));

  const gridWidth = maxX - minX + 1;
  const gridHeight = maxY - minY + 1;

  const grid: boolean[][] = Array.from({ length: gridHeight }, () =>
    Array(gridWidth).fill(false),
  );

  const cellSet = new Set(cells.map((c) => `${c.x},${c.y}`));

  for (let row = 0; row < gridHeight; row++) {
    for (let col = 0; col < gridWidth; col++) {
      const x = col + minX;
      const y = row + minY;
      if (cellSet.has(`${x},${y}`)) {
        grid[row][col] = true;
      }
    }
  }

  return { grid, gridWidth, gridHeight, offsetX: minX, offsetY: minY };
}

export const SpellAoeFootprintPreview = ({
  areaShape,
  radiusMeters,
  lengthMeters,
  sideMeters,
}: Props) => {
  if (!areaShape) {
    return (
      <p className="text-xs text-slate-500" data-testid="spell-aoe-preview-empty">
        Nenhuma forma de área selecionada.
      </p>
    );
  }

  const dimensionField = getRequiredDimensionField(areaShape);
  const dimensionValue =
    dimensionField === "radiusMeters"
      ? radiusMeters
      : dimensionField === "lengthMeters"
        ? lengthMeters
        : sideMeters;

  const meters = parseFloat(dimensionValue);
  const hasDimension = !Number.isNaN(meters) && meters > 0;

  if (!hasDimension) {
    return (
      <p
        className="text-xs text-amber-400/80"
        data-testid="spell-aoe-preview-warning"
      >
        Configure o {DIMENSION_LABEL[dimensionField]} para ver o preview da área.
      </p>
    );
  }

  const sizeCells = metersToCells(meters);
  const cells = computeAoeFootprint(areaShape, sizeCells);
  const { grid, gridWidth, gridHeight } = buildGrid(cells);

  return (
    <div data-testid="spell-aoe-preview">
      <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
        Preview da área
      </p>
      <div
        className="inline-grid gap-px rounded border border-white/8 bg-white/4 p-1"
        style={{
          gridTemplateColumns: `repeat(${gridWidth}, ${CELL_SIZE}px)`,
          gridTemplateRows: `repeat(${gridHeight}, ${CELL_SIZE}px)`,
        }}
      >
        {grid.map((row, rowIdx) =>
          row.map((cell, colIdx) => (
            <div
              key={`${rowIdx}-${colIdx}`}
              className={
                cell
                  ? "rounded-sm bg-amber-500/40 ring-1 ring-inset ring-amber-400/60"
                  : "rounded-sm bg-white/4"
              }
            />
          )),
        )}
      </div>
      <p className="mt-1.5 text-xs text-slate-400">
        {cells.length} célula{cells.length !== 1 ? "s" : ""} afetada
        {cells.length !== 1 ? "s" : ""}
      </p>
    </div>
  );
};
