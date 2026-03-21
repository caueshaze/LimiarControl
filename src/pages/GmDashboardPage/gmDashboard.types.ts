import type { CurrencyWallet } from "../../shared/api/inventoryRepo";

export type CommandFeedback = {
  tone: "success" | "error";
  type: "open_shop" | "close_shop" | "request_roll" | "start_combat" | "end_combat";
  message: string;
};

export type GrantFeedback = {
  tone: "success" | "error";
  message: string;
};

export type CurrencyDraft = {
  amount: string;
  coin: keyof CurrencyWallet;
};

export type ItemDraft = {
  itemId: string;
  quantity: string;
};
