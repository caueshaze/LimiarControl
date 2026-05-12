import {
  Centrifuge,
  SubscriptionState,
  UnauthorizedError,
  type ClientInfo,
  type ConnectionTokenContext,
  type JoinContext,
  type LeaveContext,
  type PublicationContext,
  type SubscribedContext,
  type Subscription,
  type SubscriptionErrorContext,
  type SubscriptionTokenContext,
  type SubscribingContext,
  type UnsubscribedContext,
} from "centrifuge";
import { env } from "../../app/config";
import { centrifugoRepo } from "../api/centrifugoRepo";
import { getToken } from "../auth/tokenStore";

export type ConnectionState = "connected" | "reconnecting" | "offline";

export type RealtimePresenceMember = {
  clientId: string;
  displayName: string;
  info: ClientInfo;
  userId: string;
};

export type RealtimeHistoryPublication = {
  data: unknown;
  offset?: string;
};

type SubscriptionHandlers = {
  onError?: (ctx: SubscriptionErrorContext) => void;
  onJoin?: (member: RealtimePresenceMember, ctx: JoinContext) => void;
  onLeave?: (member: RealtimePresenceMember, ctx: LeaveContext) => void;
  onPublication?: (data: unknown, ctx: PublicationContext) => void;
  onSubscribed?: (ctx: SubscribedContext) => void;
  onSubscribing?: (ctx: SubscribingContext) => void;
  onUnsubscribed?: (ctx: UnsubscribedContext) => void;
};

type ChannelEntry = {
  listeners: Map<number, SubscriptionHandlers>;
  subscription: Subscription;
};

type ConnectionStateListener = (state: ConnectionState) => void;

const channelEntries = new Map<string, ChannelEntry>();
const connectionStateListeners = new Set<ConnectionStateListener>();

let client: Centrifuge | null = null;
let currentConnectionState: ConnectionState = "offline";
let nextListenerId = 1;
let connectionRequested = false;
let reconnectStartedAt: number | null = null;
let disconnectTimer: ReturnType<typeof setTimeout> | null = null;

const DISCONNECT_GRACE_MS = 500;

const logRealtime = (
  level: "debug" | "info" | "warn" | "error",
  message: string,
  details?: Record<string, unknown>,
) => {
  if (!import.meta.env.DEV) {
    return;
  }
  const logger = console[level];
  if (details) {
    logger(`[control-web][realtime] ${message}`, details);
    return;
  }
  logger(`[control-web][realtime] ${message}`);
};

const getReconnectDurationMs = () =>
  reconnectStartedAt === null ? null : Math.max(0, Date.now() - reconnectStartedAt);

const notifyConnectionState = (state: ConnectionState) => {
  currentConnectionState = state;
  if (state === "reconnecting" && reconnectStartedAt === null) {
    reconnectStartedAt = Date.now();
  }
  if (state === "connected") {
    reconnectStartedAt = null;
  }
  if (state === "offline") {
    connectionRequested = false;
  }
  connectionStateListeners.forEach((listener) => listener(state));
};

const clearPendingDisconnect = () => {
  if (disconnectTimer === null) {
    return;
  }
  clearTimeout(disconnectTimer);
  disconnectTimer = null;
};

const scheduleDisconnectIfIdle = () => {
  clearPendingDisconnect();
  disconnectTimer = setTimeout(() => {
    disconnectTimer = null;
    if (channelEntries.size > 0) {
      return;
    }
    connectionRequested = false;
    const realtimeClient = getClient();
    if (currentConnectionState !== "offline") {
      realtimeClient.disconnect();
    }
    notifyConnectionState("offline");
  }, DISCONNECT_GRACE_MS);
};

const getDisplayName = (info: ClientInfo) => {
  const channelDisplayName = (info.chanInfo as { displayName?: string } | undefined)?.displayName;
  if (channelDisplayName) {
    return channelDisplayName;
  }
  const connectionDisplayName = (info.connInfo as { displayName?: string } | undefined)?.displayName;
  if (connectionDisplayName) {
    return connectionDisplayName;
  }
  return info.user;
};

const toPresenceMember = (clientId: string, info: ClientInfo): RealtimePresenceMember => ({
  clientId,
  displayName: getDisplayName(info),
  info,
  userId: info.user,
});

