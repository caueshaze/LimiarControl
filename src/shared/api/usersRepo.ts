import { http } from "./http";

export type UserSearchResult = {
  id: string;
  displayName: string;
  username: string;
};

export const usersRepo = {
  search: (query: string) =>
    http.get<UserSearchResult[]>(`/users/search?q=${encodeURIComponent(query)}`),
};
