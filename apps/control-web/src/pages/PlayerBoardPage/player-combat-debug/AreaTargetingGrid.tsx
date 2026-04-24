import { useMemo } from "react";
import { CombatMapFrame } from "../../../features/combat-ui/map/CombatMapFrame";
import type { CombatMapPreviewState, CombatParticipant } from "../../../shared/api/combatRepo";
import { formatAffectedTargetNames, resolveAffectedTargetNames, type GridCell } from "./areaTargetingUi";

type Props = {
  actor: CombatParticipant;
  anchorCell: GridCell | null;
  canRevealHiddenTargets?: boolean;
  mapError: string | null;
  mapLoading: boolean;
  mapState: CombatMapPreviewState | null;
  originCell: GridCell | null;
  participants: CombatParticipant[];
  previewAffectedCellCount: number;
  previewAffectedTargetRefIds: string[];
  previewCells: GridCell[];
  previewError: string | null;
  previewLoading: boolean;
  previewReason: string | null;
  previewValid: boolean;
  sessionId: string;
  onCellSelected: (cell: GridCell) => void;
};

export const AreaTargetingGrid = ({
  actor,
  anchorCell,
  canRevealHiddenTargets = false,
  mapError,
  mapLoading,
  mapState,
  originCell,
  participants,
  previewAffectedCellCount,
  previewAffectedTargetRefIds,
  previewCells,
  previewError,
  previewLoading,
  previewReason,
  previewValid,
  sessionId,
  onCellSelected,
}: Props) => {
  const affectedTargetNames = useMemo(
    () =>
      resolveAffectedTargetNames({
        affectedTargetRefIds: previewAffectedTargetRefIds,
        canRevealHiddenTargets,
        participants,
        tokens: mapState?.tokens ?? [],
      }),
    [canRevealHiddenTargets, mapState?.tokens, participants, previewAffectedTargetRefIds],
  );
  const affectedTargetText = formatAffectedTargetNames(affectedTargetNames);

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
            : previewValid
              ? `${previewAffectedCellCount} celulas · ${affectedTargetNames.length} alvos`
              : previewReason ?? "Sem preview"}
        </span>
      </div>
      {!previewLoading && previewValid ? (
        <p className="text-xs text-slate-300">{affectedTargetText}</p>
      ) : null}
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
        previewCells={previewCells}
        selectedCell={anchorCell}
        className="rounded-2xl border border-white/10 bg-slate-950/70 p-3"
        frameClassName="h-[420px] w-full border-0 bg-slate-950"
        onCellSelected={({ cell }) => onCellSelected(cell)}
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
