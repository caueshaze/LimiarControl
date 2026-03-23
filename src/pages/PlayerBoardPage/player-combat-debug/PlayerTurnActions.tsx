import type { AbilityName } from "../../../entities/roll/rollResolution.types";
import type { CombatSpellMode } from "../../../shared/api/combatRepo";
import type { CombatParticipant } from "../../../shared/api/combatRepo";
import type { PlayerBoardWeaponSummary } from "../playerBoard.types";
import type { CombatSpellOption } from "./types";

const DAMAGE_TYPE_OPTIONS = [
  "acid",
  "bludgeoning",
  "cold",
  "fire",
  "force",
  "lightning",
  "necrotic",
  "piercing",
  "poison",
  "psychic",
  "radiant",
  "slashing",
  "thunder",
];

const parseEffectBonus = (value: string) => {
  const parsed = Number.parseInt(value.trim(), 10);
  return Number.isFinite(parsed) ? parsed : 0;
};

type Props = {
  activeTab: "attack" | "cast";
  canRollDeathSave: boolean;
  currentWeapon: PlayerBoardWeaponSummary | null;
  deathSaveVisible: boolean;
  defeatedTargets: CombatParticipant[];
  isActive: boolean;
  isMyTurn: boolean;
  loading: boolean;
  livingTargets: CombatParticipant[];
  myParticipant: CombatParticipant | null;
  onAttack: () => void;
  onCast: () => void;
  onDeathSave: () => void;
  onEndTurn: () => void;
  selectedSpell: CombatSpellOption | null;
  selectedSpellId: string;
  setActiveTab: (value: "attack" | "cast") => void;
  setSelectedSpellId: (value: string) => void;
  setSpellDamageType: (value: string) => void;
  setSpellEffectBonus: (value: string) => void;
  setSpellEffectDice: (value: string) => void;
  setSpellMode: (value: CombatSpellMode) => void;
  setSpellSaveAbility: (value: AbilityName | "") => void;
  setTargetId: (value: string) => void;
  spellDamageType: string;
  spellEffectBonus: string;
  spellEffectDice: string;
  spellMode: CombatSpellMode;
  spellOptions: CombatSpellOption[];
  spellSaveAbility: AbilityName | "";
  targetId: string;
};

