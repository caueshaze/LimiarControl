import type {
  AbilityRollRequest,
  AttackBaseRollRequest,
  InitiativeRollRequest,
  RollResult,
  SaveRollRequest,
  SkillRollRequest,
} from "../../entities/roll/rollResolution.types";
import { http } from "./http";

export const rollsRepo = {
  ability: (sessionId: string, body: AbilityRollRequest) =>
    http.post<RollResult>(`/sessions/${sessionId}/rolls/ability`, body),

  save: (sessionId: string, body: SaveRollRequest) =>
    http.post<RollResult>(`/sessions/${sessionId}/rolls/save`, body),

  skill: (sessionId: string, body: SkillRollRequest) =>
    http.post<RollResult>(`/sessions/${sessionId}/rolls/skill`, body),

  initiative: (sessionId: string, body: InitiativeRollRequest) =>
    http.post<RollResult>(`/sessions/${sessionId}/rolls/initiative`, body),

  attackBase: (sessionId: string, body: AttackBaseRollRequest) =>
    http.post<RollResult>(`/sessions/${sessionId}/rolls/attack-base`, body),
};
