import type {
  CombatAreaPreviewRequest,
  CombatCastSpellRequest,
  CombatMapPreviewToken,
  CombatParticipant,
  CombatSpellMode,
} from "../../../shared/api/combatRepo";
import type { CombatSpellOption } from "./types";

export type AreaTargetingMode =
  | "single_target_select"
  | "area_target_select"
  | "confirming";

export type GridCell = {
  x: number;
  y: number;
};

const AREA_SHAPES = new Set(["sphere", "cone", "line", "cube", "cylinder"]);

export const isAreaShape = (areaShape?: string | null): boolean =>
  typeof areaShape === "string" && AREA_SHAPES.has(areaShape);

export const requiresAreaTargetingSelection = (
  selectionType?: string | null,
  areaShape?: string | null,
): boolean =>
  (selectionType === "point" || selectionType === "direction") && isAreaShape(areaShape);

export const spellRequiresExternalTarget = (
  selectionType?: string | null,
  areaShape?: string | null,
): boolean => {
  if (requiresAreaTargetingSelection(selectionType, areaShape)) {
    return false;
  }
  if (selectionType === "none" || selectionType === "self") {
    return false;
  }
  return true;
};

export const createInitialTargetingMode = (
  areaShape?: string | null,
  selectionType?: string | null,
): AreaTargetingMode =>
  requiresAreaTargetingSelection(selectionType, areaShape) || (!selectionType && isAreaShape(areaShape))
    ? "area_target_select"
    : "single_target_select";

export const getAnchorCombatantIdAtCell = (
  tokens: CombatMapPreviewToken[],
  anchorCell: GridCell,
): string | null =>
  tokens.find((token) => token.position.x === anchorCell.x && token.position.y === anchorCell.y)?.combatant_id ?? null;

type ResolveAffectedTargetNamesParams = {
  affectedTargetRefIds: string[];
  canRevealHiddenTargets?: boolean;
  participants: CombatParticipant[];
  tokens: CombatMapPreviewToken[];
  unknownTargetLabel?: string;
};

export const resolveAffectedTargetNames = ({
  affectedTargetRefIds,
  canRevealHiddenTargets = false,
  participants,
  tokens,
  unknownTargetLabel = "Alvo desconhecido",
}: ResolveAffectedTargetNamesParams): string[] =>
  affectedTargetRefIds.flatMap((targetRefId) => {
    const participant = participants.find((candidate) => candidate.ref_id === targetRefId);
    const mayRevealParticipant = Boolean(participant && (canRevealHiddenTargets || participant.visible !== false));

    if (!participant) {
      if (!canRevealHiddenTargets) {
        return [unknownTargetLabel];
      }
      const tokenLabel = tokens.find((token) => token.combatant_id === targetRefId)?.label?.trim();
      return [tokenLabel || unknownTargetLabel];
    }

    if (!mayRevealParticipant) {
      return [];
    }

    const tokenLabel = tokens.find((token) => token.combatant_id === targetRefId)?.label?.trim();
    const participantName = participant.display_name.trim();
    return [tokenLabel || participantName || unknownTargetLabel];
  });

export const formatAffectedTargetNames = (
  targetNames: string[],
  emptyLabel = "Nenhum alvo afetado",
): string => (targetNames.length > 0 ? `Afetados: ${targetNames.join(", ")}` : emptyLabel);

type BuildAreaPayloadParams = {
  actorParticipantId: string;
  spell: CombatSpellOption;
  spellMode: CombatSpellMode;
  selectedSlotLevel: number | null;
  originCell: GridCell;
  anchorCell: GridCell;
  targetRefId?: string | null;
};

export const buildAreaPreviewPayload = ({
  actorParticipantId,
  spell,
  spellMode,
  selectedSlotLevel,
  originCell,
  anchorCell,
  targetRefId,
}: BuildAreaPayloadParams): CombatAreaPreviewRequest => ({
  actor_participant_id: actorParticipantId,
  target_ref_id: targetRefId ?? null,
  origin_cell: originCell,
  anchor_cell: anchorCell,
  inventory_item_id: spell.sourceType === "magic_item" ? spell.inventoryItemId ?? null : null,
  spell_id: spell.canonicalKey,
  spell_canonical_key: spell.canonicalKey,
  spell_mode: spellMode,
  slot_level:
    spell.sourceType === "magic_item"
      ? spell.fixedCastLevel ?? spell.level ?? null
      : spell.level > 0
        ? selectedSlotLevel ?? spell.level
        : null,
});

type BuildAreaCastPayloadParams = BuildAreaPayloadParams & {
  spellEffectDice: string;
  spellEffectBonus: number;
  spellDamageType: string;
  spellSaveAbility: string;
  concentrationRollSource: "system" | "manual";
  concentrationManualRoll?: number | null;
};

export const buildAreaCastPayload = ({
  actorParticipantId,
  spell,
  spellMode,
  selectedSlotLevel,
  originCell,
  anchorCell,
  targetRefId,
  spellEffectDice,
  spellEffectBonus,
  spellDamageType,
  spellSaveAbility,
  concentrationRollSource,
  concentrationManualRoll,
}: BuildAreaCastPayloadParams): CombatCastSpellRequest => ({
  actor_participant_id: actorParticipantId,
  target_ref_id: targetRefId ?? null,
  origin_cell: originCell,
  anchor_cell: anchorCell,
  spell_canonical_key: spell.canonicalKey,
  spell_id: spell.canonicalKey,
  campaign_spell_id: spell.campaignSpellId ?? null,
  spell_mode: spellMode,
  slot_level:
    spell.sourceType === "magic_item"
      ? spell.fixedCastLevel ?? spell.level ?? null
      : spell.level > 0
        ? selectedSlotLevel ?? spell.level
        : null,
  inventory_item_id: spell.sourceType === "magic_item" ? spell.inventoryItemId ?? null : null,
  damage_dice: spellMode === "heal" ? null : spellEffectDice || null,
  damage_bonus: spellMode === "heal" ? null : spellEffectBonus,
  heal_dice: spellMode === "heal" ? spellEffectDice || null : null,
  heal_bonus: spellMode === "heal" ? spellEffectBonus : null,
  damage_type: spellMode === "heal" ? null : spellDamageType || null,
  save_ability: spellMode === "saving_throw" ? spellSaveAbility || null : null,
  concentration_roll_source: concentrationRollSource,
  concentration_manual_roll: concentrationManualRoll ?? null,
});

export const resolveActorOriginCell = (
  actor: CombatParticipant,
  tokens: CombatMapPreviewToken[],
): GridCell | null => {
  const actorToken = tokens.find((token) => token.combatant_id === actor.ref_id);
  if (!actorToken) {
    return null;
  }
  return {
    x: actorToken.position.x,
    y: actorToken.position.y,
  };
};
