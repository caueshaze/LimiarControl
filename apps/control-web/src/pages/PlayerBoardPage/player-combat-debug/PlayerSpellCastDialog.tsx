import { useEffect, useMemo, useRef, useState } from "react";
import type { SpellVariant } from "../../../entities/base-spell";
import type { AbilityName } from "../../../entities/roll/rollResolution.types";
import { participantHasActiveConcentration } from "../../../features/combat-ui/combatUi.helpers";
import type {
  CombatCastSpellRequest,
  CombatParticipant,
  CombatResolvedSpellContext,
  CombatSpellMode,
  CombatSpellResult,
} from "../../../shared/api/combatRepo";
import { combatRepo } from "../../../shared/api/combatRepo";
import { toPlayerFriendlyError } from "../../../features/combat-ui/combatErrors";
import { formatSpellVariantSummaryLines } from "../../../features/combat-ui/spellVariantUi";
import { useTargetingPreview } from "../../../features/combat-ui/hooks/useTargetingPreview";
import {
  getDamageRollCount,
  getDamageRollSides,
  formatDamageDiceExpression,
} from "../../../shared/utils/diceExpression";
import {
  buildAreaCastPayload,
  createInitialTargetingMode,
  resolveActorOriginCell,
} from "./areaTargetingUi";
import { AreaTargetingGrid } from "./AreaTargetingGrid";
import {
  hasCompleteEffectInstanceTargets,
  InstanceTargetSelector,
  normalizeEffectInstanceTargets,
  reconcileEffectInstanceTargets,
  resolveEffectInstanceContext,
  type EffectInstanceTargetInput,
} from "./InstanceTargetSelector";
import {
  hasCompleteTargetVariantAssignments,
  VariantTargetAssignmentSelector,
  type TargetVariantAssignmentInput,
} from "./VariantTargetAssignmentSelector";
import { PlainMultiTargetSelector } from "./PlainMultiTargetSelector";
import { SpellCastDialogActions } from "./SpellCastDialogActions";
import { parseBonus } from "./spellCastHelpers";
import { SpellCastDialogHeader } from "./SpellCastDialogHeader";
import { SpellCastResultPanel } from "./SpellCastResultPanel";
import {
  buildSpellMapPreviewModel,
  type SpellInstanceSpatialValidation,
} from "./spellMapPreviewModel";
import { buildSpellMapPreviewHighlights } from "./spellMapPreviewHighlights";
import type { SpellMapHighlight } from "../../../features/combat-ui/map/CombatMapFrame";
import { buildSpellPreviewModel } from "./spellPreviewModel";
import type { CombatSpellOption } from "./types";
import { useAreaTargeting } from "./useAreaTargeting";
import { useResolvedSpellContext } from "./useResolvedSpellContext";
import { useLocale } from "../../../shared/hooks/useLocale";
import {
  buildInstanceSpatialValidations,
  buildSingleTargetSpatialValidations,
  buildSpellPreviewFanoutKey,
  buildUniqueTargetRefIds,
  createPreviewRequestGate,
  fetchAreaSpatialValidation,
  fetchPreviewValidationsWithCache,
  type PreviewFanoutCacheEntry,
} from "./spellPreviewSpatialValidations";
import type { SpellAreaSpatialValidation, SpellTargetSpatialValidation } from "./spellMapPreviewModel";

type Props = {
  actor: CombatParticipant;
  actorParticipantId: string;
  canRevealHiddenTargets?: boolean;
  onClose: () => void;
  onMapPreviewChange?: (highlights: SpellMapHighlight[]) => void;
  onResolved?: (result: CombatSpellResult) => void | Promise<void>;
  participants: CombatParticipant[];
  sessionId: string;
  spell: CombatSpellOption;
  spellDamageType: string;
  spellEffectBonus: string;
  spellEffectDice: string;
  spellMode: CombatSpellMode;
  spellSaveAbility: AbilityName | "";
  target?: CombatParticipant | null;
};

const MULTI_INSTANCE_TARGET_ERROR = "Escolha um alvo para cada instância da magia.";

type EffectInstanceContext = {
  instanceCount: number;
  instanceDice: string | null;
};

type BuildNonAreaSpellCastPayloadParams = {
  actorParticipantId: string;
  concentrationManualRoll: number | null;
  concentrationRollMode: "system" | "manual";
  effectInstanceTargets: EffectInstanceTargetInput[];
  isMultiInstanceSpell: boolean;
  isVariantMultiTargetSpell?: boolean;
  isPlainMultiTargetAutomationSpell?: boolean;
  plainTargetRefIds?: string[];
  manualRoll?: number | null;
  parsedBonus: number;
  rollSource?: "manual" | "system";
  selectedSlotLevel: number | null;
  selectedVariantKey?: string | null;
  spell: CombatSpellOption;
  spellDamageType: string;
  spellEffectDice: string;
  spellMode: CombatSpellMode;
  spellSaveAbility: AbilityName | "";
  targetVariantAssignments?: TargetVariantAssignmentInput[];
  targetRefId?: string | null;
};

