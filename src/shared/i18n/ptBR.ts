import { navPtBRDictionary } from "./ptBR/nav";
import { homePtBRDictionary } from "./ptBR/home";
import { gmPtBRDictionary } from "./ptBR/gm";
import { playerPartyPtBRDictionary } from "./ptBR/playerParty";
import { campaignPtBRDictionary } from "./ptBR/campaign";
import { commonPtBRDictionary } from "./ptBR/common";
import { campaignHomePtBRDictionary } from "./ptBR/campaignHome";
import { playerBoardPtBRDictionary } from "./ptBR/playerBoard";
import { sessionActivityPtBRDictionary } from "./ptBR/sessionActivity";
import { rolePtBRDictionary } from "./ptBR/role";
import { authPtBRDictionary } from "./ptBR/auth";
import { catalogPtBRDictionary } from "./ptBR/catalog";
import { shopPtBRDictionary } from "./ptBR/shop";
import { inventoryPtBRDictionary } from "./ptBR/inventory";
import { npcPtBRDictionary } from "./ptBR/npc";
import { entityPtBRDictionary } from "./ptBR/entity";
import { joinPtBRDictionary } from "./ptBR/join";
import { rollsPtBRDictionary } from "./ptBR/rolls";
import { sheetPtBRDictionary } from "./ptBR/sheet";
import { combatUiPtBRDictionary } from "./ptBR/combatUi";

export const ptBR = {
  ...navPtBRDictionary,
  ...homePtBRDictionary,
  ...gmPtBRDictionary,
  ...playerPartyPtBRDictionary,
  ...campaignPtBRDictionary,
  ...commonPtBRDictionary,
  ...campaignHomePtBRDictionary,
  ...playerBoardPtBRDictionary,
  ...sessionActivityPtBRDictionary,
  ...rolePtBRDictionary,
  ...authPtBRDictionary,
  ...catalogPtBRDictionary,
  ...shopPtBRDictionary,
  ...inventoryPtBRDictionary,
  ...npcPtBRDictionary,
  ...entityPtBRDictionary,
  ...joinPtBRDictionary,
  ...rollsPtBRDictionary,
  ...sheetPtBRDictionary,
  ...combatUiPtBRDictionary,
} as const;
