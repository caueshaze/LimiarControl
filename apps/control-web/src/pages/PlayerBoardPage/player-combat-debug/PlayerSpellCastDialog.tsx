import { useEffect, useMemo, useState } from "react";
import type { AbilityName } from "../../../entities/roll/rollResolution.types";
import { ConcentrationSaveControl } from "../../../features/combat-ui/components/ConcentrationSaveControl";
import { CombatMapFrame } from "../../../features/combat-ui/map/CombatMapFrame";
import { participantHasActiveConcentration } from "../../../features/combat-ui/combatUi.helpers";
import type {
  CombatAreaPreviewResponse,
  CombatMapPreviewState,
  CombatParticipant,
  CombatSpellMode,
  CombatSpellResult,
} from "../../../shared/api/combatRepo";
import { combatRepo } from "../../../shared/api/combatRepo";
import { toPlayerFriendlyError } from "../../../features/combat-ui/combatErrors";
import {
  getDamageRollCount,
  getDamageRollSides,
  formatDamageDiceExpression,
} from "../../../shared/utils/diceExpression";
import {
  buildAreaCastPayload,
  buildAreaPreviewPayload,
  createInitialTargetingMode,
  getAnchorCombatantIdAtCell,
  isAreaTargetMode,
  resolveActorOriginCell,
  type GridCell,
} from "./areaTargetingUi";
import { D20_VALUES, parseBonus } from "./spellCastHelpers";
import { SpellCastResultPanel } from "./SpellCastResultPanel";
import type { CombatSpellOption } from "./types";

type Props = {
  actor: CombatParticipant;
  actorParticipantId: string;
  onClose: () => void;
  onResolved?: (result: CombatSpellResult) => void | Promise<void>;
  sessionId: string;
  spell: CombatSpellOption;
  spellDamageType: string;
  spellEffectBonus: string;
  spellEffectDice: string;
  spellMode: CombatSpellMode;
  spellSaveAbility: AbilityName | "";
  target?: CombatParticipant | null;
};

const AREA_PREVIEW_DEBOUNCE_MS = 220;

const cellKey = (cell: GridCell) => `${cell.x}:${cell.y}`;