export const buildNonAreaSpellCastPayload = ({
  actorParticipantId,
  concentrationManualRoll,
  concentrationRollMode,
  effectInstanceTargets,
  isMultiInstanceSpell,
  isVariantMultiTargetSpell = false,
  isPlainMultiTargetAutomationSpell = false,
  plainTargetRefIds = [],
  manualRoll = null,
  parsedBonus,
  rollSource = "system",
  selectedSlotLevel,
  selectedVariantKey = null,
  spell,
  spellDamageType,
  spellEffectDice,
  spellMode,
  spellSaveAbility,
  targetVariantAssignments = [],
  targetRefId = null,
}: BuildNonAreaSpellCastPayloadParams): CombatCastSpellRequest => ({
  actor_participant_id: actorParticipantId,
  target_ref_id: isVariantMultiTargetSpell || isPlainMultiTargetAutomationSpell
    ? null
    : isMultiInstanceSpell
      ? effectInstanceTargets[0]?.target_ref_id ?? targetRefId ?? null
      : targetRefId,
  target_ref_ids: isPlainMultiTargetAutomationSpell && plainTargetRefIds.length > 0 ? plainTargetRefIds : null,
  effect_instance_targets: isMultiInstanceSpell ? effectInstanceTargets : null,
  variant_key: isVariantMultiTargetSpell ? null : selectedVariantKey,
  target_variant_assignments: isVariantMultiTargetSpell ? targetVariantAssignments : null,
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
  roll_source: rollSource,
  manual_roll: manualRoll,
  damage_dice: spellMode === "heal" ? null : spellEffectDice || null,
  damage_bonus: spellMode === "heal" ? null : parsedBonus,
  heal_dice: spellMode === "heal" ? spellEffectDice || null : null,
  heal_bonus: spellMode === "heal" ? parsedBonus : null,
  damage_type: spellMode === "heal" ? null : spellDamageType || null,
  save_ability: spellMode === "saving_throw" ? spellSaveAbility || null : null,
  concentration_roll_source: concentrationRollMode,
  concentration_manual_roll: concentrationManualRoll,
});

export const getEffectiveEffectInstanceContext = (
  resolvedContext: CombatResolvedSpellContext | null,
  fallbackContext: EffectInstanceContext,
  allowFallback: boolean,
): EffectInstanceContext => {
  if (resolvedContext) {
    return {
      instanceCount: Math.max(1, resolvedContext.effect_instance_count),
      instanceDice: resolvedContext.effect_instance_dice ?? null,
    };
  }

  return allowFallback
    ? fallbackContext
    : {
        instanceCount: 1,
        instanceDice: null,
      };
};

export const mergePendingSaveResolutionResult = (
  result: CombatSpellResult,
  resolution: CombatParticipant["last_save_resolution"],
): CombatSpellResult => {
  if (!resolution) {
    return result;
  }

  return {
    ...result,
    action_kind: "saving_throw",
    damage: resolution.damage,
    healing: resolution.healing,
    damage_type: resolution.damage_type ?? result.damage_type,
    effect_kind: resolution.effect_kind ?? result.effect_kind,
    effect_roll_required: Boolean(resolution.pending_spell_id),
    is_critical: false,
    is_hit: null,
    is_saved: resolution.is_saved,
    new_hp: resolution.new_hp ?? null,
    pending_save_id: null,
    pending_spell_id: resolution.pending_spell_id ?? null,
    roll: resolution.roll_total,
    roll_result: resolution.roll_result,
    save_ability: (resolution.save_ability as AbilityName) ?? result.save_ability,
    save_dc: resolution.save_dc,
    selected_variant_key: resolution.selected_variant_key ?? result.selected_variant_key,
    selected_variant_label: resolution.selected_variant_label ?? result.selected_variant_label,
    context_origin: resolution.context_origin ?? result.context_origin,
    concentration_group: resolution.concentration_group ?? result.concentration_group,
    target_variant_assignments:
      resolution.target_variant_assignments ?? result.target_variant_assignments ?? null,
    manual_notes_by_target:
      resolution.manual_notes_by_target ?? result.manual_notes_by_target ?? null,
  };
};

