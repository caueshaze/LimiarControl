import { useState } from "react";
import type { Item, ItemInput, ItemType } from "../../../entities/item";
import { useLocale } from "../../../shared/hooks/useLocale";

type CatalogItemCardProps = {
  item: Item;
  itemTypes: ItemType[];
  onUpdate?: (itemId: string, payload: ItemInput) => void;
  onDelete?: (itemId: string) => void;
};

export const CatalogItemCard = ({
  item,
  itemTypes,
  onUpdate,
  onDelete,
}: CatalogItemCardProps) => {
  const { t } = useLocale();
  const [isEditing, setIsEditing] = useState(false);
  const [name, setName] = useState(item.name);
  const [type, setType] = useState<ItemType>(item.type);
  const [description, setDescription] = useState(item.description);
  const [price, setPrice] = useState(item.price?.toString() ?? "");
  const [weight, setWeight] = useState(item.weight?.toString() ?? "");
  const [damageDice, setDamageDice] = useState(item.damageDice ?? "");
  const [rangeMeters, setRangeMeters] = useState(item.rangeMeters?.toString() ?? "");
  const [properties, setProperties] = useState(item.properties?.join(", ") ?? "");
  const damageOptions = ["", "1d4", "1d6", "1d8", "1d10", "1d12", "2d6"];
  const damageValues = damageOptions.includes(damageDice)
    ? damageOptions
    : ["", damageDice, "1d4", "1d6", "1d8", "1d10", "1d12", "2d6"];

  const handleSave = () => {
    if (!onUpdate) return;
    onUpdate(item.id, {
      name: name.trim(),
      type,
      description: description.trim(),
      price,
      weight,
      damageDice: damageDice.trim() || undefined,
      rangeMeters,
      properties: properties
        ? properties
          .split(",")
          .map((prop) => prop.trim())
          .filter(Boolean)
        : undefined,
    });
    setIsEditing(false);
  };

  if (!isEditing) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-200">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-base font-semibold text-slate-100">{item.name}</p>
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
              {item.type}
            </p>
          </div>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-900">
            {item.price ?? "—"}
          </span>
        </div>
        <p className="mt-3 text-xs text-slate-400">{item.description}</p>
        {(onUpdate || onDelete) && (
          <div className="mt-4 flex flex-wrap gap-2 text-xs">
            {onUpdate && (
              <button
                type="button"
                onClick={() => setIsEditing(true)}
                className="rounded-full border border-slate-700 px-3 py-1 text-slate-200"
              >
                {t("catalog.edit")}
              </button>
            )}
            {onDelete && (
              <button
                type="button"
                onClick={() => onDelete(item.id)}
                className="rounded-full border border-rose-700 px-3 py-1 text-rose-200"
              >
                {t("catalog.delete")}
              </button>
            )}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-200">
      <div className="space-y-3">
        <div className="grid gap-3 sm:grid-cols-2">
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-slate-500 focus:outline-none"
          />
          <select
            value={type}
            onChange={(event) => setType(event.target.value as ItemType)}
            className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-slate-500 focus:outline-none"
          >
            {itemTypes.map((itemType) => (
              <option key={itemType} value={itemType}>
                {itemType}
              </option>
            ))}
          </select>
        </div>
        <textarea
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-slate-500 focus:outline-none"
          rows={3}
          placeholder={t("shop.form.descriptionPlaceholder")}
        />
        <div className="grid gap-3 sm:grid-cols-2">
          <input
            value={price}
            onChange={(event) => setPrice(event.target.value)}
            className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-slate-500 focus:outline-none"
            placeholder={t("shop.form.pricePlaceholder")}
          />
          <input
            value={weight}
            onChange={(event) => setWeight(event.target.value)}
            className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-slate-500 focus:outline-none"
            placeholder={t("shop.form.weightPlaceholder")}
          />
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <select
            value={damageDice}
            onChange={(event) => setDamageDice(event.target.value)}
            className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-slate-500 focus:outline-none"
          >
            {damageValues.map((option) => (
              <option key={option || "none"} value={option}>
                {option || t("shop.form.damageNone")}
              </option>
            ))}
          </select>
          <input
            value={rangeMeters}
            onChange={(event) => setRangeMeters(event.target.value)}
            className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-slate-500 focus:outline-none"
            placeholder={t("shop.form.rangePlaceholder")}
          />
        </div>
        <input
          value={properties}
          onChange={(event) => setProperties(event.target.value)}
          className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-slate-500 focus:outline-none"
        />
        <div className="flex flex-wrap gap-2 text-xs">
          <button
            type="button"
            onClick={handleSave}
            className="rounded-full bg-slate-100 px-3 py-1 font-semibold text-slate-900"
          >
            {t("catalog.save")}
          </button>
          <button
            type="button"
            onClick={() => setIsEditing(false)}
            className="rounded-full border border-slate-700 px-3 py-1 text-slate-200"
          >
            {t("catalog.cancel")}
          </button>
        </div>
      </div>
    </div>
  );
};
