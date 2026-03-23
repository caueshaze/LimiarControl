import type {
  CampaignEntityPayload,
  EntityCategory,
} from "../../../../entities/campaign-entity";
import { CATEGORIES, fieldClass, sectionClass } from "./constants";
import type { SetCampaignEntityField, Translate } from "./types";

type Props = {
  form: CampaignEntityPayload;
  hasInitialValue: boolean;
  setField: SetCampaignEntityField;
  t: Translate;
};

export const CampaignEntityGeneralSection = ({ form, hasInitialValue, setField, t }: Props) => (
  <div className={sectionClass}>
    <p className="mb-3 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
      {t("entity.form.generalSection")}
    </p>
    <div className="grid gap-3 xl:grid-cols-[minmax(0,1.2fr)_220px]">
      <input
        value={form.name}
        onChange={(event) => setField("name", event.target.value)}
        placeholder={t("entity.form.name")}
        required
        className={fieldClass}
      />
      <select
        value={form.category}
        onChange={(event) => setField("category", event.target.value as EntityCategory)}
        className={fieldClass}
      >
        {CATEGORIES.map((category) => (
          <option key={category} value={category}>
            {t(`entity.category.${category}`)}
          </option>
        ))}
      </select>
    </div>

    <textarea
      value={form.description ?? ""}
      onChange={(event) => setField("description", event.target.value)}
      placeholder={t("entity.form.description")}
      rows={4}
      className={`${fieldClass} mt-2`}
    />

    <input
      value={form.imageUrl ?? ""}
      onChange={(event) => setField("imageUrl", event.target.value)}
      placeholder={t("entity.form.imageUrl")}
      className={`${fieldClass} mt-2`}
    />

    <div className="mt-4 rounded-3xl border border-emerald-300/12 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.14),transparent_42%),linear-gradient(180deg,rgba(255,255,255,0.03),rgba(255,255,255,0.01))] p-4 sm:p-5">
      <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-emerald-100/80">
        {t("entity.form.combatBlockSection")}
      </p>
      <p className="mt-3 text-lg font-semibold text-slate-100">
        {hasInitialValue ? t("entity.form.editTitle") : t("entity.form.title")}
      </p>
      <p className="mt-2 max-w-3xl text-sm leading-7 text-slate-300">
        {t("entity.form.layoutHint")}
      </p>
    </div>
  </div>
);
