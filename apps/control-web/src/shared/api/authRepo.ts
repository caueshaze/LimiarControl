import type { RoleMode } from "../types/role";
import { http } from "./http";

type AuthResponse = { token: string };
export type MeResponse = {
  userId: string;
  username: string;
  displayName?: string | null;
  role: RoleMode;
  isSystemAdmin: boolean;
  avatarUrl?: string | null;
  tokenColor?: string | null;
  tokenImageUrl?: string | null;
  onboardedAt?: string | null;
};

export type UpdateProfileRequest = {
  displayName?: string;
  avatarUrl?: string | null;
  tokenColor?: string | null;
  tokenImageUrl?: string | null;
  markOnboarded?: boolean;
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
  updateProfile: (payload: UpdateProfileRequest) =>
    http.patch<MeResponse>("/auth/me/profile", payload),
};
