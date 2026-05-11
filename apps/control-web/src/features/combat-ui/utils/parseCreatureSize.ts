import type { CreatureSize } from "@limiarmap/shared-contracts";

const VALID_SIZES: CreatureSize[] = ["Tiny", "Small", "Medium", "Large", "Huge", "Gargantuan"];

function normalizeSize(size: unknown): string | null {
  return typeof size === "string" && size.trim() ? size.trim().toLowerCase() : null;
}

export function parseCreatureSize(raw: string | undefined | null): CreatureSize | undefined {
  const normalized = normalizeSize(raw);
  if (!normalized) return undefined;
  const found = VALID_SIZES.find((s) => s.toLowerCase() === normalized);
  return found;
}
