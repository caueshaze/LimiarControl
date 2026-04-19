import { useEffect, useState } from "react";
import {
  combatRepo,
  type CombatMapPreviewToken,
  type CombatMovementPreviewResponse,
} from "../../../shared/api/combatRepo";

export const MOVEMENT_METERS_PER_CELL = 1.5;
export const PATH_COST_UNITS_PER_CELL = 5;

export type MovementPreviewState = {
  loading: boolean;
  error: string | null;
  actorToken: CombatMapPreviewToken | null;
  preview: CombatMovementPreviewResponse | null;
};

export type UseMovementPreviewOptions = {
  sessionId: string;
  actorParticipantId: string | null | undefined;
  actorRefId: string | null | undefined;
  destinationCell: { x: number; y: number } | null;
  enabled?: boolean;
};

const INITIAL: MovementPreviewState = {
  loading: false,
  error: null,
  actorToken: null,
  preview: null,
};

export function pathCostUnitsToMeters(pathCostUnits: number): number {
  return (pathCostUnits / PATH_COST_UNITS_PER_CELL) * MOVEMENT_METERS_PER_CELL;
}

export function formatMovementMeters(
  meters: number,
  locale: "pt" | "en",
): string {
  const rounded = Math.round(meters * 10) / 10;
  const value =
    rounded % 1 === 0 ? rounded.toFixed(0) : rounded.toFixed(1);
  return `${locale === "pt" ? value.replace(".", ",") : value}m`;
}

export function canConfirmMovementPreview(
  preview: CombatMovementPreviewResponse | null,
  loading: boolean,
): boolean {
  return Boolean(preview?.is_valid && !loading);
}

export function resolveMovementCellSelection(options: {
  currentSelectedCell: { x: number; y: number } | null;
  nextCell: { x: number; y: number };
  preview: CombatMovementPreviewResponse | null;
  loading: boolean;
}): "lock" | "confirm" {
  const { currentSelectedCell, nextCell, preview, loading } = options;
  const isSameCell =
    currentSelectedCell?.x === nextCell.x &&
    currentSelectedCell?.y === nextCell.y;

  if (isSameCell && canConfirmMovementPreview(preview, loading)) {
    return "confirm";
  }

  return "lock";
}

export function getMovementPreviewReasonLabel(reason: string | null | undefined): string {
  switch (reason) {
    case "movement_budget_exceeded":
      return "O destino excede o deslocamento restante.";
    case "blocked_path":
      return "O caminho ate o destino esta bloqueado.";
    case "occupied_cell":
      return "Ja existe outro combatente nessa celula.";
    case "outside_map":
      return "O destino esta fora do mapa.";
    case "diagonal_clipped":
      return "A diagonal cruza um canto bloqueado.";
    case "out_of_turn":
      return "So o combatente ativo pode se mover agora.";
    case "empty_path":
      return "Selecione uma celula diferente da posicao atual.";
    default:
      return "Nao foi possivel validar esse deslocamento.";
  }
}

export function useMovementPreview({
  sessionId,
  actorParticipantId,
  actorRefId,
  destinationCell,
  enabled = true,
}: UseMovementPreviewOptions): MovementPreviewState {
  const [state, setState] = useState<MovementPreviewState>(INITIAL);

  useEffect(() => {
    if (!enabled || !sessionId || !actorParticipantId || !actorRefId) {
      setState(INITIAL);
      return;
    }

    let cancelled = false;
    setState((current) => ({ ...current, loading: true, error: null }));

    combatRepo
      .getMapState(sessionId, actorParticipantId)
      .then((mapState) => {
        if (cancelled) return;
        const actorToken =
          mapState.tokens.find((token) => token.combatant_id === actorRefId) ?? null;
        setState((current) => ({
          ...current,
          loading: destinationCell != null,
          actorToken,
          error: actorToken ? null : "Actor token not found on map.",
        }));
      })
      .catch((error: any) => {
        if (cancelled) return;
        setState({
          ...INITIAL,
          error: error?.data?.detail || error?.message || "Failed to load map state.",
        });
      });

    return () => {
      cancelled = true;
    };
  }, [actorParticipantId, actorRefId, enabled, sessionId]);

  useEffect(() => {
    if (!enabled || !sessionId || !actorParticipantId || !destinationCell) {
      setState((current) => ({ ...current, loading: false, preview: null, error: current.actorToken ? null : current.error }));
      return;
    }

    let cancelled = false;
    setState((current) => ({ ...current, loading: true, error: null }));

    combatRepo
      .previewMovement(sessionId, {
        actor_participant_id: actorParticipantId,
        destination_cell: destinationCell,
      })
      .then((preview) => {
        if (cancelled) return;
        setState((current) => ({
          ...current,
          loading: false,
          preview,
          error: preview.is_valid ? null : getMovementPreviewReasonLabel(preview.reason),
        }));
      })
      .catch((error: any) => {
        if (cancelled) return;
        setState((current) => ({
          ...current,
          loading: false,
          preview: null,
          error: error?.data?.detail || error?.message || "Failed to preview movement.",
        }));
      });

    return () => {
      cancelled = true;
    };
  }, [actorParticipantId, destinationCell, enabled, sessionId]);

  return state;
}
