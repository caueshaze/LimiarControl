import { HttpClient } from "./http-client";
import { sessionStore } from "./session-store";

export async function recoverRealtimeState(sessionId: string, knownVersion: number): Promise<void> {
  const httpClient = new HttpClient();
  await httpClient.requestResync(sessionId, {
    lastKnownVersion: knownVersion,
    clientInstanceId: "web-client"
  });
  const snapshot = await httpClient.fetchEncounter(sessionId);
  sessionStore.setSnapshot(snapshot);
}
