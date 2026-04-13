import { http } from "./http";

type Preferences = {
  selectedCampaignId: string | null;
};

export const preferencesRepo = {
  get: () => http.get<Preferences>("/preferences"),
  update: (payload: Preferences) => http.put<Preferences>("/preferences", payload),
};
