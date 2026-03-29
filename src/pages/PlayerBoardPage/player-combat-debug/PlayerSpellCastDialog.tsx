import { useEffect, useState } from "react";
import type { AbilityName } from "../../../entities/roll/rollResolution.types";
import { ConcentrationSaveControl } from "../../../features/combat-ui/components/ConcentrationSaveControl";
import { participantHasActiveConcentration } from "../../../features/combat-ui/combatUi.helpers";
import type {
  CombatParticipant,
  CombatSpellMode,
  CombatSpellResult,
} from "../../../shared/api/combatRepo";
import { combatRepo } from "../../../shared/api/combatRepo";
import {
  getDamageRollCount,
  getDamageRollSides,
  formatDamageDiceExpression,
} from "../../../shared/utils/diceExpression";
import { D20_VALUES, parseBonus } from "./spellCastHelpers";
import { SpellCastResultPanel } from "./SpellCastResultPanel";
import type { CombatSpellOption } from "./types";

type Props = {
  actorParticipantId: string;
  onClose: () => void;
  onResolved?: (result: CombatSpellResult) => void | Promise<void>;
  sessionId: string;
  spell: CombatSpellOption;
  spellDamageType: string;
  spellEffectBonus: string;
  spellEffectDice: string;
  spellMode: CombatSpellMode;
  spellSaveAbility: AbilityName | "";
  target: CombatParticipant;
};

