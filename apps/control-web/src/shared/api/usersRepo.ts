import { http } from "./http";

export type UserSearchResult = {
  id: string;
  displayName: string;
  username: string;
};

export type UserProfile = {
  id: string;
  displayName: string;
  username: string;
  avatarUrl?: string | null;
  tokenColor?: string | null;
  tokenImageUrl?: string | null;
  preferredWorkspaceMode?: "GM" | "PLAYER" | null;
};

export const usersRepo = {
  search: (query: string) =>
  http.get<UserSearchResult[]>(`/users/search?q=${encodeURIComponent(query)}`),
  getProfile: (userId: string) =>
    http.get<UserProfile>(`/users/${userId}/profile`),
};
