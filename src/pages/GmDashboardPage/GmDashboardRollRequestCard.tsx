import type { PartyMemberSummary } from "../../shared/api/partiesRepo";
import type { CommandFeedback } from "./gmDashboard.types";
import { useLocale } from "../../shared/hooks/useLocale";

type Props = {
  combatUiActive: boolean;
  commandFeedback: CommandFeedback | null;
  commandSending: boolean;
  partyPlayers: PartyMemberSummary[];
  rollAbility: string | null;
  rollAdvantage: "normal" | "advantage" | "disadvantage";
  rollDc: string;
  rollExpression: string;
  rollOptions: string[];
  rollReason: string;
  rollSkill: string | null;
  rollTargetUserId: string | null;
  rollType: string | null;
  onCommand: (
    type:
      | "open_shop"
      | "close_shop"
      | "request_roll"
      | "start_combat"
      | "end_combat"
      | "start_short_rest"
      | "start_long_rest"
      | "end_rest",
    payload?: Record<string, unknown>,
  ) => void;
  setRollAbility: (value: string | null) => void;
  setRollAdvantage: (value: "normal" | "advantage" | "disadvantage") => void;
  setRollDc: (value: string) => void;
  setRollExpression: (value: string) => void;
  setRollReason: (value: string) => void;
  setRollSkill: (value: string | null) => void;
  setRollTargetUserId: (value: string | null) => void;
  setRollType: (value: string | null) => void;
};