export const PlayerSpellCastDialog = ({
  actor,
  actorParticipantId,
  canRevealHiddenTargets = false,
  onClose,
  onMapPreviewChange,
  onResolved,
  participants,
  sessionId,
  spell,
  spellDamageType,
  spellEffectBonus,
  spellEffectDice,
  spellMode,
  spellSaveAbility,
  target = null,
}: Props) => {
  const { t } = useLocale();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [attackMode, setAttackMode] = useState<"choose" | "manual" | "virtual">("choose");
  const [effectMode, setEffectMode] = useState<"choose" | "manual" | "virtual">("choose");
  const [manualEffectRolls, setManualEffectRolls] = useState<number[]>([]);
  const [concentrationRollMode, setConcentrationRollMode] = useState<"system" | "manual">("system");
  const [concentrationManualRoll, setConcentrationManualRoll] = useState("");
  const [selectedSlotLevel, setSelectedSlotLevel] = useState<number | null>(
    spell.fixedCastLevel ?? (spell.level > 0 ? spell.level : null),
  );
  const [selectedVariantKey, setSelectedVariantKey] = useState<string>("");
  const [targetVariantAssignments, setTargetVariantAssignments] = useState<TargetVariantAssignmentInput[]>([]);
  const [effectInstanceTargets, setEffectInstanceTargets] = useState<EffectInstanceTargetInput[]>([]);
  const [selectedTargetIds, setSelectedTargetIds] = useState<string[]>(
    target ? [target.ref_id] : [],
  );
  const [result, setResult] = useState<CombatSpellResult | null>(null);
  const [spellMapState, setSpellMapState] = useState<Awaited<ReturnType<typeof combatRepo.getMapState>> | null>(null);
  const [multiInstanceSpatialValidations, setMultiInstanceSpatialValidations] = useState<
    SpellInstanceSpatialValidation[]
  >([]);
  const [targetingMode, setTargetingMode] = useState(createInitialTargetingMode(spell.areaShape, spell.selectionType));
  const [pointSpellInitialTargetId, setPointSpellInitialTargetId] = useState<string | null>(null);
  const handledSaveResolutionKeyRef = useRef<string | null>(null);
  const multiPreviewRequestGateRef = useRef(createPreviewRequestGate());
  const areaPreviewRequestGateRef = useRef(createPreviewRequestGate());
  const previewCacheRef = useRef(new Map<string, PreviewFanoutCacheEntry>());
  const previewInFlightRef = useRef(new Map<string, Promise<SpellTargetSpatialValidation>>());
  const [areaSpatialValidation, setAreaSpatialValidation] = useState<SpellAreaSpatialValidation | null>(null);

  const {
    anchorCell,
    canSubmitArea,
    clearAreaSelection,
    isAreaSpell,
    mapError,
    mapLoading,
    mapState,
    originCell,
    preview,
    previewError,
    previewLoading,
    setAnchorCell,
  } = useAreaTargeting({
    actor,
    actorParticipantId,
    result,
    selectedSlotLevel,
    sessionId,
    spell,
    spellMode,
  });
  const fallbackEffectInstanceContext = resolveEffectInstanceContext(spell, selectedSlotLevel);
  const resolvedSpellContextState = useResolvedSpellContext({
    actorParticipantId,
    selectedSlotLevel,
    selectedVariantKey: selectedVariantKey || null,
    sessionId,
    spell,
    spellMode,
  });
  // Keep the local derivation only as a temporary defense when the pre-cast
  // backend contract is unavailable; the resolved backend context is preferred.
  const allowLocalFallback =
    Boolean(resolvedSpellContextState.error) ||
    (!resolvedSpellContextState.loading && !resolvedSpellContextState.context);
  const spellContextReady = Boolean(resolvedSpellContextState.context) || allowLocalFallback;
  const previewModel = buildSpellPreviewModel(
    resolvedSpellContextState.context,
    {
      spell,
      selectedSlotLevel,
      spellMode,
      spellEffectDice: spellEffectDice || null,
    },
  );
  const effectInstanceContext = getEffectiveEffectInstanceContext(
    resolvedSpellContextState.context,
    fallbackEffectInstanceContext,
    allowLocalFallback,
  );
  const isMultiInstanceSpell = !isAreaSpell && effectInstanceContext.instanceCount > 1;
  const spellVariants: SpellVariant[] = (resolvedSpellContextState.context?.variants?.length
    ? resolvedSpellContextState.context.variants.map((variant) => ({
        key: variant.key,
        labelPt: variant.label,
        descriptionPt: variant.description ?? null,
        manualNotes: variant.manualNotes ?? null,
      }))
    : spell.variants ?? []) ?? [];
  const maxTargets = Math.max(1, resolvedSpellContextState.context?.max_targets ?? 1);
  const isVariantSpell = spellVariants.length > 0;
  const isVariantMultiTargetSpell = isVariantSpell && !isAreaSpell && !isMultiInstanceSpell && maxTargets > 1;
  const isPlainMultiTargetAutomationSpell = !isAreaSpell && !isMultiInstanceSpell && !isVariantSpell && maxTargets > 1;
  const hasCompleteVariantAssignments = hasCompleteTargetVariantAssignments(targetVariantAssignments, maxTargets);
  const selectableParticipants = participants.filter((participant) => participant.id !== actor.id);
  const normalizedEffectInstanceTargets = normalizeEffectInstanceTargets(
    effectInstanceTargets,
    effectInstanceContext.instanceCount,
  );
  const normalizedEffectInstanceTargetsSignature = normalizedEffectInstanceTargets
    .map((entry) => `${entry.instance_index}:${entry.target_ref_id}`)
    .join("|");
  const effectInstanceTargetsComplete = hasCompleteEffectInstanceTargets(
    effectInstanceTargets,
    effectInstanceContext.instanceCount,
  );
  const previewRangeMeters = previewModel.rangeMeters ?? spell.rangeMeters ?? null;
  const rangePreview = useTargetingPreview({
    sessionId,
    actorRefId: actor.ref_id,
    targetRefId: target?.ref_id ?? null,
    actionType: "spell",
    normalRangeMeters: previewRangeMeters,
    longRangeMeters: null,
    enabled: !isAreaSpell && !isMultiInstanceSpell && !!target,
  });
  const spellOutOfRange = !isAreaSpell && !isMultiInstanceSpell && rangePreview.rangeStatus === "out";
  const targetHasConcentration = target ? participantHasActiveConcentration(target) : false;
  const shouldShowConcentrationControl = targetHasConcentration && spellMode !== "heal" && spellMode !== "utility";
  const slotOptions =
    spell.availableSlotLevels.length > 0 ? spell.availableSlotLevels : spell.level > 0 ? [spell.level] : [];
  const parsedBonus = parseBonus(spellEffectBonus);
  const actionCostLabel =
    spell.actionCost === "bonus_action"
      ? t("combatUi.bonusAction")
      : spell.actionCost === "reaction"
        ? t("combatUi.reaction")
        : spell.actionCost === "free"
          ? t("combatUi.freeAction")
          : t("combatUi.action");
  const anchorTargetRefId =
    anchorCell && mapState
      ? mapState.tokens.find((token) => token.position.x === anchorCell.x && token.position.y === anchorCell.y)?.combatant_id ?? null
      : null;
  const effectDiceSource =
    result?.effect_dice ??
    (spellEffectDice || resolvedSpellContextState.context?.damage_preview || null);
  const effectDiceLabel =
    formatDamageDiceExpression(
      effectDiceSource,
      Boolean(result?.is_critical),
    ) ??
    effectDiceSource ??
    spellEffectDice;
  const pendingInstanceOutcomes =
    result?.effect_instance_outcomes?.filter((outcome) => outcome.needs_roll) ?? [];
  const effectRollCount =
    result?.pending_spell_id && pendingInstanceOutcomes.length > 0
      ? pendingInstanceOutcomes.reduce(
          (sum, outcome) =>
            sum + getDamageRollCount(effectDiceSource, Boolean(outcome.is_critical)),
          0,
        )
      : getDamageRollCount(effectDiceSource, Boolean(result?.is_critical));
  const effectRollSides = getDamageRollSides(effectDiceSource);
  const effectRollValues = Array.from({ length: effectRollSides }, (_, i) => i + 1);
  const effectKindLabel =
    result?.effect_kind === "healing" || spellMode === "heal"
      ? "cura"
      : spellMode === "utility"
        ? "efeito"
        : "dano";
  const effectiveMapState = mapState ?? spellMapState;
  const targetPositions = effectiveMapState?.tokens
    .filter((token) => token.combatant_id && token.position)
    .map((token) => {
      const participant = participants.find((entry) => entry.ref_id === token.combatant_id);
      return {
        refId: token.combatant_id ?? "",
        cell: token.position,
        displayName: participant?.display_name ?? token.label,
      };
    }) ?? [];
  const casterPosition = effectiveMapState ? resolveActorOriginCell(actor, effectiveMapState.tokens) : null;
  const singleTargetSpatialValidations =
    !isAreaSpell && !isMultiInstanceSpell
      ? buildSingleTargetSpatialValidations(rangePreview, target?.ref_id ?? null)
      : undefined;
  const mapPreviewModel = buildSpellMapPreviewModel({
    spellPreviewModel: previewModel,
    casterPosition,
    selectedTargetRefId: target?.ref_id ?? null,
    effectInstanceTargets: normalizedEffectInstanceTargets,
    existingAreaPreviewResult: preview,
    targetPositions,
    spatialValidations: {
      targets: singleTargetSpatialValidations,
      instances: multiInstanceSpatialValidations,
      area: isAreaSpell ? areaSpatialValidation : null,
    },
  });

  const instanceStatusSignature =
    mapPreviewModel.instanceStatuses
      ?.map((s) => `${s.instanceIndex}:${s.targetRefId ?? ""}:${s.status}:${s.reason ?? ""}`)
      .join("|") ?? "";

  const affectedSignature = `${mapPreviewModel.affectedTargetCount ?? ""}:${mapPreviewModel.affectedTargetNames?.join("|") ?? ""}`;

  const highlights = useMemo(
    () => buildSpellMapPreviewHighlights(mapPreviewModel, target?.ref_id ?? null),
    [
      mapPreviewModel.status,
      mapPreviewModel.reason,
      mapPreviewModel.areaShape,
      effectInstanceTargets,
      target?.ref_id,
      instanceStatusSignature,
      affectedSignature,
    ],
  );

  useEffect(() => {
    onMapPreviewChange?.(highlights);
  }, [highlights, onMapPreviewChange]);

  useEffect(() => {
    return () => onMapPreviewChange?.([]);
  }, [onMapPreviewChange]);

  useEffect(() => {
    setSelectedSlotLevel(spell.fixedCastLevel ?? (spell.level > 0 ? spell.level : null));
    setTargetingMode(createInitialTargetingMode(spell.areaShape, spell.selectionType));
    setSelectedVariantKey("");
    setTargetVariantAssignments([]);
    setEffectInstanceTargets([]);
    setError(null);
    handledSaveResolutionKeyRef.current = null;
    setAreaSpatialValidation(null);
    areaPreviewRequestGateRef.current.issue();
    previewCacheRef.current.clear();
    previewInFlightRef.current.clear();
  }, [spell.fixedCastLevel, spell.id, spell.level, spell.areaShape, spell.selectionType]);

  useEffect(() => {
    if (!isMultiInstanceSpell) {
      multiPreviewRequestGateRef.current.issue();
      setMultiInstanceSpatialValidations([]);
      setEffectInstanceTargets([]);
      return;
    }

    setEffectInstanceTargets((current) =>
      reconcileEffectInstanceTargets(current, effectInstanceContext.instanceCount, target?.ref_id),
    );
  }, [effectInstanceContext.instanceCount, isMultiInstanceSpell, target?.ref_id]);

  useEffect(() => {
    if (!isMultiInstanceSpell) {
      return;
    }

    const requestId = multiPreviewRequestGateRef.current.issue();
    const uniqueTargetRefIds = buildUniqueTargetRefIds(
      normalizedEffectInstanceTargets.map((entry) => entry.target_ref_id),
    );

    if (uniqueTargetRefIds.length === 0) {
      setMultiInstanceSpatialValidations([]);
      return;
    }

    void fetchPreviewValidationsWithCache({
      actorRefId: actor.ref_id,
      buildKey: (targetRefId) =>
        buildSpellPreviewFanoutKey({
          sessionId,
          actorRefId: actor.ref_id,
          spellId: spell.canonicalKey ?? spell.id,
          slotLevel: selectedSlotLevel,
          targetRefId,
        }),
      cache: previewCacheRef.current,
      inFlight: previewInFlightRef.current,
      previewAction: combatRepo.previewAction,
      rangeMeters: previewRangeMeters,
      sessionId,
      targetRefIds: uniqueTargetRefIds,
    }).then((validationsByTargetRefId) => {
      if (!multiPreviewRequestGateRef.current.isCurrent(requestId)) {
        return;
      }
      setMultiInstanceSpatialValidations(
        buildInstanceSpatialValidations(normalizedEffectInstanceTargets, validationsByTargetRefId),
      );
    });
  }, [
    actor.ref_id,
    isMultiInstanceSpell,
    normalizedEffectInstanceTargetsSignature,
    previewRangeMeters,
    selectedSlotLevel,
    sessionId,
    spell.canonicalKey,
  ]);

  useEffect(() => {
    if (!isAreaSpell || !anchorCell) {
      setAreaSpatialValidation(null);
      return;
    }

    const requestId = areaPreviewRequestGateRef.current.issue();

    void fetchAreaSpatialValidation({
      actorRefId: actor.ref_id,
      anchorCell,
      previewAction: combatRepo.previewAction,
      rangeMeters: previewRangeMeters,
      sessionId,
    }).then((validation) => {
      if (!areaPreviewRequestGateRef.current.isCurrent(requestId)) return;
      setAreaSpatialValidation(validation);
    });
  }, [actor.ref_id, anchorCell, isAreaSpell, previewRangeMeters, sessionId]);

  useEffect(() => {
    let cancelled = false;

    if (result) {
      return;
    }

    combatRepo
      .getMapState(sessionId, actorParticipantId)
      .then((nextMapState) => {
        if (cancelled) {
          return;
        }
        setSpellMapState(nextMapState);
      })
      .catch(() => {
        if (cancelled) {
          return;
        }
        setSpellMapState(null);
      });

    return () => {
      cancelled = true;
    };
  }, [actorParticipantId, result, sessionId]);

  useEffect(() => {
    if (!result?.pending_save_id || !actor.last_save_resolution) {
      return;
    }

    const resolution = actor.last_save_resolution;
    if (
      resolution.pending_save_id !== result.pending_save_id ||
      resolution.spell_name !== result.spell_name ||
      resolution.target_display_name !== result.target_display_name
    ) {
      return;
    }

    const resolutionKey = [
      resolution.spell_name,
      resolution.target_display_name,
      resolution.roll_total,
      resolution.pending_spell_id ?? "",
      resolution.damage,
      resolution.healing,
    ].join(":");
    if (handledSaveResolutionKeyRef.current === resolutionKey) {
      return;
    }
    handledSaveResolutionKeyRef.current = resolutionKey;

    const resolved = mergePendingSaveResolutionResult(result, resolution);

    setResult(resolved);
    setManualEffectRolls([]);
    setEffectMode("choose");
    void onResolved?.(resolved);
  }, [actor.last_save_resolution, onResolved, result]);

  const resolveConcentrationManualRoll = () =>
    shouldShowConcentrationControl && concentrationRollMode === "manual"
      ? Number.parseInt(concentrationManualRoll, 10) || null
      : null;

  const submitCast = async (payload?: { manual_roll?: number; roll_source?: "manual" | "system" }) => {
    if (isMultiInstanceSpell && !effectInstanceTargetsComplete) {
      setError(MULTI_INSTANCE_TARGET_ERROR);
      return;
    }
    if (isVariantSpell && !isVariantMultiTargetSpell && !selectedVariantKey) {
      setError("Escolha uma variante da magia antes de conjurar.");
      return;
    }
    if (isVariantMultiTargetSpell && !hasCompleteVariantAssignments) {
      setError("Escolha ao menos dois alvos e uma variante para cada um.");
      return;
    }
    if (isPlainMultiTargetAutomationSpell && selectedTargetIds.length === 0) {
      setError("Selecione ao menos um alvo.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const resolved = await combatRepo.castSpell(
        sessionId,
        isAreaSpell
          ? (() => {
              if (!anchorCell || !originCell) {
                throw new Error("Selecione uma area valida antes de conjurar.");
              }
              return {
                ...buildAreaCastPayload({
                  actorParticipantId,
                  spell,
                  spellMode,
                  selectedSlotLevel,
                  originCell,
                  anchorCell,
                  targetRefId: spell.areaShape
                    ? anchorTargetRefId
                    : pointSpellInitialTargetId,
                  spellEffectDice,
                  spellEffectBonus: parsedBonus,
                  spellDamageType,
                  spellSaveAbility,
                  concentrationRollSource: concentrationRollMode,
                  concentrationManualRoll: resolveConcentrationManualRoll(),
                }),
                roll_source: payload?.roll_source ?? "system",
                manual_roll: payload?.manual_roll ?? null,
              };
            })()
          : buildNonAreaSpellCastPayload({
              actorParticipantId,
              concentrationManualRoll: resolveConcentrationManualRoll(),
              concentrationRollMode,
              effectInstanceTargets: normalizedEffectInstanceTargets,
              isMultiInstanceSpell,
              isVariantMultiTargetSpell,
              isPlainMultiTargetAutomationSpell,
              plainTargetRefIds: selectedTargetIds,
              manualRoll: payload?.manual_roll ?? null,
              parsedBonus,
              rollSource: payload?.roll_source ?? "system",
              selectedSlotLevel,
              selectedVariantKey: selectedVariantKey || null,
              spell,
              spellDamageType,
              spellEffectDice,
              spellMode,
              spellSaveAbility,
              targetVariantAssignments,
              targetRefId: target?.ref_id ?? null,
            }),
      );
      setResult(resolved);
      setManualEffectRolls([]);
      setEffectMode("choose");
      if (resolved.pending_save_id) {
        await onResolved?.(resolved);
      } else if (!resolved.effect_roll_required) {
        await onResolved?.(resolved);
      }
    } catch (err: any) {
      setError(toPlayerFriendlyError(err?.data?.detail ?? err?.data ?? err?.message ?? "Falha ao conjurar magia"));
      setTargetingMode(isAreaSpell ? "area_target_select" : "single_target_select");
      setAttackMode("choose");
    } finally {
      setLoading(false);
    }
  };

  const submitEffect = async (payload: { manual_rolls?: number[]; roll_source: "manual" | "system" }) => {
    if (!result?.pending_spell_id) return;
    setLoading(true);
    setError(null);
    try {
      const resolved = await combatRepo.castSpellEffect(sessionId, {
        actor_participant_id: actorParticipantId,
        pending_spell_id: result.pending_spell_id,
        roll_source: payload.roll_source,
        manual_rolls: payload.manual_rolls ?? null,
        concentration_roll_source: concentrationRollMode,
        concentration_manual_roll: resolveConcentrationManualRoll(),
      });
      setResult(resolved);
      await onResolved?.(resolved);
    } catch (err: any) {
      setError(err?.data?.detail || err?.message || `Falha ao rolar ${effectKindLabel}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-slate-950/80 p-3 backdrop-blur-sm sm:p-4">
      <div className="my-auto flex max-h-[92vh] w-full max-w-3xl flex-col overflow-y-auto overscroll-contain rounded-2xl border border-fuchsia-400/30 bg-void-950 p-4 text-slate-100 shadow-2xl shadow-fuchsia-950/30 sm:p-5 [scrollbar-width:thin]">
        <SpellCastDialogHeader
          actionCostLabel={actionCostLabel}
          actorDisplayName={actor.display_name}
          anchorCell={anchorCell}
          concentrationManualRoll={concentrationManualRoll}
          concentrationRollMode={concentrationRollMode}
          error={error}
          isAreaSpell={isAreaSpell}
          loading={loading}
          mapPreviewModel={mapPreviewModel}
          onConcentrationManualRollChange={setConcentrationManualRoll}
          onConcentrationRollModeChange={setConcentrationRollMode}
          previewModel={previewModel}
          selectedSlotLevel={selectedSlotLevel}
          setSelectedSlotLevel={setSelectedSlotLevel}
          shouldShowConcentrationControl={shouldShowConcentrationControl}
          slotOptions={slotOptions}
          spell={spell}
          spellMode={spellMode}
          targetDisplayName={
            isMultiInstanceSpell || isVariantMultiTargetSpell
              ? "Múltiplos alvos"
              : target?.display_name ?? null
          }
          targetPreview={rangePreview}
          isPerTargetRangeSpell={
            isMultiInstanceSpell || isVariantMultiTargetSpell || isPlainMultiTargetAutomationSpell
          }
        />

        {!result && isVariantSpell && !isVariantMultiTargetSpell ? (
          <div className="mt-5 space-y-3 rounded-2xl border border-white/10 bg-slate-950/50 p-4">
            <div className="space-y-1">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-300">
                Variante da magia
              </p>
              <p className="text-xs text-slate-400">
                Escolha qual benefício será aplicado neste alvo.
              </p>
            </div>
            <select
              aria-label="Variante da magia"
              disabled={loading}
              value={selectedVariantKey}
              onChange={(event) => {
                setSelectedVariantKey(event.target.value);
                setError(null);
              }}
              className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none transition focus:border-fuchsia-400 disabled:opacity-50"
            >
              <option value="">Escolha uma variante</option>
              {spellVariants.map((variant) => (
                <option key={variant.key} value={variant.key}>
                  {variant.labelPt ?? variant.labelEn ?? variant.key}
                </option>
              ))}
            </select>
            {selectedVariantKey
              ? spellVariants
                  .filter((variant) => variant.key === selectedVariantKey)
                  .map((variant) => {
                    const summaryLines = formatSpellVariantSummaryLines(variant);
                    const label = variant.labelPt ?? variant.labelEn ?? variant.key;
                    return (
                      <div key={variant.key} className="rounded-2xl border border-fuchsia-500/15 bg-fuchsia-500/8 px-3 py-2">
                        <p className="text-sm font-semibold text-fuchsia-100">{label}</p>
                        {summaryLines.length ? (
                          <ul className="mt-2 space-y-1 text-xs text-slate-300">
                            {summaryLines.map((line, index) => (
                              <li key={`${variant.key}:${index}`}>{line}</li>
                            ))}
                          </ul>
                        ) : null}
                      </div>
                    );
                  })
              : null}
          </div>
        ) : null}

        {!result && isVariantMultiTargetSpell ? (
          <VariantTargetAssignmentSelector
            disabled={loading}
            maxTargets={maxTargets}
            participants={selectableParticipants}
            value={targetVariantAssignments}
            variants={spellVariants}
            onChange={(nextValue) => {
              setTargetVariantAssignments(nextValue);
              setError(null);
            }}
          />
        ) : null}

        {!result && isPlainMultiTargetAutomationSpell ? (
          <PlainMultiTargetSelector
            disabled={loading}
            maxTargets={maxTargets}
            participants={selectableParticipants}
            value={selectedTargetIds}
            onChange={(nextValue) => {
              setSelectedTargetIds(nextValue);
              setError(null);
            }}
          />
        ) : null}

        {!result && isMultiInstanceSpell ? (
          <InstanceTargetSelector
            disabled={loading}
            instanceCount={effectInstanceContext.instanceCount}
            instanceDice={effectInstanceContext.instanceDice}
            participants={selectableParticipants}
            spellCanonicalKey={spell.canonicalKey}
            value={normalizedEffectInstanceTargets}
            onChange={(nextValue) => {
              setEffectInstanceTargets(nextValue);
              setError(null);
            }}
          />
        ) : null}

        {!result && isAreaSpell ? (
          <AreaTargetingGrid
            actor={actor}
            anchorCell={anchorCell}
            canRevealHiddenTargets={canRevealHiddenTargets}
            mapError={mapError}
            mapLoading={mapLoading}
            mapState={mapState}
            originCell={originCell}
            participants={participants}
            previewAffectedCellCount={preview?.affected_cells.length ?? 0}
            previewAffectedTargetRefIds={preview?.affected_target_ref_ids ?? []}
            previewCells={preview?.affected_cells ?? []}
            previewError={previewError}
            previewLoading={previewLoading}
            previewReason={preview?.reason ?? null}
            previewValid={Boolean(preview?.is_valid)}
            sessionId={sessionId}
            spellHighlights={highlights}
            onCellSelected={(cell) => {
              setAnchorCell(cell);
              setPointSpellInitialTargetId(null);
              setTargetingMode("confirming");
            }}
          />
        ) : null}

        {isAreaSpell && !spell.areaShape && targetingMode === "confirming" && anchorCell && !result ? (
          <div className="mt-4 rounded-2xl border border-fuchsia-400/20 bg-fuchsia-500/8 px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-fuchsia-200">
              Posição da arma: ({anchorCell.x}, {anchorCell.y})
            </p>
            <div className="mt-3">
              <label className="block text-xs font-medium text-slate-300">Alvo inicial (opcional)</label>
              <select
                value={pointSpellInitialTargetId ?? ""}
                onChange={(e) => setPointSpellInitialTargetId(e.target.value || null)}
                className="mt-1 w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-sm text-white focus:border-fuchsia-400 focus:outline-none"
              >
                <option value="">Sem alvo inicial</option>
                {participants
                  .filter((p) => p.id !== actor.id && p.status !== "dead" && p.status !== "defeated")
                  .map((p) => (
                    <option key={p.id} value={p.ref_id ?? ""}>
                      {p.display_name}
                    </option>
                  ))}
              </select>
              <p className="mt-2 text-xs text-slate-500">
                O alvo deve estar adjacente à posição da arma. A validação final é feita pelo servidor.
              </p>
            </div>
          </div>
        ) : null}

        {result && result.pending_save_id ? (
          <div className="mt-4 rounded-2xl border border-fuchsia-500/30 bg-fuchsia-500/10 px-4 py-3 text-sm text-fuchsia-200">
            Magia conjurada. Aguardando o GM realizar o teste de resistencia de {target?.display_name ?? "alvo"}.
            <div className="mt-3 flex justify-end">
              <button
                type="button"
                onClick={onClose}
                className="rounded-full bg-white/10 border border-white/15 px-4 py-2 text-xs font-semibold uppercase tracking-widest text-white hover:bg-white/15"
              >
                Fechar
              </button>
            </div>
          </div>
        ) : result ? (
          <SpellCastResultPanel
            effectDiceLabel={effectDiceLabel}
            effectKindLabel={effectKindLabel}
            effectMode={effectMode}
            effectRollCount={effectRollCount}
            effectRollValues={effectRollValues}
            loading={loading}
            manualEffectRolls={manualEffectRolls}
            onClose={onClose}
            onEffectModeChange={setEffectMode}
            onManualEffectRollsChange={setManualEffectRolls}
            onSubmitEffect={(payload) => {
              void submitEffect(payload);
            }}
            result={result}
          />
        ) : null}

        {!result ? (
          <div className="sticky bottom-0 z-10 -mx-4 -mb-4 mt-2 border-t border-white/5 bg-void-950/95 px-4 pb-4 pt-3 backdrop-blur sm:-mx-5 sm:px-5">
          <SpellCastDialogActions
            attackMode={attackMode}
            canSubmitArea={canSubmitArea}
            hasError={!!error || mapPreviewModel?.status === "invalid"}
            isAreaSpell={isAreaSpell}
            loading={loading}
            onAttackModeChange={setAttackMode}
            onCancel={onClose}
            onClearArea={() => {
              clearAreaSelection();
              setPointSpellInitialTargetId(null);
              setTargetingMode("area_target_select");
              setError(null);
            }}
            onShowAreaHint={isAreaSpell && targetingMode === "area_target_select"}
            onSubmitCast={(payload) => {
              if (payload) {
                void submitCast(payload);
                return;
              }
              setTargetingMode(isAreaSpell ? "confirming" : "single_target_select");
              void submitCast();
            }}
            spellMode={spellMode}
            spellOutOfRange={spellOutOfRange}
            submitDisabled={
              !spellContextReady ||
              (isMultiInstanceSpell && !effectInstanceTargetsComplete) ||
              (isVariantSpell && !isVariantMultiTargetSpell && !selectedVariantKey) ||
              (isVariantMultiTargetSpell && !hasCompleteVariantAssignments) ||
              (isPlainMultiTargetAutomationSpell && selectedTargetIds.length === 0)
            }
            validationMessage={
              !spellContextReady
                ? "Resolvendo contexto da magia..."
                : isMultiInstanceSpell && !effectInstanceTargetsComplete
                  ? MULTI_INSTANCE_TARGET_ERROR
                  : isVariantSpell && !isVariantMultiTargetSpell && !selectedVariantKey
                    ? "Escolha uma variante da magia."
                    : isVariantMultiTargetSpell && !hasCompleteVariantAssignments
                      ? "Escolha ao menos dois alvos e uma variante para cada um."
                  : null
            }
          />
          </div>
        ) : null}
      </div>
    </div>
  );
};
