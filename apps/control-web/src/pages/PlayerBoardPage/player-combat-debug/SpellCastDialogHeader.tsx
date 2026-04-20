import { ConcentrationSaveControl } from "../../../features/combat-ui/components/ConcentrationSaveControl";
import { RangeStatusBadge } from "../../../features/combat-ui/components/RangeStatusBadge";
import type { TargetingPreviewResult } from "../../../features/combat-ui/hooks/useTargetingPreview";
import type { CombatSpellMode } from "../../../shared/api/combatRepo";
import type { GridCell } from "./areaTargetingUi";
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
  onConcentrationManualRollChange: (value: string) => void;
  onConcentrationRollModeChange: (value: "system" | "manual") => void;
  selectedSlotLevel: number | null;
  setSelectedSlotLevel: (value: number) => void;
  shouldShowConcentrationControl: boolean;
  slotOptions: number[];
  spell: CombatSpellOption;
  spellDamageType: string;
  spellMode: CombatSpellMode;
  spellSaveAbility: string;
  targetDisplayName?: string | null;
  targetPreview: TargetingPreviewResult;
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
  onConcentrationManualRollChange,
  onConcentrationRollModeChange,
  selectedSlotLevel,
  setSelectedSlotLevel,
  shouldShowConcentrationControl,
  slotOptions,
  spell,
  spellDamageType,
  spellMode,
  spellSaveAbility,
  targetDisplayName,
  targetPreview,
}: Props) => (
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
      Fluxo: {spellMode.replace(/_/g, " ")}
      {spellMode !== "heal" && spellMode !== "utility" && spellDamageType ? ` · ${spellDamageType}` : ""}
      {spellMode === "saving_throw" && spellSaveAbility ? ` · save ${spellSaveAbility}` : ""}
      {isAreaSpell && spell.targetMode ? ` · ${spell.targetMode}` : ""}
    </p>
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
