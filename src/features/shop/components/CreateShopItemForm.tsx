import { useState } from "react";
import type { ItemInput, ItemType } from "../../../entities/item";
import { useLocale } from "../../../shared/hooks/useLocale";

type CreateShopItemFormProps = {
  onCreate: (payload: ItemInput) => void;
  itemTypes: ItemType[];
};

export const CreateShopItemForm = ({ onCreate, itemTypes }: CreateShopItemFormProps) => {
  const { t } = useLocale();
  const [name, setName] = useState("");
  const [type, setType] = useState<ItemType>(itemTypes[0]);
  const [description, setDescription] = useState("");
  const [price, setPrice] = useState("");
  const [weight, setWeight] = useState("");
  const [damageDice, setDamageDice] = useState("");
  const [rangeMeters, setRangeMeters] = useState("");
  const [properties, setProperties] = useState("");
  const damageOptions = ["", "1d4", "1d6", "1d8", "1d10", "1d12", "2d6"];

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!name.trim() || !description.trim() || !price.trim()) {
      return;
    }

    onCreate({
      name: name.trim(),
      type,
      description: description.trim(),
      price: price,
      weight: weight,
      damageDice: damageDice.trim() || undefined,
      rangeMeters: rangeMeters,
      properties: properties
        ? properties
            .split(",")
            .map((prop) => prop.trim())
            .filter(Boolean)
        : undefined,
    });

    setName("");
    setType(itemTypes[0]);
    setDescription("");
    setPrice("");
    setWeight("");
    setDamageDice("");
    setRangeMeters("");
    setProperties("");
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900/40 p-4"
    >
      <div>
        <label className="text-xs font-semibold uppercase tracking-wide text-slate-400">
          {t("shop.form.name")}
        </label>
        <input
          value={name}
          onChange={(event) => setName(event.target.value)}
          className="mt-2 w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-slate-500 focus:outline-none"
          placeholder={t("shop.form.namePlaceholder")}
        />
      </div>
      <div>
        <label className="text-xs font-semibold uppercase tracking-wide text-slate-400">
          {t("shop.form.type")}
        </label>
        <select
          value={type}
          onChange={(event) => setType(event.target.value as ItemType)}
          className="mt-2 w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-slate-500 focus:outline-none"
        >
          {itemTypes.map((itemType) => (
            <option key={itemType} value={itemType}>
              {itemType}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="text-xs font-semibold uppercase tracking-wide text-slate-400">
          {t("shop.form.description")}
        </label>
        <textarea
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          className="mt-2 w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-slate-500 focus:outline-none"
          rows={3}
          placeholder={t("shop.form.descriptionPlaceholder")}
        />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            {t("shop.form.price")}
          </label>
          <input
            value={price}
            onChange={(event) => setPrice(event.target.value)}
            className="mt-2 w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-slate-500 focus:outline-none"
            inputMode="numeric"
            placeholder={t("shop.form.pricePlaceholder")}
          />
        </div>
        <div>
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            {t("shop.form.weight")}
          </label>
          <input
            value={weight}
            onChange={(event) => setWeight(event.target.value)}
            className="mt-2 w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-slate-500 focus:outline-none"
            inputMode="numeric"
            placeholder={t("shop.form.weightPlaceholder")}
          />
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            {t("shop.form.damage")}
          </label>
          <select
            value={damageDice}
            onChange={(event) => setDamageDice(event.target.value)}
            className="mt-2 w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-slate-500 focus:outline-none"
          >
            {damageOptions.map((option) => (
              <option key={option || "none"} value={option}>
                {option || t("shop.form.damageNone")}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            {t("shop.form.range")}
          </label>
          <input
            value={rangeMeters}
            onChange={(event) => setRangeMeters(event.target.value)}
            className="mt-2 w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-slate-500 focus:outline-none"
            inputMode="numeric"
            placeholder={t("shop.form.rangePlaceholder")}
          />
        </div>
      </div>
      <div>
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            {t("shop.form.properties")}
          </label>
        <input
          value={properties}
          onChange={(event) => setProperties(event.target.value)}
          className="mt-2 w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-slate-500 focus:outline-none"
          placeholder={t("shop.form.propertiesPlaceholder")}
        />
      </div>
      <button
        type="submit"
        disabled={!name.trim() || !description.trim() || !price.trim()}
        className="w-full rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-900 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {t("shop.form.submit")}
      </button>
    </form>
  );
};
