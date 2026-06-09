import { useEffect, useRef, useState, type MouseEvent } from "react";
import {
  CAMPAIGN_EDGE_OBSTACLE_PRESETS,
  CAMPAIGN_OBSTACLE_PRESETS,
} from "../../../entities/campaign";
import { ManagedImage } from "../../../shared/ui";
import type {
  CalibrationPreviewBounds,
  HoveredGridCell,
  MapPreviewSurfaceProps,
} from "./types";
import { clampCalibrationBounds, formatHoveredCell } from "./utils";

const PRESET_COLOR_MAP = Object.fromEntries(
  CAMPAIGN_OBSTACLE_PRESETS.map((p) => [p.id, p.color])
);

const EDGE_PRESET_COLOR_MAP = Object.fromEntries(
  CAMPAIGN_EDGE_OBSTACLE_PRESETS.map((preset) => [preset.id, preset.color]),
);

type CalibrationHandle = "nw" | "n" | "ne" | "e" | "se" | "s" | "sw" | "w";

type CalibrationDrag =
  | { kind: "draw"; anchorX: number; anchorY: number }
  | { kind: "move"; startX: number; startY: number; origin: CalibrationPreviewBounds }
  | { kind: "resize"; handle: CalibrationHandle; origin: CalibrationPreviewBounds };

