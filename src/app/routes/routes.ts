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
  partyDetails: "/gm/parties/:partyId",
  gmPartyCharacterSheetDraftNew: "/gm/parties/:partyId/character-sheet-drafts/new",
  gmPartyCharacterSheetDraft: "/gm/parties/:partyId/character-sheet-drafts/:draftId",
  campaignDashboard: "/gm/campaigns/:campaignId/dashboard",

  // Game/Runtime Board
  playerPartyDetails: "/parties/:partyId",
  board: "/board/:partyId",

  catalog: "/catalog",
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
