import { getItemPropertyLabels } from "../../../entities/item";
import type { CharacterSheet, InventoryItem } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import { Section, RemoveBtn } from "./Section";
import { input, fieldLabel, btnPrimary } from "./styles";
import { computeTotalWeight, safeParseInt } from "../utils/calculations";
import {
  findCreationItemByCanonicalKey,
  getCreationCatalogItemsSorted,
  getCreationItemCatalog,
  type CreationCatalogItem,
} from "../utils/creationItemCatalog";
import { useLocale } from "../../../shared/hooks/useLocale";
import type { LocaleKey } from "../../../shared/i18n";
import {
  localizeBaseItemDexBonusRule,
  formatDamageLabel,
} from "../../../shared/i18n/domainLabels";
import { buildWalletDisplay } from "../../shop/utils/shopCurrency";

type Props = {
  inventory: CharacterSheet["inventory"];
  currency?: CharacterSheet["currency"];
  onAdd: SheetActions["addItem"];
  onRemove: SheetActions["removeItem"];
  onUpdate: SheetActions["updateItem"];
  onSelectCatalogItem?: SheetActions["selectInventoryCatalogItem"];
  creationCatalogBacked?: boolean;
  readOnly?: boolean;
};

export const Equipment = ({
  inventory,
  currency,
  onAdd,
  onRemove,
  onUpdate,
  onSelectCatalogItem,
  creationCatalogBacked = false,
  readOnly = false,
}: Props) => {
  const { t, locale } = useLocale();
  const totalWeight = computeTotalWeight(inventory);
  const hasCurrency = Boolean(
    currency && Object.values(currency).some((value) => value > 0),
  );
  const walletCoins = buildWalletDisplay(currency, { includeZeroGp: false });
  const catalogOptions = creationCatalogBacked ? getCreationCatalogItemsSorted(getCreationItemCatalog()) : [];
  const canAddCatalogItem = !creationCatalogBacked || catalogOptions.length > 0;

  return (
    <Section title={t("sheet.equipment.title")} color="bg-amber-500">
      <div className="space-y-2">
        {inventory.length === 0 && (
          <div className="flex flex-col items-center gap-2 py-6 text-slate-600">
            <svg className="h-8 w-8 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
            </svg>
            <p className="text-xs">{readOnly ? t("sheet.equipment.emptyCreation") : t("sheet.equipment.empty")}</p>
          </div>
        )}
        {inventory.map((item) => (
          <ItemRow
            key={item.id}
            item={item}
            onRemove={onRemove}
            onUpdate={onUpdate}
            onSelectCatalogItem={onSelectCatalogItem}
            creationCatalogBacked={creationCatalogBacked}
            catalogOptions={catalogOptions}
            readOnly={readOnly}
            locale={locale}
            t={t}
          />
        ))}
      </div>

      <div className="mt-3 flex items-center justify-between border-t border-slate-800 pt-3">
        <div className="space-y-1">
          <span className="block text-xs text-slate-500">
            {t("sheet.equipment.totalWeight")}:{" "}
            <span className="font-semibold text-slate-300">{totalWeight} lb</span>
          </span>
          {readOnly && hasCurrency && (
            <div className="pt-1">
              <span className="block text-xs text-slate-500">
                {t("sheet.equipment.lockedFunds")}:
              </span>
              <div className="mt-2 flex flex-wrap gap-2">
                {walletCoins.map((coin) => (
                  <span key={coin.coin} className={coin.className} title={coin.longLabel}>
                    {coin.amount} {coin.shortLabel}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
        {!readOnly && (
          <button type="button" onClick={onAdd} disabled={!canAddCatalogItem} className={`${btnPrimary} disabled:cursor-not-allowed disabled:opacity-50`}>
            {t("sheet.equipment.addItem")}
          </button>
        )}
      </div>
    </Section>
  );
};

type RowProps = {
  item: InventoryItem;
  onRemove: SheetActions["removeItem"];
  onUpdate: SheetActions["updateItem"];
  onSelectCatalogItem?: SheetActions["selectInventoryCatalogItem"];
  creationCatalogBacked: boolean;
  catalogOptions: ReturnType<typeof getCreationCatalogItemsSorted>;
  readOnly: boolean;
  locale: string;
  t: (key: LocaleKey) => string;
};

const ItemRow = ({
  item,
  onRemove,
  onUpdate,
  onSelectCatalogItem,
  creationCatalogBacked,
  catalogOptions,
  readOnly,
  locale,
  t,
}: RowProps) => {
  const catalogItem = creationCatalogBacked
    ? findCreationItemByCanonicalKey(item.canonicalKey, getCreationItemCatalog())
    : null;
  const detailBits = catalogItem ? buildCatalogDetailBits(catalogItem, locale, t) : [];
  const propertyLabels = catalogItem ? getItemPropertyLabels(catalogItem.properties, locale) : [];
  const description =
    catalogItem
      ? (locale === "pt" ? catalogItem.descriptionPt || catalogItem.description : catalogItem.description || catalogItem.descriptionPt)
      : "";

  return (
    <div className="flex items-start gap-2 rounded-xl border border-slate-800/60 bg-void-950/40 p-3">
      <div className="flex-1 space-y-3">
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <div className="sm:col-span-2">
            <label className={fieldLabel}>{t("sheet.equipment.itemName")}</label>
            {creationCatalogBacked ? (
              <select
                value={item.canonicalKey ?? ""}
                disabled={readOnly}
                onChange={(e) => onSelectCatalogItem?.(item.id, e.target.value)}
                className={input}
              >
                {!item.canonicalKey ? (
                  <option value="">
                    {t("sheet.equipment.itemNamePlaceholder")}
                  </option>
                ) : null}
                {catalogOptions.map((option) => (
                  <option key={option.canonicalKey} value={option.canonicalKey}>
                    {locale === "pt" ? option.namePt : option.name}
                  </option>
                ))}
              </select>
            ) : (
              <input
                type="text"
                placeholder={t("sheet.equipment.itemNamePlaceholder")}
                value={item.name}
                disabled={readOnly}
                onChange={(e) => onUpdate(item.id, "name", e.target.value)}
                className={input}
              />
            )}
          </div>
          <div>
            <label className={fieldLabel}>{t("sheet.equipment.qty")}</label>
            <input
              type="number"
              min={0}
              value={item.quantity}
              disabled={readOnly}
              onChange={(e) => onUpdate(item.id, "quantity", Math.max(0, safeParseInt(e.target.value)))}
              className={input}
            />
          </div>
          <div>
            <label className={fieldLabel}>{t("sheet.equipment.weight")}</label>
            <input
              type="number"
              min={0}
              step={0.1}
              value={catalogItem?.weight ?? item.weight}
              disabled={readOnly || creationCatalogBacked}
              onChange={(e) => onUpdate(item.id, "weight", Math.max(0, parseFloat(e.target.value) || 0))}
              className={input}
            />
          </div>
          <div className="sm:col-span-4">
            <label className={fieldLabel}>{t("sheet.equipment.notes")}</label>
            <input
              type="text"
              placeholder={t("sheet.equipment.notesPlaceholder")}
              value={item.notes}
              disabled={readOnly}
              onChange={(e) => onUpdate(item.id, "notes", e.target.value)}
              className={input}
            />
          </div>
        </div>

        {creationCatalogBacked && (detailBits.length > 0 || propertyLabels.length > 0 || description) ? (
          <div className="rounded-2xl border border-slate-800/80 bg-slate-950/50 px-3 py-3">
            {detailBits.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {detailBits.map((bit) => (
                  <span
                    key={bit}
                    className="rounded-full border border-slate-700 bg-slate-950/70 px-2 py-1 text-[11px] text-slate-300"
                  >
                    {bit}
                  </span>
                ))}
              </div>
            ) : null}

            {propertyLabels.length > 0 ? (
              <div className="mt-2 flex flex-wrap gap-2">
                {propertyLabels.map((property) => (
                  <span
                    key={property}
                    className="rounded-full border border-limiar-500/25 bg-limiar-500/10 px-2 py-1 text-[11px] text-limiar-100"
                  >
                    {property}
                  </span>
                ))}
              </div>
            ) : null}

            {description ? (
              <p className="mt-2 text-xs leading-6 text-slate-400">
                {description}
              </p>
            ) : null}
          </div>
        ) : null}
      </div>
      {!readOnly && <RemoveBtn onClick={() => onRemove(item.id)} title="Remove item" />}
    </div>
  );
};

const buildCatalogDetailBits = (
  item: CreationCatalogItem,
  locale: string,
  t: (key: LocaleKey) => string,
) => {
  const strengthLabel = locale === "pt" ? "FOR" : "STR";
  const versatileLabel = locale === "pt" ? "Versátil" : "Versatile";
  const bits = [
    item.damageDice ? `${t("shop.card.damage")} ${formatDamageLabel(item.damageDice, item.damageType, locale)}` : null,
    item.rangeNormalMeters
      ? `${t("shop.card.range")} ${item.rangeNormalMeters}${item.rangeLongMeters ? `/${item.rangeLongMeters}` : ""}m`
      : null,
    item.armorClassBase != null
      ? `CA ${item.armorClassBase}${localizeBaseItemDexBonusRule(item.dexBonusRule, locale) ? ` · ${localizeBaseItemDexBonusRule(item.dexBonusRule, locale)}` : ""}`
      : null,
    item.strengthRequirement ? `${strengthLabel} ${item.strengthRequirement}` : null,
    item.versatileDamage ? `${versatileLabel} ${item.versatileDamage}` : null,
    item.weight ? `${t("shop.card.weight")} ${item.weight}` : null,
  ];

  return bits.filter((bit): bit is string => Boolean(bit));
};
