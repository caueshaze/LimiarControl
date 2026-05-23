import { ConcentrationSaveControl } from "../../../features/combat-ui/components/ConcentrationSaveControl";
import { RangeStatusBadge } from "../../../features/combat-ui/components/RangeStatusBadge";
import { SpellSlotSummary } from "../../../shared/ui/SpellSlotSummary";
import type { TargetingPreviewResult } from "../../../features/combat-ui/hooks/useTargetingPreview";
import type { CombatSpellMode } from "../../../shared/api/combatRepo";
import { getInstanceLabel } from "./InstanceTargetSelector";
import type { GridCell } from "./areaTargetingUi";
import type { SpellMapPreviewModel } from "./spellMapPreviewModel";
import {
  formatAreaOriginPreviewLabel,
  formatAreaTargetEffectiveDcLine,
  formatSpellCoverPreview,
  formatSpellMapPreviewReason,
  formatSpellMapPreviewStatus,
  formatTargetList,
  resolveCoverContext,
} from "./spellMapPreviewPresentation";
import { localizeDamageType } from "../../../shared/i18n/domainLabels";
import type { SpellPreviewModel } from "./spellPreviewModel";
import type { CombatSpellOption } from "./types";

type Props = {
  actionCostLabel: string;
  actorDisplayName: string;
  anchorCell: GridCell | null;
  concentrationManualRoll: string;
  concentrationRollMode: "system" | "manual";
  error: string | null;
  isAreaSpell: boolean;
  loading: boolean;
  mapPreviewModel: SpellMapPreviewModel | null;
  onConcentrationManualRollChange: (value: string) => void;
  onConcentrationRollModeChange: (value: "system" | "manual") => void;
  previewModel: SpellPreviewModel;
  selectedSlotLevel: number | null;
  setSelectedSlotLevel: (value: number) => void;
  shouldShowConcentrationControl: boolean;
  slotOptions: number[];
  spell: CombatSpellOption;
  spellMode: CombatSpellMode;
  targetDisplayName?: string | null;
  targetPreview: TargetingPreviewResult;
};

const formatRangeMeters = (meters: number | null): string | null =>
  meters === null ? null : `${Number.isInteger(meters) ? meters : meters.toFixed(1)}m`;

const formatAreaSizeMeters = (
  shape: SpellPreviewModel["areaShape"],
  meters: number | null,
): string | null => {
  if (!shape || meters === null) return null;
  const formatted = Number.isInteger(meters) ? `${meters}m` : `${meters.toFixed(1)}m`;
  if (shape === "sphere" || shape === "cylinder") return `raio ${formatted}`;
  if (shape === "line") return `comprimento ${formatted}`;
  if (shape === "cube") return `lado ${formatted}`;
  if (shape === "cone") return `cone ${formatted}`;
  return formatted;
};

const MAP_PREVIEW_STYLES: Record<SpellMapPreviewModel["status"], string> = {
  valid: "border-emerald-500/30 bg-emerald-500/10 text-emerald-100",
  invalid: "border-rose-500/30 bg-rose-500/10 text-rose-100",
  partial: "border-amber-500/30 bg-amber-500/10 text-amber-100",
  unknown: "border-slate-600/50 bg-slate-900/40 text-slate-200",
};

const formatResolutionType = (
  resolutionType: SpellPreviewModel["resolutionType"],
): string => {
  switch (resolutionType) {
    case "spell_attack":
      return "ataque";
    case "saving_throw":
      return "saving throw";
    case "direct_damage":
      return "dano direto";
    case "heal":
      return "cura";
    case "utility":
      return "efeito";
    default:
      return "—";
  }
};

