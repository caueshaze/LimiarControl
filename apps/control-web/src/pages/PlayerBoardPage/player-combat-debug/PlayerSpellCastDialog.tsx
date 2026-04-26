import { useEffect, useMemo, useRef, useState } from "react";
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
import { SpellCastDialogActions } from "./SpellCastDialogActions";
import { parseBonus } from "./spellCastHelpers";
import { SpellCastDialogHeader } from "./SpellCastDialogHeader";
import { SpellCastResultPanel } from "./SpellCastResultPanel";
import { buildSpellMapPreviewModel } from "./spellMapPreviewModel";
import { buildSpellMapPreviewHighlights } from "./spellMapPreviewHighlights";
import type { SpellMapHighlight } from "../../../features/combat-ui/map/CombatMapFrame";
import { buildSpellPreviewModel } from "./spellPreviewModel";
import type { CombatSpellOption } from "./types";
import { useAreaTargeting } from "./useAreaTargeting";
import { useResolvedSpellContext } from "./useResolvedSpellContext";

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
  manualRoll?: number | null;
  parsedBonus: number;
  rollSource?: "manual" | "system";
  selectedSlotLevel: number | null;
  spell: CombatSpellOption;
  spellDamageType: string;
  spellEffectDice: string;
  spellMode: CombatSpellMode;
  spellSaveAbility: AbilityName | "";
  targetRefId?: string | null;
};

export const buildNonAreaSpellCastPayload = ({
  actorParticipantId,
  concentrationManualRoll,
  concentrationRollMode,
  effectInstanceTargets,
  isMultiInstanceSpell,
  manualRoll = null,
  parsedBonus,
  rollSource = "system",
  selectedSlotLevel,
  spell,
  spellDamageType,
  spellEffectDice,
  spellMode,
  spellSaveAbility,
  targetRefId = null,
}: BuildNonAreaSpellCastPayloadParams): CombatCastSpellRequest => ({
  actor_participant_id: actorParticipantId,
  target_ref_id: isMultiInstanceSpell ? effectInstanceTargets[0]?.target_ref_id ?? targetRefId ?? null : targetRefId,
  effect_instance_targets: isMultiInstanceSpell ? effectInstanceTargets : null,
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
  const [effectInstanceTargets, setEffectInstanceTargets] = useState<EffectInstanceTargetInput[]>([]);
  const [result, setResult] = useState<CombatSpellResult | null>(null);
  const [spellMapState, setSpellMapState] = useState<Awaited<ReturnType<typeof combatRepo.getMapState>> | null>(null);
  const [targetingMode, setTargetingMode] = useState(createInitialTargetingMode(spell.areaShape, spell.selectionType));
  const handledSaveResolutionKeyRef = useRef<string | null>(null);

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
  const selectableParticipants = participants.filter((participant) => participant.id !== actor.id);
  const normalizedEffectInstanceTargets = normalizeEffectInstanceTargets(
    effectInstanceTargets,
    effectInstanceContext.instanceCount,
  );
  const effectInstanceTargetsComplete = hasCompleteEffectInstanceTargets(
    effectInstanceTargets,
    effectInstanceContext.instanceCount,
  );
  const rangePreview = useTargetingPreview({
    sessionId,
    actorRefId: actor.ref_id,
    targetRefId: target?.ref_id ?? null,
    actionType: "spell",
    normalRangeMeters: spell.rangeMeters ?? null,
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
      ? "Bonus Action"
      : spell.actionCost === "reaction"
        ? "Reaction"
        : spell.actionCost === "free"
          ? "Free"
          : "Action";
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
  const effectRollCount = getDamageRollCount(effectDiceSource, Boolean(result?.is_critical));
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
  const mapPreviewModel = buildSpellMapPreviewModel({
    spellPreviewModel: previewModel,
    casterPosition,
    selectedTargetRefId: target?.ref_id ?? null,
    effectInstanceTargets: normalizedEffectInstanceTargets,
    existingAreaPreviewResult: preview,
    targetPositions,
  });

  // Derive map highlights from the preview model. Deps are the primitive fields
  // that drive content changes, plus effectInstanceTargets (state) for per-instance changes.
  const highlights = useMemo(
    () => buildSpellMapPreviewHighlights(mapPreviewModel, target?.ref_id ?? null),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [mapPreviewModel.status, mapPreviewModel.reason, mapPreviewModel.areaShape, effectInstanceTargets, target?.ref_id],
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
    setEffectInstanceTargets([]);
    setError(null);
    handledSaveResolutionKeyRef.current = null;
  }, [spell.fixedCastLevel, spell.id, spell.level, spell.areaShape, spell.selectionType]);

  useEffect(() => {
    if (!isMultiInstanceSpell) {
      setEffectInstanceTargets([]);
      return;
    }

    setEffectInstanceTargets((current) =>
      reconcileEffectInstanceTargets(current, effectInstanceContext.instanceCount, target?.ref_id),
    );
  }, [effectInstanceContext.instanceCount, isMultiInstanceSpell, target?.ref_id]);

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

    const resolved: CombatSpellResult = {
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
    };

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
                  targetRefId: anchorTargetRefId,
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
              manualRoll: payload?.manual_roll ?? null,
              parsedBonus,
              rollSource: payload?.roll_source ?? "system",
              selectedSlotLevel,
              spell,
              spellDamageType,
              spellEffectDice,
              spellMode,
              spellSaveAbility,
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
      setError(toPlayerFriendlyError(err?.data?.detail || err?.message || "Falha ao conjurar magia"));
      setTargetingMode(isAreaSpell ? "area_target_select" : "single_target_select");
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 px-4">
      <div className="w-full max-w-4xl rounded-3xl border border-fuchsia-400/30 bg-void-950 p-6 text-slate-100 shadow-2xl shadow-fuchsia-950/30">
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
          targetDisplayName={isMultiInstanceSpell ? "Múltiplos alvos" : target?.display_name ?? null}
          targetPreview={rangePreview}
        />

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
              setTargetingMode("confirming");
            }}
          />
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
          <SpellCastDialogActions
            attackMode={attackMode}
            canSubmitArea={canSubmitArea}
            isAreaSpell={isAreaSpell}
            loading={loading}
            onAttackModeChange={setAttackMode}
            onCancel={onClose}
            onClearArea={() => {
              clearAreaSelection();
              setTargetingMode("area_target_select");
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
            submitDisabled={!spellContextReady || (isMultiInstanceSpell && !effectInstanceTargetsComplete)}
            validationMessage={
              !spellContextReady
                ? "Resolvendo contexto da magia..."
                : isMultiInstanceSpell && !effectInstanceTargetsComplete
                  ? MULTI_INSTANCE_TARGET_ERROR
                  : null
            }
          />
        ) : null}
      </div>
    </div>
  );
};
