import type { Dispatch, SetStateAction } from "react";

import type { BaseItem } from "../../entities/base-item";
import { SpellAoeFootprintPreview } from "./SpellAoeFootprintPreview";
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
import { SystemSpellCatalogFormSection } from "./SystemSpellCatalogFormSection";
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
  consumableItems: BaseItem[];
};

export const SystemSpellCatalogCastingFields = ({ form, setForm, consumableItems }: Props) => {
  const { locale, t } = useLocale();

  const formatSpellChoiceLabel = (value: string) =>
    value === "DND5E" ? "D&D 5e" : localizeSpellAdminValue(value, locale);

  const showMaterialComponent = form.componentsJson.includes("M");
  const showRadiusField = form.areaShape === "sphere" || form.areaShape === "cylinder";
  const showLengthField = form.areaShape === "cone" || form.areaShape === "line";
  const showSideField = form.areaShape === "cube";
  const showAreaSection = Boolean(form.areaShape);

  return (
    <>
      <SystemSpellCatalogFormSection title={t("catalog.spells.form.casting")}>
        <div className="grid gap-4 md:grid-cols-2">
          <label className="block min-w-0">
            <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              {t("catalog.spells.form.castingTimeTypeDetailed")}
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

          <label className="block min-w-0">
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
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <label className="block min-w-0">
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
              {t("catalog.spells.form.concentration")}
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
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                Componente consumível
              </span>
              <button
                type="button"
                onClick={() =>
                  setForm((c) => ({
                    ...c,
                    materialComponentConsumed: !c.materialComponentConsumed,
                    consumableMaterialOptionKeys: !c.materialComponentConsumed
                      ? c.consumableMaterialOptionKeys
                      : [],
                  }))
                }
                className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
                  form.materialComponentConsumed
                    ? "border-amber-300/40 bg-amber-400/15 text-amber-100"
                    : "border-white/10 bg-white/4 text-slate-400 hover:bg-white/8"
                }`}
              >
                {form.materialComponentConsumed ? "Consome item" : "Não consome"}
              </button>
            </div>
            {form.materialComponentConsumed ? (
              <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
                <p className="mb-2 text-xs text-slate-400">Itens aceitos como componente consumível:</p>
                <div className="space-y-2">
                  {(form.consumableMaterialOptionKeys.length > 0
                    ? form.consumableMaterialOptionKeys
                    : [""]).map((selectedKey, index) => (
                    <div key={`${index}-${selectedKey}`} className="flex items-center gap-2">
                      <select
                        value={selectedKey}
                        onChange={(event) =>
                          setForm((c) => ({
                            ...c,
                            consumableMaterialOptionKeys:
                              c.consumableMaterialOptionKeys.length === 0
                                ? [event.target.value]
                                : c.consumableMaterialOptionKeys.map((entry, i) =>
                                    i === index ? event.target.value : entry,
                                  ),
                          }))
                        }
                        className={`${inputClassName} flex-1`}
                      >
                        <option value="">Selecione um item consumível</option>
                        {consumableItems.map((item) => (
                          <option key={item.canonicalKey} value={item.canonicalKey}>
                            {((locale === "pt" && item.namePt) ? item.namePt : item.nameEn) ?? item.canonicalKey}
                          </option>
                        ))}
                      </select>
                      <button
                        type="button"
                        onClick={() =>
                          setForm((c) => ({
                            ...c,
                            consumableMaterialOptionKeys: c.consumableMaterialOptionKeys.filter(
                              (_entry, i) => i !== index,
                            ),
                          }))
                        }
                        className="rounded-lg border border-rose-300/30 bg-rose-400/10 px-2 py-1 text-xs font-semibold text-rose-100"
                      >
                        Remover
                      </button>
                    </div>
                  ))}
                </div>
                <button
                  type="button"
                  onClick={() =>
                    setForm((c) => ({
                      ...c,
                      consumableMaterialOptionKeys: [...c.consumableMaterialOptionKeys, ""],
                    }))
                  }
                  className="mt-3 rounded-lg border border-emerald-300/30 bg-emerald-400/10 px-3 py-1.5 text-xs font-semibold text-emerald-100"
                >
                  Adicionar item consumível
                </button>
              </div>
            ) : null}
          </div>
        )}
      </SystemSpellCatalogFormSection>

      <SystemSpellCatalogFormSection title={t("catalog.spells.form.targeting")} collapsible>
        <div className="grid gap-4 md:grid-cols-2">
          <label className="block min-w-0">
            <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              {t("catalog.admin.table.targetType")}
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

          <label className="block min-w-0">
            <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              {t("catalog.spells.form.maxTargets")}
            </span>
            <input
              type="number"
              min={1}
              step={1}
              value={form.maxTargets}
              onChange={(event) =>
                setForm((c) => ({ ...c, maxTargets: event.target.value }))
              }
              className={`${inputClassName} mt-2`}
              placeholder="1"
            />
          </label>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <label className="block min-w-0">
            <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              {t("catalog.spells.form.selectionType")}
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

          <label className="block min-w-0">
            <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              {t("catalog.spells.form.originType")}
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

          <label className="block min-w-0">
            <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              {t("catalog.spells.form.targetAnchorDetailed")}
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
          <label className="block min-w-0">
            <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              {t("catalog.spells.form.attackType")}
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

          <label className="block min-w-0">
            <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              {t("catalog.spells.form.rangeKindDetailed")}
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

          <label className="block min-w-0">
            <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              {t("catalog.spells.form.effectTimingDetailed")}
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
      </SystemSpellCatalogFormSection>

      <SystemSpellCatalogFormSection
        title="Área"
        collapsible
      >
        <label className="block min-w-0">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            {t("catalog.spells.form.areaShapeDetailed")}
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

        {showAreaSection && (showRadiusField || showLengthField || showSideField) && (
          <div className="grid gap-4 md:grid-cols-2">
            {showRadiusField && (
              <label className="block min-w-0">
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
              <label className="block min-w-0">
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
              <label className="block min-w-0">
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

        <SpellAoeFootprintPreview
          areaShape={form.areaShape}
          radiusMeters={form.radiusMeters}
          lengthMeters={form.lengthMeters}
          sideMeters={form.sideMeters}
        />
      </SystemSpellCatalogFormSection>
    </>
  );
};
