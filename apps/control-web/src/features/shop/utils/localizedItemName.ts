import type { Item } from "../../../entities/item";

export const localizedItemName = (
  item: Pick<Item, "name" | "nameEnSnapshot" | "namePtSnapshot">,
  locale: "en" | "pt" | string,
): string => {
  if (locale === "pt" && item.namePtSnapshot) {
    return item.namePtSnapshot;
  }
  if (locale === "en" && item.nameEnSnapshot) {
    return item.nameEnSnapshot;
  }
  return item.namePtSnapshot || item.nameEnSnapshot || item.name;
};
