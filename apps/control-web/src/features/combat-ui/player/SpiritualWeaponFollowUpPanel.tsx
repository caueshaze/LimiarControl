import type { CombatParticipant } from "../../../shared/api/combatRepo";
import type { SpiritualWeaponFollowUpAction } from "./spiritualWeapon";

type Props = {
  action: SpiritualWeaponFollowUpAction;
  destination: { x: number; y: number } | null;
  targetId: string;
  validTargets: CombatParticipant[];
  finalPosition: { x: number; y: number } | null;
  submitting: boolean;
  isMyTurn: boolean;
  /** True once the map-token fetch for this swMode session has resolved. */
  mapTokensLoaded: boolean;
  onTargetChange: (id: string) => void;
  onCancel: () => void;
  onConfirm: () => void;
  t: (key: string) => string;
};

/**
 * Inline panel rendered below the map while the player is choosing a
 * destination and target for a Spiritual Weapon follow-up action.
 *
 * Pure presentational component: all state lives in the parent shell.
 */
export function SpiritualWeaponFollowUpPanel({
  destination,
  targetId,
  validTargets,
  finalPosition,
  submitting,
  isMyTurn,
  mapTokensLoaded,
  onTargetChange,
  onCancel,
  onConfirm,
  t,
}: Props) {
  const confirmDisabled = (!destination && !targetId) || submitting || !isMyTurn;

  return (
    <div className="rounded-3xl border border-violet-400/30 bg-void-950 p-4 space-y-3">
      <p className="text-sm font-semibold text-white">{t("combatUi.spiritualWeaponAction")}</p>
      <p className="text-xs text-slate-400">
        {destination
          ? `Destino: (${destination.x}, ${destination.y})`
          : "Clique no mapa para selecionar o destino da arma."}
      </p>
      <select
        value={targetId}
        onChange={(e) => onTargetChange(e.target.value)}
        className="w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-sm text-white focus:border-violet-400 focus:outline-none"
      >
        <option value="">{t("combatUi.spiritualWeaponNoTarget")}</option>
        {validTargets.map((p) => (
          <option key={p.id} value={p.id}>{p.display_name}</option>
        ))}
      </select>
      {validTargets.length === 0 && finalPosition && mapTokensLoaded && (
        <p className="text-xs text-slate-500">
          Nenhum alvo válido adjacente à posição final da arma.
        </p>
      )}
      <div className="flex gap-3">
        <button
          type="button"
          onClick={onCancel}
          className="flex-1 rounded-full border border-white/10 px-4 py-2 text-sm text-slate-300 hover:bg-white/5"
        >
          Cancelar
        </button>
        <button
          type="button"
          disabled={confirmDisabled}
          onClick={onConfirm}
          className="flex-1 rounded-full bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-500 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {submitting ? "Executando..." : t("combatUi.spiritualWeaponConfirm")}
        </button>
      </div>
    </div>
  );
}
