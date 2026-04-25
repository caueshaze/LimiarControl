import type { Dispatch, SetStateAction } from "react";

import type {
  AreaShape,
  CastingTimeType,
  SpellAttackType,
  SpellEffectTiming,
  SpellOriginType,
  SpellRangeKind,
  SpellSelectionType,
  SpellTargetAnchor,
  TargetType,
} from "../../entities/base-spell";
import { useLocale } from "../../shared/hooks/useLocale";
import { localizeSpellAdminValue } from "../../shared/i18n/domainLabels";
import { toggleListValue } from "./systemSpellCatalog.helpers";
import {
  AREA_SHAPE_OPTIONS,
  ATTACK_TYPE_OPTIONS,
  CASTING_TIME_TYPE_OPTIONS,
  COMPONENT_OPTIONS,
  DURATION_OPTIONS,
  EFFECT_TIMING_OPTIONS,
  ORIGIN_TYPE_OPTIONS,
  RANGE_KIND_OPTIONS,
  SELECTION_TYPE_OPTIONS,
  TARGET_ANCHOR_OPTIONS,
  type FormState,
  TARGET_TYPE_OPTIONS,
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
  const showRadiusField = form.areaShape === "sphere" || form.areaShape === "cylinder";
  const showLengthField = form.areaShape === "cone" || form.areaShape === "line";
  const showSideField = form.areaShape === "cube";

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
            Target type
          </span>
          <select
            value={form.targetType}
            onChange={(event) =>
              setForm((c) => ({
                ...c,
                targetType: event.target.value as TargetType | "",
              }))
            }
            className={`${inputClassName} mt-2`}
          >
            <option value="">—</option>
            {TARGET_TYPE_OPTIONS.map((tt) => (
              <option key={tt} value={tt}>
                {formatSpellChoiceLabel(tt)}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Selection type
          </span>
          <select
            value={form.selectionType}
            onChange={(event) =>
              setForm((c) => ({
                ...c,
                selectionType: event.target.value as SpellSelectionType | "",
              }))
            }
            className={`${inputClassName} mt-2`}
          >
            <option value="">—</option>
            {SELECTION_TYPE_OPTIONS.map((value) => (
              <option key={value} value={value}>
                {formatSpellChoiceLabel(value)}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Origin type
          </span>
          <select
            value={form.originType}
            onChange={(event) =>
              setForm((c) => ({
                ...c,
                originType: event.target.value as SpellOriginType | "",
              }))
            }
            className={`${inputClassName} mt-2`}
          >
            <option value="">—</option>
            {ORIGIN_TYPE_OPTIONS.map((value) => (
              <option key={value} value={value}>
                {formatSpellChoiceLabel(value)}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Target anchor
          </span>
          <select
            value={form.targetAnchor}
            onChange={(event) =>
              setForm((c) => ({
                ...c,
                targetAnchor: event.target.value as SpellTargetAnchor | "",
              }))
            }
            className={`${inputClassName} mt-2`}
          >
            <option value="">—</option>
            {TARGET_ANCHOR_OPTIONS.map((value) => (
              <option key={value} value={value}>
                {formatSpellChoiceLabel(value)}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Attack type
          </span>
          <select
            value={form.attackType}
            onChange={(event) =>
              setForm((c) => ({
                ...c,
                attackType: event.target.value as SpellAttackType | "",
              }))
            }
            className={`${inputClassName} mt-2`}
          >
            <option value="">—</option>
            {ATTACK_TYPE_OPTIONS.map((value) => (
              <option key={value} value={value}>
                {formatSpellChoiceLabel(value)}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Range kind
          </span>
          <select
            value={form.rangeKind}
            onChange={(event) =>
              setForm((c) => ({
                ...c,
                rangeKind: event.target.value as SpellRangeKind | "",
              }))
            }
            className={`${inputClassName} mt-2`}
          >
            <option value="">—</option>
            {RANGE_KIND_OPTIONS.map((value) => (
              <option key={value} value={value}>
                {formatSpellChoiceLabel(value)}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Effect timing
          </span>
          <select
            value={form.effectTiming}
            onChange={(event) =>
              setForm((c) => ({
                ...c,
                effectTiming: event.target.value as SpellEffectTiming | "",
              }))
            }
            className={`${inputClassName} mt-2`}
          >
            <option value="">—</option>
            {EFFECT_TIMING_OPTIONS.map((value) => (
              <option key={value} value={value}>
                {formatSpellChoiceLabel(value)}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Area shape
          </span>
          <select
            value={form.areaShape}
            onChange={(event) =>
              setForm((c) => ({
                ...c,
                areaShape: event.target.value as AreaShape | "",
              }))
            }
            className={`${inputClassName} mt-2`}
          >
            <option value="">—</option>
            {AREA_SHAPE_OPTIONS.map((shape) => (
              <option key={shape} value={shape}>
                {formatSpellChoiceLabel(shape)}
              </option>
            ))}
          </select>
        </label>
      </div>

      {(showRadiusField || showLengthField || showSideField) && (
        <div className="grid gap-4 md:grid-cols-3">
          {showRadiusField && (
            <label className="block">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                Raio (m)
              </span>
              <input
                type="number"
                min={0.5}
                step={0.5}
                value={form.radiusMeters}
                onChange={(event) =>
                  setForm((c) => ({ ...c, radiusMeters: event.target.value }))
                }
                className={`${inputClassName} mt-2`}
                placeholder="ex: 6"
              />
            </label>
          )}
          {showLengthField && (
            <label className="block">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                Comprimento (m)
              </span>
              <input
                type="number"
                min={0.5}
                step={0.5}
                value={form.lengthMeters}
                onChange={(event) =>
                  setForm((c) => ({ ...c, lengthMeters: event.target.value }))
                }
                className={`${inputClassName} mt-2`}
                placeholder="ex: 4.5"
              />
            </label>
          )}
          {showSideField && (
            <label className="block">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                Lado (m)
              </span>
              <input
                type="number"
                min={0.5}
                step={0.5}
                value={form.sideMeters}
                onChange={(event) =>
                  setForm((c) => ({ ...c, sideMeters: event.target.value }))
                }
                className={`${inputClassName} mt-2`}
                placeholder="ex: 4.5"
              />
            </label>
          )}
        </div>
      )}

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
