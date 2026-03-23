import { navEnUSDictionary } from "./enUS/nav";
import { homeEnUSDictionary } from "./enUS/home";
import { gmEnUSDictionary } from "./enUS/gm";
import { playerPartyEnUSDictionary } from "./enUS/playerParty";
import { campaignEnUSDictionary } from "./enUS/campaign";
import { commonEnUSDictionary } from "./enUS/common";
import { campaignHomeEnUSDictionary } from "./enUS/campaignHome";
import { playerBoardEnUSDictionary } from "./enUS/playerBoard";
import { sessionActivityEnUSDictionary } from "./enUS/sessionActivity";
import { roleEnUSDictionary } from "./enUS/role";
import { authEnUSDictionary } from "./enUS/auth";
import { catalogEnUSDictionary } from "./enUS/catalog";
import { shopEnUSDictionary } from "./enUS/shop";
import { inventoryEnUSDictionary } from "./enUS/inventory";
import { npcEnUSDictionary } from "./enUS/npc";
import { entityEnUSDictionary } from "./enUS/entity";
import { joinEnUSDictionary } from "./enUS/join";
import { rollsEnUSDictionary } from "./enUS/rolls";
import { sheetEnUSDictionary } from "./enUS/sheet";

export const enUS = {
  ...navEnUSDictionary,
  ...homeEnUSDictionary,
  ...gmEnUSDictionary,
  ...playerPartyEnUSDictionary,
  ...campaignEnUSDictionary,
  ...commonEnUSDictionary,
  ...campaignHomeEnUSDictionary,
  ...playerBoardEnUSDictionary,
  ...sessionActivityEnUSDictionary,
  ...roleEnUSDictionary,
  ...authEnUSDictionary,
  ...catalogEnUSDictionary,
  ...shopEnUSDictionary,
  ...inventoryEnUSDictionary,
  ...npcEnUSDictionary,
  ...entityEnUSDictionary,
  ...joinEnUSDictionary,
  ...rollsEnUSDictionary,
  ...sheetEnUSDictionary,
} as const;
