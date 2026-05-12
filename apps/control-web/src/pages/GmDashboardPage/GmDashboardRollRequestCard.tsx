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

  const selectCls = "w-full rounded-xl border border-white/10 bg-slate-900/80 px-3 py-2 text-xs text-white focus:border-limiar-500 focus:outline-none";

  return (
    <div className="rounded-[28px] border border-white/8 bg-white/[0.04] p-5 backdrop-blur-xl">
      <div className="mb-4">
        <label className="text-[10px] font-semibold uppercase tracking-[0.35em] text-slate-400">
          {t("gm.dashboard.diceRequest")}
        </label>
        <p className="mt-1 text-xs text-slate-500">{t("gm.dashboard.diceRequestDescription")}</p>
      </div>

      {/* Two-column grid for form when wide enough */}
      <div className="grid gap-2.5 sm:grid-cols-2">
        {/* Roll type */}
        <select
          value={rollType ?? ""}
          onChange={(e) => {
            const val = e.target.value || null;
            setRollType(val);
            setRollAbility(null);
            setRollSkill(null);
            if (val) setRollExpression("d20");
          }}
          className={selectCls}
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

        {/* Target player */}
        <select
          value={rollTargetUserId ?? ""}
          onChange={(e) => setRollTargetUserId(e.target.value || null)}
          className={selectCls}
        >
          <option value="">{t("gm.dashboard.allPlayers")}</option>
          {partyPlayers.map((player) => (
            <option key={player.userId} value={player.userId}>
              {player.displayName || player.username || t("gm.dashboard.playerLabel")}
            </option>
          ))}
        </select>

        {/* Ability selector */}
        {(rollType === "ability" || rollType === "save") && (
          <select
            value={rollAbility ?? ""}
            onChange={(e) => setRollAbility(e.target.value || null)}
            className={selectCls}
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

        {/* Skill selector */}
        {rollType === "skill" && (
          <select
            value={rollSkill ?? ""}
            onChange={(e) => setRollSkill(e.target.value || null)}
            className={selectCls}
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

        {/* DC input */}
        {rollType && rollType !== "initiative" && (
          <input
            type="number"
            min={1}
            value={rollDc}
            onChange={(e) => setRollDc(e.target.value)}
            placeholder={t("gm.dashboard.dcPlaceholder")}
            className="w-full rounded-xl border border-white/10 bg-slate-900/80 px-3 py-2 text-xs text-white placeholder:text-slate-600 focus:border-limiar-500 focus:outline-none"
          />
        )}

        {/* Die selector (free roll) */}
        {!rollType && (
          <select
            value={rollExpression}
            onChange={(e) => setRollExpression(e.target.value)}
            className="w-full rounded-xl border border-white/10 bg-slate-900/80 px-3 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-white focus:border-limiar-500 focus:outline-none"
          >
            {rollOptions.map((option) => (
              <option key={option} value={option} className="text-slate-900">
                {option.toUpperCase()}
              </option>
            ))}
          </select>
        )}

        {/* Reason */}
        <input
          type="text"
          value={rollReason}
          onChange={(e) => setRollReason(e.target.value)}
          placeholder={t("gm.dashboard.reasonPlaceholder")}
          className="w-full rounded-xl border border-white/10 bg-slate-900/80 px-3 py-2 text-xs text-white placeholder:text-slate-600 focus:border-limiar-500 focus:outline-none sm:col-span-2"
        />
      </div>

      {/* Advantage toggle */}
      <div className="mt-3 flex overflow-hidden rounded-xl border border-white/10 text-[10px] font-bold uppercase tracking-widest">
        {(["normal", "advantage", "disadvantage"] as const).map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => setRollAdvantage(option)}
            className={`flex-1 py-2 transition-all ${
              rollAdvantage === option
                ? option === "advantage"
                  ? "bg-emerald-500/20 text-emerald-400"
                  : option === "disadvantage"
                  ? "bg-rose-500/20 text-rose-400"
                  : "bg-white/10 text-white"
                : "text-slate-500 hover:bg-white/5 hover:text-slate-400"
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

      {/* Submit */}
      <button
        onClick={() => onCommand("request_roll", { expression: rollExpression })}
        disabled={
          commandSending ||
          (rollType === "ability" && !rollAbility) ||
          (rollType === "save" && !rollAbility) ||
          (rollType === "skill" && !rollSkill)
        }
        className="mt-3 w-full rounded-xl border border-white/10 bg-white/6 px-4 py-2.5 text-xs font-semibold uppercase tracking-[0.22em] text-slate-200 transition-all hover:border-white/20 hover:bg-white/10 active:scale-[0.98] disabled:opacity-50"
      >
        {t("gm.dashboard.requestRollTo")}
        {rollTargetUserId
          ? ` → ${partyPlayers.find((p) => p.userId === rollTargetUserId)?.displayName ?? ""}`
          : ""}
      </button>

      {commandFeedback?.type === "request_roll" && (
        <p className={`mt-2 text-[11px] ${commandFeedback.tone === "success" ? "text-emerald-400" : "text-rose-400"}`}>
          {commandFeedback.message}
        </p>
      )}
    </div>
  );
};
