import {
  ITEM_PROPERTY_SLUGS,
  getItemPropertyLabel,
  type ItemPropertySlug,
} from "../../../entities/item";
import { useLocale } from "../../../shared/hooks/useLocale";

type ItemPropertiesSelectorProps = {
  available?: ItemPropertySlug[];
  disabled?: boolean;
  legacyUnknown?: string[];
  value: ItemPropertySlug[];
  onChange: (next: ItemPropertySlug[]) => void;
};

export const ItemPropertiesSelector = ({
  available = ITEM_PROPERTY_SLUGS,
  disabled = false,
  legacyUnknown = [],
  value,
  onChange,
}: ItemPropertiesSelectorProps) => {
  const { t, locale } = useLocale();

  const toggleProperty = (slug: ItemPropertySlug) => {
    if (disabled) {
      return;
    }
    onChange(
      value.includes(slug)
        ? value.filter((entry) => entry !== slug)
        : [...value, slug],
    );
  };

  return (
    <div className="space-y-3">
      <div className="rounded-2xl border border-white/8 bg-slate-950/45 p-3">
        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
          {t("catalog.properties.selected")}
        </p>

        {value.length > 0 ? (
          <div className="mt-3 flex flex-wrap gap-2">
            {value.map((slug) => {
              const label = getItemPropertyLabel(slug, locale);
              return (
                <button
                  key={slug}
                  type="button"
                  onClick={() => toggleProperty(slug)}
                  disabled={disabled}
                  className="inline-flex items-center gap-2 rounded-full border border-limiar-300/18 bg-limiar-400/12 px-3 py-1.5 text-xs font-semibold text-limiar-100 transition hover:border-limiar-300/28 hover:bg-limiar-400/16 disabled:cursor-not-allowed disabled:opacity-70"
                >
                  <span>{label}</span>
                  <span className="text-[10px] text-limiar-50/80">x</span>
                </button>
              );
            })}
          </div>
        ) : (
          <p className="mt-3 text-xs text-slate-400">
            {t("catalog.properties.noneSelected")}
          </p>
        )}

        {legacyUnknown.length > 0 && (
          <p className="mt-3 text-xs leading-6 text-amber-200">
            {t("catalog.properties.legacyUnknown")} {legacyUnknown.join(", ")}
          </p>
        )}
      </div>

      <div className="rounded-2xl border border-white/8 bg-slate-950/30 p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
            {t("catalog.properties.available")}
          </p>
          <p className="text-[11px] text-slate-500">
            {t("catalog.properties.helper")}
          </p>
        </div>

        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          {available.map((slug) => {
            const active = value.includes(slug);
            return (
              <button
                key={slug}
                type="button"
                onClick={() => toggleProperty(slug)}
                disabled={disabled}
                className={`rounded-2xl border px-3 py-2.5 text-left text-sm transition ${
                  active
                    ? "border-limiar-300/18 bg-limiar-400/12 text-limiar-50"
                    : "border-white/8 bg-white/3 text-slate-300 hover:border-white/16 hover:bg-white/6"
                } disabled:cursor-not-allowed disabled:opacity-70`}
              >
                {getItemPropertyLabel(slug, locale)}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};