export const PlayerTurnActions = ({
  activeTab,
  canRollDeathSave,
  currentWeapon,
  deathSaveVisible,
  defeatedTargets,
  isActive,
  isMyTurn,
  loading,
  livingTargets,
  myParticipant,
  onAttack,
  onCast,
  onDeathSave,
  onEndTurn,
  selectedSpell,
  selectedSpellId,
  setActiveTab,
  setSelectedSpellId,
  setSpellDamageType,
  setSpellEffectBonus,
  setSpellEffectDice,
  setSpellMode,
  setSpellSaveAbility,
  setTargetId,
  spellDamageType,
  spellEffectBonus,
  spellEffectDice,
  spellMode,
  spellOptions,
  spellSaveAbility,
  targetId,
}: Props) => {
  const canSubmitSpell =
    Boolean(targetId) &&
    Boolean(selectedSpell?.canonicalKey) &&
    (spellMode === "heal" || Boolean(spellDamageType)) &&
    (spellMode !== "saving_throw" || Boolean(spellSaveAbility)) &&
    (spellEffectDice.trim().length > 0 || parseEffectBonus(spellEffectBonus) > 0);

  if (deathSaveVisible) {
    return (
      <div className="mt-4 rounded border border-rose-500/40 bg-rose-950/40 p-4">
        <h4 className="text-sm font-bold uppercase tracking-widest text-rose-300">Downed</h4>
        <p className="mt-2 text-sm text-rose-100">
          {canRollDeathSave
            ? "You reached 0 HP and must roll a Death Save now."
            : "You reached 0 HP. Your Death Save will become available on your turn."}
        </p>
        <button
          disabled={loading || !canRollDeathSave}
          onClick={onDeathSave}
          className="mt-4 w-full rounded bg-rose-600 px-4 py-4 text-lg font-bold uppercase tracking-widest text-white hover:bg-rose-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Roll Death Save
        </button>
      </div>
    );
  }

  if (!isMyTurn || !myParticipant) {
    return null;
  }

  return (
    <div className="mt-4 border-t border-sky-500/20 pt-4">
      <h4 className="mb-2 font-bold text-sky-300">Your Turn Actions (Debug UI)</h4>

      {isActive ? (
        <>
          <div className="mb-4 flex gap-2">
            <select
              className="flex-1 rounded border border-slate-700 bg-slate-900 p-2 text-white"
              value={targetId}
              onChange={(e) => setTargetId(e.target.value)}
            >
              <option value="">Select Target...</option>
              {livingTargets.length > 0 && (
                <optgroup label="Vivos / em combate">
                  {livingTargets.map((participant) => (
                    <option key={participant.id} value={participant.ref_id}>
                      {participant.display_name} [{participant.status}]
                    </option>
                  ))}
                </optgroup>
              )}
              {defeatedTargets.length > 0 && (
                <optgroup label="Mortos / derrotados">
                  {defeatedTargets.map((participant) => (
                    <option key={participant.id} value={participant.ref_id} disabled>
                      {participant.display_name} [{participant.status}]
                    </option>
                  ))}
                </optgroup>
              )}
            </select>
          </div>
          <p className="mb-4 text-xs text-slate-400">
            Alvos vivos aparecem primeiro. Mortos/derrotados continuam visíveis, mas ficam bloqueados.
          </p>

          <div className="mb-4 flex font-mono text-xs font-bold">
            <button
              onClick={() => setActiveTab("attack")}
              className={`flex-1 rounded-l border p-2 ${
                activeTab === "attack"
                  ? "border-amber-500 bg-amber-600 text-white"
                  : "border-slate-700 bg-slate-800 text-slate-400"
              }`}
            >
              ATTACK
            </button>
            <button
              onClick={() => setActiveTab("cast")}
              className={`flex-1 rounded-r border-b border-r border-t p-2 ${
                activeTab === "cast"
                  ? "border-fuchsia-500 bg-fuchsia-600 text-white"
                  : "border-slate-700 bg-slate-800 text-slate-400"
              }`}
            >
              CAST SPELL
            </button>
          </div>

          {activeTab === "attack" && (
            <div className="space-y-3">
              <div className="rounded border border-amber-500/20 bg-amber-500/10 p-3">
                <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-amber-200">
                  Ataque atual
                </p>
                <p className="mt-2 text-base font-semibold text-white">
                  {currentWeapon?.name ?? "Ataque desarmado"}
                </p>
                <p className="mt-1 text-xs text-slate-300">
                  Bônus de ataque: {currentWeapon ? `${currentWeapon.attackBonus >= 0 ? "+" : ""}${currentWeapon.attackBonus}` : "FOR + proficiência"}
                </p>
                <p className="mt-1 text-xs text-slate-400">
                  Dano: {currentWeapon?.damageLabel ?? "1 + modificador de Força"}
                </p>
              </div>

              <button
                disabled={loading || !targetId}
                onClick={onAttack}
                className="w-full rounded bg-rose-600 px-4 py-3 font-bold text-white hover:bg-rose-500 disabled:opacity-50"
              >
                Rolar ataque
              </button>
            </div>
          )}

          {activeTab === "cast" && (
            <div className="space-y-3">
              <select
                className="w-full rounded border border-slate-700 bg-slate-900 p-2 text-white"
                value={selectedSpellId}
                onChange={(e) => setSelectedSpellId(e.target.value)}
              >
                <option value="">Select Spell...</option>
                {spellOptions.map((spell) => (
                  <option key={spell.id} value={spell.id}>
                    {spell.name} {spell.level > 0 ? `(Lv ${spell.level})` : "(Cantrip)"}
                  </option>
                ))}
              </select>

              {selectedSpell ? (
                <div className="rounded border border-fuchsia-500/20 bg-fuchsia-500/10 p-3">
                  <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-fuchsia-200">
                    Magia atual
                  </p>
                  <p className="mt-2 text-base font-semibold text-white">{selectedSpell.name}</p>
                  <p className="mt-1 text-xs text-slate-300">
                    Sugestao do catalogo: {selectedSpell.suggestedMode?.replaceAll("_", " ") ?? "nenhuma"}
                  </p>
                  <p className="mt-1 text-xs text-slate-400">
                    Tipo de dano: {selectedSpell.damageType ?? "nao estruturado"} · Save: {selectedSpell.savingThrow ?? "nao estruturado"}
                  </p>
                </div>
              ) : null}

              <select
                className="w-full rounded border border-slate-700 bg-slate-900 p-2 text-white"
                value={spellMode}
                onChange={(e) => setSpellMode(e.target.value as CombatSpellMode)}
              >
                <option value="spell_attack">Spell Attack</option>
                <option value="saving_throw">Saving Throw</option>
                <option value="direct_damage">Direct Damage (override)</option>
                <option value="heal">Direct Heal</option>
              </select>

              {spellMode === "direct_damage" ? (
                <p className="text-[11px] text-amber-200">
                  Use apenas para magias desta fase que causam dano direto sem attack roll nem saving throw.
                </p>
              ) : null}

              <input
                type="text"
                value={spellEffectDice}
                onChange={(e) => setSpellEffectDice(e.target.value)}
                placeholder={spellMode === "heal" ? "Heal Dice (ex: 1d4)" : "Damage Dice (ex: 2d6)"}
                className="w-full rounded border border-slate-700 bg-slate-900 p-2 font-mono text-white"
              />

              <input
                type="number"
                value={spellEffectBonus}
                onChange={(e) => setSpellEffectBonus(e.target.value)}
                placeholder="Bonus"
                className="w-full rounded border border-slate-700 bg-slate-900 p-2 font-mono text-white"
              />

              {spellMode !== "heal" ? (
                <select
                  value={spellDamageType}
                  onChange={(e) => setSpellDamageType(e.target.value)}
                  className="w-full rounded border border-slate-700 bg-slate-900 p-2 text-white"
                >
                  <option value="">Damage Type...</option>
                  {DAMAGE_TYPE_OPTIONS.map((damageType) => (
                    <option key={damageType} value={damageType}>
                      {damageType}
                    </option>
                  ))}
                </select>
              ) : null}

              {spellMode === "saving_throw" ? (
                <select
                  value={spellSaveAbility}
                  onChange={(e) => setSpellSaveAbility(e.target.value as AbilityName | "")}
                  className="w-full rounded border border-slate-700 bg-slate-900 p-2 text-white"
                >
                  <option value="">Save Ability...</option>
                  <option value="strength">Strength</option>
                  <option value="dexterity">Dexterity</option>
                  <option value="constitution">Constitution</option>
                  <option value="intelligence">Intelligence</option>
                  <option value="wisdom">Wisdom</option>
                  <option value="charisma">Charisma</option>
                </select>
              ) : null}

              <button
                disabled={loading || !canSubmitSpell}
                onClick={onCast}
                className="w-full rounded bg-fuchsia-600 px-4 py-3 font-bold text-white hover:bg-fuchsia-500 disabled:opacity-50"
              >
                Cast Spell
              </button>
            </div>
          )}

          <button
            disabled={loading}
            onClick={onEndTurn}
            className="mt-4 w-full rounded border border-sky-500/50 bg-transparent px-4 py-3 font-bold text-sky-400 hover:bg-sky-500/10 disabled:opacity-50"
          >
            End Turn
          </button>
        </>
      ) : (
        <div className="rounded border border-slate-700 bg-slate-800 p-4 text-center text-slate-400">
          You cannot act right now due to your status: {myParticipant.status}.
        </div>
      )}
    </div>
  );
};
