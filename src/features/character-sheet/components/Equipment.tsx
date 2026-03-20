import type { CharacterSheet, InventoryItem } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import { Section, RemoveBtn } from "./Section";
import { input, fieldLabel, btnPrimary } from "./styles";
import { computeTotalWeight, safeParseInt } from "../utils/calculations";
import { useLocale } from "../../../shared/hooks/useLocale";
import type { LocaleKey } from "../../../shared/i18n";

type Props = {
  inventory: CharacterSheet["inventory"];
  currency?: CharacterSheet["currency"];
  onAdd: SheetActions["addItem"];
  onRemove: SheetActions["removeItem"];
  onUpdate: SheetActions["updateItem"];
  readOnly?: boolean;
};

export const Equipment = ({ inventory, currency, onAdd, onRemove, onUpdate, readOnly = false }: Props) => {
  const { t } = useLocale();
  const totalWeight = computeTotalWeight(inventory);
  const hasCurrency = Boolean(
    currency && Object.values(currency).some((value) => value > 0),
  );

  return (
    <Section title={t("sheet.equipment.title")} color="bg-amber-500">
      <div className="space-y-2">
        {inventory.length === 0 && (
          <div className="flex flex-col items-center gap-2 py-6 text-slate-600">
            <svg className="h-8 w-8 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
            </svg>
            <p className="text-xs">{readOnly ? t("sheet.equipment.emptyCreation") : t("sheet.equipment.empty")}</p>
          </div>
        )}
        {inventory.map((item) => (
          <ItemRow key={item.id} item={item} onRemove={onRemove} onUpdate={onUpdate} readOnly={readOnly} t={t} />
        ))}
      </div>

      <div className="mt-3 flex items-center justify-between border-t border-slate-800 pt-3">
        <div className="space-y-1">
          <span className="block text-xs text-slate-500">
            {t("sheet.equipment.totalWeight")}:{" "}
            <span className="font-semibold text-slate-300">{totalWeight} lb</span>
          </span>
          {readOnly && hasCurrency && (
            <span className="block text-xs text-slate-500">
              {t("sheet.equipment.lockedFunds")}:{" "}
              <span className="font-semibold text-slate-300">
                {Object.entries(currency ?? {})
                  .filter(([, value]) => value > 0)
                  .map(([coin, value]) => `${value} ${coin}`)
                  .join(", ")}
              </span>
            </span>
          )}
        </div>
        {!readOnly && (
          <button type="button" onClick={onAdd} className={btnPrimary}>
            {t("sheet.equipment.addItem")}
          </button>
        )}
      </div>
    </Section>
  );
};

type RowProps = {
  item: InventoryItem;
  onRemove: SheetActions["removeItem"];
  onUpdate: SheetActions["updateItem"];
  readOnly: boolean;
  t: (key: LocaleKey) => string;
};

const ItemRow = ({ item, onRemove, onUpdate, readOnly, t }: RowProps) => (
  <div className="flex items-start gap-2 rounded-xl border border-slate-800/60 bg-void-950/40 p-3">
    <div className="flex-1 grid grid-cols-2 gap-2 sm:grid-cols-4">
      <div className="sm:col-span-2">
        <label className={fieldLabel}>{t("sheet.equipment.itemName")}</label>
        <input
          type="text"
          placeholder={t("sheet.equipment.itemNamePlaceholder")}
          value={item.name}
          disabled={readOnly}
          onChange={(e) => onUpdate(item.id, "name", e.target.value)}
          className={input}
        />
      </div>
      <div>
        <label className={fieldLabel}>{t("sheet.equipment.qty")}</label>
        <input
          type="number"
          min={0}
          value={item.quantity}
          disabled={readOnly}
          onChange={(e) => onUpdate(item.id, "quantity", Math.max(0, safeParseInt(e.target.value)))}
          className={input}
        />
      </div>
      <div>
        <label className={fieldLabel}>{t("sheet.equipment.weight")}</label>
        <input
          type="number"
          min={0}
          step={0.1}
          value={item.weight}
          disabled={readOnly}
          onChange={(e) => onUpdate(item.id, "weight", Math.max(0, parseFloat(e.target.value) || 0))}
          className={input}
        />
      </div>
      <div className="sm:col-span-4">
        <label className={fieldLabel}>{t("sheet.equipment.notes")}</label>
        <input
          type="text"
          placeholder={t("sheet.equipment.notesPlaceholder")}
          value={item.notes}
          disabled={readOnly}
          onChange={(e) => onUpdate(item.id, "notes", e.target.value)}
          className={input}
        />
      </div>
    </div>
    {!readOnly && <RemoveBtn onClick={() => onRemove(item.id)} title="Remove item" />}
  </div>
);
