export type CurrencyUnit = "cp" | "sp" | "ep" | "gp" | "pp";

export type Money = {
  copperValue: number;
};

export const COPPER_PER_UNIT: Record<CurrencyUnit, number> = {
  cp: 1,
  sp: 10,
  ep: 50,
  gp: 100,
  pp: 1000,
};

const toWholeNumber = (value: unknown) => {
  const number = Number(value ?? 0);
  if (!Number.isFinite(number)) {
    return 0;
  }
  return Math.max(0, Math.trunc(number));
};

export const toCopper = (value: number, unit: CurrencyUnit): number =>
  Math.max(0, Math.trunc(value)) * COPPER_PER_UNIT[unit];

export const fromCopper = (copperValue: number) => {
  let remaining = Math.max(0, toWholeNumber(copperValue));
  const pp = Math.floor(remaining / COPPER_PER_UNIT.pp);
  remaining %= COPPER_PER_UNIT.pp;
  const gp = Math.floor(remaining / COPPER_PER_UNIT.gp);
  remaining %= COPPER_PER_UNIT.gp;
  const ep = Math.floor(remaining / COPPER_PER_UNIT.ep);
  remaining %= COPPER_PER_UNIT.ep;
  const sp = Math.floor(remaining / COPPER_PER_UNIT.sp);
  remaining %= COPPER_PER_UNIT.sp;
  const cp = remaining;

  return { pp, gp, ep, sp, cp };
};

export const formatMoney = (copperValue: number): string => {
  const { pp, gp, sp, cp } = fromCopper(copperValue);
  const parts = [
    pp > 0 ? `${pp} pp` : null,
    gp > 0 ? `${gp} gp` : null,
    sp > 0 ? `${sp} sp` : null,
    cp > 0 ? `${cp} cp` : null,
  ].filter((part): part is string => Boolean(part));

  return parts.length > 0 ? parts.join(", ") : "0 gp";
};

export const normalizeMoney = (value: unknown): Money => {
  if (!value || typeof value !== "object") {
    return { copperValue: 0 };
  }

  const source = value as Record<string, unknown>;
  if (typeof source.copperValue !== "undefined") {
    return { copperValue: toWholeNumber(source.copperValue) };
  }

  return {
    copperValue:
      toWholeNumber(source.cp) +
      toWholeNumber(source.sp) * COPPER_PER_UNIT.sp +
      toWholeNumber(source.ep) * COPPER_PER_UNIT.ep +
      toWholeNumber(source.gp) * COPPER_PER_UNIT.gp +
      toWholeNumber(source.pp) * COPPER_PER_UNIT.pp,
  };
};

export const addMoney = (wallet: Money | null | undefined, amountCopper: number): Money => ({
  copperValue: Math.max(0, toWholeNumber(wallet?.copperValue) + Math.max(0, toWholeNumber(amountCopper))),
});

export const subtractMoney = (wallet: Money | null | undefined, amountCopper: number): Money => ({
  copperValue: Math.max(0, toWholeNumber(wallet?.copperValue) - Math.max(0, toWholeNumber(amountCopper))),
});

export const hasEnough = (wallet: Money | null | undefined, costCopper: number): boolean =>
  toWholeNumber(wallet?.copperValue) >= Math.max(0, toWholeNumber(costCopper));
