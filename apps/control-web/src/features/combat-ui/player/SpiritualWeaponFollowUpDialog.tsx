import { useState } from "react";
import { useLocale } from "../../../shared/hooks/useLocale";
import type { CombatParticipant } from "../../../shared/api/combatRepo";
import type { SpiritualWeaponFollowUpAction } from "./spiritualWeapon";

type Props = {
  open: boolean;
  onClose: () => void;
  action: SpiritualWeaponFollowUpAction;
  participants: CombatParticipant[];
  myParticipantId?: string | null;
  isMyTurn: boolean;
  bonusActionUsed: boolean;
  onSubmit: (
    destination: { x: number; y: number } | null,
    targetRefId: string | null,
    targetKind: string | null,
  ) => Promise<void>;
  isSubmitting?: boolean;
};

export const SpiritualWeaponFollowUpDialog = ({
  open,
  onClose,
  action,
  participants,
  myParticipantId,
  isMyTurn,
  bonusActionUsed,
  onSubmit,
  isSubmitting = false,
}: Props) => {
  const { t } = useLocale();
  const [moveX, setMoveX] = useState("");
  const [moveY, setMoveY] = useState("");
  const [keepPosition, setKeepPosition] = useState(false);
  const [selectedTargetId, setSelectedTargetId] = useState("");
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  const destination =
    !keepPosition && moveX !== "" && moveY !== ""
      ? { x: parseInt(moveX, 10), y: parseInt(moveY, 10) }
      : null;

  const targetParticipant = participants.find((p) => p.id === selectedTargetId);
  const targetRefId = targetParticipant?.ref_id ?? null;
  const targetKind = targetParticipant?.kind ?? null;

  const isNoop = !destination && !targetRefId;
  const canSubmit = !isNoop && !isSubmitting && isMyTurn && !bonusActionUsed;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setError(null);
    try {
      await onSubmit(destination, targetRefId, targetKind);
      onClose();
    } catch {
      setError("Não foi possível executar a ação. Tente novamente.");
    }
  };

  const eligibleTargets = participants.filter(
    (p) => p.id !== myParticipantId && p.status !== "dead" && p.status !== "defeated",
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-sm rounded-3xl border border-violet-400/30 bg-void-950 p-6 shadow-2xl">
        <h2 className="text-lg font-semibold text-white">
          {t("combatUi.spiritualWeaponAction")}
        </h2>

        <p className="mt-2 text-xs text-slate-400">
          {t("combatUi.spiritualWeaponCurrentPosition")}:{" "}
          <span className="font-mono text-slate-200">
            ({action.position.x}, {action.position.y})
          </span>
          {action.remainingRounds != null && (
            <span className="ml-2 text-violet-300">
              · {t("combatUi.spiritualWeaponRoundsLeft").replace("{rounds}", String(action.remainingRounds))}
            </span>
          )}
        </p>

        {/* Destino */}
        <div className="mt-5">
          <label className="block text-sm font-medium text-slate-200">
            {t("combatUi.spiritualWeaponDestinationLabel")}
          </label>
          <div className="mt-2 flex items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={keepPosition}
                onChange={(e) => {
                  setKeepPosition(e.target.checked);
                  if (e.target.checked) {
                    setMoveX("");
                    setMoveY("");
                  }
                }}
                className="accent-violet-500"
              />
              {t("combatUi.spiritualWeaponKeepPosition")}
            </label>
          </div>
          {!keepPosition && (
            <div className="mt-2 flex gap-2">
              <div className="flex flex-col gap-1">
                <label className="text-xs text-slate-400">{t("combatUi.spiritualWeaponDestinationX")}</label>
                <input
                  type="number"
                  value={moveX}
                  onChange={(e) => setMoveX(e.target.value)}
                  placeholder="0"
                  className="w-20 rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-sm text-white focus:border-violet-400 focus:outline-none"
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-slate-400">{t("combatUi.spiritualWeaponDestinationY")}</label>
                <input
                  type="number"
                  value={moveY}
                  onChange={(e) => setMoveY(e.target.value)}
                  placeholder="0"
                  className="w-20 rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-sm text-white focus:border-violet-400 focus:outline-none"
                />
              </div>
            </div>
          )}
        </div>

        {/* Alvo */}
        <div className="mt-5">
          <label className="block text-sm font-medium text-slate-200">
            {t("combatUi.spiritualWeaponOptionalTarget")}
          </label>
          <select
            value={selectedTargetId}
            onChange={(e) => setSelectedTargetId(e.target.value)}
            className="mt-2 w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-sm text-white focus:border-violet-400 focus:outline-none"
          >
            <option value="">{t("combatUi.spiritualWeaponNoTarget")}</option>
            {eligibleTargets.map((p) => (
              <option key={p.id} value={p.id}>
                {p.display_name}
              </option>
            ))}
          </select>
        </div>

        {error && (
          <p className="mt-3 text-sm text-red-400">{error}</p>
        )}

        {isNoop && (
          <p className="mt-3 text-xs text-slate-500">
            Informe um destino ou selecione um alvo para confirmar a ação.
          </p>
        )}

        <div className="mt-6 flex gap-3">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 rounded-full border border-white/10 px-4 py-2 text-sm text-slate-300 transition-colors hover:bg-white/5"
          >
            Cancelar
          </button>
          <button
            type="button"
            disabled={!canSubmit}
            onClick={() => void handleSubmit()}
            className="flex-1 rounded-full bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {isSubmitting ? "Executando..." : t("combatUi.spiritualWeaponConfirm")}
          </button>
        </div>
      </div>
    </div>
  );
};
