import type { PendingSpellPreparation } from "../../shared/api/combatRepo";

const sortPreparedSpellIds = (spellIds: string[]) => [...spellIds].sort();

export const buildPendingSpellPreparationSignature = (
  pendingSpellPreparation: PendingSpellPreparation | null | undefined,
): string | null => {
  if (!pendingSpellPreparation) return null;

  const createdAt = pendingSpellPreparation.createdAt.trim();
  if (createdAt) {
    return `createdAt:${createdAt}`;
  }

  return JSON.stringify({
    source: pendingSpellPreparation.source,
    classKey: pendingSpellPreparation.classKey,
    preparedLimit: pendingSpellPreparation.preparedLimit,
    availableDuringRest: pendingSpellPreparation.availableDuringRest,
    currentPreparedSpellIds: sortPreparedSpellIds(
      pendingSpellPreparation.currentPreparedSpellIds,
    ),
  });
};

export const shouldAutoOpenPendingSpellPreparation = ({
  autoOpenedSignatures,
  combatActive,
  pendingSignature,
}: {
  pendingSignature: string | null;
  combatActive: boolean;
  autoOpenedSignatures: ReadonlySet<string>;
}): boolean => {
  if (!pendingSignature) return false;
  if (combatActive) return false;
  return !autoOpenedSignatures.has(pendingSignature);
};
