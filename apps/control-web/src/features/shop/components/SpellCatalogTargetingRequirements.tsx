import type { Dispatch, SetStateAction } from "react";
import type { LocaleKey } from "../../../shared/i18n";
import { SpellCatalogField } from "./SpellCatalogEditorControls";
import type { SpellCatalogEditorState } from "../utils/spellCatalogForm";

type Props = {
  state: SpellCatalogEditorState;
  setState: Dispatch<SetStateAction<SpellCatalogEditorState>>;
  t: (key: LocaleKey) => string;
  booleanSelectValue: (value: boolean | null) => string;
  parseBooleanSelectValue: (value: string) => boolean | null;
};

const fieldClassName =
  "w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-violet-400/60 focus:outline-none";

export const SpellCatalogTargetingRequirements = ({
  state,
  setState,
  t,
  booleanSelectValue,
  parseBooleanSelectValue,
}: Props) => (
  <div className="space-y-4 rounded-2xl border border-white/8 bg-slate-950/35 p-4">
    <div>
      <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
        {t("catalog.spells.form.targetingRequirements")}
      </p>
    </div>
    <div className="grid gap-4 sm:grid-cols-2">
      <SpellCatalogField label={t("catalog.spells.form.requiresTargetSight")}>
        <select
          value={booleanSelectValue(state.requiresTargetSight)}
          onChange={(event) =>
            setState((current) => ({
              ...current,
              requiresTargetSight: parseBooleanSelectValue(event.target.value),
            }))
          }
          className={fieldClassName}
        >
          <option value="">{t("catalog.spells.form.inherit")}</option>
          <option value="true">{t("catalog.admin.table.yes")}</option>
          <option value="false">{t("catalog.admin.table.no")}</option>
        </select>
      </SpellCatalogField>
      <SpellCatalogField label={t("catalog.spells.form.requiresTargetEffect")}>
        <select
          value={booleanSelectValue(state.requiresTargetEffect)}
          onChange={(event) =>
            setState((current) => ({
              ...current,
              requiresTargetEffect: parseBooleanSelectValue(event.target.value),
            }))
          }
          className={fieldClassName}
        >
          <option value="">{t("catalog.spells.form.inherit")}</option>
          <option value="true">{t("catalog.admin.table.yes")}</option>
          <option value="false">{t("catalog.admin.table.no")}</option>
        </select>
      </SpellCatalogField>
      <SpellCatalogField label={t("catalog.spells.form.requiresPointSight")}>
        <select
          value={booleanSelectValue(state.requiresPointSight)}
          onChange={(event) =>
            setState((current) => ({
              ...current,
              requiresPointSight: parseBooleanSelectValue(event.target.value),
            }))
          }
          className={fieldClassName}
        >
          <option value="">{t("catalog.spells.form.inherit")}</option>
          <option value="true">{t("catalog.admin.table.yes")}</option>
          <option value="false">{t("catalog.admin.table.no")}</option>
        </select>
      </SpellCatalogField>
      <SpellCatalogField label={t("catalog.spells.form.requiresPointEffect")}>
        <select
          value={booleanSelectValue(state.requiresPointEffect)}
          onChange={(event) =>
            setState((current) => ({
              ...current,
              requiresPointEffect: parseBooleanSelectValue(event.target.value),
            }))
          }
          className={fieldClassName}
        >
          <option value="">{t("catalog.spells.form.inherit")}</option>
          <option value="true">{t("catalog.admin.table.yes")}</option>
          <option value="false">{t("catalog.admin.table.no")}</option>
        </select>
      </SpellCatalogField>
    </div>
  </div>
);
