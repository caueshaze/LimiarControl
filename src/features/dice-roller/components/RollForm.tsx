import { useState } from "react";
import { useLocale } from "../../../shared/hooks/useLocale";

type RollFormProps = {
  onRoll: (expression: string, label?: string) => void;
  disabled?: boolean;
};

export const RollForm = ({ onRoll, disabled = false }: RollFormProps) => {
  const { t } = useLocale();
  const [expression, setExpression] = useState("");
  const [label, setLabel] = useState("");

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!expression.trim()) {
      return;
    }
    onRoll(expression, label || undefined);
    setExpression("");
    setLabel("");
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900/40 p-4"
    >
      <div>
        <label className="text-xs font-semibold uppercase tracking-wide text-slate-400">
          {t("rolls.form.expression")}
        </label>
        <input
          value={expression}
          onChange={(event) => setExpression(event.target.value)}
          className="mt-2 w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-slate-500 focus:outline-none"
          placeholder={t("rolls.form.expressionPlaceholder")}
          disabled={disabled}
        />
      </div>
      <div>
        <label className="text-xs font-semibold uppercase tracking-wide text-slate-400">
          {t("rolls.form.label")}
        </label>
        <input
          value={label}
          onChange={(event) => setLabel(event.target.value)}
          className="mt-2 w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-slate-500 focus:outline-none"
          placeholder={t("rolls.form.labelPlaceholder")}
          disabled={disabled}
        />
      </div>
      <button
        type="submit"
        disabled={disabled || !expression.trim()}
        className="w-full rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-900 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {t("rolls.form.submit")}
      </button>
    </form>
  );
};
