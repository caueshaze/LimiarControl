import type { CharacterSheet, ConditionName } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import { Section } from "./Section";
import { CONDITION_LABELS, CONDITION_NAMES } from "../constants";
import { useLocale } from "../../../shared/hooks/useLocale";

type Props = {
  conditions: CharacterSheet["conditions"];
  onToggle: SheetActions["toggleCondition"];
  readOnly?: boolean;
};

export const Conditions = ({ conditions, onToggle, readOnly = false }: Props) => {
  const { t } = useLocale();
  const activeCount = CONDITION_NAMES.filter((c) => conditions[c]).length;

  return (
    <Section
      title={`${t("sheet.conditions.title")}${activeCount > 0 ? ` (${activeCount})` : ""}`}
      color="bg-rose-500"
      defaultOpen={false}
    >
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7">
        {CONDITION_NAMES.map((condition) => (
          <ConditionBadge
            key={condition}
            condition={condition}
            active={conditions[condition]}
            onToggle={onToggle}
            readOnly={readOnly}
          />
        ))}
      </div>
    </Section>
  );
};

type BadgeProps = {
  condition: ConditionName;
  active: boolean;
  onToggle: (c: ConditionName) => void;
  readOnly: boolean;
};

const ConditionBadge = ({ condition, active, onToggle, readOnly }: BadgeProps) => (
  <button
    type="button"
    disabled={readOnly}
    onClick={() => onToggle(condition)}
    className={`rounded-xl border px-2 py-1.5 text-[11px] font-semibold transition-colors ${
      active
        ? "border-rose-500 bg-rose-500/20 text-rose-300"
        : "border-slate-700 bg-transparent text-slate-600 hover:border-slate-600 hover:text-slate-400"
    }`}
  >
    {CONDITION_LABELS[condition]}
  </button>
);
