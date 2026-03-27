import type { Item } from "../../../entities/item";
import { useLocale } from "../../../shared/hooks/useLocale";
import {
  formatDamageLabel,
  localizeBaseItemDexBonusRule,
} from "../../../shared/i18n/domainLabels";
import { getShopItemTypeLabelKey } from "../utils/shopItemTypes";
import { formatItemPrice } from "../utils/shopCurrency";

type Props = {
  item: Item;
  locale: string;
  localizedName: string;
  secondaryName: string | null;
  meta: {
    chipClass: string;
    iconPath: string;
    panelClass: string;
  };
  propertyItems: string[];
  sourceClass: string;
  sourceLabel: string;
  statItems: Array<{ label: string; value: string }>;
  onDelete?: (itemId: string) => void | Promise<void>;
  onEdit?: () => void;
};

export const CatalogItemReadonlyView = ({
  item,
  localizedName,
  secondaryName,
  meta,
  propertyItems,
  sourceClass,
  sourceLabel,
  statItems,
  onDelete,
  onEdit,
}: Props) => {
  const { t } = useLocale();

  return (
    <article className="group relative overflow-hidden rounded-[28px] border border-white/8 bg-[linear-gradient(180deg,rgba(8,12,28,0.92),rgba(3,7,20,0.97))] p-5 shadow-[0_24px_60px_rgba(2,6,23,0.24)] transition duration-300 hover:-translate-y-0.5 hover:border-white/12">
      <div
        className={`pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.06),transparent_28%),linear-gradient(135deg,var(--tw-gradient-stops))] ${meta.panelClass}`}
      />

      <div className="relative">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex flex-wrap gap-2">
              <span
                className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] ${meta.chipClass}`}
              >
                <svg
                  className="h-3.5 w-3.5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={1.7}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d={meta.iconPath} />
                </svg>
                {t(getShopItemTypeLabelKey(item.type))}
              </span>
              <span
                className={`rounded-full border px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] ${sourceClass}`}
              >
                {sourceLabel}
              </span>
            </div>

            <h3 className="mt-4 break-words font-display text-2xl font-bold text-white">
              {localizedName}
            </h3>
            {secondaryName && (
              <p className="mt-1 text-xs uppercase tracking-[0.18em] text-slate-500">
                {secondaryName}
              </p>
            )}
          </div>

          <div className="min-w-[120px] rounded-[24px] border border-white/8 bg-white/5 px-4 py-3 text-right">
            <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
              {t("catalog.card.price")}
            </p>
            <p className="mt-3 font-display text-2xl font-bold text-white">
              {formatItemPrice(item.price, item.priceLabel, item.priceCopperValue)}
            </p>
          </div>
        </div>

        <p className="mt-4 text-sm leading-7 text-slate-300">{item.description}</p>

        {(statItems.length > 0 || propertyItems.length > 0) && (
          <div className="mt-5 grid gap-3 xl:grid-cols-[minmax(0,0.88fr)_minmax(0,1.12fr)]">
            {statItems.length > 0 && (
              <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
                {statItems.map((stat) => (
                  <div
                    key={stat.label}
                    className="rounded-2xl border border-white/8 bg-slate-950/55 px-4 py-3"
                  >
                    <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
                      {stat.label}
                    </p>
                    <p className="mt-2 text-sm font-semibold text-white">{stat.value}</p>
                  </div>
                ))}
              </div>
            )}

            {propertyItems.length > 0 && (
              <div className="rounded-2xl border border-white/8 bg-slate-950/55 px-4 py-3">
                <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
                  {t("catalog.card.properties")}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {propertyItems.map((property) => (
                    <span
                      key={property}
                      className="rounded-full border border-white/8 bg-white/5 px-3 py-1.5 text-xs text-slate-200"
                    >
                      {property}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {(onEdit || onDelete) && (
          <div className="mt-5 flex flex-wrap gap-2">
            {onEdit && (
              <button
                type="button"
                onClick={onEdit}
                className="inline-flex items-center rounded-full border border-white/10 bg-white/5 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-100 transition hover:border-white/20 hover:bg-white/9"
              >
                {t("catalog.edit")}
              </button>
            )}
            {onDelete && (
              <button
                type="button"
                onClick={() => void onDelete(item.id)}
                className="inline-flex items-center rounded-full border border-rose-300/18 bg-rose-400/10 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-rose-100 transition hover:border-rose-300/28 hover:bg-rose-400/16"
              >
                {t("catalog.delete")}
              </button>
            )}
          </div>
        )}
      </div>
    </article>
  );
};

export const buildCatalogStatItems = (
  item: Item,
  locale: string,
  labels: {
    damage: string;
    range: string;
    versatileDamage: string;
    armorClassBase: string;
    dexBonusRule: string;
    strengthRequirement: string;
    weight: string;
  },
) =>
  [
    item.damageDice
      ? {
          label: labels.damage,
          value: formatDamageLabel(item.damageDice, item.damageType, locale) ?? item.damageDice,
        }
      : null,
    typeof item.rangeMeters === "number"
      ? {
          label: labels.range,
          value:
            typeof item.rangeLongMeters === "number"
              ? `${item.rangeMeters}/${item.rangeLongMeters} m`
              : `${item.rangeMeters} m`,
        }
      : null,
    item.versatileDamage
      ? { label: labels.versatileDamage, value: item.versatileDamage }
      : null,
    typeof item.armorClassBase === "number"
      ? { label: labels.armorClassBase, value: `${item.armorClassBase}` }
      : null,
    item.dexBonusRule
      ? {
          label: labels.dexBonusRule,
          value: localizeBaseItemDexBonusRule(item.dexBonusRule, locale) ?? item.dexBonusRule,
        }
      : null,
    typeof item.strengthRequirement === "number"
      ? { label: labels.strengthRequirement, value: `${item.strengthRequirement}` }
      : null,
    typeof item.weight === "number"
      ? { label: labels.weight, value: `${item.weight}` }
      : null,
  ].filter((entry): entry is { label: string; value: string } => Boolean(entry));
