export type Session = {
  id: string;
  campaignId: string;
  number: number;
  title: string;
  joinCode?: string | null;
  status?: "ACTIVE" | "CLOSED";
  isActive?: boolean;
  startedAt?: string | null;
  endedAt?: string | null;
  durationSeconds?: number;
  createdAt: string;
  updatedAt?: string | null;
};
