import { type BaseSpell } from "../../../../entities/base-spell";
import {
  ENTITY_ABILITIES,
  ENTITY_DAMAGE_TYPES,
  type AbilityName,
  type CombatAction,
  type DamageType,
} from "../../../../entities/campaign-entity";
import { fieldClass, isAbilityName, isDamageType } from "./constants";
import { DiceExpressionSelect } from "./DiceExpressionSelect";
import type { SetCombatActionField, SpellLabelFn, Translate } from "./types";

type Props = {
  action: CombatAction;
  index: number;
  catalogSpells: BaseSpell[];
  spellByKey: Map<string, BaseSpell>;
  setCombatAction: SetCombatActionField;
  selectSpellCatalogAction: (index: number, canonicalKey: string) => void;
  t: Translate;
  spellLabel: SpellLabelFn;
};

export const CampaignEntitySpellActionFields = ({
  action,
  index,
  catalogSpells,
  spellByKey,
  setCombatAction,
  selectSpellCatalogAction,
  t,
  spellLabel,
}: Props) => {
  const isSpellAttackAction = action.kind === "spell_attack";
  const isSaveAction = action.kind === "saving_throw";
  const isHealAction = action.kind === "heal";
  const selectedSpell = action.spellCanonicalKey
    ? (spellByKey.get(action.spellCanonicalKey) ?? null)
    : null;
  const derivedSpellDamageType = isDamageType(selectedSpell?.damageType?.toLowerCase())
    ? (selectedSpell?.damageType?.toLowerCase() as DamageType)
    : null;
  const derivedSpellSaveAbility = isAbilityName(selectedSpell?.savingThrow?.toLowerCase())
    ? (selectedSpell?.savingThrow?.toLowerCase() as AbilityName)
    : null;

  return (
    <>
      <div className="grid gap-3 xl:grid-cols-[minmax(0,1.4fr)_180px_180px]">
        <select
          value={action.spellCanonicalKey ?? ""}
          onChange={(event) => selectSpellCatalogAction(index, event.target.value)}
          className={fieldClass}
        >
          <option value="">
            {isHealAction ? t("entity.form.spellCatalogOptional") : t("entity.form.noCatalogSpell")}
          </option>
          {catalogSpells.map((spell) => (
            <option key={spell.id} value={spell.canonicalKey}>
              {spellLabel(spell)}
            </option>
          ))}
        </select>
        {(isSpellAttackAction || isSaveAction || (isHealAction && action.spellCanonicalKey)) && (
          <input
            type="number"
            min={1}
            max={9}
            value={action.castAtLevel ?? ""}
            onChange={(event) =>
              setCombatAction(index, "castAtLevel", event.target.value === "" ? null : Number(event.target.value))
            }
            placeholder={t("entity.form.castAtLevel")}
            className={fieldClass}
          />
        )}
        {isSpellAttackAction ? (
          <input
            type="number"
            value={action.spellAttackBonus ?? ""}
            onChange={(event) =>
              setCombatAction(index, "spellAttackBonus", event.target.value === "" ? null : Number(event.target.value))
            }
            placeholder={t("entity.form.spellAttackBonus")}
            className={fieldClass}
          />
        ) : isSaveAction ? (
          <input
            type="number"
            min={1}
            value={action.saveDc ?? ""}
            onChange={(event) =>
              setCombatAction(index, "saveDc", event.target.value === "" ? null : Number(event.target.value))
            }
            placeholder={t("entity.form.saveDc")}
            className={fieldClass}
          />
        ) : (
          <input
            type="number"
            value={action.healBonus ?? ""}
            onChange={(event) =>
              setCombatAction(index, "healBonus", event.target.value === "" ? null : Number(event.target.value))
            }
            placeholder={t("entity.form.healBonus")}
            className={fieldClass}
          />
        )}
      </div>

      <div className="rounded-2xl border border-white/8 bg-white/3 px-4 py-3">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">
          {selectedSpell ? t("entity.form.catalogDerivedProfile") : t("entity.form.actionOverrides")}
        </p>
        {selectedSpell ? (
          <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-300">
            <span className="rounded-full border border-sky-300/20 bg-sky-400/10 px-3 py-1 text-sky-100">
              {t("entity.form.usesCatalogSpell")}: {spellLabel(selectedSpell)}
            </span>
            {derivedSpellSaveAbility && (
              <span>
                {t("entity.form.saveAbility")}:{" "}
                {ENTITY_ABILITIES.find((ability) => ability.key === derivedSpellSaveAbility)?.label ??
                  derivedSpellSaveAbility}
              </span>
            )}
            {derivedSpellDamageType && (
              <span>
                {ENTITY_DAMAGE_TYPES.find((entry) => entry.key === derivedSpellDamageType)?.label ??
                  derivedSpellDamageType}
              </span>
            )}
            {selectedSpell.rangeText && (
              <span>
                {t("entity.form.catalogRangeText")}: {selectedSpell.rangeText}
              </span>
            )}
            {typeof selectedSpell.rangeMeters === "number" && (
              <span>
                {t("entity.form.rangeMeters")}: {selectedSpell.rangeMeters}m
              </span>
            )}
          </div>
        ) : (
          <p className="mt-2 text-xs text-slate-400">
            {isHealAction ? t("entity.form.spellCatalogOptionalHint") : t("entity.form.spellCatalogRequired")}
          </p>
        )}
      </div>

      {isSpellAttackAction && (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <DiceExpressionSelect
            value={action.damageDice}
            onChange={(value) => setCombatAction(index, "damageDice", value)}
            countPlaceholder="Qtd"
            sidesPlaceholder={t("entity.form.damageDice")}
          />
          <input
            type="number"
            value={action.damageBonus ?? ""}
            onChange={(event) =>
              setCombatAction(index, "damageBonus", event.target.value === "" ? null : Number(event.target.value))
            }
            placeholder={t("entity.form.damageBonus")}
            className={fieldClass}
          />
          <select
            value={action.damageType ?? ""}
            onChange={(event) =>
              setCombatAction(
                index,
                "damageType",
                event.target.value === "" ? null : (event.target.value as DamageType),
              )
            }
            className={fieldClass}
          >
            <option value="">{t("entity.form.damageType")}</option>
            {ENTITY_DAMAGE_TYPES.map((type) => (
              <option key={type.key} value={type.key}>
                {type.label}
              </option>
            ))}
          </select>
          <input
            type="number"
            min={0}
            value={action.rangeMeters ?? ""}
            onChange={(event) =>
              setCombatAction(index, "rangeMeters", event.target.value === "" ? null : Number(event.target.value))
            }
            placeholder={t("entity.form.rangeMeters")}
            className={fieldClass}
          />
        </div>
      )}

      {isSaveAction && (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <select
            value={action.saveAbility ?? ""}
            onChange={(event) =>
              setCombatAction(
                index,
                "saveAbility",
                event.target.value === "" ? null : (event.target.value as AbilityName),
              )
            }
            className={fieldClass}
          >
            <option value="">{t("entity.form.saveAbility")}</option>
            {ENTITY_ABILITIES.map((ability) => (
              <option key={ability.key} value={ability.key}>
                {ability.label}
              </option>
            ))}
          </select>
          <DiceExpressionSelect
            value={action.damageDice}
            onChange={(value) => setCombatAction(index, "damageDice", value)}
            countPlaceholder="Qtd"
            sidesPlaceholder={t("entity.form.damageDice")}
          />
          <input
            type="number"
            value={action.damageBonus ?? ""}
            onChange={(event) =>
              setCombatAction(index, "damageBonus", event.target.value === "" ? null : Number(event.target.value))
            }
            placeholder={t("entity.form.damageBonus")}
            className={fieldClass}
          />
          <select
            value={action.damageType ?? ""}
            onChange={(event) =>
              setCombatAction(
                index,
                "damageType",
                event.target.value === "" ? null : (event.target.value as DamageType),
              )
            }
            className={fieldClass}
          >
            <option value="">{t("entity.form.damageType")}</option>
            {ENTITY_DAMAGE_TYPES.map((type) => (
              <option key={type.key} value={type.key}>
                {type.label}
              </option>
            ))}
          </select>
        </div>
      )}

      {isHealAction && (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <DiceExpressionSelect
            value={action.healDice}
            onChange={(value) => setCombatAction(index, "healDice", value)}
            countPlaceholder="Qtd"
            sidesPlaceholder={t("entity.form.healDice")}
          />
          <input
            type="number"
            value={action.healBonus ?? ""}
            onChange={(event) =>
              setCombatAction(index, "healBonus", event.target.value === "" ? null : Number(event.target.value))
            }
            placeholder={t("entity.form.healBonus")}
            className={fieldClass}
          />
          <input
            value={action.description ?? ""}
            onChange={(event) => setCombatAction(index, "description", event.target.value)}
            placeholder={t("entity.form.combatActionDescription")}
            className={fieldClass}
          />
        </div>
      )}
    </>
  );
};
