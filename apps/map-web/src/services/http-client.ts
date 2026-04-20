import type {
  CombatAdvanceRequest,
  Coordinate,
  EncounterSnapshotResponse,
  GridCalibrationRequest,
  MovementRequest,
  ResyncRequest,
  ResyncResponse,
  TargetingSubmitRequest,
  ObstaclePaintRequest,
  EdgeObstaclePaintRequest
} from "@limiarmap/shared-contracts";
import type { TacticalDiagnostics } from "../features/battle-map/battle-map-store";

// ─── Combat preview types ─────────────────────────────────────────────────────

export interface CombatPreviewRequest {
  source_ref_id: string;
  action_type: "move" | "attack" | "spell";
  target_ref_id?: string;
  source_position?: { x: number; y: number };
  target_position?: { x: number; y: number };
  reach_cells?: number;
  /** AoE fields — only for spell actions with area targeting. */
  aoe_shape?: "sphere" | "cone" | "line";
  /** Size in grid cells, resolved by the frontend from the spell catalog (meters → cells). */
  aoe_size_cells?: number;
}

export interface CombatPreviewResponse {
  diagnostics: TacticalDiagnostics | null;
  effectiveReachCells: number;
  /**
   * AoE footprint from LimiarMap /targeting/area/preview — the read-only
   * variant of the same spatial engine used for the final cast.
   * Empty when no AoE fields were sent or LimiarMap is unavailable.
   */
  aoeCells: { x: number; y: number }[];
}
import { getCurrentActor } from "./centrifugo-client";

export class HttpClient {
  constructor(private readonly baseUrl = "") {}

  private async buildRequestError(
    response: Response
  ): Promise<Error & { status: number }> {
    let message = `Request failed: ${response.status} ${response.statusText}`;
    try {
      const data = (await response.json()) as { message?: string };
      if (typeof data.message === "string" && data.message.trim()) {
        message = data.message;
      }
    } catch {
      // ignore malformed error payloads
    }

    const error = new Error(message) as Error & { status: number };
    error.status = response.status;
    return error;
  }

  private buildActorHeaders(): HeadersInit {
    const actor = getCurrentActor();
    return {
      "Content-Type": "application/json",
      "X-Limiar-Actor-Id": actor.actorId,
      "X-Limiar-Actor-Type": actor.actorType
    };
  }

  private async postJson<TResponse>(
    path: string,
    payload: unknown,
    withActorHeaders = false
  ): Promise<TResponse> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: withActorHeaders
        ? this.buildActorHeaders()
        : { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      throw new Error(
        `Request failed: ${response.status} ${response.statusText}`
      );
    }

    return response.json() as Promise<TResponse>;
  }

  async fetchEncounter(sessionId: string): Promise<EncounterSnapshotResponse> {
    const response = await fetch(
      `${this.baseUrl}/sessions/${sessionId}/encounter`
    );
    if (!response.ok) {
      throw await this.buildRequestError(response);
    }
    return response.json() as Promise<EncounterSnapshotResponse>;
  }

  async requestResync(
    sessionId: string,
    payload: ResyncRequest
  ): Promise<ResyncResponse> {
    return this.postJson<ResyncResponse>(
      `/sessions/${sessionId}/resync`,
      payload
    );
  }

  async fetchConnectionToken(): Promise<{ token: string }> {
    return this.postJson<{ token: string }>(
      "/centrifugo/connection-token",
      getCurrentActor()
    );
  }

  async submitMovement(
    sessionId: string,
    payload: MovementRequest
  ): Promise<EncounterSnapshotResponse> {
    return this.postJson<EncounterSnapshotResponse>(
      `/sessions/${sessionId}/actions/movement`,
      payload,
      true
    );
  }

  async submitPlacement(
    sessionId: string,
    payload: { actionId: string; tokenId: string; position: Coordinate }
  ): Promise<EncounterSnapshotResponse> {
    return this.postJson<EncounterSnapshotResponse>(
      `/sessions/${sessionId}/actions/place-token`,
      payload,
      true
    );
  }

  async advanceCombat(
    sessionId: string,
    payload: CombatAdvanceRequest
  ): Promise<EncounterSnapshotResponse> {
    return this.postJson<EncounterSnapshotResponse>(
      `/sessions/${sessionId}/actions/combat/advance`,
      payload,
      true
    );
  }

  async submitTargeting(
    sessionId: string,
    payload: TargetingSubmitRequest
  ): Promise<EncounterSnapshotResponse> {
    return this.postJson<EncounterSnapshotResponse>(
      `/sessions/${sessionId}/actions/targeting`,
      payload,
      true
    );
  }

  async submitGridCalibration(
    sessionId: string,
    payload: GridCalibrationRequest
  ): Promise<EncounterSnapshotResponse> {
    return this.postJson<EncounterSnapshotResponse>(
      `/sessions/${sessionId}/actions/grid-calibration`,
      payload,
      true
    );
  }

  async submitObstaclePaint(
    sessionId: string,
    payload: ObstaclePaintRequest
  ): Promise<EncounterSnapshotResponse> {
    return this.postJson<EncounterSnapshotResponse>(
      `/sessions/${sessionId}/actions/obstacles`,
      payload,
      true
    );
  }

  async fetchCombatPreview(
    sessionId: string,
    payload: CombatPreviewRequest
  ): Promise<CombatPreviewResponse> {
    return this.postJson<CombatPreviewResponse>(
      `/sessions/${sessionId}/combat/preview`,
      payload,
      true
    );
  }

  async submitEdgeObstaclePaint(
    sessionId: string,
    payload: EdgeObstaclePaintRequest
  ): Promise<EncounterSnapshotResponse> {
    return this.postJson<EncounterSnapshotResponse>(
      `/sessions/${sessionId}/actions/edge-obstacles`,
      payload,
      true
    );
  }
}
