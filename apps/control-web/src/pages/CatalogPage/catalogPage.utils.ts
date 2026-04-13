import type { ItemType } from "../../entities/item";
import type { LocaleKey } from "../../shared/i18n";

export type CatalogTab = "items" | "spells";

export const normalizeText = (value: string) => value.trim().toLowerCase();

export const createTypeCounts = (itemTypes: ItemType[]) =>
  itemTypes.reduce(
    (accumulator, itemType) => {
      accumulator[itemType] = 0;
      return accumulator;
    },
    {} as Record<ItemType, number>,
  );

export const resolveCatalogMessage = (
  t: (key: LocaleKey) => string,
  message: string | undefined,
  fallback: LocaleKey,
) => {
  if (!message) {
    return t(fallback);
  }

  return (t(message as LocaleKey) as string | undefined) ?? message;
};
