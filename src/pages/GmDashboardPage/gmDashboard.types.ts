import type { CurrencyUnit } from "../../shared/utils/money";

export type CommandFeedback = {
  tone: "success" | "error";
  type:
    | "open_shop"
    | "close_shop"
    | "request_roll"
    | "start_combat"
    | "end_combat"
    | "start_short_rest"
    | "start_long_rest"
    | "end_rest";
  message: string;
};

export type GrantFeedback = {
  tone: "success" | "error";
  message: string;
};

export type CurrencyDraft = {
  amount: string;
  coin: CurrencyUnit;
};

export type ItemDraft = {
  itemId: string;
  quantity: string;
};

export type HpActionState = {
  action: "damage" | "heal";
  userId: string;
};
