import type { Dispatch, SetStateAction } from "react";

import type { CastingTimeType, TargetMode } from "../../entities/base-spell";
import { useLocale } from "../../shared/hooks/useLocale";
import { localizeSpellAdminValue } from "../../shared/i18n/domainLabels";
import { toggleListValue } from "./systemSpellCatalog.helpers";
import {
  CASTING_TIME_TYPE_OPTIONS,
  COMPONENT_OPTIONS,
  DURATION_OPTIONS,
  type FormState,
  TARGET_MODE_OPTIONS,
  inputClassName,
} from "./systemSpellCatalog.types";

type Props = {
  form: FormState;
  setForm: Dispatch<SetStateAction<FormState>>;
};

export const SystemSpellCatalogCastingFields = ({ form, setForm }: Props) => {
  const { locale } = useLocale();

  const formatSpellChoiceLabel = (value: string) =>
    value === "DND5E" ? "D&D 5e" : localizeSpellAdminValue(value, locale);

  const showMaterialComponent = form.componentsJson.includes("M");

  return (
    <>
      <div className="grid gap-4 md:grid-cols-3">
        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Casting time type
          </span>
          <select
            value={form.castingTimeType}
            onChange={(event) =>
              setForm((c) => ({
                ...c,
                castingTimeType: event.target.value as CastingTimeType | "",
              }))
            }
            className={`${inputClassName} mt-2`}
          >
            <option value="">—</option>
            {CASTING_TIME_TYPE_OPTIONS.map((ctt) => (
              <option key={ctt} value={ctt}>
                {formatSpellChoiceLabel(ctt)}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Alcance (m)
          </span>
          <input
            type="number"
            min={0}
            value={form.rangeMeters}
            onChange={(event) =>
              setForm((c) => ({ ...c, rangeMeters: event.target.value }))
            }
            className={`${inputClassName} mt-2`}
            placeholder="0"
          />
        </label>

        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Target mode
          </span>
          <select
            value={form.targetMode}
            onChange={(event) =>
              setForm((c) => ({
                ...c,
                targetMode: event.target.value as TargetMode | "",
              }))
            }
            className={`${inputClassName} mt-2`}
          >
            <option value="">—</option>
            {TARGET_MODE_OPTIONS.map((tm) => (
              <option key={tm} value={tm}>
                {formatSpellChoiceLabel(tm)}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Duração
          </span>
          <select
            value={form.duration}
            onChange={(event) =>
              setForm((c) => ({ ...c, duration: event.target.value }))
            }
            className={`${inputClassName} mt-2`}
          >
            <option value="">—</option>
            {DURATION_OPTIONS.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </label>

        <div className="flex items-end gap-3 pb-1">
          <button
            type="button"
            onClick={() =>
              setForm((c) => ({ ...c, concentration: !c.concentration }))
            }
            className={`rounded-full border px-3 py-2 text-xs font-semibold transition ${
              form.concentration
                ? "border-amber-300/40 bg-amber-400/15 text-amber-100"
                : "border-white/10 bg-white/4 text-slate-400 hover:bg-white/8"
            }`}
          >
            Concentration
          </button>
          <button
            type="button"
            onClick={() => setForm((c) => ({ ...c, ritual: !c.ritual }))}
            className={`rounded-full border px-3 py-2 text-xs font-semibold transition ${
              form.ritual
                ? "border-teal-300/40 bg-teal-400/15 text-teal-100"
                : "border-white/10 bg-white/4 text-slate-400 hover:bg-white/8"
            }`}
          >
            Ritual
          </button>
        </div>
      </div>

      <div>
        <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
          Componentes
        </span>
        <div className="mt-2 flex flex-wrap gap-2">
          {COMPONENT_OPTIONS.map((comp) => (
            <button
              key={comp}
              type="button"
              onClick={() =>
                setForm((c) => ({
                  ...c,
                  componentsJson: toggleListValue(c.componentsJson, comp),
                }))
              }
              className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
                form.componentsJson.includes(comp)
                  ? "border-violet-300/40 bg-violet-400/15 text-violet-100"
                  : "border-white/10 bg-white/4 text-slate-400 hover:bg-white/8"
              }`}
            >
              {comp}
            </button>
          ))}
        </div>
      </div>

      {showMaterialComponent && (
        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Material component
          </span>
          <input
            value={form.materialComponentText}
            onChange={(event) =>
              setForm((c) => ({
                ...c,
                materialComponentText: event.target.value,
              }))
            }
            className={`${inputClassName} mt-2`}
            placeholder="a tiny ball of bat guano and sulfur"
          />
        </label>
      )}
    </>
  );
};
