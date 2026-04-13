import { http } from "./http";

type ConnectionTokenResponse = {
  token: string;
};

type SubscribeTokenResponse = {
  token: string;
};

export const centrifugoRepo = {
  connectionToken: () =>
    http.post<ConnectionTokenResponse>("/centrifugo/connection-token", {}),
  subscribeToken: (payload: { channel: string }) =>
    http.post<SubscribeTokenResponse>("/centrifugo/subscribe", payload),
};
