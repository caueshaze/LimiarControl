import { useEffect, useState } from "react";
import { characterSheetsRepo } from "../../../shared/api/characterSheetsRepo";
import { loadSpellCatalog } from "../../../entities/dnd-base";
import { parseCharacterSheet } from "../model/characterSheet.schema";
import type { CharacterSheet } from "../model/characterSheet.types";

type ViewState = {
  sheet: CharacterSheet | null;
  loading: boolean;
  error: string | null;
  /** True when the party has no character sheet yet (404). */
  missing: boolean;
};

/**
 * Read-only loader for the "Ver ficha" view.
 *
 * Loads the accepted character sheet for `playerUserId` (or the authenticated
 * player's own sheet when `playerUserId` is null) and parses it into a typed
 * CharacterSheet. No catalog preloads — the view never edits the sheet.
 */
export const useCharacterSheetView = (
  partyId: string | null,
  playerUserId: string | null,
  campaignId: string | null,
): ViewState => {
  const [state, setState] = useState<ViewState>({
    sheet: null,
    loading: true,
    error: null,
    missing: false,
  });

  useEffect(() => {
    if (!partyId) {
      setState({ sheet: null, loading: false, error: null, missing: true });
      return;
    }

    let active = true;
    setState({ sheet: null, loading: true, error: null, missing: false });

    const request = playerUserId
      ? characterSheetsRepo.getForPlayer(partyId, playerUserId)
      : characterSheetsRepo.getByParty(partyId);

    // Load the spell catalog so spell names can be localized (namePt). A catalog
    // failure must not block rendering the sheet.
    Promise.all([request, loadSpellCatalog(campaignId).catch(() => undefined)])
      .then(([record]) => {
        if (!active) return;
        setState({
          sheet: parseCharacterSheet(record.data),
          loading: false,
          error: null,
          missing: false,
        });
      })
      .catch((err: unknown) => {
        if (!active) return;
        if ((err as { status?: number })?.status === 404) {
          setState({ sheet: null, loading: false, error: null, missing: true });
          return;
        }
        setState({
          sheet: null,
          loading: false,
          error: err instanceof Error ? err.message : "Failed to load character sheet",
          missing: false,
        });
      });

    return () => {
      active = false;
    };
  }, [partyId, playerUserId, campaignId]);

  return state;
};
