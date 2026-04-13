import { test, expect } from "@playwright/test";
import { Centrifuge, type Subscription } from "centrifuge";

const SERVER_URL = "http://localhost:3000";
const CENTRIFUGO_URL = "ws://localhost:8001/connection/websocket";

async function connect(actorId: string): Promise<{
  client: Centrifuge;
  subscription: Subscription;
}> {
  const tokenResponse = await fetch(`${SERVER_URL}/centrifugo/connection-token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ actorId, actorType: "player" })
  });
  const tokenPayload = (await tokenResponse.json()) as { token: string };
  const client = new Centrifuge(CENTRIFUGO_URL, { token: tokenPayload.token });
  const subscription = client.newSubscription("session:demo-session", {
    recoverable: true,
  });

  client.connect();
  subscription.subscribe();

  await new Promise<void>((resolve) => client.on("connected", () => resolve()));
  return { client, subscription };
}

function waitFor(subscription: Subscription, eventType: string): Promise<unknown> {
  return new Promise((resolve) =>
    subscription.on("publication", (ctx) => {
      const payload = ctx.data as { eventType?: string };
      if (payload.eventType === eventType) {
        resolve(payload);
      }
    })
  );
}

test.describe("movement sync", () => {
  test("valid movement is applied and both clients receive the authoritative event", async () => {
    const mover = await connect("player_1");
    const observer = await connect("player_2");

    const moverEvent = waitFor(mover.subscription, "movement.applied");
    const observerEvent = waitFor(observer.subscription, "movement.applied");

    // tok_player starts at (4,4), cmb_1 is active — move one step right (cost: 5)
    await fetch(`${SERVER_URL}/sessions/demo-session/actions/movement`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Limiar-Actor-Id": "player_1",
        "X-Limiar-Actor-Type": "player"
      },
      body: JSON.stringify({
      actionId: "action-e2e-01",
      sessionId: "demo-session",
      tokenId: "tok_player",
      path: [{ x: 5, y: 4 }],
      knownVersion: 1
      })
    });

    const [moverPayload, observerPayload] = (await Promise.all([moverEvent, observerEvent])) as Array<{
      payload: { tokenId: string; position: { x: number; y: number }; remainingBudget: number };
    }>;

    expect(moverPayload.payload.tokenId).toBe("tok_player");
    expect(moverPayload.payload.position).toEqual({ x: 5, y: 4 });
    expect(moverPayload.payload.remainingBudget).toBe(25); // 30 - 5

    expect(observerPayload.payload.position).toEqual({ x: 5, y: 4 });
    expect(observerPayload.payload.remainingBudget).toBe(25);

    mover.subscription.unsubscribe();
    mover.client.disconnect();
    observer.subscription.unsubscribe();
    observer.client.disconnect();
  });
});
