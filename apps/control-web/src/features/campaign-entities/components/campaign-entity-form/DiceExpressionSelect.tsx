import { useEffect, useRef, useState } from "react";

import { fieldClass } from "./constants";

const DICE_COUNTS = Array.from({ length: 12 }, (_, index) => index + 1);
const DICE_SIDES = [4, 6, 8, 10, 12, 20];

type DiceParts = {
  count: string;
  sides: string;
};

export const parseDiceExpression = (value: string | null | undefined): DiceParts => {
  if (!value) {
    return { count: "", sides: "" };
  }
  const match = value.trim().match(/^(\d*)d(\d+)$/i);
  if (!match) {
    return { count: "", sides: "" };
  }
  return {
    count: match[1] && match[1].length > 0 ? match[1] : "1",
    sides: match[2] ?? "",
  };
};

export const buildDiceExpression = ({ count, sides }: DiceParts) =>
  count && sides ? `${count}d${sides}` : "";

type Props = {
  value: string | null | undefined;
  onChange: (value: string) => void;
  disabled?: boolean;
  countPlaceholder: string;
  sidesPlaceholder: string;
};

export const DiceExpressionSelect = ({
  value,
  onChange,
  disabled = false,
  countPlaceholder,
  sidesPlaceholder,
}: Props) => {
  const [draft, setDraft] = useState<DiceParts>(() => parseDiceExpression(value));
  const previousValue = useRef(value ?? "");

  useEffect(() => {
    if (value) {
      setDraft(parseDiceExpression(value));
    } else if (previousValue.current) {
      setDraft({ count: "", sides: "" });
    }
    previousValue.current = value ?? "";
  }, [value]);

  const update = (nextCount: string, nextSides: string) => {
    const next = { count: nextCount, sides: nextSides };
    setDraft(next);
    onChange(buildDiceExpression(next));
  };

  return (
    <div className="grid grid-cols-2 gap-3">
      <select
        value={draft.count}
        disabled={disabled}
        onChange={(event) => update(event.target.value, draft.sides)}
        className={fieldClass}
      >
        <option value="">{countPlaceholder}</option>
        {DICE_COUNTS.map((count) => (
          <option key={count} value={String(count)}>
            {count}x
          </option>
        ))}
      </select>
      <select
        value={draft.sides}
        disabled={disabled}
        onChange={(event) => update(draft.count, event.target.value)}
        className={fieldClass}
      >
        <option value="">{sidesPlaceholder}</option>
        {DICE_SIDES.map((sides) => (
          <option key={sides} value={String(sides)}>
            d{sides}
          </option>
        ))}
      </select>
    </div>
  );
};
