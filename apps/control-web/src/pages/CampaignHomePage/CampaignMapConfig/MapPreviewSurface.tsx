import { useRef, useState, type MouseEvent } from "react";
import {
  CAMPAIGN_EDGE_OBSTACLE_PRESETS,
  CAMPAIGN_OBSTACLE_PRESETS,
} from "../../../entities/campaign";
import { ManagedImage } from "../../../shared/ui";
import type { HoveredGridCell, MapPreviewSurfaceProps } from "./types";
import { formatHoveredCell } from "./utils";

const PRESET_COLOR_MAP = Object.fromEntries(
  CAMPAIGN_OBSTACLE_PRESETS.map((p) => [p.id, p.color])
);

const EDGE_PRESET_COLOR_MAP = Object.fromEntries(
  CAMPAIGN_EDGE_OBSTACLE_PRESETS.map((preset) => [preset.id, preset.color]),
);

export const MapPreviewSurface = ({
  imageUrl,
  alt,
  bounds,
  gridWidth,
  gridHeight,
  imageClassName,
  invalidMessage,
  hoverHint,
  hoverMissingGrid,
  hoverCellLabel,
  hoverColumnLabel,
  hoverRowLabel,
  obstacleMap,
  edgeObstacleMap,
  obstacleEditTarget = "cell",
  edgeDirection = "N",
  onCellToggle,
  onEdgeToggle,
  onHoveredCellChange,
}: MapPreviewSurfaceProps) => {
  const [hoveredCell, setHoveredCell] = useState<HoveredGridCell | null>(null);
  const hoveredCellRef = useRef<HoveredGridCell | null>(null);
  const isCellEditMode = obstacleEditTarget === "cell" && Boolean(onCellToggle);
  const isEdgeEditMode = obstacleEditTarget === "edge" && Boolean(onEdgeToggle);
  const isEditMode = isCellEditMode || isEdgeEditMode;

  const previewVerticalLines =
    bounds != null && gridWidth != null && gridWidth > 1
      ? Array.from({ length: gridWidth - 1 }, (_, index) => index + 1)
      : [];
  const previewHorizontalLines =
    bounds != null && gridHeight != null && gridHeight > 1
      ? Array.from({ length: gridHeight - 1 }, (_, index) => index + 1)
      : [];
  const canHoverCells =
    bounds != null && gridWidth != null && gridHeight != null && gridWidth > 0 && gridHeight > 0;

  const resolveHoveredCell = (
    event: MouseEvent<HTMLDivElement>,
  ): HoveredGridCell | null => {
    if (!canHoverCells || bounds == null || gridWidth == null || gridHeight == null) {
      return null;
    }
    const rect = event.currentTarget.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return null;

    const normalizedX = (event.clientX - rect.left) / rect.width;
    const normalizedY = (event.clientY - rect.top) / rect.height;
    const insideBounds =
      normalizedX >= bounds.x &&
      normalizedY >= bounds.y &&
      normalizedX <= bounds.x + bounds.width &&
      normalizedY <= bounds.y + bounds.height;
    if (!insideBounds) return null;

    const gridX = (normalizedX - bounds.x) / bounds.width;
    const gridY = (normalizedY - bounds.y) / bounds.height;
    return {
      column: Math.min(gridWidth, Math.floor(gridX * gridWidth) + 1),
      row: Math.min(gridHeight, Math.floor(gridY * gridHeight) + 1),
    };
  };

  const handleMouseMove = (event: MouseEvent<HTMLDivElement>) => {
    const next = resolveHoveredCell(event);
    const prev = hoveredCellRef.current;
    if (prev?.row === next?.row && prev?.column === next?.column) return;
    hoveredCellRef.current = next;
    setHoveredCell(next);
    onHoveredCellChange?.(next);
  };

  const handleClick = (event: MouseEvent<HTMLDivElement>) => {
    if (!isEditMode) return;
    const cell = resolveHoveredCell(event);
    if (cell == null) return;
    const x = cell.column - 1;
    const y = cell.row - 1;
    if (isCellEditMode) {
      onCellToggle?.(x, y);
      return;
    }
    onEdgeToggle?.(x, y, edgeDirection);
  };

  const hoverBadgeText =
    bounds == null
      ? null
      : canHoverCells
        ? hoveredCell != null
          ? hoverCellLabel.replace(
              "{cell}",
              formatHoveredCell(hoveredCell, {
                columnLabel: hoverColumnLabel,
                rowLabel: hoverRowLabel,
              }),
            )
          : hoverHint
        : hoverMissingGrid;

  return (
    <div
      className="relative"
      style={isEditMode ? { cursor: "crosshair" } : undefined}
      onMouseMove={bounds != null ? handleMouseMove : undefined}
      onMouseLeave={() => {
        hoveredCellRef.current = null;
        setHoveredCell(null);
        onHoveredCellChange?.(null);
      }}
      onClick={isEditMode && bounds != null ? handleClick : undefined}
    >
      <ManagedImage
        src={imageUrl}
        alt={alt}
        className={imageClassName}
      />
      {hoverBadgeText ? (
        <div className="pointer-events-none absolute right-3 top-3 z-10 rounded-full border border-slate-700 bg-slate-950/90 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-100">
          {hoverBadgeText}
        </div>
      ) : null}
      {bounds != null ? (
        <div className="pointer-events-none absolute inset-0">
          <div
            className="absolute border-2 border-limiar-300/95 bg-limiar-400/10 shadow-[0_0_0_9999px_rgba(2,6,23,0.52)]"
            style={{
              left: `${bounds.x * 100}%`,
              top: `${bounds.y * 100}%`,
              width: `${bounds.width * 100}%`,
              height: `${bounds.height * 100}%`,
            }}
          >
            {/* Obstacle overlays — color-coded by preset */}
            {obstacleMap != null && gridWidth != null && gridHeight != null &&
              Array.from(obstacleMap.entries()).map(([key, presetId]) => {
                const [cx, cy] = key.split(":").map(Number);
                const color = PRESET_COLOR_MAP[presetId] ?? "#d24646";
                return (
                  <div
                    key={key}
                    className="absolute border border-white/20"
                    style={{
                      left: `${(cx / gridWidth) * 100}%`,
                      top: `${(cy / gridHeight) * 100}%`,
                      width: `${100 / gridWidth}%`,
                      height: `${100 / gridHeight}%`,
                      backgroundColor: `${color}70`,
                    }}
                  />
                );
              })
            }
            {hoveredCell != null && gridWidth != null && gridHeight != null ? (
              <>
                <div
                  className={`absolute border ${
                    isEditMode
                      ? "border-rose-300/90 bg-rose-400/20"
                      : "border-amber-200/90 bg-amber-300/15"
                  }`}
                  style={{
                    left: `${((hoveredCell.column - 1) / gridWidth) * 100}%`,
                    top: `${((hoveredCell.row - 1) / gridHeight) * 100}%`,
                    width: `${100 / gridWidth}%`,
                    height: `${100 / gridHeight}%`,
                  }}
                />
                {isEdgeEditMode ? (
                  <div
                    className="absolute bg-fuchsia-200"
                    style={{
                      ...(edgeDirection === "N"
                        ? {
                            left: `${((hoveredCell.column - 1) / gridWidth) * 100}%`,
                            top: `${((hoveredCell.row - 1) / gridHeight) * 100}%`,
                            width: `${100 / gridWidth}%`,
                            height: "4px",
                          }
                        : edgeDirection === "S"
                          ? {
                              left: `${((hoveredCell.column - 1) / gridWidth) * 100}%`,
                              top: `${(hoveredCell.row / gridHeight) * 100}%`,
                              width: `${100 / gridWidth}%`,
                              height: "4px",
                            }
                          : edgeDirection === "E"
                            ? {
                                left: `${(hoveredCell.column / gridWidth) * 100}%`,
                                top: `${((hoveredCell.row - 1) / gridHeight) * 100}%`,
                                width: "4px",
                                height: `${100 / gridHeight}%`,
                              }
                            : {
                                left: `${((hoveredCell.column - 1) / gridWidth) * 100}%`,
                                top: `${((hoveredCell.row - 1) / gridHeight) * 100}%`,
                                width: "4px",
                                height: `${100 / gridHeight}%`,
                              }),
                      boxShadow: "0 0 0 1px rgba(244,114,182,0.9)",
                    }}
                  />
                ) : null}
              </>
            ) : null}
            {previewVerticalLines.map((line) => (
              <div
                key={`preview-v-${line}`}
                className="absolute bottom-0 top-0 w-px bg-white/35"
                style={{ left: `${(line / gridWidth!) * 100}%` }}
              />
            ))}
            {previewHorizontalLines.map((line) => (
              <div
                key={`preview-h-${line}`}
                className="absolute left-0 right-0 h-px bg-white/35"
                style={{ top: `${(line / gridHeight!) * 100}%` }}
              />
            ))}
            {edgeObstacleMap != null &&
              gridWidth != null &&
              gridHeight != null &&
              Array.from(edgeObstacleMap.entries()).map(([key, presetId]) => {
                const [cx, cy, direction] = key.split(":");
                const color = EDGE_PRESET_COLOR_MAP[presetId] ?? "#d24646";
                const left = (Number(cx) / gridWidth) * 100;
                const top = (Number(cy) / gridHeight) * 100;
                const width = 100 / gridWidth;
                const height = 100 / gridHeight;
                const lineStyle =
                  direction === "N"
                    ? {
                        left: `${left}%`,
                        top: `${top}%`,
                        width: `${width}%`,
                        height: "3px",
                      }
                    : direction === "S"
                      ? {
                          left: `${left}%`,
                          top: `${top + height}%`,
                          width: `${width}%`,
                          height: "3px",
                        }
                      : direction === "E"
                        ? {
                            left: `${left + width}%`,
                            top: `${top}%`,
                            width: "3px",
                            height: `${height}%`,
                          }
                        : {
                            left: `${left}%`,
                            top: `${top}%`,
                            width: "3px",
                            height: `${height}%`,
                          };
                return (
                  <div
                    key={key}
                    className="absolute"
                    style={{
                      ...lineStyle,
                      backgroundColor: color,
                      boxShadow: `0 0 0 1px ${color}88`,
                      opacity: 0.95,
                    }}
                  />
                );
              })}
          </div>
        </div>
      ) : (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-slate-950/60 px-6 text-center text-xs font-medium text-amber-100">
          {invalidMessage}
        </div>
      )}
    </div>
  );
};
