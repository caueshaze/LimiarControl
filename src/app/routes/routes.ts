export const routes = {
  root: "/",
  home: "/home",
  gmHome: "/gm",
  login: "/login",
  register: "/register",
  join: "/join", // Legacy URL

  // GM Routes
  campaigns: "/gm/campaigns",
  campaignEdit: "/gm/campaigns/:campaignId",
  partyDetails: "/gm/parties/:partyId",
  campaignDashboard: "/gm/campaigns/:campaignId/dashboard",

  // Game/Runtime Board
  playerPartyDetails: "/parties/:partyId",
  board: "/board/:partyId",

  catalog: "/catalog",
  systemCatalogAdmin: "/admin/base-items",
  systemSpellCatalogAdmin: "/admin/base-spells",
  npcs: "/npcs",
  bestiary: "/bestiary",
  characterSheet: "/character-sheet",
  characterSheetParty: "/parties/:partyId/character-sheet",
} as const;
