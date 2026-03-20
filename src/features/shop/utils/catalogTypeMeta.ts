import type { ItemType } from "../../../entities/item";

export const CATALOG_TYPE_META: Record<
  ItemType,
  {
    iconPath: string;
    accentClass: string;
    chipClass: string;
    panelClass: string;
  }
> = {
  WEAPON: {
    iconPath:
      "M4 20l8.5-8.5m0 0L16 8m-3.5 3.5L9 8m3.5 3.5L20 4m-8 8L4 4",
    accentClass: "from-rose-400/30 via-orange-300/18 to-transparent",
    chipClass: "border-rose-300/20 bg-rose-400/12 text-rose-100",
    panelClass: "from-rose-400/12 via-orange-400/8 to-transparent",
  },
  ARMOR: {
    iconPath:
      "M12 3l7 3v5c0 4.5-2.7 8.6-7 10-4.3-1.4-7-5.5-7-10V6l7-3z",
    accentClass: "from-sky-300/28 via-cyan-300/14 to-transparent",
    chipClass: "border-sky-300/20 bg-sky-400/12 text-sky-100",
    panelClass: "from-sky-400/12 via-cyan-300/8 to-transparent",
  },
  CONSUMABLE: {
    iconPath:
      "M10 4h4m-3 0v6m-3 0h8m-6 0v7a2 2 0 104 0v-7",
    accentClass: "from-emerald-300/28 via-lime-300/14 to-transparent",
    chipClass: "border-emerald-300/20 bg-emerald-400/12 text-emerald-100",
    panelClass: "from-emerald-400/12 via-lime-300/8 to-transparent",
  },
  MISC: {
    iconPath:
      "M5 12h14M12 5v14M7.5 7.5l9 9m0-9l-9 9",
    accentClass: "from-violet-300/28 via-fuchsia-300/14 to-transparent",
    chipClass: "border-violet-300/20 bg-violet-400/12 text-violet-100",
    panelClass: "from-violet-400/12 via-fuchsia-300/8 to-transparent",
  },
  MAGIC: {
    iconPath:
      "M12 3l1.8 4.7L19 9.5l-4.1 3 1.5 5-4.4-2.7-4.4 2.7 1.5-5-4.1-3 5.2-1.8L12 3z",
    accentClass: "from-amber-300/28 via-fuchsia-300/12 to-transparent",
    chipClass: "border-amber-300/20 bg-amber-300/12 text-amber-50",
    panelClass: "from-amber-300/12 via-fuchsia-300/8 to-transparent",
  },
};
