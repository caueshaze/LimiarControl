import type { CurrencyWallet } from "../../../shared/api/inventoryRepo";
import {
  type CurrencyUnit,
  formatMoney,
  fromCopper,
  normalizeMoney,
} from "../../../shared/utils/money";

export const EMPTY_WALLET: CurrencyWallet = {
  copperValue: 0,
};

export const COIN_ORDER = ["pp", "gp", "ep", "sp", "cp"] as const;

export const COIN_VISUALS: Record<
  CurrencyUnit,
  { longLabel: string; shortLabel: string; className: string }
> = {
  pp: {
    longLabel: "Platina",
    shortLabel: "PP",
    className:
      "rounded-full border border-cyan-500/25 bg-cyan-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-cyan-200",
  },
  gp: {
    longLabel: "Ouro",
    shortLabel: "PO",
    className:
      "rounded-full border border-amber-500/25 bg-amber-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-amber-200",
  },
  ep: {
    longLabel: "Electrum",
    shortLabel: "PE",
    className:
      "rounded-full border border-lime-500/25 bg-lime-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-lime-200",
  },
  sp: {
    longLabel: "Prata",
    shortLabel: "PPt",
    className:
      "rounded-full border border-slate-500/25 bg-slate-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-slate-200",
  },
  cp: {
    longLabel: "Cobre",
    shortLabel: "PC",
    className:
      "rounded-full border border-rose-500/25 bg-rose-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-rose-200",
  },
};

export const normalizeWallet = (value: unknown): CurrencyWallet => {
  return normalizeMoney(value);
};

export const formatWallet = (wallet: CurrencyWallet | null | undefined) =>
  formatMoney(wallet?.copperValue ?? 0);

export const buildWalletDisplay = (
  wallet: CurrencyWallet | null | undefined,
  { includeZeroGp = true }: { includeZeroGp?: boolean } = {},
) => {
  const current = fromCopper(wallet?.copperValue ?? 0);
  return COIN_ORDER.map((coin) => ({
    amount: current[coin],
    coin,
    ...COIN_VISUALS[coin],
  })).filter((entry) => entry.amount > 0 || (includeZeroGp && entry.coin === "gp"));
};

export const formatItemPrice = (
  price?: number | null,
  priceLabel?: string,
  priceCopperValue?: number | null,
) => {
  if (priceLabel) {
    return priceLabel;
  }
  if (typeof priceCopperValue === "number" && Number.isFinite(priceCopperValue) && priceCopperValue >= 0) {
    return formatPriceMoney(priceCopperValue);
  }
  if (typeof price !== "number" || Number.isNaN(price) || price < 0) {
    return "0 gp";
  }
  return formatPriceMoney(Math.max(0, Math.round(price * 100)));
};

export const formatPriceMoney = (copperValue: number) => {
  const totalCp = Math.max(0, Math.trunc(copperValue));
  if (totalCp === 0) {
    return "0 gp";
  }
  if (totalCp % 1000 === 0) {
    return `${totalCp / 1000} pp`;
  }
  if (totalCp % 100 === 0) {
    return `${totalCp / 100} gp`;
  }
  if (totalCp % 10 === 0) {
    return `${totalCp / 10} sp`;
  }
  return `${totalCp} cp`;
};
