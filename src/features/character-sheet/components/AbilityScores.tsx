import type { AbilityName, CharacterSheet, CharacterSheetMode } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import { Section } from "./Section";
import { inputSm, statBox } from "./styles";
import { ABILITIES, ABILITY_SCORE_POOL, STANDARD_ARRAY } from "../constants";
import {
  getModifier,
  formatMod,
  computeAbilityScoreTotal,
  safeParseInt,
} from "../utils/calculations";
import { getRace } from "../data/races";
import { stripClassLevelAbilityBonuses } from "../data/classFeatures";
import { useLocale } from "../../../shared/hooks/useLocale";

type Props = {
  className?: string;
  abilities: CharacterSheet["abilities"];
  race: CharacterSheet["race"];
  raceConfig?: CharacterSheet["raceConfig"];
  level: number;
  mode: CharacterSheetMode;
  readOnly?: boolean;
  allowFreeformCreationEditing?: boolean;
  setAbility: SheetActions["setAbility"];
};

export const AbilityScores = ({
  className,
  abilities,
  race,
  raceConfig = null,
  level,
  mode,
  readOnly = false,
  allowFreeformCreationEditing = false,
  setAbility,
}: Props) => {
  const { t } = useLocale();
  const isCreation = mode === "creation";
  const raceData = getRace(race, raceConfig);
  const baseAbilities = stripClassLevelAbilityBonuses(
    { ...abilities },
    className ?? "",
    level,
  );
  if (isCreation && raceData) {
    for (const [key, bonus] of Object.entries(raceData.abilityBonuses)) {
      const abilityKey = key as AbilityName;
      baseAbilities[abilityKey] -= bonus ?? 0;
    }
  }
  const usedPoints = computeAbilityScoreTotal(isCreation ? baseAbilities : abilities);
  const remainingPoints = ABILITY_SCORE_POOL - usedPoints;

  return (
    <Section title={t("sheet.abilities.title")} color="bg-violet-500" className={className}>
      {!isCreation && (
        <div className="mb-3 rounded-xl border border-white/8 bg-slate-950/55 px-3 py-2.5 text-xs shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
          <p className="font-semibold text-slate-200">
            {t("sheet.abilities.used")}: <span className="text-white">{usedPoints}</span> / {ABILITY_SCORE_POOL}
          </p>
          <p
            className={`mt-1 font-semibold ${
              remainingPoints < 0 ? "text-rose-400" : "text-limiar-300"
            }`}
          >
            {t("sheet.abilities.remaining")}: {remainingPoints}
          </p>
        </div>
      )}

      <div className="grid grid-cols-2 gap-2 lg:grid-cols-3">
        {ABILITIES.map(({ key, short }) => {
          const mod = getModifier(abilities[key]);
          const baseValue = baseAbilities[key];
          return (
            <AbilityCard
              key={key}
              abilityKey={key}
              short={short}
              baseValue={baseValue}
              value={abilities[key]}
              bonus={abilities[key] - baseValue}
              mod={mod}
              isCreation={isCreation}
              allowFreeformCreationEditing={allowFreeformCreationEditing}
              readOnly={readOnly}
              onChange={setAbility}
              labelFinal={t("sheet.abilities.final")}
              labelMod={t("sheet.abilities.mod")}
            />
          );
        })}
      </div>
    </Section>
  );
};

type CardProps = {
  abilityKey: AbilityName;
  short: string;
  baseValue: number;
  value: number;
  bonus: number;
  mod: number;
  isCreation: boolean;
  allowFreeformCreationEditing: boolean;
  readOnly: boolean;
  onChange: (ability: AbilityName, value: number) => void;
  labelFinal: string;
  labelMod: string;
};

const AbilityCard = ({
  abilityKey,
  short,
  baseValue,
  value,
  bonus,
  mod,
  isCreation,
  allowFreeformCreationEditing,
  readOnly,
  onChange,
  labelFinal,
  labelMod,
}: CardProps) => (
  <div className={`${statBox} min-h-[130px] items-stretch justify-between gap-2`}>
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-bold uppercase tracking-[0.3em] text-slate-500">{short}</span>
        {isCreation && bonus !== 0 && (
          <span className="rounded-full border border-limiar-500/20 bg-limiar-500/10 px-2 py-0.5 text-[10px] font-semibold text-limiar-300">
            {bonus > 0 ? `+${bonus}` : bonus}
          </span>
        )}
      </div>
      {isCreation ? (
        allowFreeformCreationEditing ? (
          <input
            type="number"
            min={0}
            max={30}
            value={baseValue}
            disabled={readOnly}
            onChange={(e) => onChange(abilityKey, safeParseInt(e.target.value, 0))}
            className={`${inputSm} h-10 text-lg ${readOnly ? "opacity-70" : ""}`}
          />
        ) : (
          <select
            value={baseValue}
            disabled={readOnly}
            onChange={(e) => onChange(abilityKey, safeParseInt(e.target.value, 0))}
            className={`${inputSm} h-10 text-lg ${readOnly ? "opacity-70" : ""}`}
          >
            {!STANDARD_ARRAY.includes(baseValue as (typeof STANDARD_ARRAY)[number]) && (
              <option value={baseValue}>{baseValue}</option>
            )}
            {STANDARD_ARRAY.map((score) => (
              <option key={score} value={score}>
                {score}
              </option>
            ))}
          </select>
        )
      ) : (
        <input
          type="number"
          min={0}
          max={30}
          value={value}
          disabled={readOnly}
          onChange={(e) => onChange(abilityKey, safeParseInt(e.target.value, 0))}
          className={`${inputSm} h-10 text-lg ${readOnly ? "opacity-70" : ""}`}
        />
      )}
    </div>

    <div className="grid grid-cols-2 gap-2 rounded-xl border border-white/6 bg-white/3 px-2.5 py-2">
      <div className="text-center">
        <p className="text-[9px] font-semibold uppercase tracking-[0.22em] text-slate-500">
          {labelFinal}
        </p>
        <p className="mt-1 text-2xl font-bold text-slate-50">{value}</p>
      </div>
      <div className="text-center">
        <p className="text-[9px] font-semibold uppercase tracking-[0.22em] text-slate-500">
          {labelMod}
        </p>
        <p className={`mt-1 text-2xl font-bold ${mod >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
          {formatMod(mod)}
        </p>
      </div>
    </div>
  </div>
);
