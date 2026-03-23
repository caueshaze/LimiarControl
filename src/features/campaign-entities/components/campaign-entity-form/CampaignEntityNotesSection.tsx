import { type CampaignEntityPayload } from "../../../../entities/campaign-entity";
import { fieldClass, sectionClass } from "./constants";
import type { SetCampaignEntityField, Translate } from "./types";

type Props = {
  form: CampaignEntityPayload;
  setField: SetCampaignEntityField;
  t: Translate;
};

export const CampaignEntityNotesSection = ({ form, setField, t }: Props) => (
  <div className={sectionClass}>
    <p className="mb-3 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
      {t("entity.form.notesSection")}
    </p>

    <div>
      <label className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-slate-500">
        {t("entity.form.actions")}
      </label>
      <p className="mb-2 text-xs text-slate-500">
        {t("entity.form.actionsSupportOnly")}
      </p>
      <textarea
        value={form.actions ?? ""}
        onChange={(event) => setField("actions", event.target.value)}
        placeholder={t("entity.form.actionsPlaceholder")}
        rows={2}
        className={fieldClass}
      />
    </div>

    <div className="mt-4 grid gap-3 xl:grid-cols-2">
      <textarea
        value={form.notesPrivate ?? ""}
        onChange={(event) => setField("notesPrivate", event.target.value)}
        placeholder={t("entity.form.notesPrivatePlaceholder")}
        rows={2}
        className={fieldClass}
      />
      <textarea
        value={form.notesPublic ?? ""}
        onChange={(event) => setField("notesPublic", event.target.value)}
        placeholder={t("entity.form.notesPublicPlaceholder")}
        rows={2}
        className={fieldClass}
      />
    </div>
  </div>
);
