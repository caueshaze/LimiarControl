import type { SpellVariant } from "../../../entities/base-spell";
import { useLocale } from "../../../shared/hooks/useLocale";
import {
  addSpellVariant,
  createEmptySpellVariantManualNote,
  getSpellVariantErrors,
  getSpellVariantWarnings,
  removeSpellVariant,
  summarizeSpellVariant,
} from "../utils/spellVariantEditor";
import { SpellCatalogEffectEditor } from "./SpellCatalogDeclarativeEffectsFields";

type Props = {
  variants: SpellVariant[];
  onChange: (next: SpellVariant[]) => void;
};

const fieldClassName =
  "w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-violet-400/60 focus:outline-none";

const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <div className="space-y-4 rounded-2xl border border-white/8 bg-slate-950/35 p-4">
    <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
      {title}
    </p>
    <div className="space-y-4">{children}</div>
  </div>
);

const updateVariant = (
  variants: SpellVariant[],
  index: number,
  updater: (variant: SpellVariant) => SpellVariant,
) => variants.map((variant, variantIndex) => (variantIndex === index ? updater(variant) : variant));

export const SpellCatalogVariantsFields = ({ variants, onChange }: Props) => {
  const { t } = useLocale();
  const errors = getSpellVariantErrors(variants);
  const warnings = getSpellVariantWarnings(variants);

  return (
    <Section title="Variants">
      {errors.length > 0 ? (
        <div className="space-y-2 rounded-2xl border border-rose-400/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
          {errors.map((error) => (
            <p key={error}>{error}</p>
          ))}
        </div>
      ) : null}
      {warnings.length > 0 ? (
        <div className="space-y-2 rounded-2xl border border-amber-400/20 bg-amber-400/10 px-4 py-3 text-sm text-amber-100">
          {warnings.map((warning) => (
            <p key={warning}>{warning}</p>
          ))}
        </div>
      ) : null}

      {variants.map((variant, index) => (
        <div
          key={`variant-${index}`}
          className="space-y-4 rounded-2xl border border-white/8 bg-slate-950/45 p-4"
        >
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-white">
                Variante {index + 1}
              </p>
              <p className="text-xs text-slate-400">
                Configure rótulos, descrições, efeitos e notas manuais desta opção de cast.
              </p>
              <p className="mt-1 text-xs text-violet-200/85">
                {summarizeSpellVariant(variant, "pt")}
              </p>
            </div>
            <button
              type="button"
              onClick={() => onChange(removeSpellVariant(variants, index))}
              className="rounded-full border border-rose-400/20 px-3 py-2 text-xs uppercase tracking-[0.18em] text-rose-200"
            >
              Remover variante
            </button>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block min-w-0">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                Key
              </span>
              <input
                value={variant.key}
                onChange={(event) =>
                  onChange(
                    updateVariant(variants, index, (current) => ({
                      ...current,
                      key: event.target.value,
                    })),
                  )
                }
                className={`${fieldClassName} mt-2`}
                placeholder="bears_endurance"
              />
            </label>

            <label className="block min-w-0">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                Label PT
              </span>
              <input
                value={variant.labelPt}
                onChange={(event) =>
                  onChange(
                    updateVariant(variants, index, (current) => ({
                      ...current,
                      labelPt: event.target.value,
                    })),
                  )
                }
                className={`${fieldClassName} mt-2`}
                placeholder="Resistência do Urso"
              />
            </label>

            <label className="block min-w-0">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                Label EN
              </span>
              <input
                value={variant.labelEn ?? ""}
                onChange={(event) =>
                  onChange(
                    updateVariant(variants, index, (current) => ({
                      ...current,
                      labelEn: event.target.value,
                    })),
                  )
                }
                className={`${fieldClassName} mt-2`}
                placeholder="Bear's Endurance"
              />
            </label>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block min-w-0">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                Description PT
              </span>
              <textarea
                value={variant.descriptionPt ?? ""}
                onChange={(event) =>
                  onChange(
                    updateVariant(variants, index, (current) => ({
                      ...current,
                      descriptionPt: event.target.value,
                    })),
                  )
                }
                className={`${fieldClassName} mt-2 min-h-24`}
              />
            </label>

            <label className="block min-w-0">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                Description EN
              </span>
              <textarea
                value={variant.descriptionEn ?? ""}
                onChange={(event) =>
                  onChange(
                    updateVariant(variants, index, (current) => ({
                      ...current,
                      descriptionEn: event.target.value,
                    })),
                  )
                }
                className={`${fieldClassName} mt-2 min-h-24`}
              />
            </label>
          </div>

          <SpellCatalogEffectEditor
            title="Efeitos declarativos da variante"
            effects={variant.effects ?? []}
            onChange={(next) =>
              onChange(
                updateVariant(variants, index, (current) => ({
                  ...current,
                  effects: next,
                })),
              )
            }
          />

          <SpellCatalogEffectEditor
            title="Efeitos ao terminar da variante"
            effects={variant.onEndEffects ?? []}
            onChange={(next) =>
              onChange(
                updateVariant(variants, index, (current) => ({
                  ...current,
                  onEndEffects: next,
                })),
              )
            }
          />

          <div className="space-y-3 rounded-2xl border border-white/8 bg-slate-950/35 p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
                  Manual notes
                </p>
                <p className="text-xs text-slate-400">
                  Use para efeitos ainda não automatizados no motor.
                </p>
              </div>
              <button
                type="button"
                onClick={() =>
                  onChange(
                    updateVariant(variants, index, (current) => ({
                      ...current,
                      manualNotes: [
                        ...(current.manualNotes ?? []),
                        createEmptySpellVariantManualNote(),
                      ],
                    })),
                  )
                }
                className="rounded-full border border-violet-300/20 px-3 py-2 text-xs uppercase tracking-[0.18em] text-violet-100"
              >
                Adicionar nota
              </button>
            </div>

            {(variant.manualNotes ?? []).map((note, noteIndex) => (
              <div
                key={`variant-${index}-note-${noteIndex}`}
                className="space-y-3 rounded-2xl border border-white/8 bg-slate-950/55 p-3"
              >
                <div className="grid gap-3 sm:grid-cols-3">
                  <input
                    value={note.key}
                    onChange={(event) =>
                      onChange(
                        updateVariant(variants, index, (current) => ({
                          ...current,
                          manualNotes: (current.manualNotes ?? []).map((entry, entryIndex) =>
                            entryIndex === noteIndex
                              ? { ...entry, key: event.target.value }
                              : entry,
                          ),
                        })),
                      )
                    }
                    className={fieldClassName}
                    placeholder="grant_temp_hp"
                  />
                  <input
                    value={note.label}
                    onChange={(event) =>
                      onChange(
                        updateVariant(variants, index, (current) => ({
                          ...current,
                          manualNotes: (current.manualNotes ?? []).map((entry, entryIndex) =>
                            entryIndex === noteIndex
                              ? { ...entry, label: event.target.value }
                              : entry,
                          ),
                        })),
                      )
                    }
                    className={fieldClassName}
                    placeholder="PV temporários"
                  />
                  <button
                    type="button"
                    onClick={() =>
                      onChange(
                        updateVariant(variants, index, (current) => ({
                          ...current,
                          manualNotes: (current.manualNotes ?? []).filter(
                            (_, entryIndex) => entryIndex !== noteIndex,
                          ),
                        })),
                      )
                    }
                    className="rounded-full border border-rose-400/20 px-3 py-2 text-xs uppercase tracking-[0.18em] text-rose-200"
                  >
                    Remover nota
                  </button>
                </div>
                <textarea
                  value={note.description}
                  onChange={(event) =>
                    onChange(
                      updateVariant(variants, index, (current) => ({
                        ...current,
                        manualNotes: (current.manualNotes ?? []).map((entry, entryIndex) =>
                          entryIndex === noteIndex
                            ? { ...entry, description: event.target.value }
                            : entry,
                        ),
                      })),
                    )
                  }
                  className={`${fieldClassName} min-h-20`}
                  placeholder="Explique o que ainda precisa ser aplicado manualmente."
                />
              </div>
            ))}
          </div>
        </div>
      ))}

      <button
        type="button"
        onClick={() => onChange(addSpellVariant(variants))}
        className="rounded-full border border-violet-300/20 px-3 py-2 text-xs uppercase tracking-[0.18em] text-violet-100"
      >
        {t("catalog.createAction")} variante
      </button>
    </Section>
  );
};