export const PlayerSpellCastDialog = ({
  actorParticipantId,
  onClose,
  onResolved,
  sessionId,
  spell,
  spellDamageType,
  spellEffectBonus,
  spellEffectDice,
  spellMode,
  spellSaveAbility,
  target,
}: Props) => {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [attackMode, setAttackMode] = useState<"choose" | "manual" | "virtual">("choose");
  const [effectMode, setEffectMode] = useState<"choose" | "manual" | "virtual">("choose");
  const [manualEffectRolls, setManualEffectRolls] = useState<number[]>([]);
  const [concentrationRollMode, setConcentrationRollMode] = useState<"system" | "manual">("system");
  const [concentrationManualRoll, setConcentrationManualRoll] = useState("");
  const [selectedSlotLevel, setSelectedSlotLevel] = useState<number | null>(
    spell.fixedCastLevel ?? (spell.level > 0 ? spell.level : null),
  );
  const [result, setResult] = useState<CombatSpellResult | null>(null);
  const targetHasConcentration = participantHasActiveConcentration(target);
  const shouldShowConcentrationControl = targetHasConcentration && spellMode !== "heal" && spellMode !== "utility";
  const slotOptions = spell.availableSlotLevels.length > 0 ? spell.availableSlotLevels : (spell.level > 0 ? [spell.level] : []);

  useEffect(() => {
    setSelectedSlotLevel(spell.fixedCastLevel ?? (spell.level > 0 ? spell.level : null));
  }, [spell.fixedCastLevel, spell.id, spell.level]);

  const effectDiceLabel =
    formatDamageDiceExpression(result?.effect_dice ?? spellEffectDice, Boolean(result?.is_critical)) ??
    result?.effect_dice ??
    spellEffectDice;
  const effectRollCount = getDamageRollCount(result?.effect_dice ?? spellEffectDice, Boolean(result?.is_critical));
  const effectRollSides = getDamageRollSides(result?.effect_dice ?? spellEffectDice);
  const effectRollValues = Array.from({ length: effectRollSides }, (_, i) => i + 1);
  const effectKindLabel =
    result?.effect_kind === "healing" || spellMode === "heal"
      ? "cura"
      : spellMode === "utility"
        ? "efeito"
        : "dano";
  const parsedBonus = parseBonus(spellEffectBonus);
  const actionCostLabel =
    spell.actionCost === "bonus_action"
      ? "Bonus Action"
      : spell.actionCost === "reaction"
        ? "Reaction"
        : spell.actionCost === "free"
          ? "Free"
          : "Action";

  const submitCast = async (payload?: {
    manual_roll?: number;
    roll_source?: "manual" | "system";
  }) => {
    setLoading(true);
    setError(null);

    try {
      const resolved = await combatRepo.castSpell(sessionId, {
        actor_participant_id: actorParticipantId,
        target_ref_id: target.ref_id,
        spell_canonical_key: spell.canonicalKey,
        spell_id: spell.canonicalKey,
        spell_mode: spellMode,
        slot_level:
          spell.sourceType === "magic_item"
            ? spell.fixedCastLevel ?? spell.level ?? null
            : spell.level > 0
              ? selectedSlotLevel ?? spell.level
              : null,
        inventory_item_id: spell.sourceType === "magic_item" ? spell.inventoryItemId ?? null : null,
        roll_source: payload?.roll_source ?? "system",
        manual_roll: payload?.manual_roll ?? null,
        damage_dice: spellMode === "heal" ? null : spellEffectDice || null,
        damage_bonus: spellMode === "heal" ? null : parsedBonus,
        heal_dice: spellMode === "heal" ? spellEffectDice || null : null,
        heal_bonus: spellMode === "heal" ? parsedBonus : null,
        damage_type: spellMode === "heal" ? null : spellDamageType || null,
        save_ability: spellMode === "saving_throw" ? spellSaveAbility || null : null,
        concentration_roll_source: concentrationRollMode,
        concentration_manual_roll:
          shouldShowConcentrationControl && concentrationRollMode === "manual"
            ? Number.parseInt(concentrationManualRoll, 10) || null
            : null,
      });
      setResult(resolved);
      setManualEffectRolls([]);
      setEffectMode("choose");
      if (!resolved.effect_roll_required) {
        await onResolved?.(resolved);
      }
    } catch (err: any) {
      setError(err?.data?.detail || err?.message || "Falha ao conjurar magia");
    } finally {
      setLoading(false);
    }
  };

  const submitEffect = async (payload: {
    manual_rolls?: number[];
    roll_source: "manual" | "system";
  }) => {
    if (!result?.pending_spell_id) return;
    setLoading(true);
    setError(null);

    try {
      const resolved = await combatRepo.castSpellEffect(sessionId, {
        actor_participant_id: actorParticipantId,
        pending_spell_id: result.pending_spell_id,
        roll_source: payload.roll_source,
        manual_rolls: payload.manual_rolls ?? null,
        concentration_roll_source: concentrationRollMode,
        concentration_manual_roll:
          shouldShowConcentrationControl && concentrationRollMode === "manual"
            ? Number.parseInt(concentrationManualRoll, 10) || null
            : null,
      });
      setResult(resolved);
      await onResolved?.(resolved);
    } catch (err: any) {
      setError(err?.data?.detail || err?.message || `Falha ao rolar ${effectKindLabel}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 px-4">
      <div className="w-full max-w-md rounded-3xl border border-fuchsia-400/30 bg-void-950 p-6 text-slate-100 shadow-2xl shadow-fuchsia-950/30">
        <p className="text-xs uppercase tracking-[0.3em] text-fuchsia-200">Magia</p>
        <h2 className="mt-3 text-2xl font-semibold text-white">{spell.name}</h2>
        <p className="mt-2 text-sm text-slate-300">
          Alvo: <span className="font-semibold text-white">{target.display_name}</span>
        </p>
        {spell.sourceType === "magic_item" && spell.sourceItemName ? (
          <p className="mt-1 text-sm text-slate-400">
            Item: <span className="font-semibold text-white">{spell.sourceItemName}</span>
            {typeof spell.chargesCurrent === "number" && typeof spell.chargesMax === "number"
              ? ` · ${spell.chargesCurrent}/${spell.chargesMax}`
              : ""}
          </p>
        ) : null}
        <p className="mt-1 text-sm text-slate-400">
          Fluxo: {spellMode.replace(/_/g, " ")}
          {spellMode !== "heal" && spellMode !== "utility" && spellDamageType ? ` · ${spellDamageType}` : ""}
          {spellMode === "saving_throw" && spellSaveAbility ? ` · save ${spellSaveAbility}` : ""}
        </p>
        <p className="mt-1 text-xs uppercase tracking-[0.2em] text-fuchsia-200/80">
          {actionCostLabel}
        </p>
        {spell.sourceType === "magic_item" && spell.fixedCastLevel ? (
          <p className="mt-4 text-xs uppercase tracking-[0.18em] text-slate-400">
            Item cast level: {spell.fixedCastLevel}
          </p>
        ) : null}
        {spell.level > 0 && spell.sourceType !== "magic_item" ? (
          <label className="mt-4 block">
            <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
              Slot level
            </span>
            <select
              value={selectedSlotLevel ?? spell.level}
              onChange={(event) => setSelectedSlotLevel(Number.parseInt(event.target.value, 10))}
              className="mt-2 w-full rounded-2xl border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none transition focus:border-fuchsia-400"
            >
              {slotOptions.map((slotLevel) => (
                <option key={slotLevel} value={slotLevel}>
                  {slotLevel}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        {shouldShowConcentrationControl ? (
          <div className="mt-4">
            <ConcentrationSaveControl
              disabled={loading}
              manualValue={concentrationManualRoll}
              mode={concentrationRollMode}
              onManualValueChange={setConcentrationManualRoll}
              onModeChange={setConcentrationRollMode}
            />
          </div>
        ) : null}

        {error && (
          <div className="mt-4 rounded-2xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            {error}
          </div>
        )}

        {result ? (
          <SpellCastResultPanel
            effectDiceLabel={effectDiceLabel}
            effectKindLabel={effectKindLabel}
            effectMode={effectMode}
            effectRollCount={effectRollCount}
            effectRollValues={effectRollValues}
            loading={loading}
            manualEffectRolls={manualEffectRolls}
            onClose={onClose}
            onEffectModeChange={setEffectMode}
            onManualEffectRollsChange={setManualEffectRolls}
            onSubmitEffect={(payload) => { void submitEffect(payload); }}
            result={result}
          />
        ) : null}

        {!result && spellMode === "spell_attack" && attackMode === "choose" ? (
          <div className="mt-5 grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setAttackMode("virtual")}
              className="rounded-2xl bg-fuchsia-600 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white hover:bg-fuchsia-500"
            >
              Virtual
            </button>
            <button
              type="button"
              onClick={() => setAttackMode("manual")}
              className="rounded-2xl border border-slate-600 bg-slate-800 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-slate-200 hover:bg-slate-700"
            >
              Manual
            </button>
          </div>
        ) : null}

        {!result && spellMode === "spell_attack" && attackMode === "virtual" ? (
          <div className="mt-5 flex gap-3">
            <button
              type="button"
              disabled={loading}
              onClick={() => { void submitCast({ roll_source: "system" }); }}
              className="flex-1 rounded-full bg-fuchsia-600 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white disabled:opacity-50"
            >
              {loading ? "..." : "Rolar ataque magico"}
            </button>
            <button
              type="button"
              onClick={() => setAttackMode("choose")}
              className="rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400"
            >
              Voltar
            </button>
          </div>
        ) : null}

        {!result && spellMode === "spell_attack" && attackMode === "manual" ? (
          <div className="mt-5 space-y-3">
            <p className="text-xs text-slate-400">Selecione o d20 manual do ataque.</p>

            <div className="grid grid-cols-5 gap-2">
              {D20_VALUES.map((value) => (
                <button
                  key={value}
                  type="button"
                  disabled={loading}
                  onClick={() => { void submitCast({ roll_source: "manual", manual_roll: value }); }}
                  className="rounded-xl border border-slate-700 bg-slate-900 px-2 py-3 text-center text-lg font-bold text-white transition-colors hover:border-fuchsia-500/50 hover:bg-slate-800 disabled:opacity-50"
                >
                  {value}
                </button>
              ))}
            </div>

            <button
              type="button"
              onClick={() => setAttackMode("choose")}
              className="rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400"
            >
              Voltar
            </button>
          </div>
        ) : null}

        {!result && spellMode !== "spell_attack" ? (
          <div className="mt-5 flex gap-3">
            <button
              type="button"
              disabled={loading}
              onClick={() => { void submitCast(); }}
              className="flex-1 rounded-full bg-fuchsia-600 px-4 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-white disabled:opacity-50"
            >
              {loading ? "..." : "Conjurar"}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-full border border-slate-700 px-4 py-3 text-xs text-slate-400"
            >
              Fechar
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
};
