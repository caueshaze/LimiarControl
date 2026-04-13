import { useCallback, useState } from "react";
import type {
  AbilityName,
  AdvantageMode,
  RollResult,
  RollType,
  SkillName,
} from "../../../entities/roll/rollResolution.types";
import { rollsRepo } from "../../../shared/api/rollsRepo";
import { markRollEventKnown } from "../knownRollEvents";

export type AuthoritativeRollParams = {
  rollType: RollType;
  ability?: AbilityName;
  skill?: SkillName;
  advantageMode: AdvantageMode;
  dc?: number | null;
  targetAc?: number | null;
  bonusOverride?: number | null;
  rollSource: "system" | "manual";
  manualRoll?: number | null;
  manualRolls?: [number, number] | null;
};

export const useRollResolution = (
  sessionId: string | null,
  actorKind: "player" | "session_entity",
  actorRefId: string,
) => {
  const [result, setResult] = useState<RollResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submitRoll = useCallback(
    async (params: AuthoritativeRollParams) => {
      if (!sessionId) return null;

      setLoading(true);
      setError(null);
      setResult(null);

      try {
        const base = {
          actor_kind: actorKind,
          actor_ref_id: actorRefId,
          advantage_mode: params.advantageMode,
          bonus_override: params.bonusOverride ?? undefined,
          roll_source: params.rollSource,
          manual_roll: params.manualRoll ?? undefined,
          manual_rolls: params.manualRolls ?? undefined,
        };

        let res: RollResult;

        switch (params.rollType) {
          case "ability":
            res = await rollsRepo.ability(sessionId, {
              ...base,
              ability: params.ability!,
              dc: params.dc ?? undefined,
            });
            break;
          case "save":
            res = await rollsRepo.save(sessionId, {
              ...base,
              ability: params.ability!,
              dc: params.dc ?? undefined,
            });
            break;
          case "skill":
            res = await rollsRepo.skill(sessionId, {
              ...base,
              skill: params.skill!,
              dc: params.dc ?? undefined,
            });
            break;
          case "initiative":
            res = await rollsRepo.initiative(sessionId, base);
            break;
          case "attack":
            res = await rollsRepo.attackBase(sessionId, {
              ...base,
              target_ac: params.targetAc ?? undefined,
            });
            break;
          default:
            throw new Error(`Unknown roll type: ${params.rollType}`);
        }

        markRollEventKnown(res.event_id);
        setResult(res);
        return res;
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Roll failed";
        setError(msg);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [actorKind, actorRefId, sessionId],
  );

  const clearResult = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return { result, loading, error, submitRoll, clearResult };
};
