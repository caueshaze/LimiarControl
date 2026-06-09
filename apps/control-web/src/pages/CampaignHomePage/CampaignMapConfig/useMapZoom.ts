import { useState, type WheelEvent } from "react";

const ZOOM_MIN = 0.5;
const ZOOM_MAX = 4;
const ZOOM_STEP = 0.25;

const clampZoom = (value: number) =>
  Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, Math.round(value * 100) / 100));

/**
 * Width-based zoom for the map preview: the surface is scaled via its container
 * width so the surrounding `overflow-auto` keeps scroll in sync (no transform
 * clipping). Ctrl/⌘ + wheel zooms; plain wheel scrolls.
 */
export function useMapZoom() {
  const [zoom, setZoom] = useState(1);

  const adjust = (delta: number) => setZoom((current) => clampZoom(current + delta));

  const handleWheelZoom = (event: WheelEvent<HTMLDivElement>) => {
    if (!event.ctrlKey && !event.metaKey) return;
    event.preventDefault();
    adjust(event.deltaY < 0 ? ZOOM_STEP : -ZOOM_STEP);
  };

  return {
    zoom,
    canZoomIn: zoom < ZOOM_MAX,
    canZoomOut: zoom > ZOOM_MIN,
    zoomIn: () => adjust(ZOOM_STEP),
    zoomOut: () => adjust(-ZOOM_STEP),
    reset: () => setZoom(1),
    handleWheelZoom,
  };
}