export const SpellCastDialogHeader = ({
  actionCostLabel,
  actorDisplayName,
  anchorCell,
  concentrationManualRoll,
  concentrationRollMode,
  error,
  isAreaSpell,
  loading,
  mapPreviewModel,
  onConcentrationManualRollChange,
  onConcentrationRollModeChange,
  previewModel,
  selectedSlotLevel,
  setSelectedSlotLevel,
  shouldShowConcentrationControl,
  slotOptions,
  spell,
  spellMode,
  targetDisplayName,
  targetPreview,
}: Props) => {
  const flowDamageType =
    spellMode !== "heal" && spellMode !== "utility" && previewModel.damageType
      ? localizeDamageType(previewModel.damageType, "pt-BR")
      : null;
  const flowSaveAbility =
    previewModel.requiresSavingThrow && previewModel.saveAbility 
      ? previewModel.saveAbility.substring(0, 3).toUpperCase() 
      : null;
  const flowAreaShape = isAreaSpell && previewModel.areaShape ? previewModel.areaShape : null;
  const showInstanceCount =
    previewModel.effectInstanceCount > 1 && previewModel.source === "resolved";
  const rangeLabel = formatRangeMeters(previewModel.rangeMeters);
  const areaSizeLabel = isAreaSpell
    ? formatAreaSizeMeters(previewModel.areaShape, previewModel.areaSizeMeters)
    : null;
  const resolutionLabel = formatResolutionType(previewModel.resolutionType);
  const mapPreviewReason = mapPreviewModel
    ? formatSpellMapPreviewReason(mapPreviewModel.reason, mapPreviewModel.status)
    : null;
  const coverContext = resolveCoverContext(spellMode, previewModel.coverAppliesToSave);
  const coverLabel = mapPreviewModel?.cover
    ? formatSpellCoverPreview(mapPreviewModel.cover, coverContext)
    : null;
  const selectedSlotSummary =
    selectedSlotLevel != null
      ? spell.slotSummary?.find((entry) => entry.level === selectedSlotLevel) ?? null
      : null;
  const hasSlotCost = spell.sourceType !== "magic_item" && spell.level > 0;

  return (
    <>
      <div className="mb-6 border-b border-fuchsia-900/30 pb-4">
        <p className="text-[10px] font-semibold uppercase tracking-[0.3em] text-fuchsia-200/70">
          Magia
        </p>
        <h2 className="mt-1 text-3xl font-semibold text-white">{spell.name}</h2>
        {spell.sourceType === "magic_item" && spell.fixedCastLevel ? (
          <p className="mt-1 text-xs uppercase tracking-[0.18em] text-fuchsia-400/80">
            Nível Fixo do Item: {spell.fixedCastLevel}
          </p>
        ) : null}
      </div>

      <div className="mb-6 grid grid-cols-2 gap-y-4 gap-x-6">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
            Alvo
          </p>
          <p className="mt-1 text-sm font-semibold text-white">
            {isAreaSpell
              ? `Origem: ${actorDisplayName}${anchorCell ? ` · Ancora: (${anchorCell.x}, ${anchorCell.y})` : ""}`
              : targetDisplayName ?? "Nenhum"}
          </p>
        </div>

        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
            Custo
          </p>
          <p className="mt-1 text-sm text-slate-300">
            {actionCostLabel}
          </p>
        </div>

        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
            Fluxo
          </p>
          <p className="mt-1 text-sm text-slate-300">
            {resolutionLabel}
            {flowDamageType ? ` · ${flowDamageType}` : ""}
            {flowSaveAbility ? ` · save ${flowSaveAbility}` : ""}
            {flowAreaShape ? ` · ${flowAreaShape}` : ""}
          </p>
        </div>

        {spell.sourceType === "magic_item" && spell.sourceItemName ? (
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
              Item de Origem
            </p>
            <p className="mt-1 text-sm text-slate-300">
              {spell.sourceItemName}
              {typeof spell.chargesCurrent === "number" && typeof spell.chargesMax === "number"
                ? ` (${spell.chargesCurrent}/${spell.chargesMax} cargas)`
                : ""}
            </p>
          </div>
        ) : null}
      </div>

      {spell.sourceType !== "magic_item" ? (
        <div className="mb-6 rounded-2xl border border-white/8 bg-white/4 px-4 py-4">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
            Recursos
          </p>
          {spell.level === 0 ? (
            <p className="mt-2 text-sm font-semibold text-emerald-100">Truque - sem custo de slot</p>
          ) : hasSlotCost && spell.availableSlotLevels.length === 0 ? (
            <p className="mt-2 text-sm font-semibold text-rose-200">Sem slots disponíveis</p>
          ) : (
            <>
              {selectedSlotSummary ? (
                <p className="mt-2 text-sm text-slate-200">
                  Slot selecionado: {selectedSlotSummary.level}º ({selectedSlotSummary.remaining}/{selectedSlotSummary.max} restantes)
                </p>
              ) : null}
              <div className="mt-3">
                <SpellSlotSummary
                  compact
                  entries={spell.slotSummary}
                  emptyLabel="Sem slots disponíveis"
                  highlightLevel={selectedSlotLevel}
                />
              </div>
            </>
          )}
        </div>
      ) : null}

      <div
        className="mb-6"
        data-testid="spell-tactical-preview"
        data-preview-source={previewModel.source}
      >
        <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-fuchsia-200/80">
          Mecânica Básica
        </p>
        <p className="mt-1 text-sm text-slate-200">
          {previewModel.damagePreview ? `Dano ${previewModel.damagePreview}` : "Sem dano direto"}
          {previewModel.attackMissOutcome === "half_damage" ? (
            <span className="text-amber-300"> · no erro: metade do dano</span>
          ) : null}
          {previewModel.delayedDamagePreview ? (
            <span className="text-cyan-300">{` · fim do próximo turno: ${previewModel.delayedDamagePreview}`}</span>
          ) : null}
          {showInstanceCount ? (
            <span className="text-fuchsia-300">
              {` · ${previewModel.effectInstanceCount} instâncias`}
              {previewModel.effectInstanceDice ? ` (${previewModel.effectInstanceDice})` : ""}
            </span>
          ) : null}
          {areaSizeLabel ? <span className="text-slate-400"> · {areaSizeLabel}</span> : null}
          {rangeLabel && !isAreaSpell ? (
            <span className="text-slate-400"> · alcance {rangeLabel}</span>
          ) : null}
        </p>
      </div>

      {mapPreviewModel ? (
        <div
          className={`mb-6 rounded-2xl border px-5 py-4 ${MAP_PREVIEW_STYLES[mapPreviewModel.status]}`}
          data-testid="spell-map-preview"
        >
          <p className="text-xs font-semibold uppercase tracking-[0.18em]">
            {isAreaSpell
              ? formatAreaOriginPreviewLabel(mapPreviewModel)
              : `Visão tática: ${formatSpellMapPreviewStatus(mapPreviewModel.status)}`}
          </p>
          {!isAreaSpell && mapPreviewReason ? (
            <p className="mt-1 text-sm">Motivo: {mapPreviewReason}</p>
          ) : null}
          {mapPreviewModel.rangeMeters != null ? (
            <p className="mt-2 text-xs opacity-90">Alcance: {formatRangeMeters(mapPreviewModel.rangeMeters)}</p>
          ) : null}
          {coverLabel ? (
            <p className="mt-1 text-xs opacity-90">{coverLabel}</p>
          ) : null}
          {mapPreviewModel.areaShape ? (
            <p className="mt-1 text-xs opacity-90">
              Área: {mapPreviewModel.areaShape}
              {mapPreviewModel.areaSizeMeters != null
                ? `, ${formatAreaSizeMeters(mapPreviewModel.areaShape as SpellPreviewModel["areaShape"], mapPreviewModel.areaSizeMeters)}`
                : ""}
            </p>
          ) : null}
          {typeof mapPreviewModel.affectedTargetCount === "number" ? (
            <p className="mt-1 text-xs opacity-90">Afetados: {mapPreviewModel.affectedTargetCount}</p>
          ) : null}
          {mapPreviewModel.affectedTargetNames?.length ? (
            <p className="mt-1 text-xs opacity-90">Alvos: {formatTargetList(mapPreviewModel.affectedTargetNames)}</p>
          ) : null}
          {mapPreviewModel.affectedTargetSpatialMetadata?.length ? (
            <div className="mt-2 space-y-0.5 text-xs opacity-90">
              <p className="font-semibold">DC por alvo:</p>
              {mapPreviewModel.affectedTargetSpatialMetadata.map((item) => {
                const line = formatAreaTargetEffectiveDcLine(item);
                return line ? <p key={item.targetRefId}>{line}</p> : null;
              })}
            </div>
          ) : null}
          {mapPreviewModel.guardrailTargetOutcomes?.length ? (
            <div className="mt-2 space-y-0.5 text-xs opacity-90">
              <p className="font-semibold">Exclusões mecânicas previstas:</p>
              {mapPreviewModel.guardrailTargetOutcomes.map((item) => (
                <p key={item.target_ref_id}>
                  {item.target_display_name}: {item.guardrail_reason}
                </p>
              ))}
            </div>
          ) : null}
          {mapPreviewModel.instanceStatuses?.length ? (
            <div className="mt-2 space-y-1 text-xs">
              {mapPreviewModel.instanceStatuses.map((instanceStatus) => {
                const instanceReason = formatSpellMapPreviewReason(
                  instanceStatus.reason,
                  instanceStatus.status,
                );
                const instanceCoverLabel = instanceStatus.cover
                  ? formatSpellCoverPreview(instanceStatus.cover, coverContext)
                  : null;
                return (
                  <p key={`${instanceStatus.instanceIndex}:${instanceStatus.targetRefId ?? "none"}`}>
                    {getInstanceLabel(spell.canonicalKey, instanceStatus.instanceIndex)}:{" "}
                    {formatSpellMapPreviewStatus(instanceStatus.status)}
                    {instanceReason ? ` · ${instanceReason}` : ""}
                    {instanceCoverLabel ? ` · ${instanceCoverLabel}` : ""}
                  </p>
                );
              })}
            </div>
          ) : null}
        </div>
      ) : null}

      {!isAreaSpell ? (
        <div className="mb-6">
          <RangeStatusBadge preview={targetPreview} />
        </div>
      ) : null}

      {spell.level > 0 && spell.sourceType !== "magic_item" ? (
        <label className="mb-6 block">
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
        <div className="mb-6">
          <ConcentrationSaveControl
            disabled={loading}
            manualValue={concentrationManualRoll}
            mode={concentrationRollMode}
            onManualValueChange={onConcentrationManualRollChange}
            onModeChange={onConcentrationRollModeChange}
          />
        </div>
      ) : null}

      {error ? (
        <div className="mb-6 rounded-2xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
          {error}
        </div>
      ) : null}
    </>
  );
};