const dispatchToChannel = <TContext>(
  channel: string,
  callback: (handlers: SubscriptionHandlers, ctx: TContext) => void,
  ctx: TContext,
) => {
  const entry = channelEntries.get(channel);
  if (!entry) {
    return;
  }
  entry.listeners.forEach((handlers) => callback(handlers, ctx));
};

export const fetchConnectionToken = async (
  _ctx?: ConnectionTokenContext,
): Promise<string> => {
  if (!getToken()) {
    logRealtime("warn", "missing auth token for connection token request");
    throw new UnauthorizedError("Missing auth token");
  }
  try {
    const response = await centrifugoRepo.connectionToken();
    return response.token;
  } catch (error) {
    const status = (error as { status?: number }).status;
    if (status === 401 || status === 403) {
      logRealtime("warn", "connection token rejected", { status });
      throw new UnauthorizedError("Connection token rejected");
    }
    logRealtime("error", "connection token request failed", {
      status,
      error,
    });
    throw error;
  }
};

export const fetchSubscriptionToken = async (channel: string): Promise<string> => {
  if (!getToken()) {
    logRealtime("warn", "missing auth token for subscription token request", { channel });
    throw new UnauthorizedError("Missing auth token");
  }
  try {
    const response = await centrifugoRepo.subscribeToken({ channel });
    return response.token;
  } catch (error) {
    const status = (error as { status?: number }).status;
    if (status === 401 || status === 403) {
      logRealtime("warn", "subscription token rejected", { channel, status });
      throw new UnauthorizedError(`Subscription rejected for ${channel}`);
    }
    logRealtime("error", "subscription token request failed", {
      channel,
      status,
      error,
    });
    throw error;
  }
};

export const getClient = () => {
  if (!client) {
    client = new Centrifuge(env.VITE_CENTRIFUGO_URL, {
      debug: import.meta.env.DEV,
      getToken: fetchConnectionToken,
    });
    client.on("connecting", (ctx) => {
      logRealtime("info", "connecting", {
        code: ctx.code,
        reason: ctx.reason,
      });
      notifyConnectionState("reconnecting");
    });
    client.on("connected", (ctx) => {
      const reconnectDurationMs = getReconnectDurationMs();
      logRealtime("info", "connected", {
        client: ctx.client,
        transport: ctx.transport,
        reconnectDurationMs,
      });
      notifyConnectionState("connected");
    });
    client.on("disconnected", (ctx) => {
      const reconnectDurationMs = getReconnectDurationMs();
      logRealtime("warn", "disconnected", {
        code: ctx.code,
        reason: ctx.reason,
        reconnectDurationMs,
      });
      notifyConnectionState("offline");
    });
  }
  return client;
};

const ensureClientConnected = () => {
  clearPendingDisconnect();
  const realtimeClient = getClient();
  if (currentConnectionState === "offline" && !connectionRequested) {
    connectionRequested = true;
    logRealtime("info", "connect requested", { channelCount: channelEntries.size });
    realtimeClient.connect();
  }
};

const ensureSubscriptionActive = (subscription: Subscription) => {
  if (subscription.state === SubscriptionState.Unsubscribed) {
    subscription.subscribe();
  }
};

