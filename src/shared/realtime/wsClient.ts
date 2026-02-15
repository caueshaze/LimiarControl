type MessageHandler = (message: unknown) => void;
type StateHandler = (state: ConnectionState) => void;

export type ConnectionState = "connected" | "reconnecting" | "offline";

type OutgoingMessage = {
  type: string;
  payload?: unknown;
};

class WsClient {
  private socket: WebSocket | null = null;
  private listeners = new Set<MessageHandler>();
  private stateListeners = new Set<StateHandler>();
  private reconnectAttempts = 0;
  private closedManually = false;

  constructor(private url: string) {}

  connect() {
    this.closedManually = false;
    this.socket = new WebSocket(this.url);
    this.socket.onopen = () => {
      this.reconnectAttempts = 0;
      this.emitState("connected");
    };
    this.socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.listeners.forEach((listener) => listener(data));
      } catch {
        // ignore malformed messages
      }
    };
    this.socket.onclose = () => {
      if (this.closedManually) {
        this.emitState("offline");
        return;
      }
      this.scheduleReconnect();
    };
    this.socket.onerror = () => {
      // rely on close event for reconnect
    };
  }

  send(message: OutgoingMessage) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      return false;
    }
    this.socket.send(JSON.stringify(message));
    return true;
  }

  onMessage(handler: MessageHandler) {
    this.listeners.add(handler);
    return () => this.listeners.delete(handler);
  }

  onStateChange(handler: StateHandler) {
    this.stateListeners.add(handler);
    return () => this.stateListeners.delete(handler);
  }

  close() {
    this.closedManually = true;
    this.socket?.close();
  }

  private emitState(state: ConnectionState) {
    this.stateListeners.forEach((handler) => handler(state));
  }

  private scheduleReconnect() {
    if (this.reconnectAttempts >= 5) {
      this.emitState("offline");
      return;
    }
    this.reconnectAttempts += 1;
    this.emitState("reconnecting");
    const delay = Math.min(1000 * 2 ** (this.reconnectAttempts - 1), 10000);
    window.setTimeout(() => {
      if (this.closedManually) {
        return;
      }
      this.connect();
    }, delay);
  }
}

const getWsUrl = (path: string, token?: string | null) => {
  const baseUrl = import.meta.env.VITE_API_BASE_URL;
  if (!baseUrl) {
    throw new Error("Missing API base URL");
  }
  const url = new URL(baseUrl);
  const protocol = url.protocol === "https:" ? "wss:" : "ws:";
  const host = url.host;
  const wsUrl = new URL(`${protocol}//${host}${path}`);
  if (token) {
    wsUrl.searchParams.set("token", token);
  }
  return wsUrl.toString();
};

export const connect = (sessionId: string, token?: string | null) => {
  const url = getWsUrl(`/ws/sessions/${sessionId}`, token);
  const client = new WsClient(url);
  client.connect();
  return client;
};

export const connectCampaign = (campaignId: string, token?: string | null) => {
  const url = getWsUrl(`/ws/campaigns/${campaignId}`, token);
  const client = new WsClient(url);
  client.connect();
  return client;
};
