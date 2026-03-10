import type { CharacterSheet, InventoryItem } from "../model/characterSheet.types";
import type { SheetActions } from "../hooks/useCharacterSheet";
import { Section, RemoveBtn } from "./Section";
import { input, fieldLabel, btnPrimary } from "./styles";
import { computeTotalWeight, safeParseInt } from "../utils/calculations";

type Props = {
  inventory: CharacterSheet["inventory"];
  currency?: CharacterSheet["currency"];
  onAdd: SheetActions["addItem"];
  onRemove: SheetActions["removeItem"];
  onUpdate: SheetActions["updateItem"];
  readOnly?: boolean;
};

export const Equipment = ({ inventory, currency, onAdd, onRemove, onUpdate, readOnly = false }: Props) => {
  const totalWeight = computeTotalWeight(inventory);
  const hasCurrency = Boolean(
    currency && Object.values(currency).some((value) => value > 0),
  );

  return (
    <Section title="Equipment & Inventory" color="bg-amber-500">
      <div className="space-y-2">
        {inventory.length === 0 && (
          <p className="py-4 text-center text-xs text-slate-600">{readOnly ? "No starting equipment." : "No items. Click Add Item to start."}</p>
        )}
        {inventory.map((item) => (
          <ItemRow key={item.id} item={item} onRemove={onRemove} onUpdate={onUpdate} readOnly={readOnly} />
        ))}
      </div>

      <div className="mt-3 flex items-center justify-between border-t border-slate-800 pt-3">
        <div className="space-y-1">
          <span className="block text-xs text-slate-500">
            Total weight:{" "}
            <span className="font-semibold text-slate-300">{totalWeight} lb</span>
          </span>
          {readOnly && hasCurrency && (
            <span className="block text-xs text-slate-500">
              Locked funds:{" "}
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
            Add Item
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
};

const ItemRow = ({ item, onRemove, onUpdate, readOnly }: RowProps) => (
  <div className="flex items-start gap-2 rounded-xl border border-slate-800/60 bg-void-950/40 p-3">
    <div className="flex-1 grid grid-cols-2 gap-2 sm:grid-cols-4">
      <div className="sm:col-span-2">
        <label className={fieldLabel}>Item Name</label>
        <input
          type="text"
          placeholder="Item name"
          value={item.name}
          disabled={readOnly}
          onChange={(e) => onUpdate(item.id, "name", e.target.value)}
          className={input}
        />
      </div>
      <div>
        <label className={fieldLabel}>Qty</label>
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
        <label className={fieldLabel}>Weight (lb)</label>
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
        <label className={fieldLabel}>Notes</label>
        <input
          type="text"
          placeholder="Notes..."
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
