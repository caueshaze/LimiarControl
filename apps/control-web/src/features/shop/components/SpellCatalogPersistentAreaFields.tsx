import type { Dispatch, SetStateAction } from "react";
import type { SpellCatalogEditorState } from "../utils/spellCatalogForm";
import {
  SPELL_DAMAGE_TYPE_OPTIONS,
  SPELL_PERSISTENT_AREA_KIND_OPTIONS,
  SPELL_PERSISTENT_AREA_OBSCUREMENT_OPTIONS,
  SPELL_PERSISTENT_AREA_TERRAIN_OPTIONS,
} from "../utils/spellCatalogForm";

type Props = {
  state: SpellCatalogEditorState;
  setState: Dispatch<SetStateAction<SpellCatalogEditorState>>;
};

const fieldClassName =
  "w-full rounded-2xl border border-white/8 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-violet-400/60 focus:outline-none";

const labelize = (value: string) => value.replace(/_/g, " ");

export const SpellCatalogPersistentAreaFields = ({ state, setState }: Props) => {
  if (state.effectTiming !== "persistent") {
    return null;
  }

  return (
    <div className="space-y-4 rounded-2xl border border-white/8 bg-slate-950/35 p-4">
      <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
        Persistent area semantics
      </p>

      <select
        value={state.persistentAreaKind}
        onChange={(event) =>
          setState((current) => ({
            ...current,
            persistentAreaKind: event.target.value as SpellCatalogEditorState["persistentAreaKind"],
          }))
        }
        className={fieldClassName}
      >
        <option value="">Select semantic kind</option>
        {SPELL_PERSISTENT_AREA_KIND_OPTIONS.map((option) => (
          <option key={option} value={option}>
            {labelize(option)}
          </option>
        ))}
      </select>

      {state.persistentAreaKind === "obscurement" ? (
        <select
          value={state.persistentAreaObscurement}
          onChange={(event) =>
            setState((current) => ({
              ...current,
              persistentAreaObscurement:
                event.target.value as SpellCatalogEditorState["persistentAreaObscurement"],
            }))
          }
          className={fieldClassName}
        >
          <option value="">Select obscurement</option>
          {SPELL_PERSISTENT_AREA_OBSCUREMENT_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {labelize(option)}
            </option>
          ))}
        </select>
      ) : null}

      {state.persistentAreaKind === "hazard" ? (
        <div className="grid gap-3 sm:grid-cols-2">
          <select
            value={state.persistentAreaTerrainEffect}
            onChange={(event) =>
              setState((current) => ({
                ...current,
                persistentAreaTerrainEffect:
                  event.target.value as SpellCatalogEditorState["persistentAreaTerrainEffect"],
              }))
            }
            className={fieldClassName}
          >
            <option value="">Select terrain effect</option>
            {SPELL_PERSISTENT_AREA_TERRAIN_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {labelize(option)}
              </option>
            ))}
          </select>

          <input
            value={state.persistentAreaMovementDamageDice}
            onChange={(event) =>
              setState((current) => ({
                ...current,
                persistentAreaMovementDamageDice: event.target.value,
              }))
            }
            className={fieldClassName}
            placeholder="Movement damage dice"
          />

          <select
            value={state.persistentAreaDamageType}
            onChange={(event) =>
              setState((current) => ({
                ...current,
                persistentAreaDamageType: event.target.value,
              }))
            }
            className={fieldClassName}
          >
            <option value="">Select damage type</option>
            {SPELL_DAMAGE_TYPE_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>

          <input
            type="number"
            min={0}
            step="0.1"
            value={state.persistentAreaDamagePerMeters}
            onChange={(event) =>
              setState((current) => ({
                ...current,
                persistentAreaDamagePerMeters: event.target.value,
              }))
            }
            className={fieldClassName}
            placeholder="Damage per meters"
          />
        </div>
      ) : null}

      {state.persistentAreaKind === "no_semantic_effect" ? (
        <p className="text-sm text-slate-300">
          This area will render and persist normally, but will not add sight or hazard semantics.
        </p>
      ) : null}
    </div>
  );
};
