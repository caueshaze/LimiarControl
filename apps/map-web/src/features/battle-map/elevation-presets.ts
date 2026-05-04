/**
 * Elevation brush presets — Issue #184.
 *
 * Presets are authoring conveniences only. The elevation value always relies
 * on the explicit `elevationMeters` number. Preset IDs are never persisted.
 *
 * Preset set (5 tactically relevant heights):
 *
 * | meters | Label  | Color    | Use case                         |
 * |--------|--------|----------|----------------------------------|
 * | 0 m    | Ground | #4b5563  | Reset to ground level            |
 * | 3 m    | Low    | #3b82f6  | Low platform, ledge              |
 * | 6 m    | Medium | #8b5cf6  | Wall top, second floor           |
 * | 9 m    | High   | #ec4899  | Tower, cliff                     |
 * | 12 m   | Very   | #ef4444  | High cliff, tall structure       |
 */

export interface ElevationPreset {
  meters: number;
  label: string;
  swatchColor: string;
}

export const ELEVATION_PRESETS: ElevationPreset[] = [
  { meters: 0, label: "0 m", swatchColor: "#4b5563" },
  { meters: 3, label: "3 m", swatchColor: "#3b82f6" },
  { meters: 6, label: "6 m", swatchColor: "#8b5cf6" },
  { meters: 9, label: "9 m", swatchColor: "#ec4899" },
  { meters: 12, label: "12 m", swatchColor: "#ef4444" },
];

export function getElevationPreset(meters: number): ElevationPreset {
  return (
    ELEVATION_PRESETS.find((preset) => preset.meters === meters) ??
    ELEVATION_PRESETS[0]
  );
}
