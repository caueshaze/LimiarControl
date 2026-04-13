import { Centrifuge, type Subscription } from "centrifuge";
import { useSyncExternalStore } from "react";
import { handleRealtimePublication } from "./realtime-events";
import { resolveCentrifugoUrl } from "./resolve-centrifugo-url";

type MapActorType = "player" | "gm";

type MapActor = {
  actorId: string;
  actorType: MapActorType;
};

type Listener = () => void;

const DEFAULT_ACTOR: MapActor = {
  actorId: "player_1",
  actorType: "player",
};

const CENTRIFUGO_URL = resolveCentrifugoUrl(import.meta.env.VITE_CENTRIFUGO_URL);

let currentActor: MapActor = DEFAULT_ACTOR;
let client: Centrifuge | null = null;
let subscription: Subscription | null = null;
let connectedSessionId: string | null = null;
const actorListeners = new Set<Listener>();

function emitActorChange(): void {
  actorListeners.forEach((listener) => listener());
}

async function fetchConnectionToken(): Promise<string> {
  const response = await fetch("/centrifugo/connection-token", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(currentActor),
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch realtime connection token: ${response.status}`);
  }

  const data = (await response.json()) as { token?: string };
  if (!data.token) {
    throw new Error("Realtime connection token response was missing a token");
  }
  return data.token;
}

function buildClient(): Centrifuge {
  const nextClient = new Centrifuge(CENTRIFUGO_URL, {
    debug: import.meta.env.DEV,
    getToken: () => fetchConnectionToken(),
  });
  nextClient.on("connected", () => {
    if (import.meta.env.DEV) {
      console.info("[map-web] centrifugo connected");
    }
  });
  nextClient.on("disconnected", (ctx) => {
    if (import.meta.env.DEV) {
      console.warn("[map-web] centrifugo disconnected", ctx);
    }
  });
  nextClient.on("error", (ctx) => {
    console.error("[map-web] centrifugo error", ctx);
  });
  return nextClient;
}

function ensureClient(): Centrifuge {
  if (!client) {
    client = buildClient();
  }
  return client;
}

function cleanupSubscription(): void {
  if (!subscription) {
    return;
  }
  subscription.unsubscribe();
  subscription.removeAllListeners();
  client?.removeSubscription(subscription);
  subscription = null;
}

function connectSessionInternal(sessionId: string): void {
  const realtimeClient = ensureClient();
  cleanupSubscription();

  const channel = `session:${sessionId}`;
  const nextSubscription = realtimeClient.newSubscription(channel, {
    recoverable: true,
  });
  nextSubscription.on("publication", (ctx) => {
    handleRealtimePublication(ctx.data);
  });
  nextSubscription.on("subscribed", (ctx) => {
    if (import.meta.env.DEV) {
      console.info("[map-web] subscribed", channel, ctx);
    }
  });
  nextSubscription.on("error", (ctx) => {
    console.error("[map-web] subscription error", channel, ctx);
  });

  subscription = nextSubscription;
  connectedSessionId = sessionId;
  realtimeClient.connect();
  nextSubscription.subscribe();
}

export function connectSessionRealtime(sessionId: string): () => void {
  connectSessionInternal(sessionId);
  return () => {
    if (connectedSessionId !== sessionId) {
      return;
    }
    disconnectRealtime();
  };
}

export function disconnectRealtime(clearSession = true): void {
  cleanupSubscription();
  if (client) {
    client.disconnect();
    client = null;
  }
  if (clearSession) {
    connectedSessionId = null;
  }
}

export function reconnectAs(actorId: string, actorType: MapActorType): void {
  if (currentActor.actorId === actorId && currentActor.actorType === actorType) {
    return;
  }
  currentActor = { actorId, actorType };
  emitActorChange();
  const sessionId = connectedSessionId;
  disconnectRealtime(false);
  if (sessionId) {
    connectSessionInternal(sessionId);
  }
}

export function getCurrentActor(): MapActor {
  return currentActor;
}

export function subscribeToCurrentActor(listener: Listener): () => void {
  actorListeners.add(listener);
  return () => actorListeners.delete(listener);
}

export function useCurrentActor(): MapActor {
  return useSyncExternalStore(subscribeToCurrentActor, getCurrentActor, getCurrentActor);
}
