import type { Dispatch, SetStateAction } from "react";

import type { BaseSpell, SpellSchool, SpellSource } from "../../entities/base-spell";
import { useLocale } from "../../shared/hooks/useLocale";
import {
  localizeSpellAdminValue,
  localizeSpellSchool,
} from "../../shared/i18n/domainLabels";
import { SystemSpellCatalogCastingFields } from "./SystemSpellCatalogCastingFields";
import { SystemSpellCatalogResolutionFields } from "./SystemSpellCatalogResolutionFields";
import { toggleListValue } from "./systemSpellCatalog.helpers";
import {
  CLASS_OPTIONS,
  type FormState,
  LEVEL_OPTIONS,
  SCHOOL_OPTIONS,
  SOURCE_OPTIONS,
  SYSTEM_OPTIONS,
  inputClassName,
  panelClassName,
} from "./systemSpellCatalog.types";

type Props = {
  form: FormState;
  setForm: Dispatch<SetStateAction<FormState>>;
  selectedSpellId: string | null;
  loadingMessage: string | null;
  error: string | null;
  onSave: () => void;
  onCreateNew: () => void;
  onDelete: () => void;
};

export const SystemSpellCatalogSpellForm = ({
  form,
  setForm,
  selectedSpellId,
  loadingMessage,
  error,
  onSave,
  onCreateNew,
  onDelete,
}: Props) => {
  const { locale, t } = useLocale();

  const formatSpellChoiceLabel = (value: string) =>
    value === "DND5E" ? "D&D 5e" : localizeSpellAdminValue(value, locale);

  const selectedLabel = selectedSpellId ? t("catalog.edit") : t("catalog.createAction");

  return (
    <div className={`${panelClassName} space-y-5`}>
      <div className="flex flex-col gap-2 border-b border-white/8 pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">
            {t("catalog.edit")}
          </p>
          <h2 className="mt-1 text-2xl font-black tracking-tight text-white">
            {selectedLabel}
          </h2>
        </div>
        {loadingMessage && (
          <p className="text-sm text-violet-200">{loadingMessage}</p>
        )}
      </div>

      {error && (
        <div className="rounded-2xl border border-rose-400/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
          {error}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            {t("catalog.admin.table.system")}
          </span>
          <select
            value={form.system}
            onChange={(event) =>
              setForm((c) => ({
                ...c,
                system: event.target.value as BaseSpell["system"],
              }))
            }
            className={`${inputClassName} mt-2`}
          >
            {SYSTEM_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {formatSpellChoiceLabel(s)}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            {t("catalog.admin.table.canonicalKey")}
          </span>
          <input
            value={form.canonicalKey}
            onChange={(event) =>
              setForm((c) => ({ ...c, canonicalKey: event.target.value }))
            }
            className={`${inputClassName} mt-2`}
            placeholder="fireball"
          />
        </label>

        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            {t("catalog.admin.table.level")}
          </span>
          <select
            value={form.level}
            onChange={(event) =>
              setForm((c) => ({ ...c, level: Number(event.target.value) }))
            }
            className={`${inputClassName} mt-2`}
          >
            {LEVEL_OPTIONS.map((level) => (
              <option key={level} value={level}>
                {level === 0
                  ? t("catalog.spells.cantrip")
                  : `${t("catalog.spells.levelLabel")} ${level}`}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            {t("catalog.admin.table.nameEn")}
          </span>
          <input
            value={form.nameEn}
            onChange={(event) =>
              setForm((c) => ({ ...c, nameEn: event.target.value }))
            }
            className={`${inputClassName} mt-2`}
            placeholder="Fireball"
          />
        </label>
        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            {t("catalog.admin.table.namePt")}
          </span>
          <input
            value={form.namePt}
            onChange={(event) =>
              setForm((c) => ({ ...c, namePt: event.target.value }))
            }
            className={`${inputClassName} mt-2`}
            placeholder="Bola de Fogo"
          />
        </label>
      </div>

      <label className="block">
        <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
          {t("catalog.admin.table.school")}
        </span>
        <select
          value={form.school}
          onChange={(event) =>
            setForm((c) => ({ ...c, school: event.target.value as SpellSchool }))
          }
          className={`${inputClassName} mt-2`}
        >
          {SCHOOL_OPTIONS.map((school) => (
            <option key={school} value={school}>
              {localizeSpellSchool(school, locale)}
            </option>
          ))}
        </select>
      </label>

      <div>
        <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
          Classes
        </span>
        <div className="mt-2 flex flex-wrap gap-2">
          {CLASS_OPTIONS.map((cls) => (
            <button
              key={cls}
              type="button"
              onClick={() =>
                setForm((c) => ({
                  ...c,
                  classesJson: toggleListValue(c.classesJson, cls),
                }))
              }
              className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
                form.classesJson.includes(cls)
                  ? "border-violet-300/40 bg-violet-400/15 text-violet-100"
                  : "border-white/10 bg-white/4 text-slate-400 hover:bg-white/8"
              }`}
            >
              {cls}
            </button>
          ))}
        </div>
      </div>

      <SystemSpellCatalogCastingFields form={form} setForm={setForm} />
      <SystemSpellCatalogResolutionFields form={form} setForm={setForm} />

      <div className="grid gap-4 md:grid-cols-2">
        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Descrição EN
          </span>
          <textarea
            value={form.descriptionEn}
            onChange={(event) =>
              setForm((c) => ({ ...c, descriptionEn: event.target.value }))
            }
            className={`${inputClassName} mt-2 min-h-28`}
          />
        </label>
        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Descrição PT
          </span>
          <textarea
            value={form.descriptionPt}
            onChange={(event) =>
              setForm((c) => ({ ...c, descriptionPt: event.target.value }))
            }
            className={`${inputClassName} mt-2 min-h-28`}
          />
        </label>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Source
          </span>
          <select
            value={form.source}
            onChange={(event) =>
              setForm((c) => ({ ...c, source: event.target.value as SpellSource }))
            }
            className={`${inputClassName} mt-2`}
          >
            {SOURCE_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {formatSpellChoiceLabel(s)}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Source ref
          </span>
          <input
            value={form.sourceRef}
            onChange={(event) =>
              setForm((c) => ({ ...c, sourceRef: event.target.value }))
            }
            className={`${inputClassName} mt-2`}
            placeholder="PHB p.241"
          />
        </label>

        <div className="flex items-end gap-3 pb-1">
          <button
            type="button"
            onClick={() => setForm((c) => ({ ...c, isSrd: !c.isSrd }))}
            className={`rounded-full border px-3 py-2 text-xs font-semibold transition ${
              form.isSrd
                ? "border-emerald-300/40 bg-emerald-400/15 text-emerald-100"
                : "border-white/10 bg-white/4 text-slate-400 hover:bg-white/8"
            }`}
          >
            SRD
          </button>
          <button
            type="button"
            onClick={() => setForm((c) => ({ ...c, isActive: !c.isActive }))}
            className={`rounded-full border px-3 py-2 text-xs font-semibold transition ${
              form.isActive
                ? "border-emerald-300/40 bg-emerald-400/15 text-emerald-100"
                : "border-rose-300/40 bg-rose-400/15 text-rose-100"
            }`}
          >
            {form.isActive ? "Ativo" : "Inativo"}
          </button>
        </div>
      </div>

      <div className="flex flex-wrap gap-3 border-t border-white/8 pt-4">
        <button
          type="button"
          onClick={onSave}
          className="rounded-2xl border border-violet-400/30 bg-violet-400/12 px-5 py-3 text-sm font-semibold text-violet-100 transition hover:bg-violet-400/18"
        >
          {selectedSpellId ? "Salvar alterações" : "Criar magia"}
        </button>
        {selectedSpellId && (
          <button
            type="button"
            onClick={onDelete}
            className="rounded-2xl border border-rose-400/30 bg-rose-400/8 px-5 py-3 text-sm font-semibold text-rose-200 transition hover:bg-rose-400/15"
          >
            Remover
          </button>
        )}
        <button
          type="button"
          onClick={onCreateNew}
          className="rounded-2xl border border-white/10 bg-white/4 px-5 py-3 text-sm font-semibold text-slate-200 transition hover:border-white/20 hover:bg-white/8"
        >
          Limpar
        </button>
      </div>
    </div>
  );
};
