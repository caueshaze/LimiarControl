import type { CampaignSystemType } from "../../../../entities/campaign";
import { useEffect, useMemo, useState } from "react";
import { type BaseSpell } from "../../../../entities/base-spell";
import { type Item } from "../../../../entities/item";
import { baseSpellsRepo } from "../../../../shared/api/baseSpellsRepo";
import { itemsRepo } from "../../../../shared/api/itemsRepo";
import type { Translate, WeaponLabelFn, SpellLabelFn } from "./types";

type Props = {
  locale: "pt" | "en";
  selectedCampaignId?: string | null;
  systemType?: CampaignSystemType;
  t: Translate;
};

export const useCombatActionCatalog = ({
  locale,
  selectedCampaignId,
  systemType,
  t,
}: Props) => {
  const [catalogWeapons, setCatalogWeapons] = useState<Item[]>([]);
  const [catalogSpells, setCatalogSpells] = useState<BaseSpell[]>([]);
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [catalogError, setCatalogError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedCampaignId || !systemType) {
      setCatalogWeapons([]);
      setCatalogSpells([]);
      setCatalogError(null);
      return;
    }

    let active = true;
    setCatalogLoading(true);
    setCatalogError(null);

    Promise.all([
      itemsRepo.list(selectedCampaignId),
      baseSpellsRepo.list({ system: systemType }),
    ])
      .then(([items, spells]) => {
        if (!active) return;
        const weapons = Array.isArray(items)
          ? items.filter(
              (item) =>
                item.isEnabled !== false &&
                (item.itemKind === "weapon" || item.type === "WEAPON"),
            )
          : [];
        setCatalogWeapons(weapons);
        setCatalogSpells(Array.isArray(spells) ? spells : []);
      })
      .catch(() => {
        if (!active) return;
        setCatalogWeapons([]);
        setCatalogSpells([]);
        setCatalogError(t("entity.form.catalogLoadError"));
      })
      .finally(() => {
        if (active) {
          setCatalogLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [selectedCampaignId, systemType, t]);

  const weaponLabel: WeaponLabelFn = (weapon) =>
    locale === "pt"
      ? weapon.namePtSnapshot ?? weapon.name
      : weapon.nameEnSnapshot ?? weapon.name;
  const spellLabel: SpellLabelFn = (spell) =>
    locale === "pt" ? spell.namePt ?? spell.nameEn : spell.nameEn;

  const weaponById = useMemo(
    () => new Map(catalogWeapons.map((weapon) => [weapon.id, weapon])),
    [catalogWeapons],
  );
  const spellByKey = useMemo(
    () => new Map(catalogSpells.map((spell) => [spell.canonicalKey, spell])),
    [catalogSpells],
  );

  return {
    catalogWeapons,
    catalogSpells,
    catalogLoading,
    catalogError,
    weaponLabel,
    spellLabel,
    weaponById,
    spellByKey,
  };
};
