import type { RoleMode } from "../types/role";
import { http } from "./http";

type AuthResponse = { token: string };
type MeResponse = {
  userId: string;
  username: string;
  displayName?: string | null;
  role: RoleMode;
};

export const authRepo = {
  register: (payload: {
    username: string;
    pin: string;
    displayName?: string;
    role: RoleMode;
  }) =>
    http.post<AuthResponse>("/auth/register", payload),
  login: (payload: { username: string; pin: string }) =>
    http.post<AuthResponse>("/auth/login", payload),
  me: () => http.get<MeResponse>("/auth/me"),
};
