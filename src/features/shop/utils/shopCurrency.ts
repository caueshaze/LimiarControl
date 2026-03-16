import type { CurrencyWallet } from "../../../shared/api/inventoryRepo";

export const EMPTY_WALLET: CurrencyWallet = {
  cp: 0,
  sp: 0,
  ep: 0,
  gp: 0,
  pp: 0,
};

export const normalizeWallet = (value: unknown): CurrencyWallet => {
  if (!value || typeof value !== "object") {
    return EMPTY_WALLET;
  }
  const source = value as Record<string, unknown>;
  return {
    cp: toWholeNumber(source.cp),
    sp: toWholeNumber(source.sp),
    ep: toWholeNumber(source.ep),
    gp: toWholeNumber(source.gp),
    pp: toWholeNumber(source.pp),
  };
};

export const formatWallet = (wallet: CurrencyWallet | null | undefined) => {
  const current = wallet ?? EMPTY_WALLET;
  const parts = ([
    ["pp", current.pp],
    ["gp", current.gp],
    ["ep", current.ep],
    ["sp", current.sp],
    ["cp", current.cp],
  ] as const)
    .filter(([, amount]) => amount > 0)
    .map(([coin, amount]) => `${amount} ${coin}`);

  return parts.length > 0 ? parts.join(" · ") : "0 gp";
};

export const formatItemPrice = (price?: number | null, priceLabel?: string) => {
  if (priceLabel) {
    return priceLabel;
  }
  if (typeof price !== "number" || Number.isNaN(price) || price < 0) {
    return "0 gp";
  }
  const totalCp = Math.max(0, Math.round(price * 100));
  const gp = Math.floor(totalCp / 100);
  const sp = Math.floor((totalCp % 100) / 10);
  const cp = totalCp % 10;
  const parts = [
    gp > 0 ? `${gp} gp` : null,
    sp > 0 ? `${sp} sp` : null,
    cp > 0 ? `${cp} cp` : null,
  ].filter((part): part is string => Boolean(part));
  return parts.length > 0 ? parts.join(" ") : "0 gp";
};

const toWholeNumber = (value: unknown) => {
  const number = Number(value ?? 0);
  if (!Number.isFinite(number)) {
    return 0;
  }
  return Math.max(0, Math.trunc(number));
};