const CALIBRATION_HANDLES: { id: CalibrationHandle; left: number; top: number; cursor: string }[] = [
  { id: "nw", left: 0, top: 0, cursor: "nwse-resize" },
  { id: "n", left: 0.5, top: 0, cursor: "ns-resize" },
  { id: "ne", left: 1, top: 0, cursor: "nesw-resize" },
  { id: "e", left: 1, top: 0.5, cursor: "ew-resize" },
  { id: "se", left: 1, top: 1, cursor: "nwse-resize" },
  { id: "s", left: 0.5, top: 1, cursor: "ns-resize" },
  { id: "sw", left: 0, top: 1, cursor: "nesw-resize" },
  { id: "w", left: 0, top: 0.5, cursor: "ew-resize" },
];

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
  showGridLines = true,
  calibrationCell = null,
  onCellToggle,
  onEdgeToggle,
  onHoveredCellChange,
  calibrationEditing = false,
  onCalibrationChange,
}: MapPreviewSurfaceProps) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [hoveredCell, setHoveredCell] = useState<HoveredGridCell | null>(null);
  const hoveredCellRef = useRef<HoveredGridCell | null>(null);
  const [calibrationDrag, setCalibrationDrag] = useState<CalibrationDrag | null>(null);
  const isCellEditMode =
    !calibrationEditing && obstacleEditTarget === "cell" && Boolean(onCellToggle);
  const isEdgeEditMode =
    !calibrationEditing && obstacleEditTarget === "edge" && Boolean(onEdgeToggle);
  const isEditMode = isCellEditMode || isEdgeEditMode;
  const canCalibrate = calibrationEditing && Boolean(onCalibrationChange);

  const previewVerticalLines =
    showGridLines && bounds != null && gridWidth != null && gridWidth > 1
      ? Array.from({ length: gridWidth - 1 }, (_, index) => index + 1)
      : [];
  const previewHorizontalLines =
    showGridLines && bounds != null && gridHeight != null && gridHeight > 1
      ? Array.from({ length: gridHeight - 1 }, (_, index) => index + 1)
      : [];
  const canHoverCells =
    bounds != null && gridWidth != null && gridHeight != null && gridWidth > 0 && gridHeight > 0;

  const resolveFraction = (
    clientX: number,
    clientY: number,
  ): { fx: number; fy: number } | null => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (rect == null || rect.width <= 0 || rect.height <= 0) return null;
    return {
      fx: Math.min(1, Math.max(0, (clientX - rect.left) / rect.width)),
      fy: Math.min(1, Math.max(0, (clientY - rect.top) / rect.height)),
    };
  };

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

  // --- Calibration drag (draw / move / resize) ---------------------------
  const startDraw = (event: MouseEvent<HTMLDivElement>) => {
    if (!canCalibrate) return;
    const point = resolveFraction(event.clientX, event.clientY);
    if (point == null) return;
    event.preventDefault();
    setCalibrationDrag({ kind: "draw", anchorX: point.fx, anchorY: point.fy });
  };

  const startMove = (event: MouseEvent<HTMLDivElement>) => {
    if (!canCalibrate || calibrationCell == null) return;
    const point = resolveFraction(event.clientX, event.clientY);
    if (point == null) return;
    event.preventDefault();
    event.stopPropagation();
    setCalibrationDrag({
      kind: "move",
      startX: point.fx,
      startY: point.fy,
      origin: calibrationCell,
    });
  };

  const startResize = (
    event: MouseEvent<HTMLDivElement>,
    handle: CalibrationHandle,
  ) => {
    if (!canCalibrate || calibrationCell == null) return;
    event.preventDefault();
    event.stopPropagation();
    setCalibrationDrag({ kind: "resize", handle, origin: calibrationCell });
  };

  useEffect(() => {
    if (calibrationDrag == null || onCalibrationChange == null) return;

    const handleWindowMove = (event: globalThis.MouseEvent) => {
      const point = resolveFraction(event.clientX, event.clientY);
      if (point == null) return;

      if (calibrationDrag.kind === "draw") {
        const x1 = Math.min(calibrationDrag.anchorX, point.fx);
        const y1 = Math.min(calibrationDrag.anchorY, point.fy);
        const x2 = Math.max(calibrationDrag.anchorX, point.fx);
        const y2 = Math.max(calibrationDrag.anchorY, point.fy);
        onCalibrationChange(
          clampCalibrationBounds({ x: x1, y: y1, width: x2 - x1, height: y2 - y1 }),
        );
        return;
      }

      if (calibrationDrag.kind === "move") {
        const { origin } = calibrationDrag;
        const dx = point.fx - calibrationDrag.startX;
        const dy = point.fy - calibrationDrag.startY;
        onCalibrationChange(
          clampCalibrationBounds({
            x: origin.x + dx,
            y: origin.y + dy,
            width: origin.width,
            height: origin.height,
          }),
        );
        return;
      }

      const { origin, handle } = calibrationDrag;
      let x1 = origin.x;
      let y1 = origin.y;
      let x2 = origin.x + origin.width;
      let y2 = origin.y + origin.height;
      if (handle.includes("w")) x1 = point.fx;
      if (handle.includes("e")) x2 = point.fx;
      if (handle.includes("n")) y1 = point.fy;
      if (handle.includes("s")) y2 = point.fy;
      const left = Math.min(x1, x2);
      const right = Math.max(x1, x2);
      const top = Math.min(y1, y2);
      const bottom = Math.max(y1, y2);
      onCalibrationChange(
        clampCalibrationBounds({
          x: left,
          y: top,
          width: right - left,
          height: bottom - top,
        }),
      );
    };

    const handleWindowUp = () => setCalibrationDrag(null);

    window.addEventListener("mousemove", handleWindowMove);
    window.addEventListener("mouseup", handleWindowUp);
    return () => {
      window.removeEventListener("mousemove", handleWindowMove);
      window.removeEventListener("mouseup", handleWindowUp);
    };
  }, [calibrationDrag, onCalibrationChange]);

  const hoverBadgeText =
    calibrationEditing || bounds == null
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
      ref={containerRef}
      className="relative select-none"
      style={
        canCalibrate
          ? { cursor: "crosshair" }
          : isEditMode
            ? { cursor: "crosshair" }
            : undefined
      }
      onMouseMove={!calibrationEditing && bounds != null ? handleMouseMove : undefined}
      onMouseLeave={
        calibrationEditing
          ? undefined
          : () => {
              hoveredCellRef.current = null;
              setHoveredCell(null);
              onHoveredCellChange?.(null);
            }
      }
      onMouseDown={canCalibrate ? startDraw : undefined}
      onClick={!calibrationEditing && isEditMode && bounds != null ? handleClick : undefined}
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
          {canCalibrate && calibrationCell != null ? (
            <div
              className="absolute border-2 border-emerald-300 bg-emerald-400/25"
              style={{
                left: `${calibrationCell.x * 100}%`,
                top: `${calibrationCell.y * 100}%`,
                width: `${calibrationCell.width * 100}%`,
                height: `${calibrationCell.height * 100}%`,
                pointerEvents: "auto",
                cursor: "move",
              }}
              onMouseDown={startMove}
            >
              {CALIBRATION_HANDLES.map((handle) => {
                // Anchor handles inside the cell so edge ones aren't clipped.
                const translateX =
                  handle.left === 0 ? "0%" : handle.left === 1 ? "-100%" : "-50%";
                const translateY =
                  handle.top === 0 ? "0%" : handle.top === 1 ? "-100%" : "-50%";
                return (
                  <div
                    key={handle.id}
                    onMouseDown={(event) => startResize(event, handle.id)}
                    className="absolute h-3 w-3 rounded-sm border border-slate-900 bg-emerald-200 shadow"
                    style={{
                      left: `${handle.left * 100}%`,
                      top: `${handle.top * 100}%`,
                      transform: `translate(${translateX}, ${translateY})`,
                      cursor: handle.cursor,
                      pointerEvents: "auto",
                    }}
                  />
                );
              })}
            </div>
          ) : null}
        </div>
      ) : (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-slate-950/60 px-6 text-center text-xs font-medium text-amber-100">
          {invalidMessage}
        </div>
      )}
    </div>
  );
};