export const GmDashboardRollRequestCard = ({
  combatUiActive,
  commandFeedback,
  commandSending,
  partyPlayers,
  rollAbility,
  rollAdvantage,
  rollDc,
  rollExpression,
  rollOptions,
  rollReason,
  rollSkill,
  rollTargetUserId,
  rollType,
  onCommand,
  setRollAbility,
  setRollAdvantage,
  setRollDc,
  setRollExpression,
  setRollReason,
  setRollSkill,
  setRollTargetUserId,
  setRollType,
}: Props) => {
  const { t } = useLocale();

  return (
    <div className="rounded-2xl border border-slate-800 bg-linear-to-br from-slate-950/60 to-slate-900/40 p-4">
      <div>
        <label className="text-[10px] font-semibold uppercase tracking-[0.35em] text-slate-500">
          {t("gm.dashboard.diceRequest")}
        </label>
        <p className="mt-1 text-xs text-slate-400">{t("gm.dashboard.diceRequestDescription")}</p>
      </div>
      <div className="mt-4 space-y-3">
        {/* Roll type selector */}
        <select
          value={rollType ?? ""}
          onChange={(event) => {
            const val = event.target.value || null;
            setRollType(val);
            setRollAbility(null);
            setRollSkill(null);
            if (val) setRollExpression("d20");
          }}
          className="w-full rounded-2xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-limiar-500 focus:outline-none"
        >
          <option value="">{t("gm.dashboard.freeRollLegacy")}</option>
          <option value="ability">{t("rolls.abilityCheck")}</option>
          <option value="save">{t("rolls.savingThrow")}</option>
          <option value="skill">{t("rolls.skillCheck")}</option>
          {combatUiActive && (
            <>
              <option value="initiative">{t("rolls.initiative")}</option>
              <option value="attack">{t("rolls.attackRoll")}</option>
            </>
          )}
        </select>

        {/* Ability/skill selector when roll type requires it */}
        {(rollType === "ability" || rollType === "save") && (
          <select
            value={rollAbility ?? ""}
            onChange={(event) => setRollAbility(event.target.value || null)}
            className="w-full rounded-2xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-limiar-500 focus:outline-none"
          >
            <option value="">{t("gm.dashboard.selectAbility")}</option>
            <option value="strength">{t("rolls.ability.strength")}</option>
            <option value="dexterity">{t("rolls.ability.dexterity")}</option>
            <option value="constitution">{t("rolls.ability.constitution")}</option>
            <option value="intelligence">{t("rolls.ability.intelligence")}</option>
            <option value="wisdom">{t("rolls.ability.wisdom")}</option>
            <option value="charisma">{t("rolls.ability.charisma")}</option>
          </select>
        )}
        {rollType === "skill" && (
          <select
            value={rollSkill ?? ""}
            onChange={(event) => setRollSkill(event.target.value || null)}
            className="w-full rounded-2xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-limiar-500 focus:outline-none"
          >
            <option value="">{t("gm.dashboard.selectSkill")}</option>
            <option value="acrobatics">{t("rolls.skill.acrobatics")}</option>
            <option value="animalHandling">{t("rolls.skill.animalHandling")}</option>
            <option value="arcana">{t("rolls.skill.arcana")}</option>
            <option value="athletics">{t("rolls.skill.athletics")}</option>
            <option value="deception">{t("rolls.skill.deception")}</option>
            <option value="history">{t("rolls.skill.history")}</option>
            <option value="insight">{t("rolls.skill.insight")}</option>
            <option value="intimidation">{t("rolls.skill.intimidation")}</option>
            <option value="investigation">{t("rolls.skill.investigation")}</option>
            <option value="medicine">{t("rolls.skill.medicine")}</option>
            <option value="nature">{t("rolls.skill.nature")}</option>
            <option value="perception">{t("rolls.skill.perception")}</option>
            <option value="performance">{t("rolls.skill.performance")}</option>
            <option value="persuasion">{t("rolls.skill.persuasion")}</option>
            <option value="religion">{t("rolls.skill.religion")}</option>
            <option value="sleightOfHand">{t("rolls.skill.sleightOfHand")}</option>
            <option value="stealth">{t("rolls.skill.stealth")}</option>
            <option value="survival">{t("rolls.skill.survival")}</option>
          </select>
        )}

        {/* DC input for authoritative rolls */}
        {rollType && rollType !== "initiative" && (
          <input
            type="number"
            min={1}
            value={rollDc}
            onChange={(event) => setRollDc(event.target.value)}
            placeholder={t("gm.dashboard.dcPlaceholder")}
            className="w-full rounded-2xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white placeholder:text-slate-600 focus:border-limiar-500 focus:outline-none"
          />
        )}

        {/* Die selector (only for legacy/free rolls) */}
        {!rollType && (
          <select
            value={rollExpression}
            onChange={(event) => setRollExpression(event.target.value)}
            className="w-full rounded-2xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-white focus:border-limiar-500 focus:outline-none"
          >
            {rollOptions.map((option) => (
              <option key={option} value={option} className="text-slate-900">
                {option.toUpperCase()}
              </option>
            ))}
          </select>
        )}

        {/* Target player */}
        <select
          value={rollTargetUserId ?? ""}
          onChange={(event) => setRollTargetUserId(event.target.value || null)}
          className="w-full rounded-2xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white focus:border-limiar-500 focus:outline-none"
        >
          <option value="">{t("gm.dashboard.allPlayers")}</option>
          {partyPlayers.map((player) => (
            <option key={player.userId} value={player.userId}>
              {player.displayName || player.username || "Player"}
            </option>
          ))}
        </select>

        <input
          type="text"
          value={rollReason}
          onChange={(event) => setRollReason(event.target.value)}
          placeholder={t("gm.dashboard.reasonPlaceholder")}
          className="w-full rounded-2xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white placeholder:text-slate-600 focus:border-limiar-500 focus:outline-none"
        />
        <div className="flex overflow-hidden rounded-2xl border border-slate-700 text-[10px] font-bold uppercase tracking-widest">
          {(["normal", "advantage", "disadvantage"] as const).map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => setRollAdvantage(option)}
              className={`flex-1 py-2 transition-colors ${
                rollAdvantage === option
                  ? option === "advantage"
                    ? "bg-emerald-500/20 text-emerald-400"
                    : option === "disadvantage"
                    ? "bg-red-500/20 text-red-400"
                    : "bg-slate-700 text-white"
                  : "bg-slate-900 text-slate-500 hover:bg-slate-800"
              }`}
            >
              {option === "normal"
                ? t("gm.dashboard.advantageNormal")
                : option === "advantage"
                ? t("gm.dashboard.advantageAdv")
                : t("gm.dashboard.advantageDisadv")}
            </button>
          ))}
        </div>
        <button
          onClick={() => onCommand("request_roll", { expression: rollExpression })}
          disabled={
            commandSending ||
            (rollType === "ability" && !rollAbility) ||
            (rollType === "save" && !rollAbility) ||
            (rollType === "skill" && !rollSkill)
          }
          className="w-full rounded-2xl bg-slate-800 px-4 py-2 text-xs font-semibold uppercase tracking-[0.25em] text-slate-200 hover:bg-slate-700 disabled:opacity-50"
        >
          {t("gm.dashboard.requestRollTo")}
          {rollTargetUserId
            ? ` → ${partyPlayers.find((player) => player.userId === rollTargetUserId)?.displayName ?? ""}`
            : ""}
        </button>
        {commandFeedback?.type === "request_roll" && (
          <div
            className={`rounded-2xl border px-3 py-2 text-[11px] ${
              commandFeedback.tone === "success"
                ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-300"
                : "border-rose-500/20 bg-rose-500/10 text-rose-200"
            }`}
          >
            {commandFeedback.message}
          </div>
        )}
      </div>
    </div>
  );
};
