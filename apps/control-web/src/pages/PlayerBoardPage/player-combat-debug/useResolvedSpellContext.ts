import { useEffect, useState } from "react";
import {
  combatRepo,
  type CombatResolvedSpellContext,
  type CombatSpellMode,
} from "../../../shared/api/combatRepo";
import type { CombatSpellOption } from "./types";

type UseResolvedSpellContextParams = {
  actorParticipantId: string;
  sessionId: string;
  spell: CombatSpellOption;
  spellMode: CombatSpellMode;
  selectedSlotLevel: number | null;
};

type UseResolvedSpellContextResult = {
  context: CombatResolvedSpellContext | null;
  error: string | null;
  loading: boolean;
};

const INITIAL: UseResolvedSpellContextResult = {
  context: null,
  error: null,
  loading: false,
};

export const useResolvedSpellContext = ({
  actorParticipantId,
  sessionId,
  spell,
  spellMode,
  selectedSlotLevel,
}: UseResolvedSpellContextParams): UseResolvedSpellContextResult => {
  const [state, setState] = useState<UseResolvedSpellContextResult>(INITIAL);

  useEffect(() => {
    let cancelled = false;

    setState((current) => ({
      context: current.context,
      error: null,
      loading: true,
    }));

    combatRepo
      .resolveSpellContext(sessionId, {
        actor_participant_id: actorParticipantId,
        inventory_item_id: spell.sourceType === "magic_item" ? spell.inventoryItemId ?? null : null,
        spell_id: spell.canonicalKey,
        spell_canonical_key: spell.canonicalKey,
        campaign_spell_id: spell.campaignSpellId ?? null,
        spell_mode: spellMode,
        slot_level:
          spell.sourceType === "magic_item"
            ? spell.fixedCastLevel ?? spell.level ?? null
            : spell.level > 0
              ? selectedSlotLevel ?? spell.level
              : null,
      })
      .then((context) => {
        if (cancelled) {
          return;
        }
        setState({
          context,
          error: null,
          loading: false,
        });
      })
      .catch((error: any) => {
        if (cancelled) {
          return;
        }
        setState({
          context: null,
          error: error?.data?.detail || error?.message || "Falha ao resolver contexto da magia.",
          loading: false,
        });
      });

    return () => {
      cancelled = true;
    };
  }, [
    actorParticipantId,
    selectedSlotLevel,
    sessionId,
    spell.campaignSpellId,
    spell.canonicalKey,
    spell.fixedCastLevel,
    spell.id,
    spell.inventoryItemId,
    spell.level,
    spell.sourceType,
    spellMode,
  ]);

  return state;
};
