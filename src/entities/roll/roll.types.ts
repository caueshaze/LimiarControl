export type RoleMode = "GM" | "PLAYER";

export type RollDice = {
  count: number;
  sides: number;
  modifier: number;
};

export type RollEvent = {
  id: string;
  campaignId: string;
  sessionId: string;
  authorName: string;
  roleMode: RoleMode;
  label?: string | null;
  expression: string;
  dice: RollDice;
  results: number[];
  total: number;
  createdAt: string;
};

export type RollRequest = {
  requestId: string;
  label: string | null;
  expression: string;
};
