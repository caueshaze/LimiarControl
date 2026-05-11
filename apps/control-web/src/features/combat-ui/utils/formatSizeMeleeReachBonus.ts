import { getSizeMeleeReachBonusCells, METERS_PER_CELL } from "@limiarmap/shared-contracts";
import type { CreatureSize } from "@limiarmap/shared-contracts";

export function getSizeMeleeReachBonusMeters(size: CreatureSize): number {
  return getSizeMeleeReachBonusCells(size) * METERS_PER_CELL;
}

/**
 * Formata valor em metros com o mesmo padrao da UI (1,5m / 3m),
 * evitando +3.0m ou artefatos de ponto flutuante.
 */
export function formatMetersCompact(meters: number): string {
  const rounded = Math.round(meters * 10) / 10;
  return rounded % 1 === 0 ? `${rounded.toFixed(0)}m` : `${rounded.toFixed(1).replace(".", ",")}m`;
}

export function formatSizeMeleeReachBonusSource(
  effectiveSize: CreatureSize | undefined,
  t: (key: string) => string,
): { label: string; bonusMeters: number } | null {
  if (!effectiveSize) return null;
  const bonusCells = getSizeMeleeReachBonusCells(effectiveSize);
  if (bonusCells <= 0) return null;
  const sizeLabel = t(`playerBoard.creatureSize.${effectiveSize}`);
  const bonusMeters = bonusCells * METERS_PER_CELL;
  return {
    label: `${t("combatUi.meleeReachSizePrefix")} ${sizeLabel} +${formatMetersCompact(bonusMeters)}`,
    bonusMeters,
  };
}
