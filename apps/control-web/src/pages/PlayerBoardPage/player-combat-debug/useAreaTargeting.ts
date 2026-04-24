import { useEffect, useMemo, useState } from "react";
import type {
  CombatAreaPreviewResponse,
  CombatMapPreviewState,
  CombatParticipant,
  CombatSpellMode,
  CombatSpellResult,
} from "../../../shared/api/combatRepo";
import { combatRepo } from "../../../shared/api/combatRepo";
import {
  buildAreaPreviewPayload,
  getAnchorCombatantIdAtCell,
  isAreaShape,
  resolveActorOriginCell,
  type GridCell,
} from "./areaTargetingUi";
import type { CombatSpellOption } from "./types";

const AREA_PREVIEW_DEBOUNCE_MS = 220;

type Params = {
  actor: CombatParticipant;
  actorParticipantId: string;
  result: CombatSpellResult | null;
  selectedSlotLevel: number | null;
  sessionId: string;
  spell: CombatSpellOption;
  spellMode: CombatSpellMode;
};

export const useAreaTargeting = ({
  actor,
  actorParticipantId,
  result,
  selectedSlotLevel,
  sessionId,
  spell,
  spellMode,
}: Params) => {
  const [mapState, setMapState] = useState<CombatMapPreviewState | null>(null);
  const [mapLoading, setMapLoading] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);
  const [anchorCell, setAnchorCell] = useState<GridCell | null>(null);
  const [preview, setPreview] = useState<CombatAreaPreviewResponse | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  const isAreaSpell = isAreaShape(spell.areaShape);
  const originCell = useMemo(
    () => (mapState ? resolveActorOriginCell(actor, mapState.tokens) : null),
    [actor, mapState],
  );
  const anchorTargetRefId = useMemo(
    () => (anchorCell && mapState ? getAnchorCombatantIdAtCell(mapState.tokens, anchorCell) : null),
    [anchorCell, mapState],
  );
  const canSubmitArea = Boolean(anchorCell && originCell && preview?.is_valid);

  useEffect(() => {
    setAnchorCell(null);
    setPreview(null);
    setPreviewError(null);
    setMapError(null);
  }, [spell.fixedCastLevel, spell.id, spell.level, spell.areaShape]);

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

  return {
    anchorCell,
    canSubmitArea,
    clearAreaSelection: () => {
      setAnchorCell(null);
      setPreview(null);
      setPreviewError(null);
    },
    isAreaSpell,
    mapError,
    mapLoading,
    mapState,
    originCell,
    preview,
    previewError,
    previewLoading,
    setAnchorCell,
    setPreview,
    setPreviewError,
  };
};
