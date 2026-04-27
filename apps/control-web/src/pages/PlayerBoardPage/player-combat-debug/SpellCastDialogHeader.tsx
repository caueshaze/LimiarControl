import { ConcentrationSaveControl } from "../../../features/combat-ui/components/ConcentrationSaveControl";
import { RangeStatusBadge } from "../../../features/combat-ui/components/RangeStatusBadge";
import type { TargetingPreviewResult } from "../../../features/combat-ui/hooks/useTargetingPreview";
import type { CombatSpellMode } from "../../../shared/api/combatRepo";
import { getInstanceLabel } from "./InstanceTargetSelector";
import type { GridCell } from "./areaTargetingUi";
import type { SpellMapPreviewModel } from "./spellMapPreviewModel";
import {
  formatAreaOriginPreviewLabel,
  formatSpellMapPreviewReason,
  formatSpellMapPreviewStatus,
} from "./spellMapPreviewPresentation";
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
      ? previewModel.damageType
      : null;
  const flowSaveAbility =
    previewModel.requiresSavingThrow && previewModel.saveAbility ? previewModel.saveAbility : null;
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

  return (
    <>
      <p className="text-xs uppercase tracking-[0.3em] text-fuchsia-200">Magia</p>
      <h2 className="mt-3 text-2xl font-semibold text-white">{spell.name}</h2>
      <p className="mt-2 text-sm text-slate-300">
        {isAreaSpell
          ? `Origem: ${actorDisplayName}${anchorCell ? ` · Ancora: (${anchorCell.x}, ${anchorCell.y})` : ""}`
          : (
            <>
              Alvo: <span className="font-semibold text-white">{targetDisplayName ?? "Nenhum"}</span>
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
        Fluxo: {resolutionLabel}
        {flowDamageType ? ` · ${flowDamageType}` : ""}
        {flowSaveAbility ? ` · save ${flowSaveAbility}` : ""}
        {flowAreaShape ? ` · ${flowAreaShape}` : ""}
      </p>
      <p
        className="mt-2 text-xs text-slate-300"
        data-testid="spell-tactical-preview"
        data-preview-source={previewModel.source}
      >
        <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-fuchsia-200/80">
          Preview
        </span>
        <span className="ml-2 text-slate-200">
          {previewModel.damagePreview ? `Dano ${previewModel.damagePreview}` : "Sem dano direto"}
        </span>
        {showInstanceCount ? (
          <span className="ml-2 text-fuchsia-100">
            · {previewModel.effectInstanceCount} instâncias
            {previewModel.effectInstanceDice ? ` (${previewModel.effectInstanceDice})` : ""}
          </span>
        ) : null}
        {areaSizeLabel ? <span className="ml-2 text-slate-300">· {areaSizeLabel}</span> : null}
        {rangeLabel && !isAreaSpell ? (
          <span className="ml-2 text-slate-300">· alcance {rangeLabel}</span>
        ) : null}
      </p>
      {mapPreviewModel ? (
        <div
          className={`mt-4 rounded-2xl border px-4 py-3 ${MAP_PREVIEW_STYLES[mapPreviewModel.status]}`}
          data-testid="spell-map-preview"
        >
          <p className="text-xs font-semibold uppercase tracking-[0.18em]">
            {isAreaSpell
              ? formatAreaOriginPreviewLabel(mapPreviewModel)
              : `Preview tático: ${formatSpellMapPreviewStatus(mapPreviewModel.status)}`}
          </p>
          {!isAreaSpell && mapPreviewReason ? (
            <p className="mt-1 text-sm">Motivo: {mapPreviewReason}</p>
          ) : null}
          {mapPreviewModel.rangeMeters != null ? (
            <p className="mt-2 text-xs opacity-90">Alcance: {formatRangeMeters(mapPreviewModel.rangeMeters)}</p>
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
            <p className="mt-1 text-xs opacity-90">Alvos: {mapPreviewModel.affectedTargetNames.join(", ")}</p>
          ) : null}
          {mapPreviewModel.instanceStatuses?.length ? (
            <div className="mt-2 space-y-1 text-xs">
              {mapPreviewModel.instanceStatuses.map((instanceStatus) => {
                const instanceReason = formatSpellMapPreviewReason(
                  instanceStatus.reason,
                  instanceStatus.status,
                );
                return (
                  <p key={`${instanceStatus.instanceIndex}:${instanceStatus.targetRefId ?? "none"}`}>
                    {getInstanceLabel(spell.canonicalKey, instanceStatus.instanceIndex)}:{" "}
                    {formatSpellMapPreviewStatus(instanceStatus.status)}
                    {instanceReason ? ` · ${instanceReason}` : ""}
                  </p>
                );
              })}
            </div>
          ) : null}
        </div>
      ) : null}
      <p className="mt-1 text-xs uppercase tracking-[0.2em] text-fuchsia-200/80">{actionCostLabel}</p>
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
            onManualValueChange={onConcentrationManualRollChange}
            onModeChange={onConcentrationRollModeChange}
          />
        </div>
      ) : null}
      {!isAreaSpell ? (
        <div className="mt-4">
          <RangeStatusBadge preview={targetPreview} />
        </div>
      ) : null}
      {error ? (
        <div className="mt-4 rounded-2xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
          {error}
        </div>
      ) : null}
    </>
  );
};