const createSubscription = (channel: string) => {
  const subscription = getClient().newSubscription(channel, {
    getToken: ({ channel: targetChannel }: SubscriptionTokenContext) =>
      fetchSubscriptionToken(targetChannel),
    joinLeave: channel.startsWith("campaign:"),
    recoverable: true,
  });

  subscription.on("publication", (ctx) => {
    dispatchToChannel(channel, (handlers, publication) => {
      handlers.onPublication?.(publication.data, publication);
    }, ctx);
  });

  subscription.on("join", (ctx) => {
    dispatchToChannel(channel, (handlers, join) => {
      handlers.onJoin?.(toPresenceMember(join.info.client, join.info), join);
    }, ctx);
  });

  subscription.on("leave", (ctx) => {
    dispatchToChannel(channel, (handlers, leave) => {
      handlers.onLeave?.(toPresenceMember(leave.info.client, leave.info), leave);
    }, ctx);
  });

  subscription.on("subscribed", (ctx) => {
    logRealtime("info", "subscribed", {
      channel,
      recovered: ctx.wasRecovering,
      positioned: ctx.positioned,
      recoverable: ctx.recoverable,
      streamPosition: ctx.streamPosition,
    });
    dispatchToChannel(channel, (handlers, subscribed) => {
      handlers.onSubscribed?.(subscribed);
    }, ctx);
  });

  subscription.on("subscribing", (ctx) => {
    logRealtime("info", "subscribing", {
      channel,
      code: ctx.code,
      reason: ctx.reason,
    });
    dispatchToChannel(channel, (handlers, subscribing) => {
      handlers.onSubscribing?.(subscribing);
    }, ctx);
  });

  subscription.on("unsubscribed", (ctx) => {
    logRealtime("warn", "unsubscribed", {
      channel,
      code: ctx.code,
      reason: ctx.reason,
    });
    dispatchToChannel(channel, (handlers, unsubscribed) => {
      handlers.onUnsubscribed?.(unsubscribed);
    }, ctx);
  });

  subscription.on("error", (ctx) => {
    logRealtime("error", "subscription error", {
      channel,
      error: ctx.error,
    });
    dispatchToChannel(channel, (handlers, error) => {
      handlers.onError?.(error);
    }, ctx);
  });

  return subscription;
};

const releaseChannelListener = (channel: string, listenerId: number) => {
  const entry = channelEntries.get(channel);
  if (!entry) {
    return;
  }

  entry.listeners.delete(listenerId);
  if (entry.listeners.size > 0) {
    return;
  }

  entry.subscription.unsubscribe();
  entry.subscription.removeAllListeners();
  getClient().removeSubscription(entry.subscription);
  channelEntries.delete(channel);

  if (channelEntries.size === 0) {
    scheduleDisconnectIfIdle();
  }
};

export const subscribe = (channel: string, handlers: SubscriptionHandlers) => {
  let entry = channelEntries.get(channel);
  if (!entry) {
    entry = {
      listeners: new Map(),
      subscription: createSubscription(channel),
    };
    channelEntries.set(channel, entry);
  }

  const listenerId = nextListenerId++;
  entry.listeners.set(listenerId, handlers);
  ensureSubscriptionActive(entry.subscription);
  ensureClientConnected();

  if (entry.subscription.state === SubscriptionState.Subscribed) {
    Promise.resolve().then(() => {
      const currentEntry = channelEntries.get(channel);
      if (!currentEntry?.listeners.has(listenerId)) {
        return;
      }
      handlers.onSubscribed?.({ channel } as SubscribedContext);
    });
  }

  return () => {
    releaseChannelListener(channel, listenerId);
  };
};

export const unsubscribe = (channel: string) => {
  const entry = channelEntries.get(channel);
  if (!entry) {
    return;
  }
  [...entry.listeners.keys()].forEach((listenerId) => {
    releaseChannelListener(channel, listenerId);
  });
};

export const subscribeConnectionState = (listener: ConnectionStateListener) => {
  connectionStateListeners.add(listener);
  listener(currentConnectionState);
  return () => {
    connectionStateListeners.delete(listener);
  };
};

export const getPresence = async (channel: string) => {
  const entry = channelEntries.get(channel);
  const result = entry
    ? await entry.subscription.presence()
    : await getClient().presence(channel);
  return Object.fromEntries(
    Object.entries(result.clients).map(([clientId, info]) => [
      clientId,
      toPresenceMember(clientId, info),
    ]),
  );
};

export const getHistory = async (channel: string, limit = 20) => {
  const entry = channelEntries.get(channel);
  const result = entry
    ? await entry.subscription.history({ limit })
    : await getClient().history(channel, { limit });
  return (result.publications ?? []).map((publication) => ({
    data: publication.data,
    offset: publication.offset,
  })) as RealtimeHistoryPublication[];
};

export const disconnectRealtime = () => {
  clearPendingDisconnect();
  if (!client) {
    notifyConnectionState("offline");
    return;
  }

  channelEntries.forEach((entry) => {
    entry.subscription.unsubscribe();
    entry.subscription.removeAllListeners();
    client?.removeSubscription(entry.subscription);
  });
  channelEntries.clear();
  connectionRequested = false;
  reconnectStartedAt = null;
  client.disconnect();
  notifyConnectionState("offline");
};