export const PlayerSpellCastDialog = ({
  actor,
  actorParticipantId,
  onClose,
  onResolved,
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
  const [result, setResult] = useState<CombatSpellResult | null>(null);
  const [targetingMode, setTargetingMode] = useState(createInitialTargetingMode(spell.targetMode));
  const [mapState, setMapState] = useState<CombatMapPreviewState | null>(null);
  const [mapLoading, setMapLoading] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);
  const [anchorCell, setAnchorCell] = useState<GridCell | null>(null);
  const [preview, setPreview] = useState<CombatAreaPreviewResponse | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  const isAreaSpell = isAreaTargetMode(spell.targetMode);
  const targetHasConcentration = target ? participantHasActiveConcentration(target) : false;
  const shouldShowConcentrationControl = targetHasConcentration && spellMode !== "heal" && spellMode !== "utility";
  const slotOptions = spell.availableSlotLevels.length > 0 ? spell.availableSlotLevels : (spell.level > 0 ? [spell.level] : []);
  const parsedBonus = parseBonus(spellEffectBonus);
  const actionCostLabel =
    spell.actionCost === "bonus_action"
      ? "Bonus Action"
      : spell.actionCost === "reaction"
        ? "Reaction"
        : spell.actionCost === "free"
          ? "Free"
          : "Action";

  useEffect(() => {
    setSelectedSlotLevel(spell.fixedCastLevel ?? (spell.level > 0 ? spell.level : null));
    setTargetingMode(createInitialTargetingMode(spell.targetMode));
    setAnchorCell(null);
    setPreview(null);
    setPreviewError(null);
    setMapError(null);
    setError(null);
  }, [spell.fixedCastLevel, spell.id, spell.level, spell.targetMode]);

  useEffect(() => {
    if (!isAreaSpell || result) {
      return;
    }
    let active = true;
    setMapLoading(true);
    setMapError(null);
    combatRepo
      .getMapState(sessionId, actorParticipantId)
      .then((nextMapState) => {
        if (!active) return;
        setMapState(nextMapState);
      })
      .catch((err: any) => {
        if (!active) return;
        setMapError(err?.data?.detail || err?.message || "Falha ao carregar o mapa para area.");
        setMapState(null);
      })
      .finally(() => {
        if (active) {
          setMapLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [actorParticipantId, isAreaSpell, result, sessionId]);

  const originCell = useMemo(
    () => (mapState ? resolveActorOriginCell(actor, mapState.tokens) : null),
    [actor, mapState],
  );
  const anchorTargetRefId = useMemo(
    () => (anchorCell && mapState ? getAnchorCombatantIdAtCell(mapState.tokens, anchorCell) : null),
    [anchorCell, mapState],
  );

  useEffect(() => {
    if (!isAreaSpell || !anchorCell || !originCell || !mapState || result) {
      return;
    }
    let active = true;
    const timeout = window.setTimeout(() => {
      setPreviewLoading(true);
      setPreviewError(null);
      combatRepo
        .previewAreaSpell(
          sessionId,
          buildAreaPreviewPayload({
            actorParticipantId,
            spell,
            spellMode,
            selectedSlotLevel,
            originCell,
            anchorCell,
            targetRefId: anchorTargetRefId,
          }),
        )
        .then((nextPreview) => {
          if (!active) return;
          setPreview(nextPreview);
        })
        .catch((err: any) => {
          if (!active) return;
          setPreview(null);
          setPreviewError(err?.data?.detail || err?.message || "Falha ao gerar preview da area.");
        })
        .finally(() => {
          if (active) {
            setPreviewLoading(false);
          }
        });
    }, AREA_PREVIEW_DEBOUNCE_MS);

    return () => {
      active = false;
      window.clearTimeout(timeout);
    };
  }, [
    actorParticipantId,
    anchorCell,
    anchorTargetRefId,
    isAreaSpell,
    mapState,
    originCell,
    result,
    selectedSlotLevel,
    sessionId,
    spell,
    spellMode,
  ]);

  const effectDiceLabel =
    formatDamageDiceExpression(result?.effect_dice ?? spellEffectDice, Boolean(result?.is_critical)) ??
    result?.effect_dice ??
    spellEffectDice;
  const effectRollCount = getDamageRollCount(result?.effect_dice ?? spellEffectDice, Boolean(result?.is_critical));
  const effectRollSides = getDamageRollSides(result?.effect_dice ?? spellEffectDice);
  const effectRollValues = Array.from({ length: effectRollSides }, (_, i) => i + 1);
  const effectKindLabel =
    result?.effect_kind === "healing" || spellMode === "heal"
      ? "cura"
      : spellMode === "utility"
        ? "efeito"
        : "dano";
  const previewCellKeys = useMemo(
    () => new Set((preview?.affected_cells ?? []).map(cellKey)),
    [preview],
  );
  const canSubmitArea = Boolean(
    !loading &&
    anchorCell &&
    originCell &&
    preview?.is_valid,
  );

  const submitCast = async (payload?: {
    manual_roll?: number;
    roll_source?: "manual" | "system";
  }) => {
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
                  concentrationManualRoll:
                    shouldShowConcentrationControl && concentrationRollMode === "manual"
                      ? Number.parseInt(concentrationManualRoll, 10) || null
                      : null,
                }),
                roll_source: payload?.roll_source ?? "system",
                manual_roll: payload?.manual_roll ?? null,
              };
            })()
          : {
              actor_participant_id: actorParticipantId,
              target_ref_id: target?.ref_id,
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
              roll_source: payload?.roll_source ?? "system",
              manual_roll: payload?.manual_roll ?? null,
              damage_dice: spellMode === "heal" ? null : spellEffectDice || null,
              damage_bonus: spellMode === "heal" ? null : parsedBonus,
              heal_dice: spellMode === "heal" ? spellEffectDice || null : null,
              heal_bonus: spellMode === "heal" ? parsedBonus : null,
              damage_type: spellMode === "heal" ? null : spellDamageType || null,
              save_ability: spellMode === "saving_throw" ? spellSaveAbility || null : null,
              concentration_roll_source: concentrationRollMode,
              concentration_manual_roll:
                shouldShowConcentrationControl && concentrationRollMode === "manual"
                  ? Number.parseInt(concentrationManualRoll, 10) || null
                  : null,
            },
      );
      setResult(resolved);
      setManualEffectRolls([]);
      setEffectMode("choose");
      if (!resolved.effect_roll_required) {
        await onResolved?.(resolved);
      }
    } catch (err: any) {
      setError(toPlayerFriendlyError(err?.data?.detail || err?.message || "Falha ao conjurar magia"));
      setTargetingMode(isAreaSpell ? "area_target_select" : "single_target_select");
    } finally {
      setLoading(false);
    }
  };

  const submitEffect = async (payload: {
    manual_rolls?: number[];
    roll_source: "manual" | "system";
  }) => {
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
        concentration_manual_roll:
          shouldShowConcentrationControl && concentrationRollMode === "manual"
            ? Number.parseInt(concentrationManualRoll, 10) || null
            : null,
      });
      setResult(resolved);
      await onResolved?.(resolved);
    } catch (err: any) {
      setError(err?.data?.detail || err?.message || `Falha ao rolar ${effectKindLabel}`);
    } finally {
      setLoading(false);
    }
  };

  const renderAreaGrid = () => {
    if (mapLoading) {
      return <p className="mt-4 text-sm text-slate-400">Carregando mapa...</p>;
    }
    if (mapError) {
      return (
        <div className="mt-4 rounded-2xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
          {mapError}
        </div>
      );
    }
    if (!mapState) {
      return null;
    }

    return (
      <div className="mt-4 space-y-3">
        <div className="flex items-center justify-between gap-3 text-xs text-slate-400">
          <span>Selecione a celula ancora diretamente no mapa.</span>
          <span>
            {previewLoading
              ? "Atualizando preview..."
              : preview?.is_valid
                ? `${preview.affected_cells.length} celulas · ${preview.affected_target_ref_ids.length} alvos`
                : preview?.reason ?? "Sem preview"}
          </span>
        </div>
        <CombatMapFrame
          sessionId={sessionId}
          title="Mapa tatico"
          hint={
            anchorCell
              ? `Ancora selecionada em (${anchorCell.x}, ${anchorCell.y}). Clique em outra celula para reposicionar.`
              : "Clique em qualquer celula do mapa para escolher a ancora da magia."
          }
          actor={{
            actorId: actor.actor_user_id ?? actor.ref_id,
            actorType: actor.kind === "player" ? "player" : "gm",
          }}
          selectionMode="select-cell"
          previewCells={preview?.affected_cells ?? []}
          selectedCell={anchorCell}
          className="rounded-2xl border border-white/10 bg-slate-950/70 p-3"
          frameClassName="h-[420px] w-full border-0 bg-slate-950"
          onCellSelected={({ cell }) => {
            setAnchorCell(cell);
            setPreview(null);
            setPreviewError(null);
            setTargetingMode("confirming");
          }}
        />
        <div className="flex flex-wrap gap-3 text-xs text-slate-400">
          <span className="rounded-full border border-fuchsia-400/30 px-3 py-1 text-fuchsia-100">Ancora</span>
          <span className="rounded-full border border-amber-400/30 px-3 py-1 text-amber-100">Preview</span>
          {originCell ? (
            <span className="rounded-full border border-sky-400/30 px-3 py-1 text-sky-100">
              Origem ({originCell.x}, {originCell.y})
            </span>
          ) : null}
        </div>
        {previewError ? (
          <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            {previewError}
          </div>
        ) : null}
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 px-4">
      <div className="w-full max-w-4xl rounded-3xl border border-fuchsia-400/30 bg-void-950 p-6 text-slate-100 shadow-2xl shadow-fuchsia-950/30">
        <p className="text-xs uppercase tracking-[0.3em] text-fuchsia-200">Magia</p>
        <h2 className="mt-3 text-2xl font-semibold text-white">{spell.name}</h2>
        <p className="mt-2 text-sm text-slate-300">
          {isAreaSpell
            ? `Origem: ${actor.display_name}${anchorCell ? ` · Ancora: (${anchorCell.x}, ${anchorCell.y})` : ""}`
            : (
              <>
                Alvo: <span className="font-semibold text-white">{target?.display_name ?? "Nenhum"}</span>
              </>
            )}
        </p>
        {spell.sourceType === "magic_item" && spell.sourceItemName ? (
          <p className="mt-1 text-sm text-slate-400">
            Item: <span className="font-semibold text-white">{spell.sourceItemName}</span>
            {typeof spell.chargesCurrent === "number" && typeof spell.chargesMax === "number"
              ? ` · ${spell.chargesCurrent}/${spell.chargesMax}`
              : ""}
          </p>
        ) : null}
        <p className="mt-1 text-sm text-slate-400">
          Fluxo: {spellMode.replace(/_/g, " ")}
          {spellMode !== "heal" && spellMode !== "utility" && spellDamageType ? ` · ${spellDamageType}` : ""}
          {spellMode === "saving_throw" && spellSaveAbility ? ` · save ${spellSaveAbility}` : ""}
          {isAreaSpell && spell.targetMode ? ` · ${spell.targetMode}` : ""}
        </p>
        <p className="mt-1 text-xs uppercase tracking-[0.2em] text-fuchsia-200/80">
          {actionCostLabel}
        </p>
        {spell.sourceType === "magic_item" && spell.fixedCastLevel ? (
          <p className="mt-4 text-xs uppercase tracking-[0.18em] text-slate-400">
            Item cast level: {spell.fixedCastLevel}
          </p>
        ) : null}
        {spell.level > 0 && spell.sourceType !== "magic_item" ? (
          <label className="mt-4 block">
            <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
              Slot level
            </span>
            <select
              value={selectedSlotLevel ?? spell.level}
              onChange={(event) => setSelectedSlotLevel(Number.parseInt(event.target.value, 10))}
              className="mt-2 w-full rounded-2xl border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none transition focus:border-fuchsia-400"
            >
              {slotOptions.map((slotLevel) => (
                <option key={slotLevel} value={slotLevel}>
                  {slotLevel}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        {shouldShowConcentrationControl ? (
          <div className="mt-4">
            <ConcentrationSaveControl
              disabled={loading}
              manualValue={concentrationManualRoll}
              mode={concentrationRollMode}
              onManualValueChange={setConcentrationManualRoll}
              onModeChange={setConcentrationRollMode}
            />
          </div>
        ) : null}

        {error ? (
          <div className="mt-4 rounded-2xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            {error}
          </div>
        ) : null}

        {!result && isAreaSpell ? renderAreaGrid() : null}

        {result ? (
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
            onSubmitEffect={(payload) => { void submitEffect(payload); }}
            result={result}
          />
        ) : null}

        {!result && !isAreaSpell && spellMode === "spell_attack" && attackMode === "choose" ? (
          <div className="mt-5 grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setAttackMode("virtual")}
              className="rounded-2xl bg-fuchsia-600 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white hover:bg-fuchsia-500"
            >
              Virtual
            </button>
            <button
              type="button"
              onClick={() => setAttackMode("manual")}
              className="rounded-2xl border border-slate-600 bg-slate-800 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-slate-200 hover:bg-slate-700"
            >
              Manual
            </button>
          </div>
        ) : null}

        {!result && !isAreaSpell && spellMode === "spell_attack" && attackMode === "virtual" ? (
          <div className="mt-5 flex gap-3">
            <button
              type="button"
              disabled={loading}
              onClick={() => { void submitCast({ roll_source: "system" }); }}
              className="flex-1 rounded-full bg-fuchsia-600 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white disabled:opacity-50"
            >
              {loading ? "..." : "Rolar ataque magico"}
            </button>
            <button
              type="button"
              onClick={() => setAttackMode("choose")}
              className="rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400"
            >
              Voltar
            </button>
          </div>
        ) : null}

        {!result && !isAreaSpell && spellMode === "spell_attack" && attackMode === "manual" ? (
          <div className="mt-5 space-y-3">
            <p className="text-xs text-slate-400">Selecione o d20 manual do ataque.</p>

            <div className="grid grid-cols-5 gap-2">
              {D20_VALUES.map((value) => (
                <button
                  key={value}
                  type="button"
                  disabled={loading}
                  onClick={() => { void submitCast({ roll_source: "manual", manual_roll: value }); }}
                  className="rounded-xl border border-slate-700 bg-slate-900 px-2 py-3 text-center text-lg font-bold text-white transition-colors hover:border-fuchsia-500/50 hover:bg-slate-800 disabled:opacity-50"
                >
                  {value}
                </button>
              ))}
            </div>

            <button
              type="button"
              onClick={() => setAttackMode("choose")}
              className="rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400"
            >
              Voltar
            </button>
          </div>
        ) : null}

        {!result && ((isAreaSpell && spellMode !== "spell_attack") || (!isAreaSpell && spellMode !== "spell_attack")) ? (
          <div className="mt-5 flex gap-3">
            <button
              type="button"
              disabled={isAreaSpell ? !canSubmitArea : loading}
              onClick={() => {
                setTargetingMode(isAreaSpell ? "confirming" : "single_target_select");
                void submitCast();
              }}
              className="flex-1 rounded-full bg-fuchsia-600 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white disabled:opacity-50"
            >
              {loading ? "..." : "Conjurar"}
            </button>
            {isAreaSpell ? (
              <button
                type="button"
                onClick={() => {
                  setAnchorCell(null);
                  setPreview(null);
                  setPreviewError(null);
                  setTargetingMode("area_target_select");
                }}
                className="rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400"
              >
                Limpar area
              </button>
            ) : null}
            <button
              type="button"
              onClick={onClose}
              className="rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400"
            >
              Cancelar
            </button>
          </div>
        ) : null}

        {!result && isAreaSpell && targetingMode === "area_target_select" ? (
          <p className="mt-3 text-xs text-slate-500">
            Clique no grid para escolher a ancora. O preview usa o Map como autoridade geometrica.
          </p>
        ) : null}
      </div>
    </div>
  );
};
