import { CampaignSystemType } from "../../../entities/campaign";
import type { Item, ItemInput } from "../../../entities/item";

type CatalogAdapter = {
  normalizeItem: (item: Item) => Item;
  normalizeItemInput: (payload: ItemInput) => ItemInput;
  getMissingSeedItems: (existingItems: Pick<Item, "name">[]) => Item[];
};

const genericCatalogAdapter: CatalogAdapter = {
  normalizeItem: (item) => ({
    ...item,
    name: item.name.trim(),
  }),
  normalizeItemInput: (payload) => ({
    ...payload,
    name: payload.name.trim(),
  }),
  getMissingSeedItems: () => [],
};

const adapterCache = new Map<CampaignSystemType, Promise<CatalogAdapter>>();

const loadDndCatalogAdapter = async (): Promise<CatalogAdapter> => {
  const [
    { canonicalizeDndItemName },
    { getBaseCatalogItemByName, getMissingBaseCatalogItems },
  ] = await Promise.all([
    import("../../../entities/dnd-base"),
    import("./baseCatalogItems"),
  ]);

  return {
    normalizeItem: (item) => {
      const canonicalName = canonicalizeDndItemName(item.name);
      const baseItem = getBaseCatalogItemByName(canonicalName);
      const priceMatchesBase =
        baseItem &&
        typeof item.price === "number" &&
        typeof baseItem.price === "number" &&
        Math.abs(item.price - baseItem.price) < 0.0001;

      return {
        ...item,
        name: canonicalName,
        priceLabel: item.priceLabel ?? (priceMatchesBase ? baseItem?.priceLabel : undefined),
      };
    },
    normalizeItemInput: (payload) => ({
      ...payload,
      name: canonicalizeDndItemName(payload.name.trim()),
    }),
    getMissingSeedItems: (existingItems) => getMissingBaseCatalogItems(existingItems),
  };
};

const loadCatalogAdapter = (
  systemType: CampaignSystemType | null | undefined,
): Promise<CatalogAdapter> => {
  if (systemType !== CampaignSystemType.DND5E) {
    return Promise.resolve(genericCatalogAdapter);
  }

  const cachedAdapter = adapterCache.get(CampaignSystemType.DND5E);
  if (cachedAdapter) {
    return cachedAdapter;
  }

  const nextAdapter = loadDndCatalogAdapter();
  adapterCache.set(CampaignSystemType.DND5E, nextAdapter);
  return nextAdapter;
};

export const normalizeCatalogItemsForSystem = async (
  systemType: CampaignSystemType | null | undefined,
  items: Item[],
) => {
  const adapter = await loadCatalogAdapter(systemType);
  return items.map(adapter.normalizeItem);
};

export const normalizeCatalogItemInputForSystem = async (
  systemType: CampaignSystemType | null | undefined,
  payload: ItemInput,
) => {
  const adapter = await loadCatalogAdapter(systemType);
  return adapter.normalizeItemInput(payload);
};

export const getMissingCatalogSeedItemsForSystem = async (
  systemType: CampaignSystemType | null | undefined,
  existingItems: Pick<Item, "name">[],
) => {
  const adapter = await loadCatalogAdapter(systemType);
  return adapter.getMissingSeedItems(existingItems);
};
