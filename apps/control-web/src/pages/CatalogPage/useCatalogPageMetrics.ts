import { useMemo } from "react";
import type { BaseSpell } from "../../entities/base-spell";
import { getItemPropertyLabels, type Item, type ItemType } from "../../entities/item";
import { localizedItemName } from "../../features/shop/utils/localizedItemName";
import { getShopItemTypeLabelKey } from "../../features/shop/utils/shopItemTypes";
import type { LocaleKey } from "../../shared/i18n";
import { createTypeCounts, normalizeText } from "./catalogPage.utils";

type Props = {
  allSpells: BaseSpell[];
  deferredSearch: string;
  deferredSpellSearch: string;
  itemTypes: ItemType[];
  items: Item[];
  locale: "en" | "pt";
  spellClassFilter: string | null;
  spellLevelFilter: number | null;
  spellSchoolFilter: string | null;
  t: (key: LocaleKey) => string;
  typeFilter: "ALL" | ItemType;
};

export const useCatalogPageMetrics = ({
  allSpells,
  deferredSearch,
  deferredSpellSearch,
  itemTypes,
  items,
  locale,
  spellClassFilter,
  spellLevelFilter,
  spellSchoolFilter,
  t,
  typeFilter,
}: Props) => {
  const typeCounts = useMemo(() => {
    const counts = createTypeCounts(itemTypes);
    items.forEach((item) => {
      counts[item.type] += 1;
    });
    return counts;
  }, [items, itemTypes]);

  const filteredItems = useMemo(() => {
    const query = normalizeText(deferredSearch);
    const filtered = items.filter((item) => {
      if (typeFilter !== "ALL" && item.type !== typeFilter) {
        return false;
      }
      if (!query) {
        return true;
      }

      const haystack = [
        localizedItemName(item, locale),
        item.name,
        item.nameEnSnapshot ?? "",
        item.namePtSnapshot ?? "",
        item.description,
        item.canonicalKeySnapshot ?? "",
        item.damageDice ?? "",
        item.damageType ?? "",
        item.versatileDamage ?? "",
        item.weaponCategory ?? "",
        item.weaponRangeType ?? "",
        item.armorCategory ?? "",
        item.dexBonusRule ?? "",
        item.armorClassBase?.toString() ?? "",
        item.strengthRequirement?.toString() ?? "",
        t(getShopItemTypeLabelKey(item.type)),
        ...(item.properties ?? []),
        ...getItemPropertyLabels(item.properties, locale),
      ]
        .join(" ")
        .toLowerCase();

      return haystack.includes(query);
    });

    return filtered.sort((left, right) => {
      const typeOrder = itemTypes.indexOf(left.type) - itemTypes.indexOf(right.type);
      if (typeOrder !== 0) {
        return typeOrder;
      }

      return localizedItemName(left, locale).localeCompare(
        localizedItemName(right, locale),
        locale === "pt" ? "pt-BR" : "en-US",
      );
    });
  }, [deferredSearch, itemTypes, items, locale, t, typeFilter]);

  const filteredSpells = useMemo(() => {
    let result = allSpells;

    if (spellLevelFilter !== null) {
      result = result.filter((spell) => spell.level === spellLevelFilter);
    }
    if (spellSchoolFilter) {
      result = result.filter((spell) => spell.school === spellSchoolFilter);
    }
    if (spellClassFilter) {
      const classNeedle = spellClassFilter.toLowerCase();
      result = result.filter((spell) =>
        spell.classesJson?.some((className) => className.toLowerCase() === classNeedle),
      );
    }
    if (deferredSpellSearch.trim()) {
      const query = deferredSpellSearch.trim().toLowerCase();
      result = result.filter((spell) => {
        const haystack = [
          spell.nameEn,
          spell.namePt ?? "",
          spell.descriptionEn,
          spell.descriptionPt ?? "",
          spell.canonicalKey,
        ]
          .join(" ")
          .toLowerCase();
        return haystack.includes(query);
      });
    }

    return result;
  }, [
    allSpells,
    deferredSpellSearch,
    spellClassFilter,
    spellLevelFilter,
    spellSchoolFilter,
  ]);

  const linkedCount = items.filter((item) => item.baseItemId && !item.isCustom).length;
  const customCount = items.filter((item) => item.isCustom || !item.baseItemId).length;

  return { customCount, filteredItems, filteredSpells, linkedCount, typeCounts };
};
