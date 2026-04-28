export const routes = {
  root: "/",
  home: "/home",
  gmHome: "/gm",
  workspaceHome: "/workspace",
  login: "/login",
  register: "/register",
  join: "/join", // Legacy URL

  // GM Routes
  campaigns: "/gm/campaigns",
  campaignEdit: "/gm/campaigns/:campaignId",
  campaignMaps: "/gm/campaigns/:campaignId/maps",
  partyDetails: "/gm/parties/:partyId",
  gmPartyCharacterSheetDraftNew: "/gm/parties/:partyId/character-sheet-drafts/new",
  gmPartyCharacterSheetDraft: "/gm/parties/:partyId/character-sheet-drafts/:draftId",
  campaignDashboard: "/gm/campaigns/:campaignId/dashboard",

  // Game/Runtime Board
  playerPartyDetails: "/parties/:partyId",
  board: "/board/:partyId",

  catalog: "/catalog",
  catalogItems: "/catalog/items",
  catalogSpells: "/catalog/spells",
  catalogSpellNew: "/catalog/spells/new",
  catalogSpellEdit: "/catalog/spells/:spellId/edit",
  adminHome: "/admin",
  adminCatalogItems: "/admin/catalog/items",
  adminCatalogSpells: "/admin/catalog/spells",
  adminUsers: "/admin/users",
  adminCampaigns: "/admin/campaigns",
  adminDiagnostics: "/admin/diagnostics",
  systemCatalogAdmin: "/admin/base-items",
  systemSpellCatalogAdmin: "/admin/base-spells",
  npcs: "/npcs",
  bestiary: "/bestiary",
  characterSheet: "/character-sheet",
  characterSheetParty: "/parties/:partyId/character-sheet",
} as const;

export function buildCampaignDashboardPath(
  campaignId: string,
  partyId?: string | null,
): string {
  const path = routes.campaignDashboard.replace(":campaignId", campaignId);
  if (!partyId) {
    return path;
  }
  const search = new URLSearchParams({ partyId });
  return `${path}?${search.toString()}`;
}

export function buildCatalogSpellEditPath(spellId: string): string {
  return routes.catalogSpellEdit.replace(":spellId", spellId);
}
